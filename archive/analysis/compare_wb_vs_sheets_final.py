#!/usr/bin/env python3
"""
Финальное сравнение данных Wildberries CSV vs Google Sheets (после внедрения Dual API)
"""

import csv
from collections import defaultdict
import re

def parse_number(value):
    """Парсит числа с пробелами и запятыми"""
    if not value:
        return 0
    # Убираем пробелы и заменяем запятую на точку
    cleaned = str(value).replace(' ', '').replace(',', '.')
    try:
        return int(float(cleaned))
    except:
        return 0

def normalize_warehouse_name(name):
    """Нормализует название склада"""
    if not name:
        return ""
    name = name.strip()
    # Маркетплейс -> Fulllog FBS
    if "маркетплейс" in name.lower():
        return "Маркетплейс/FBS"
    # Обухово -> Обухово МП
    if "обухово" in name.lower():
        return "Обухово МП"
    return name

def load_wb_data(csv_path):
    """Загружает данные из CSV Wildberries"""
    products = defaultdict(lambda: {
        'total_stock': 0,
        'total_orders': 0,
        'warehouses': {}
    })
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        # Пропускаем первую строку (заголовок категории)
        next(f)
        
        reader = csv.DictReader(f)
        
        for row in reader:
            seller_article = row['Артикул продавца'].strip()
            if not seller_article:
                continue
            
            warehouse = normalize_warehouse_name(row['Склад'])
            stock = parse_number(row['Остатки на текущий день, шт'])
            orders = parse_number(row['Заказали, шт'])
            
            # Суммируем остатки и заказы
            products[seller_article]['total_stock'] += stock
            products[seller_article]['total_orders'] += orders
            
            # Детализация по складам
            if warehouse:
                if warehouse not in products[seller_article]['warehouses']:
                    products[seller_article]['warehouses'][warehouse] = {
                        'stock': 0,
                        'orders': 0
                    }
                products[seller_article]['warehouses'][warehouse]['stock'] += stock
                products[seller_article]['warehouses'][warehouse]['orders'] += orders
    
    return products

def load_sheets_data(csv_path):
    """Загружает данные из Google Sheets CSV"""
    products = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            seller_article = row['Артикул продавца'].strip()
            if not seller_article:
                continue
            
            total_stock = parse_number(row['Остатки (всего)'])
            total_orders = parse_number(row['Заказы (всего)'])
            
            # Парсим склады (многострочные ячейки)
            warehouse_names = row['Название склада'].split('\n')
            warehouse_stocks = row['Остатки на складе'].split('\n')
            warehouse_orders = row['Заказы со склада'].split('\n')
            
            warehouses = {}
            for i in range(len(warehouse_names)):
                wh_name = warehouse_names[i].strip() if i < len(warehouse_names) else ""
                wh_stock = parse_number(warehouse_stocks[i]) if i < len(warehouse_stocks) else 0
                wh_orders = parse_number(warehouse_orders[i]) if i < len(warehouse_orders) else 0
                
                if wh_name:
                    # Нормализуем для сравнения
                    normalized_name = normalize_warehouse_name(wh_name)
                    warehouses[normalized_name] = {
                        'stock': wh_stock,
                        'orders': wh_orders
                    }
            
            products[seller_article] = {
                'total_stock': total_stock,
                'total_orders': total_orders,
                'warehouses': warehouses
            }
    
    return products

def compare_data(wb_data, sheets_data):
    """Сравнивает данные WB и Sheets"""
    
    print("\n" + "="*100)
    print("📊 ФИНАЛЬНОЕ СРАВНЕНИЕ: WILDBERRIES CSV vs GOOGLE SHEETS (после Dual API)")
    print("="*100 + "\n")
    
    # Все артикулы
    all_articles = sorted(set(list(wb_data.keys()) + list(sheets_data.keys())))
    
    total_discrepancies = 0
    perfect_matches = 0
    
    for article in all_articles:
        wb = wb_data.get(article, {'total_stock': 0, 'total_orders': 0, 'warehouses': {}})
        sheets = sheets_data.get(article, {'total_stock': 0, 'total_orders': 0, 'warehouses': {}})
        
        wb_stock = wb['total_stock']
        sheets_stock = sheets['total_stock']
        stock_diff = sheets_stock - wb_stock
        
        wb_orders = wb['total_orders']
        sheets_orders = sheets['total_orders']
        orders_diff = sheets_orders - wb_orders
        
        # Определяем статус
        if stock_diff == 0 and orders_diff == 0:
            status = "✅ ИДЕАЛЬНО"
            perfect_matches += 1
        elif abs(stock_diff) <= 10:
            status = "⚠️ МИНИМАЛЬНОЕ РАСХОЖДЕНИЕ"
        else:
            status = "❌ РАСХОЖДЕНИЕ"
            total_discrepancies += 1
        
        print(f"{status} {article}")
        print(f"  Остатки:")
        print(f"    WB:     {wb_stock:>6} шт")
        print(f"    Sheets: {sheets_stock:>6} шт")
        if stock_diff != 0:
            sign = "+" if stock_diff > 0 else ""
            percent = (stock_diff / wb_stock * 100) if wb_stock > 0 else 0
            print(f"    Разница: {sign}{stock_diff:>5} шт ({sign}{percent:>.1f}%)")
        
        print(f"  Заказы:")
        print(f"    WB:     {wb_orders:>6} шт")
        print(f"    Sheets: {sheets_orders:>6} шт")
        if orders_diff != 0:
            sign = "+" if orders_diff > 0 else ""
            print(f"    Разница: {sign}{orders_diff:>5} шт")
        
        # Сравнение складов (только для товаров с расхождениями)
        if stock_diff != 0 or orders_diff != 0:
            print(f"  Детализация по складам:")
            
            all_warehouses = sorted(set(list(wb['warehouses'].keys()) + list(sheets['warehouses'].keys())))
            
            for wh in all_warehouses:
                wb_wh = wb['warehouses'].get(wh, {'stock': 0, 'orders': 0})
                sheets_wh = sheets['warehouses'].get(wh, {'stock': 0, 'orders': 0})
                
                wh_stock_diff = sheets_wh['stock'] - wb_wh['stock']
                
                if wh_stock_diff != 0 or wb_wh['stock'] > 0 or sheets_wh['stock'] > 0:
                    diff_marker = ""
                    if wh_stock_diff != 0:
                        diff_marker = f" ({'+' if wh_stock_diff > 0 else ''}{wh_stock_diff})"
                    
                    print(f"    {wh:30s}: WB={wb_wh['stock']:>4}, Sheets={sheets_wh['stock']:>4}{diff_marker}")
        
        print()
    
    print("="*100)
    print(f"📈 ИТОГОВАЯ СТАТИСТИКА:")
    print(f"  Всего продуктов: {len(all_articles)}")
    print(f"  ✅ Идеальное совпадение: {perfect_matches}")
    print(f"  ❌ С расхождениями: {total_discrepancies}")
    print(f"  📊 Точность: {(perfect_matches / len(all_articles) * 100):.1f}%")
    print("="*100 + "\n")
    
    # Проверка наличия складов Маркетплейс/FBS
    print("="*100)
    print("🏪 ПРОВЕРКА НАЛИЧИЯ FBS СКЛАДОВ В SHEETS:")
    print("="*100 + "\n")
    
    for article in all_articles:
        sheets = sheets_data.get(article, {'warehouses': {}})
        
        fbs_warehouses = [wh for wh in sheets['warehouses'].keys() 
                         if 'fbs' in wh.lower() or 'маркетплейс' in wh.lower() or 'fulllog' in wh.lower()]
        
        if fbs_warehouses:
            fbs_stock = sum(sheets['warehouses'][wh]['stock'] for wh in fbs_warehouses)
            print(f"✅ {article}: FBS склады найдены ({', '.join(fbs_warehouses)}), остатки: {fbs_stock} шт")
        else:
            print(f"❌ {article}: FBS склады НЕ найдены")
    
    print("\n" + "="*100)

if __name__ == "__main__":
    wb_csv = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export (1).csv"
    sheets_csv = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (7).csv"
    
    print("📥 Загрузка данных...")
    wb_data = load_wb_data(wb_csv)
    sheets_data = load_sheets_data(sheets_csv)
    
    print(f"✅ WB: загружено {len(wb_data)} продуктов")
    print(f"✅ Sheets: загружено {len(sheets_data)} продуктов")
    
    compare_data(wb_data, sheets_data)
