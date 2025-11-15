#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальное сравнение: свежие данные Stock Tracker vs официальная статистика WB
Дата: 30 октября 2025
"""

import pandas as pd
from collections import defaultdict
import sys

# Настройка кодировки вывода для Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def parse_number(value):
    """Парсит число, удаляя пробелы (включая неразрывные)"""
    if pd.isna(value) or value == '':
        return 0
    try:
        # Удаляем все пробелы (обычные и неразрывные)
        cleaned = str(value).replace(' ', '').replace('\xa0', '').replace(',', '.')
        return float(cleaned)
    except:
        return 0

# Файлы
wb_file = "30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv"
tracker_file = "Stock Tracker - Stock Tracker (1).csv"

print("=" * 80)
print("ФИНАЛЬНОЕ СРАВНЕНИЕ: Stock Tracker vs Официальная статистика WB")
print("=" * 80)
print()

# Читаем WB статистику
print("📊 Загружаем WB статистику...")
wb_df = pd.read_csv(wb_file, sep=',', encoding='utf-8', skiprows=1)  # Пропускаем первую строку "Остатки по КТ"
print(f"   Найдено строк: {len(wb_df)}")
print(f"   Колонки: {list(wb_df.columns[:5])}...")
print()

# Читаем Stock Tracker
print("📋 Загружаем Stock Tracker...")
tracker_df = pd.read_csv(tracker_file, sep=',', encoding='utf-8')
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
    
    # Заказы (допуск ±1)
    order_diff = abs(wb_orders - tracker_orders)
    if order_diff <= 1:
        order_matches += 1
    else:
        order_discrepancies.append({
            'article': article,
            'wb': wb_orders,
            'tracker': tracker_orders,
            'diff': tracker_orders - wb_orders,
            'diff_pct': ((tracker_orders - wb_orders) / wb_orders * 100) if wb_orders > 0 else 0
        })
    
    # Остатки (допуск ±5)
    stock_diff = abs(wb_stock - tracker_stock)
    if stock_diff <= 5:
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
print("🎯 СОВПАДЕНИЕ ЗАКАЗОВ:")
order_match_rate = (order_matches / len(common_articles)) * 100
print(f"   Совпадений: {order_matches} из {len(common_articles)} ({order_match_rate:.1f}%)")

if order_discrepancies:
    print(f"   Расхождений: {len(order_discrepancies)}")
    print()
    print("   ТОП-5 расхождений по заказам:")
    sorted_order_discrep = sorted(order_discrepancies, key=lambda x: abs(x['diff']), reverse=True)[:5]
    for item in sorted_order_discrep:
        print(f"      {item['article']:20} | WB: {item['wb']:6.0f} | Tracker: {item['tracker']:6.0f} | Δ: {item['diff']:+7.0f} ({item['diff_pct']:+6.1f}%)")
print()

print("📦 СОВПАДЕНИЕ ОСТАТКОВ:")
stock_match_rate = (stock_matches / len(common_articles)) * 100
print(f"   Совпадений: {stock_matches} из {len(common_articles)} ({stock_match_rate:.1f}%)")

if stock_discrepancies:
    print(f"   Расхождений: {len(stock_discrepancies)}")
    print()
    print("   ТОП-5 расхождений по остаткам:")
    sorted_stock_discrep = sorted(stock_discrepancies, key=lambda x: abs(x['diff']), reverse=True)[:5]
    for item in sorted_stock_discrep:
        print(f"      {item['article']:20} | WB: {item['wb']:8.0f} | Tracker: {item['tracker']:8.0f} | Δ: {item['diff']:+9.0f} ({item['diff_pct']:+6.1f}%)")
print()

# Детальное сравнение по складам (первые 3 артикула)
print("=" * 80)
print("🏭 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО СКЛАДАМ (первые 3 артикула)")
print("=" * 80)
print()

for article in list(common_articles)[:3]:
    wb_warehouses = wb_aggregated[article]['warehouses']
    print(f"Артикул: {article}")
    print(f"  WB Заказы: {wb_aggregated[article]['orders']:.0f}")
    print(f"  WB Остатки: {wb_aggregated[article]['stock']:.0f}")
    print(f"  WB Склады ({len(wb_warehouses)}): {', '.join(sorted(wb_warehouses)[:5])}")
    print(f"  Tracker Заказы: {tracker_data[article]['orders']:.0f}")
    print(f"  Tracker Остатки: {tracker_data[article]['stock']:.0f}")
    print()

# Итоговый вывод
print("=" * 80)
print("📊 ИТОГОВЫЙ ВЫВОД")
print("=" * 80)
print()

if order_match_rate >= 80 and stock_match_rate >= 80:
    print("✅ ОТЛИЧНО! Все критические исправления работают корректно!")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("🎉 Цель на $1,000,000 достигнута!")
elif order_match_rate >= 70 or stock_match_rate >= 70:
    print("⚠️  ХОРОШО, но есть небольшие расхождения:")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("Рекомендуется дополнительная проверка расхождений.")
else:
    print("❌ ВНИМАНИЕ: Значительные расхождения обнаружены!")
    print(f"   - Совпадение заказов: {order_match_rate:.1f}%")
    print(f"   - Совпадение остатков: {stock_match_rate:.1f}%")
    print()
    print("Требуется дополнительный анализ.")

print()
print("=" * 80)
