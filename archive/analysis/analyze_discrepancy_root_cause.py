#!/usr/bin/env python3
"""
Анализ первопричины расхождений данных между CSV WB и Google Sheets.
Проверяем всю цепочку обработки данных.
"""

import sys
import os
import csv
from collections import defaultdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.core.calculator import is_real_warehouse


def analyze_csv_warehouses(csv_file):
    """Анализ складов в CSV от Wildberries."""
    print("\n" + "="*100)
    print("📊 ШАГ 1: АНАЛИЗ CSV ФАЙЛА ОТ WILDBERRIES")
    print("="*100)
    
    products = defaultdict(lambda: {
        'total_orders': 0,
        'total_stock': 0,
        'warehouses': defaultdict(lambda: {'orders': 0, 'stock': 0})
    })
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        # Пропускаем первую строку (заголовок отчета)
        f.readline()
        reader = csv.DictReader(f)
        
        for row in reader:
            article = row['Артикул продавца']
            wb_article = row['Артикул WB']
            warehouse = row['Склад']
            
            # Парсим числовые значения
            try:
                orders = int(row['Заказали, шт']) if row['Заказали, шт'] else 0
            except:
                orders = 0
                
            try:
                stock = int(row['Остатки на текущий день, шт']) if row['Остатки на текущий день, шт'] else 0
            except:
                stock = 0
            
            # Агрегируем по товару
            products[article]['wb_article'] = wb_article
            products[article]['total_orders'] += orders
            products[article]['total_stock'] += stock
            products[article]['warehouses'][warehouse]['orders'] += orders
            products[article]['warehouses'][warehouse]['stock'] += stock
    
    print(f"\n✅ Загружено {len(products)} уникальных товаров из CSV")
    
    # Анализ по первым 3 товарам
    for article in list(products.keys())[:3]:
        data = products[article]
        print(f"\n📦 {article} (WB: {data['wb_article']})")
        print(f"   ИТОГО: Заказы={data['total_orders']}, Остатки={data['total_stock']}")
        print(f"   Складов: {len(data['warehouses'])}")
        
        # Детали по складам
        for wh_name, wh_data in sorted(data['warehouses'].items(), 
                                       key=lambda x: x[1]['stock'], 
                                       reverse=True):
            is_real = is_real_warehouse(wh_name)
            status = "✅ ВКЛЮЧЕН" if is_real else "❌ ОТФИЛЬТРОВАН"
            
            print(f"   - {wh_name}: Заказы={wh_data['orders']}, Остатки={wh_data['stock']} [{status}]")
    
    return products


def analyze_google_sheets_data(sheets_csv):
    """Анализ данных из Google Sheets."""
    print("\n" + "="*100)
    print("📊 ШАГ 2: АНАЛИЗ ДАННЫХ ИЗ GOOGLE SHEETS")
    print("="*100)
    
    products = {}
    
    with open(sheets_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            article = row['Артикул продавца']
            wb_article = row['Артикул товара']
            
            try:
                total_orders = int(row['Заказы (всего)'])
            except:
                total_orders = 0
                
            try:
                total_stock = int(row['Остатки (всего)'])
            except:
                total_stock = 0
            
            # Парсим склады (многострочные ячейки разделены \n)
            warehouse_names = row['Название склада'].split('\n')
            warehouse_orders = row['Заказы со склада'].split('\n')
            warehouse_stocks = row['Остатки на складе'].split('\n')
            
            warehouses = {}
            for i, name in enumerate(warehouse_names):
                if name.strip():
                    try:
                        orders = int(warehouse_orders[i]) if i < len(warehouse_orders) else 0
                    except:
                        orders = 0
                    try:
                        stock = int(warehouse_stocks[i]) if i < len(warehouse_stocks) else 0
                    except:
                        stock = 0
                    warehouses[name.strip()] = {'orders': orders, 'stock': stock}
            
            products[article] = {
                'wb_article': wb_article,
                'total_orders': total_orders,
                'total_stock': total_stock,
                'warehouses': warehouses
            }
    
    print(f"\n✅ Загружено {len(products)} товаров из Google Sheets")
    
    # Анализ по первым 3 товарам
    for article in list(products.keys())[:3]:
        data = products[article]
        print(f"\n📦 {article} (WB: {data['wb_article']})")
        print(f"   ИТОГО: Заказы={data['total_orders']}, Остатки={data['total_stock']}")
        print(f"   Складов: {len(data['warehouses'])}")
        
        for wh_name, wh_data in sorted(data['warehouses'].items(), 
                                       key=lambda x: x[1]['stock'], 
                                       reverse=True):
            print(f"   - {wh_name}: Заказы={wh_data['orders']}, Остатки={wh_data['stock']}")
    
    return products


def compare_data(wb_products, sheets_products):
    """Сравнение данных и поиск расхождений."""
    print("\n" + "="*100)
    print("🔍 ШАГ 3: СРАВНЕНИЕ ДАННЫХ И ПОИСК РАСХОЖДЕНИЙ")
    print("="*100)
    
    for article in list(wb_products.keys())[:3]:
        wb_data = wb_products[article]
        sheets_data = sheets_products.get(article)
        
        if not sheets_data:
            print(f"\n❌ {article}: НЕТ В GOOGLE SHEETS!")
            continue
        
        print(f"\n📦 {article}")
        print(f"   WB CSV:     Заказы={wb_data['total_orders']}, Остатки={wb_data['total_stock']}")
        print(f"   Sheets:     Заказы={sheets_data['total_orders']}, Остатки={sheets_data['total_stock']}")
        
        # Проверяем расхождения
        orders_diff = wb_data['total_orders'] - sheets_data['total_orders']
        stock_diff = wb_data['total_stock'] - sheets_data['total_stock']
        
        if orders_diff != 0 or stock_diff != 0:
            print(f"   ⚠️ РАСХОЖДЕНИЕ: Заказы {orders_diff:+d}, Остатки {stock_diff:+d}")
        else:
            print(f"   ✅ Данные совпадают")
        
        # Анализ складов
        wb_warehouses = set(wb_data['warehouses'].keys())
        sheets_warehouses = set(sheets_data['warehouses'].keys())
        
        # Склады только в WB CSV
        only_in_wb = wb_warehouses - sheets_warehouses
        if only_in_wb:
            print(f"\n   🚨 СКЛАДЫ ТОЛЬКО В WB CSV (НЕ СИНХРОНИЗИРОВАНЫ):")
            for wh in only_in_wb:
                wh_data = wb_data['warehouses'][wh]
                is_real = is_real_warehouse(wh)
                status = "должен был быть включен" if is_real else "правильно отфильтрован"
                
                print(f"      - {wh}: Заказы={wh_data['orders']}, Остатки={wh_data['stock']}")
                print(f"        is_real_warehouse() = {is_real} ({status})")
        
        # Склады только в Sheets
        only_in_sheets = sheets_warehouses - wb_warehouses
        if only_in_sheets:
            print(f"\n   ℹ️ Склады только в Google Sheets:")
            for wh in only_in_sheets:
                wh_data = sheets_data['warehouses'][wh]
                print(f"      - {wh}: Заказы={wh_data['orders']}, Остатки={wh_data['stock']}")
        
        # Общие склады с расхождениями
        common = wb_warehouses & sheets_warehouses
        if common:
            print(f"\n   📊 Общие склады:")
            for wh in common:
                wb_wh = wb_data['warehouses'][wh]
                sheets_wh = sheets_data['warehouses'][wh]
                
                orders_match = "✅" if wb_wh['orders'] == sheets_wh['orders'] else "❌"
                stock_match = "✅" if wb_wh['stock'] == sheets_wh['stock'] else "❌"
                
                print(f"      - {wh}:")
                print(f"        WB:     Заказы={wb_wh['orders']} {orders_match}, Остатки={wb_wh['stock']} {stock_match}")
                print(f"        Sheets: Заказы={sheets_wh['orders']}, Остатки={sheets_wh['stock']}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    
    wb_csv = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export (1).csv"
    sheets_csv = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (5).csv"
    
    print("ANALIZ RASHOZHDENIY DANNYKH")
    print("="*100)
    
    # Шаг 1: Анализ CSV от WB
    wb_products = analyze_csv_warehouses(wb_csv)
    
    # Шаг 2: Анализ Google Sheets
    sheets_products = analyze_google_sheets_data(sheets_csv)
    
    # Шаг 3: Сравнение
    compare_data(wb_products, sheets_products)
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print("="*100)
