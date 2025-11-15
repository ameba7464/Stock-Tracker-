#!/usr/bin/env python3
"""Analyze Its1_2_3/50g stocks from CSV export"""

import csv

def main():
    total_stock = 0
    warehouse_stocks = []
    
    print("\n" + "="*60)
    print("📊 Остатки Its1_2_3/50g по складам (из CSV)")
    print("="*60)
    
    with open('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row.get('Артикул продавца', '') == 'Its1_2_3/50g':
                warehouse = row.get('Склад', 'Unknown')
                stock_str = row.get('Остатки на текущий день, шт', '0').strip()
                stock_int = int(stock_str) if stock_str.isdigit() else 0
                
                total_stock += stock_int
                if stock_int > 0:
                    warehouse_stocks.append((warehouse, stock_int))
    
    # Sort by stock descending
    warehouse_stocks.sort(key=lambda x: x[1], reverse=True)
    
    for warehouse, stock in warehouse_stocks:
        print(f"{warehouse:35} - {stock:>5} шт")
    
    print("="*60)
    print(f"ИТОГО ОСТАТКОВ: {total_stock} шт")
    print("="*60)
    
    print("\n⚠️ В API показано: 475 шт")
    print(f"✅ В CSV показано: {total_stock} шт")
    
    if total_stock > 475:
        diff = total_stock - 475
        percent = (diff / total_stock * 100)
        print(f"\n❌ РАСХОЖДЕНИЕ: {diff} шт ({percent:.1f}%)")
        print("\n💡 Вероятная причина:")
        print("   API возвращает quantityNotInOrders (свободные)")
        print("   CSV показывает quantityNotInOrders + quantityInOrders (все)")

if __name__ == "__main__":
    main()
