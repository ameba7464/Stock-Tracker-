#!/usr/bin/env python3
"""
Проверка колонок с данными о складах в Google Sheets
"""

from stock_tracker.utils.config import get_config
from stock_tracker.database.operations import SheetsOperations
import pprint

def check_warehouse_columns():
    """Проверяет наличие и содержимое колонок F, G, H с данными о складах"""
    
    print("\n" + "="*80)
    print("🔍 ПРОВЕРКА КОЛОНОК СО СКЛАДАМИ В GOOGLE SHEETS")
    print("="*80 + "\n")
    
    # Load config
    config = get_config()
    
    # Connect to Google Sheets
    print(f"📊 Подключение к таблице: {config.google_sheets.sheet_id}")
    operations = SheetsOperations(config)
    
    # Open worksheet
    worksheet = operations.get_or_create_worksheet(
        config.google_sheets.sheet_id,
        "Stock Tracker"
    )
    
    # Get all data
    all_data = worksheet.get_all_values()
    
    print(f"✅ Загружено {len(all_data)} строк\n")
    
    # Check header row
    if len(all_data) > 0:
        headers = all_data[0]
        print("📋 Заголовки таблицы:")
        for i, header in enumerate(headers):
            col_letter = chr(ord('A') + i)
            print(f"   {col_letter}: {header}")
        
        print()
        
        # Check for warehouse columns
        expected_warehouse_cols = {
            'F': 'Название склада',
            'G': 'Заказы со склада',
            'H': 'Остатки на складе'
        }
        
        print("🔍 Проверка наличия колонок со складами:")
        for col_index, expected_name in expected_warehouse_cols.items():
            col_num = ord(col_index) - ord('A')
            if col_num < len(headers):
                actual_name = headers[col_num]
                match = "✅" if expected_name.lower() in actual_name.lower() else "❌"
                print(f"   {match} Колонка {col_index}: ожидали '{expected_name}', есть '{actual_name}'")
            else:
                print(f"   ❌ Колонка {col_index}: НЕ НАЙДЕНА (таблица имеет только {len(headers)} колонок)")
    
    print()
    
    # Check first few data rows
    if len(all_data) > 1:
        print("📦 Проверка первых 3 продуктов:")
        print()
        
        for row_idx in range(1, min(4, len(all_data))):
            row = all_data[row_idx]
            
            # Ensure row has enough columns
            while len(row) < 8:
                row.append("")
            
            seller_article = row[0] if len(row) > 0 else "N/A"
            nm_id = row[1] if len(row) > 1 else "N/A"
            total_orders = row[2] if len(row) > 2 else "N/A"
            total_stock = row[3] if len(row) > 3 else "N/A"
            
            warehouse_names = row[5] if len(row) > 5 else ""
            warehouse_orders = row[6] if len(row) > 6 else ""
            warehouse_stock = row[7] if len(row) > 7 else ""
            
            print(f"   Продукт #{row_idx}: {seller_article} (NM: {nm_id})")
            print(f"   Всего: Orders={total_orders}, Stock={total_stock}")
            print()
            print(f"   Колонка F (Название склада):")
            if warehouse_names:
                wh_names = warehouse_names.split('\n')
                for i, name in enumerate(wh_names, 1):
                    print(f"      {i}. {name}")
            else:
                print(f"      ❌ ПУСТО!")
            
            print(f"   Колонка G (Заказы со склада):")
            if warehouse_orders:
                wh_orders = warehouse_orders.split('\n')
                for i, orders in enumerate(wh_orders, 1):
                    print(f"      {i}. {orders}")
            else:
                print(f"      ❌ ПУСТО!")
            
            print(f"   Колонка H (Остатки на складе):")
            if warehouse_stock:
                wh_stock = warehouse_stock.split('\n')
                for i, stock in enumerate(wh_stock, 1):
                    print(f"      {i}. {stock}")
            else:
                print(f"      ❌ ПУСТО!")
            
            print(f"   " + "-"*70)
            print()
    
    print("="*80)
    print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
    print("="*80 + "\n")


if __name__ == "__main__":
    check_warehouse_columns()
