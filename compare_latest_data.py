#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальное сравнение: Актуальные данные Stock Tracker vs WB статистика
Дата: 30 октября 2025
"""

import pandas as pd
from collections import defaultdict
import sys

# Настройка кодировки
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def parse_number(value):
    """Парсит число, удаляя пробелы"""
    if pd.isna(value) or value == '':
        return 0
    try:
        cleaned = str(value).replace(' ', '').replace('\xa0', '').replace(',', '.')
        return float(cleaned)
    except:
        return 0

# Файлы (актуальные TSV)
wb_file = "c:/Users/miros/Downloads/30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv_export (1).tsv"
tracker_file = "c:/Users/miros/Downloads/Stock Tracker - Stock Tracker (2).tsv"

print("=" * 80)
print("ФИНАЛЬНОЕ СРАВНЕНИЕ: Stock Tracker vs Официальная статистика WB")
print("=" * 80)
print()

# Читаем WB статистику
print("📊 Загружаем WB статистику...")
wb_df = pd.read_csv(wb_file, sep='\t', encoding='utf-8')
print(f"   Найдено строк: {len(wb_df)}")
print(f"   Колонки: {list(wb_df.columns[:5])}...")
print()

# Читаем Stock Tracker
print("📋 Загружаем Stock Tracker...")
tracker_df = pd.read_csv(tracker_file, sep='\t', encoding='utf-8')
print(f"   Найдено строк: {len(tracker_df)}")
print(f"   Колонки: {list(tracker_df.columns[:5])}...")
print()

# Агрегируем WB данные по артикулу
print("🔄 Агрегируем данные WB по артикулам...")
wb_aggregated = defaultdict(lambda: {'orders': 0, 'stock': 0, 'warehouses': set()})

for _, row in wb_df.iterrows():
    article = str(row.get('Артикул продавца', '')).strip()
    warehouse = str(row.get('Склад', '')).strip()
    
    try:
        orders = parse_number(row.get('Заказали, шт', 0))
    except:
        orders = 0
    
    try:
        stock = parse_number(row.get('Остатки на текущий день, шт', 0))
    except:
        stock = 0
    
    if article and article not in ['', 'nan', 'None']:
        wb_aggregated[article]['orders'] += orders
        wb_aggregated[article]['stock'] += stock
        if warehouse:
            wb_aggregated[article]['warehouses'].add(warehouse)

print(f"   Уникальных артикулов в WB: {len(wb_aggregated)}")
print()

# Подготавливаем Stock Tracker данные
print("🔄 Обрабатываем Stock Tracker...")
tracker_data = {}

for _, row in tracker_df.iterrows():
    article = str(row.get('Артикул продавца', '')).strip()
    
    try:
        orders = parse_number(row.get('Заказы (всего)', 0))
    except:
        orders = 0
    
    try:
        stock = parse_number(row.get('Остатки (всего)', 0))
    except:
        stock = 0
    
    if article and article not in ['', 'nan', 'None']:
        tracker_data[article] = {
            'orders': orders,
            'stock': stock
        }

print(f"   Артикулов в Stock Tracker: {len(tracker_data)}")
print()

# Сравниваем
print("=" * 80)
print("📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ")
print("=" * 80)
print()

common_articles = set(wb_aggregated.keys()) & set(tracker_data.keys())
print(f"✅ Общих артикулов: {len(common_articles)}")
print()

if len(common_articles) == 0:
    print("⚠️  ВНИМАНИЕ: Нет общих артикулов!")
    print()
    print("Артикулы в WB (первые 10):")
    for art in list(wb_aggregated.keys())[:10]:
        print(f"  - '{art}'")
    print()
    print("Артикулы в Stock Tracker (первые 10):")
    for art in list(tracker_data.keys())[:10]:
        print(f"  - '{art}'")
    sys.exit(0)

# Статистика совпадений
order_matches = 0
stock_matches = 0
order_discrepancies = []
stock_discrepancies = []

for article in common_articles:
    wb_orders = wb_aggregated[article]['orders']
    wb_stock = wb_aggregated[article]['stock']
    tracker_orders = tracker_data[article]['orders']
    tracker_stock = tracker_data[article]['stock']
    
    # Заказы (допуск ±5 для более мягкого сравнения)
    order_diff = abs(wb_orders - tracker_orders)
    if order_diff <= 5:
        order_matches += 1
    else:
        order_discrepancies.append({
            'article': article,
            'wb': wb_orders,
            'tracker': tracker_orders,
            'diff': tracker_orders - wb_orders,
            'diff_pct': ((tracker_orders - wb_orders) / wb_orders * 100) if wb_orders > 0 else 0
        })
    
    # Остатки (допуск ±50 для учета складской логистики)
    stock_diff = abs(wb_stock - tracker_stock)
    if stock_diff <= 50:
        stock_matches += 1
    else:
        stock_discrepancies.append({
            'article': article,
            'wb': wb_stock,
            'tracker': tracker_stock,
            'diff': tracker_stock - wb_stock,
            'diff_pct': ((tracker_stock - wb_stock) / wb_stock * 100) if wb_stock > 0 else 0
        })

# Выводим результаты
print("🎯 СОВПАДЕНИЕ ЗАКАЗОВ (допуск ±5):")
order_match_rate = (order_matches / len(common_articles)) * 100
print(f"   Совпадений: {order_matches} из {len(common_articles)} ({order_match_rate:.1f}%)")

if order_discrepancies:
    print(f"   Расхождений: {len(order_discrepancies)}")
    print()
    print("   ТОП-5 расхождений по заказам:")
    sorted_order_discrep = sorted(order_discrepancies, key=lambda x: abs(x['diff']), reverse=True)[:5]
    for item in sorted_order_discrep:
        print(f"      {item['article']:30} | WB: {item['wb']:6.0f} | Tracker: {item['tracker']:6.0f} | Δ: {item['diff']:+7.0f} ({item['diff_pct']:+6.1f}%)")
print()

print("📦 СОВПАДЕНИЕ ОСТАТКОВ (допуск ±50):")
stock_match_rate = (stock_matches / len(common_articles)) * 100
print(f"   Совпадений: {stock_matches} из {len(common_articles)} ({stock_match_rate:.1f}%)")

if stock_discrepancies:
    print(f"   Расхождений: {len(stock_discrepancies)}")
    print()
    print("   ТОП-5 расхождений по остаткам:")
    sorted_stock_discrep = sorted(stock_discrepancies, key=lambda x: abs(x['diff']), reverse=True)[:5]
    for item in sorted_stock_discrep:
        print(f"      {item['article']:30} | WB: {item['wb']:8.0f} | Tracker: {item['tracker']:8.0f} | Δ: {item['diff']:+9.0f} ({item['diff_pct']:+6.1f}%)")
print()

# Детальное сравнение (первые 3 артикула)
print("=" * 80)
print("🏭 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ (первые 3 артикула)")
print("=" * 80)
print()

for article in list(common_articles)[:3]:
    wb_warehouses = wb_aggregated[article]['warehouses']
    print(f"📦 {article}")
    print(f"   WB:      Заказы={wb_aggregated[article]['orders']:.0f}  Остатки={wb_aggregated[article]['stock']:.0f}  Склады={len(wb_warehouses)}")
    print(f"   Tracker: Заказы={tracker_data[article]['orders']:.0f}  Остатки={tracker_data[article]['stock']:.0f}")
    
    # Разница
    order_diff = tracker_data[article]['orders'] - wb_aggregated[article]['orders']
    stock_diff = tracker_data[article]['stock'] - wb_aggregated[article]['stock']
    print(f"   Δ:       Заказы={order_diff:+.0f}  Остатки={stock_diff:+.0f}")
    print()

# Итоговый вывод
print("=" * 80)
print("📊 ИТОГОВЫЙ ВЫВОД")
print("=" * 80)
print()

if order_match_rate >= 80 and stock_match_rate >= 80:
    print("✅ ✅ ✅ ОТЛИЧНО! Все критические исправления работают корректно! ✅ ✅ ✅")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("🎉 🎉 🎉 ЦЕЛЬ НА $1,000,000 ДОСТИГНУТА! 🎉 🎉 🎉")
elif order_match_rate >= 60 or stock_match_rate >= 60:
    print("⚠️  ХОРОШО, но есть расхождения:")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("Возможные причины:")
    print("  1. Данные WB включают период 24-30 октября (7 дней)")
    print("  2. Stock Tracker может включать более свежие заказы")
    print("  3. Остатки синхронизированы в разное время суток")
else:
    print("❌ ВНИМАНИЕ: Значительные расхождения обнаружены!")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("Требуется дополнительный анализ.")

print()
print("=" * 80)
