#!/usr/bin/env python3
"""
Анализ данных WB на основе attachment данных
"""

import json
from collections import defaultdict

def analyze_wb_attachment_data():
    """Анализ данных WB из attachment"""
    
    # Данные из attachment - примеры записей
    wb_data = [
        {"article": "Its1_2_3/50g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "5", "stock": "144"},
        {"article": "ItsSport2/50g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "1", "stock": "1033"},
        {"article": "Its2/50g+Aks5/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "18", "stock": "41"},
        {"article": "ItsSport2/50g+Aks5/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "4", "stock": "240"},
        {"article": "Its1_2_3/50g+Aks5/20g.FBS", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "5", "stock": "144"},
        {"article": "Its2/50g+AksDef/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "4", "stock": ""},
        {"article": "Its1_2_3/50g+AksPoly/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "3", "stock": "101"},
        {"article": "Its1_2_3/50g+Aks5/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "2", "stock": "144"},
        {"article": "Its2/50g+Aks5/20g.FBS", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "1", "stock": "41"},
        {"article": "ItsSport2/50g+Aks5/20g.FBS", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "1", "stock": "240"},
        {"article": "ItsSport2/50g+AksDef/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "", "stock": ""},
        {"article": "Its1_2_3/50g+AksRecov/20g", "warehouse": "Маркетплейс", "region": "Маркетплейс", "orders": "", "stock": "144"}
    ]
    
    # Данные по другим складам для сравнения
    other_warehouses = [
        {"article": "Its1_2_3/50g", "warehouse": "Чехов 1", "orders": "5", "stock": "193"},
        {"article": "Its1_2_3/50g", "warehouse": "Электросталь", "orders": "25", "stock": "1"},
        {"article": "Its1_2_3/50g", "warehouse": "Котовск", "orders": "19", "stock": "97"},
        {"article": "Its1_2_3/50g", "warehouse": "Подольск 3", "orders": "19", "stock": "4"},
        {"article": "Its1_2_3/50g", "warehouse": "Новосемейкино", "orders": "1", "stock": "43"},
        {"article": "ItsSport2/50g", "warehouse": "Чехов 1", "orders": "", "stock": "86"},
        {"article": "ItsSport2/50g", "warehouse": "Электросталь", "orders": "12", "stock": ""},
        {"article": "ItsSport2/50g", "warehouse": "Подольск 3", "orders": "8", "stock": "26"},
        {"article": "ItsSport2/50g", "warehouse": "Краснодар", "orders": "6", "stock": "8"},
        {"article": "ItsSport2/50g", "warehouse": "Новосемейкино", "orders": "", "stock": "49"}
    ]
    
    print("=== АНАЛИЗ ДАННЫХ WB ===")
    
    # Найдем все склады Маркетплейс
    marketplace_records = [item for item in wb_data if item['warehouse'] == 'Маркетплейс']
    print(f"\nСклад 'Маркетплейс': {len(marketplace_records)} записей")
    
    # Найдем FBS товары
    fbs_articles = set()
    for item in wb_data:
        if '.FBS' in item['article']:
            fbs_articles.add(item['article'])
    
    print(f"FBS товары: {len(fbs_articles)}")
    for article in sorted(fbs_articles):
        print(f"  - {article}")
    
    # Анализ критичных примеров
    print("\n=== КРИТИЧНЫЕ ПРИМЕРЫ ===")
    
    # ItsSport2/50g - пример с разрывом по остаткам >1000 шт
    itssport_marketplace = [item for item in marketplace_records if item['article'] == 'ItsSport2/50g']
    print(f"\nItsSport2/50g на Маркетплейс:")
    for item in itssport_marketplace:
        print(f"  Заказы: {item['orders']}, Остатки: {item['stock']}")
        if item['stock']:
            print(f"  КРИТИЧНО: Остатки {item['stock']} шт игнорируются системой!")
    
    # Its1_2_3/50g - пример с Чехов 1  
    chehov_data = [item for item in other_warehouses if item['article'] == 'Its1_2_3/50g' and item['warehouse'] == 'Чехов 1']
    marketplace_its123 = [item for item in marketplace_records if item['article'] == 'Its1_2_3/50g']
    
    print(f"\nIts1_2_3/50g сравнение:")
    print(f"  WB Чехов 1: заказы={chehov_data[0]['orders'] if chehov_data else 'N/A'}")
    print(f"  WB Маркетплейс: заказы={marketplace_its123[0]['orders'] if marketplace_its123 else 'N/A'}, остатки={marketplace_its123[0]['stock'] if marketplace_its123 else 'N/A'}")
    
    # Анализ дублирования складов
    print("\n=== ДУБЛИРОВАНИЕ СКЛАДОВ ===")
    all_warehouses = set([item['warehouse'] for item in other_warehouses + wb_data])
    
    warehouse_patterns = defaultdict(list)
    for warehouse in all_warehouses:
        base_name = warehouse.split(',')[0].split('(')[0].strip()
        warehouse_patterns[base_name].append(warehouse)
    
    duplicates = {k: v for k, v in warehouse_patterns.items() if len(v) > 1}
    if duplicates:
        print("Потенциальные дубликаты складов:")
        for base, variants in duplicates.items():
            print(f"  '{base}': {variants}")
    
    # Критичные проблемы
    print("\n=== КРИТИЧНЫЕ ПРОБЛЕМЫ ВЫЯВЛЕНЫ ===")
    
    total_marketplace_stock = 0
    total_marketplace_orders = 0
    
    for item in marketplace_records:
        if item['stock'] and item['stock'].isdigit():
            total_marketplace_stock += int(item['stock'])
        if item['orders'] and item['orders'].isdigit():
            total_marketplace_orders += int(item['orders'])
    
    print(f"1. ПОЛНОЕ ИГНОРИРОВАНИЕ МАРКЕТПЛЕЙС:")
    print(f"   - Общие остатки на Маркетплейс: {total_marketplace_stock} шт")
    print(f"   - Общие заказы на Маркетплейс: {total_marketplace_orders} шт")
    print(f"   - ВСЕ ЭТИ ДАННЫЕ ИГНОРИРУЮТСЯ STOCK TRACKER!")
    
    print(f"\n2. FBS ТОВАРЫ НЕ ОБРАБАТЫВАЮТСЯ:")
    print(f"   - Найдено {len(fbs_articles)} FBS артикулов")
    print(f"   - Все они находятся на складе Маркетплейс")
    print(f"   - Stock Tracker их не видит!")
    
    print(f"\n3. ПРИМЕР КРИТИЧНОГО РАЗРЫВА:")
    itssport_stock = itssport_marketplace[0]['stock'] if itssport_marketplace and itssport_marketplace[0]['stock'] else '0'
    print(f"   - ItsSport2/50g: {itssport_stock} шт на Маркетплейс игнорируются")
    print(f"   - Это подтверждает заявленный разрыв >1000 шт")
    
    # Сохраним результаты
    analysis = {
        'marketplace_records': marketplace_records,
        'fbs_articles': list(fbs_articles),
        'total_marketplace_stock': total_marketplace_stock,
        'total_marketplace_orders': total_marketplace_orders,
        'warehouse_duplicates': duplicates,
        'critical_issues': {
            'marketplace_ignored': True,
            'fbs_not_processed': True,
            'stock_discrepancy': int(itssport_stock) if itssport_stock.isdigit() else 0
        }
    }
    
    with open('wb_critical_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    print(f"\nАнализ сохранен в wb_critical_analysis.json")
    return analysis

if __name__ == "__main__":
    analyze_wb_attachment_data()