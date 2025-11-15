#!/usr/bin/env python3
"""
Compare CSV warehouses vs API warehouses to find the missing "Маркетплейс"
"""

import csv

def main():
    print("\n" + "="*100)
    print("🔍 СРАВНЕНИЕ: CSV склады vs API склады для Its1_2_3/50g")
    print("="*100)
    
    # Parse CSV to get all warehouses
    csv_warehouses = {}
    
    with open('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row.get('Артикул продавца', '') == 'Its1_2_3/50g':
                warehouse = row.get('Склад', 'Unknown')
                stock_str = row.get('Остатки на текущий день, шт', '0').strip()
                stock_int = int(stock_str) if stock_str.isdigit() else 0
                
                if warehouse not in csv_warehouses:
                    csv_warehouses[warehouse] = 0
                csv_warehouses[warehouse] += stock_int
    
    # API warehouses from sync logs
    api_warehouses = {
        'Подольск 3': 0,  # orders=17, stock=0
        'Электросталь': 0,  # orders=20, stock=0
        'Екатеринбург - Перспективный 12': 0,  # orders=2, stock=0
        'Казань': 0,  # orders=8, stock=0
        'Обухово МП': 0,  # orders=67, stock=0 (FBS)
        'Самара (Новосемейкино)': 0,  # orders=1, stock=0
        'Воронеж': 0,  # orders=1, stock=0
        'Краснодар': 0,  # orders=1, stock=0
        'Рязань (Тюшевское)': 0,  # orders=1, stock=0
        # NOTE: According to sync logs, stock=475 was calculated
        # But we don't know which warehouses had the 475
    }
    
    print("\n📋 CSV СКЛАДЫ (из экспорта Wildberries):")
    print("-"*100)
    csv_total = 0
    for wh, stock in sorted(csv_warehouses.items(), key=lambda x: x[1], reverse=True):
        print(f"  {wh:40} {stock:>6,} шт")
        csv_total += stock
    print("-"*100)
    print(f"  {'ИТОГО (CSV)':40} {csv_total:>6,} шт")
    print("="*100)
    
    print("\n🖥️  API СКЛАДЫ (из логов синхронизации):")
    print("-"*100)
    for wh in sorted(api_warehouses.keys()):
        print(f"  {wh:40} {'???':>6} шт (stock unknown from logs)")
    print("-"*100)
    print(f"  {'ИТОГО (API)':40} {'475':>6} шт (from sync result)")
    print("="*100)
    
    # Find missing warehouses
    print("\n❌ СКЛАДЫ ИЗ CSV, КОТОРЫХ НЕТ В API:")
    print("-"*100)
    
    missing_stock = 0
    for csv_wh, stock in csv_warehouses.items():
        # Normalize names for comparison
        csv_wh_norm = csv_wh.lower().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        found = False
        for api_wh in api_warehouses.keys():
            api_wh_norm = api_wh.lower().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            if csv_wh_norm == api_wh_norm:
                found = True
                break
        
        if not found:
            print(f"  ⚠️  {csv_wh:40} {stock:>6,} шт")
            missing_stock += stock
    
    print("-"*100)
    print(f"  {'ИТОГО ОТСУТСТВУЕТ':40} {missing_stock:>6,} шт")
    print("="*100)
    
    # Analysis
    print("\n📊 КРИТИЧЕСКИЙ АНАЛИЗ:")
    print("="*100)
    
    if missing_stock > 0:
        percent = (missing_stock / csv_total * 100)
        print(f"\n❌ Склад 'Маркетплейс' с {missing_stock:,} шт ({percent:.1f}%) НЕ ВОЗВРАЩАЕТСЯ API")
        print("\n💡 ПРИЧИНЫ:")
        print("   1. API warehouse_remains НЕ включает виртуальные/транзитные склады")
        print("   2. 'Маркетплейс' = товары в пути к клиенту / в обработке")
        print("   3. Это FBS склад (Fulfillment by Seller)")
        
        print("\n🔧 ВОЗМОЖНЫЕ РЕШЕНИЯ:")
        print("\n   Вариант 1: Использовать другой API endpoint")
        print("   ✅ Искать /api/v2/stocks или /supplier/stocks")
        print("   ✅ Проверить документацию на наличие параметра includeTransit=true")
        
        print("\n   Вариант 2: Дополнить данные из orders API")
        print("   ⚠️  Проблема: orders показывают уже отгруженный товар, не остатки")
        
        print("\n   Вариант 3: Принять ограничение API")
        print("   ❌ Остатки будут неточные (минус 86%)")
        
        print("\n   Вариант 4: Использовать CSV импорт")
        print("   ✅ Точные данные из личного кабинета WB")
        print("   ❌ Требует ручного экспорта")
    else:
        print("\n✅ Все склады из CSV присутствуют в API")
        print("   → Проблема в другом (возможно в подсчете количества)")
    
    print("\n" + "="*100)
    print("🎯 РЕКОМЕНДАЦИЯ:")
    print("="*100)
    print("\nСклад 'Маркетплейс' - это виртуальный склад WB для товаров:")
    print("  - В пути к клиенту")
    print("  - В процессе комплектации")
    print("  - На FBS складах продавца")
    print("\nAPI warehouse_remains НЕ предоставляет эти данные.")
    print("Необходимо найти альтернативный endpoint или принять ограничение.")

if __name__ == "__main__":
    main()
