#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение данных из официальной статистики WB и таблицы Stock Tracker
"""

import csv
import re
from collections import defaultdict

def parse_number(value):
    """Парсинг числовых значений из строк"""
    if not value or value == '':
        return 0
    # Убираем пробелы и заменяем запятую на точку
    value = str(value).replace(' ', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0

def parse_turnover(value):
    """Парсинг оборачиваемости из формата '408д 8ч' в дни"""
    if not value or value == '' or value == '>999д':
        return None
    
    days = 0
    # Извлекаем дни
    days_match = re.search(r'(\d+)д', value)
    if days_match:
        days = int(days_match.group(1))
    
    # Извлекаем часы
    hours_match = re.search(r'(\d+)ч', value)
    if hours_match:
        hours = int(hours_match.group(1))
        days += hours / 24
    
    return days if days > 0 else None

def load_wb_data(filepath):
    """Загрузка данных из официальной статистики WB"""
    wb_data = defaultdict(lambda: {
        'orders': 0,
        'stock': 0,
        'turnover_days': [],
        'warehouses': set(),
        'article_name': ''
    })
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        # Пропускаем первую строку с заголовком отчета
        first_line = f.readline()
        reader = csv.DictReader(f)
        for row in reader:
            article = row['Артикул продавца']
            wb_article = row['Артикул WB']
            orders = parse_number(row.get('Заказали, шт', 0))
            stock = parse_number(row.get('Остатки на текущий день, шт', 0))
            turnover = parse_turnover(row.get('Оборачиваемость текущих остатков', ''))
            warehouse = row['Склад']
            
            # Агрегируем данные по артикулу продавца
            wb_data[article]['orders'] += orders
            wb_data[article]['stock'] += stock
            wb_data[article]['article_name'] = wb_article
            
            if turnover is not None and turnover > 0 and turnover < 999:
                wb_data[article]['turnover_days'].append(turnover)
            
            if warehouse and warehouse != '':
                wb_data[article]['warehouses'].add(warehouse)
    
    # Вычисляем среднюю оборачиваемость
    for article in wb_data:
        if wb_data[article]['turnover_days']:
            wb_data[article]['avg_turnover'] = sum(wb_data[article]['turnover_days']) / len(wb_data[article]['turnover_days'])
        else:
            wb_data[article]['avg_turnover'] = None
    
    return wb_data

def load_tracker_data(filepath):
    """Загрузка данных из Stock Tracker"""
    tracker_data = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            article = row['Артикул продавца']
            wb_article = row['Артикул товара']
            orders = parse_number(row['Заказы (всего)'])
            stock = parse_number(row['Остатки (всего)'])
            turnover = parse_number(row['Оборачиваемость'])
            
            tracker_data[article] = {
                'orders': orders,
                'stock': stock,
                'turnover': turnover,
                'article_name': wb_article
            }
    
    return tracker_data

def compare_data(wb_data, tracker_data):
    """Сравнение данных"""
    print("=" * 120)
    print("СРАВНИТЕЛЬНЫЙ АНАЛИЗ ДАННЫХ WB И STOCK TRACKER")
    print("=" * 120)
    print()
    
    # Все артикулы из обеих систем
    all_articles = set(list(wb_data.keys()) + list(tracker_data.keys()))
    
    total_articles = len(all_articles)
    matches = 0
    order_discrepancies = []
    stock_discrepancies = []
    turnover_discrepancies = []
    missing_in_tracker = []
    missing_in_wb = []
    
    print(f"{'Артикул продавца':<30} {'WB Артикул':<12} {'Заказы':<25} {'Остатки':<25} {'Оборачиваемость (дни)':<30}")
    print(f"{'='*30} {'='*12} {'='*25} {'='*25} {'='*30}")
    
    for article in sorted(all_articles):
        wb = wb_data.get(article, {})
        tracker = tracker_data.get(article, {})
        
        # Проверяем наличие данных
        if not wb:
            missing_in_wb.append(article)
            continue
        if not tracker:
            missing_in_tracker.append(article)
            wb_article = wb.get('article_name', 'N/A')
            print(f"{article:<30} {wb_article:<12} {'WB: ' + str(int(wb.get('orders', 0))):<25} {'WB: ' + str(int(wb.get('stock', 0))):<25} {'N/A':<30}")
            print(f"{' '*30} {' '*12} {'[!] Otsutstvuet v Tracker':<25}")
            print()
            continue
        
        wb_article = wb.get('article_name', tracker.get('article_name', 'N/A'))
        
        # Заказы
        wb_orders = int(wb.get('orders', 0))
        tracker_orders = int(tracker.get('orders', 0))
        orders_diff = abs(wb_orders - tracker_orders)
        orders_match = orders_diff <= 1  # Допускаем разницу в 1 заказ
        
        # Остатки
        wb_stock = int(wb.get('stock', 0))
        tracker_stock = int(tracker.get('stock', 0))
        stock_diff = abs(wb_stock - tracker_stock)
        stock_match = stock_diff == 0
        
        # Оборачиваемость
        wb_turnover = wb.get('avg_turnover')
        tracker_turnover = tracker.get('turnover', 0)
        turnover_match = None
        turnover_str = ""
        
        if wb_turnover and tracker_turnover > 0:
            turnover_diff_percent = abs(wb_turnover - tracker_turnover) / wb_turnover * 100
            turnover_match = turnover_diff_percent <= 20  # Допускаем разницу до 20%
            turnover_str = f"WB: {wb_turnover:.1f} / Tracker: {tracker_turnover:.1f}"
            if not turnover_match:
                turnover_str += f" [X] ({turnover_diff_percent:.1f}%)"
        elif wb_turnover:
            turnover_str = f"WB: {wb_turnover:.1f} / Tracker: N/A [!]"
        elif tracker_turnover > 0:
            turnover_str = f"WB: N/A / Tracker: {tracker_turnover:.1f} [!]"
        else:
            turnover_str = "N/A"
        
        # Вывод строки
        orders_str = f"WB: {wb_orders} / Tr: {tracker_orders}"
        if not orders_match:
            orders_str += f" [X] (D{orders_diff})"
        else:
            orders_str += " [OK]"
        
        stock_str = f"WB: {wb_stock} / Tr: {tracker_stock}"
        if not stock_match:
            stock_str += f" [X] (D{stock_diff})"
        else:
            stock_str += " [OK]"
        
        print(f"{article:<30} {wb_article:<12} {orders_str:<25} {stock_str:<25} {turnover_str:<30}")
        
        # Собираем статистику
        if orders_match and stock_match:
            matches += 1
        
        if not orders_match and orders_diff > 0:
            order_discrepancies.append({
                'article': article,
                'wb': wb_orders,
                'tracker': tracker_orders,
                'diff': orders_diff
            })
        
        if not stock_match and stock_diff > 0:
            stock_discrepancies.append({
                'article': article,
                'wb': wb_stock,
                'tracker': tracker_stock,
                'diff': stock_diff
            })
        
        if turnover_match is not None and not turnover_match:
            turnover_discrepancies.append({
                'article': article,
                'wb': wb_turnover,
                'tracker': tracker_turnover
            })
        
        print()
    
    # Итоговая статистика
    print("=" * 120)
    print("ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 120)
    print()
    print(f"Всего артикулов в сравнении: {total_articles}")
    print(f"Полное совпадение (заказы + остатки): {matches} ({matches/total_articles*100:.1f}%)")
    print()
    
    if missing_in_tracker:
        print(f"⚠ Отсутствует в Tracker (но есть в WB): {len(missing_in_tracker)}")
        for art in missing_in_tracker:
            print(f"  - {art}")
        print()
    
    if missing_in_wb:
        print(f"⚠ Отсутствует в WB (но есть в Tracker): {len(missing_in_wb)}")
        for art in missing_in_wb:
            print(f"  - {art}")
        print()
    
    if order_discrepancies:
        print(f"❌ Расхождения по ЗАКАЗАМ: {len(order_discrepancies)}")
        for item in sorted(order_discrepancies, key=lambda x: x['diff'], reverse=True):
            print(f"  - {item['article']}: WB={item['wb']}, Tracker={item['tracker']}, Δ={item['diff']}")
        print()
    
    if stock_discrepancies:
        print(f"❌ Расхождения по ОСТАТКАМ: {len(stock_discrepancies)}")
        for item in sorted(stock_discrepancies, key=lambda x: x['diff'], reverse=True):
            print(f"  - {item['article']}: WB={item['wb']}, Tracker={item['tracker']}, Δ={item['diff']}")
        print()
    
    if turnover_discrepancies:
        print(f"⚠ Расхождения по ОБОРАЧИВАЕМОСТИ: {len(turnover_discrepancies)}")
        for item in turnover_discrepancies[:5]:  # Показываем топ-5
            if item['wb'] and item['tracker']:
                diff_percent = abs(item['wb'] - item['tracker']) / item['wb'] * 100
                print(f"  - {item['article']}: WB={item['wb']:.1f} дней, Tracker={item['tracker']:.1f} дней (разница {diff_percent:.1f}%)")
        print()
    
    # Анализ метрик
    print("=" * 120)
    print("АНАЛИЗ МЕТРИК")
    print("=" * 120)
    print()
    print("СООТВЕТСТВИЕ КОЛОНОК:")
    print("  WB 'Заказали, шт' ↔ Tracker 'Заказы (всего)'")
    print("  WB 'Остатки на текущий день, шт' ↔ Tracker 'Остатки (всего)'")
    print("  WB 'Оборачиваемость текущих остатков' ↔ Tracker 'Оборачиваемость'")
    print()
    print("ПРИМЕЧАНИЯ:")
    print("  ✓ - данные совпадают")
    print("  ❌ - есть расхождения")
    print("  ⚠ - данные отсутствуют в одной из систем")
    print()

if __name__ == '__main__':
    wb_file = r'c:\Users\miros\Downloads\30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv'
    tracker_file = r'c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (8).csv'
    
    print("Загрузка данных из WB...")
    wb_data = load_wb_data(wb_file)
    
    print("Загрузка данных из Stock Tracker...")
    tracker_data = load_tracker_data(tracker_file)
    
    print()
    compare_data(wb_data, tracker_data)
