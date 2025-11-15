#!/usr/bin/env python3
"""Analyze Marketplace warehouse in CSV"""

import csv

with open('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    print("\n" + "="*100)
    print("📦 АНАЛИЗ СКЛАДА 'МАРКЕТПЛЕЙС' ИЗ CSV")
    print("="*100)
    
    marketplace_rows = [r for r in reader if r.get('Склад') == 'Маркетплейс' and r.get('Артикул продавца') == 'Its1_2_3/50g']
    
    if not marketplace_rows:
        print("\n❌ Записи 'Маркетплейс' не найдены")
    else:
        print(f"\n✅ Найдено записей: {len(marketplace_rows)}\n")
        
        for i, row in enumerate(marketplace_rows, 1):
            print(f"Запись #{i}:")
            print(f"  Доступность: {row.get('Доступность', '')}")
            print(f"  Остатки на текущий день: {row.get('Остатки на текущий день, шт', '0')} шт")
            print(f"  В пути к клиенту: {row.get('В пути к клиенту, шт', '0')} шт")
            print(f"  В пути от клиента: {row.get('В пути от клиента, шт', '0')} шт")
            print()
        
        total_stock = sum(int(r.get('Остатки на текущий день, шт', '0').strip() or '0') for r in marketplace_rows)
        total_to_client = sum(int(r.get('В пути к клиенту, шт', '0').strip() or '0') for r in marketplace_rows)
        total_from_client = sum(int(r.get('В пути от клиента, шт', '0').strip() or '0') for r in marketplace_rows)
        
        print("="*100)
        print(f"ИТОГО для 'Маркетплейс':")
        print(f"  Остатки: {total_stock:,} шт")
        print(f"  В пути к клиенту: {total_to_client:,} шт")
        print(f"  В пути от клиента: {total_from_client:,} шт")
        print("="*100)
        
        print("\n💡 ВЫВОД:")
        print(f"  Склад 'Маркетплейс' содержит {total_stock:,} шт остатков")
        print("  Это виртуальный склад, который НЕ возвращается в API!")
