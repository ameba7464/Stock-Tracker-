#!/usr/bin/env python3
"""
Collect ALL warehouse records for Its1_2_3/50g from Statistics API
"""

import requests
import json
from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    params = {'dateFrom': '2025-10-27'}
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    print("\n" + "="*100)
    print("📊 ПОЛНЫЙ АНАЛИЗ: Its1_2_3/50g по всем складам (Statistics API)")
    print("="*100)
    
    response = requests.get(url, headers=headers, params=params, timeout=30)
    data = response.json()
    
    # Find all records for Its1_2_3/50g
    records = [r for r in data if r.get('supplierArticle') == 'Its1_2_3/50g']
    
    print(f"\n✅ Найдено записей: {len(records)}")
    print("\n" + "-"*100)
    print(f"{'Склад':<40} {'quantity':<12} {'quantityFull':<15} {'inWayToClient':<15} {'inWayFromClient':<15}")
    print("-"*100)
    
    total_quantity = 0
    total_quantity_full = 0
    total_in_way_to = 0
    total_in_way_from = 0
    
    warehouse_data = []
    
    for record in records:
        warehouse = record.get('warehouseName', 'Unknown')
        qty = record.get('quantity', 0)
        qty_full = record.get('quantityFull', 0)
        in_way_to = record.get('inWayToClient', 0)
        in_way_from = record.get('inWayFromClient', 0)
        
        warehouse_data.append((warehouse, qty, qty_full, in_way_to, in_way_from))
        
        total_quantity += qty
        total_quantity_full += qty_full
        total_in_way_to += in_way_to
        total_in_way_from += in_way_from
    
    # Sort by quantity_full descending
    warehouse_data.sort(key=lambda x: x[2], reverse=True)
    
    for warehouse, qty, qty_full, in_way_to, in_way_from in warehouse_data:
        if qty > 0 or qty_full > 0 or in_way_to > 0 or in_way_from > 0:
            print(f"{warehouse:<40} {qty:<12,} {qty_full:<15,} {in_way_to:<15,} {in_way_from:<15,}")
    
    print("-"*100)
    print(f"{'ИТОГО:':<40} {total_quantity:<12,} {total_quantity_full:<15,} {total_in_way_to:<15,} {total_in_way_from:<15,}")
    print("="*100)
    
    # Analysis
    print("\n📊 АНАЛИЗ:")
    print("-"*100)
    print(f"quantity (свободные остатки):        {total_quantity:>6,} шт")
    print(f"quantityFull (полные остатки):       {total_quantity_full:>6,} шт")
    print(f"inWayToClient (в пути к клиенту):    {total_in_way_to:>6,} шт")
    print(f"inWayFromClient (в пути от клиента): {total_in_way_from:>6,} шт")
    print("-"*100)
    
    # Compare with CSV
    csv_total = 3478
    
    print(f"\n📋 СРАВНЕНИЕ С CSV:")
    print("-"*100)
    print(f"CSV экспорт:                         {csv_total:>6,} шт")
    print(f"Statistics API (quantity):           {total_quantity:>6,} шт")
    print(f"Statistics API (quantityFull):       {total_quantity_full:>6,} шт")
    print(f"Сумма всех полей:                    {total_quantity + total_quantity_full + total_in_way_to + total_in_way_from:>6,} шт")
    print("-"*100)
    
    # Which field matches?
    if abs(total_quantity_full - csv_total) < 100:
        print(f"\n✅ НАЙДЕНО! quantityFull ({total_quantity_full:,}) ≈ CSV ({csv_total:,})")
        print("   → Используем поле quantityFull для точных остатков")
    elif abs(total_quantity - csv_total) < 100:
        print(f"\n✅ НАЙДЕНО! quantity ({total_quantity:,}) ≈ CSV ({csv_total:,})")
        print("   → Используем поле quantity для точных остатков")
    else:
        diff_full = abs(total_quantity_full - csv_total)
        diff_qty = abs(total_quantity - csv_total)
        print(f"\n⚠️ Расхождение:")
        print(f"   quantityFull: разница {diff_full:,} шт ({diff_full/csv_total*100:.1f}%)")
        print(f"   quantity: разница {diff_qty:,} шт ({diff_qty/csv_total*100:.1f}%)")
    
    print("\n" + "="*100)
    print("🎯 РЕКОМЕНДАЦИЯ:")
    print("="*100)
    
    if total_quantity_full > 0 or total_quantity > 0:
        print("\n✅ Statistics API РАБОТАЕТ и возвращает данные!")
        print("\n💡 РЕШЕНИЕ:")
        print("   1. Переключиться с warehouse_remains на Statistics API")
        print("   2. Использовать поле 'quantityFull' для полных остатков")
        print("   3. Агрегировать данные по всем складам для каждого товара")
        print("\n📝 Изменения в коде:")
        print("   - Заменить client.download_warehouse_remains()")
        print("   - На requests.get('statistics-api.wildberries.ru/api/v1/supplier/stocks')")
        print("   - Группировать по supplierArticle и суммировать quantityFull")
    else:
        print("\n⚠️ Statistics API возвращает нули")
        print("   Возможно, нужен другой параметр dateFrom или другой endpoint")

if __name__ == "__main__":
    main()
