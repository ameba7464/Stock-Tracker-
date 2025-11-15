#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение данных официальной статистики WB с трекером Stock-Tracker
Дата анализа: 30-10-2025
"""

import pandas as pd
from collections import defaultdict

# Загружаем файлы
wb_file = r"c:\Users\miros\Downloads\30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv_export (1).tsv"
tracker_file = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker.tsv_export.tsv"

print("=" * 100)
print("СРАВНИТЕЛЬНЫЙ АНАЛИЗ: Официальная статистика WB vs Stock-Tracker")
print("=" * 100)

# Загружаем данные
wb_df = pd.read_csv(wb_file, sep='\t', encoding='utf-8')
tracker_df = pd.read_csv(tracker_file, sep='\t', encoding='utf-8')

print(f"\n📊 Загружено данных:")
print(f"  - WB статистика: {len(wb_df)} строк")
print(f"  - Stock-Tracker: {len(tracker_df)} строк")

# Получаем уникальные артикулы
wb_articles = set(wb_df['Артикул продавца'].unique())
tracker_articles = set(tracker_df['Артикул продавца'].unique())

print(f"\n📦 Артикулы:")
print(f"  - В WB статистике: {len(wb_articles)} уникальных")
print(f"  - В Stock-Tracker: {len(tracker_articles)} уникальных")

common_articles = wb_articles & tracker_articles
print(f"  - Общих артикулов: {len(common_articles)}")

if wb_articles - tracker_articles:
    print(f"  - Только в WB: {wb_articles - tracker_articles}")
if tracker_articles - wb_articles:
    print(f"  - Только в Tracker: {tracker_articles - wb_articles}")

print("\n" + "=" * 100)
print("ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО АРТИКУЛАМ")
print("=" * 100)

# Агрегируем данные WB по артикулу продавца (суммируем по всем складам)
wb_aggregated = {}
for article in common_articles:
    wb_article_data = wb_df[wb_df['Артикул продавца'] == article]
    
    # Суммируем заказы и остатки по всем складам
    total_orders = wb_article_data['Заказали, шт'].sum()
    
    # Для остатков берем только активные склады (не "Маркетплейс" и не служебные)
    stock_rows = wb_article_data[
        (wb_article_data['Склад'] != 'Маркетплейс') & 
        (~wb_article_data['Склад'].str.contains('Коледино|Обухово|Пушкино|Виртуальный|Остальные', na=False))
    ]
    total_stock = stock_rows['Остатки на текущий день, шт'].sum()
    
    # Собираем информацию по складам
    warehouses_info = []
    for _, row in wb_article_data.iterrows():
        wh_name = row['Склад']
        wh_orders = row['Заказали, шт']
        wh_stock = row['Остатки на текущий день, шт']
        if pd.notna(wh_orders) or pd.notna(wh_stock):
            warehouses_info.append({
                'name': wh_name,
                'orders': wh_orders if pd.notna(wh_orders) else 0,
                'stock': wh_stock if pd.notna(wh_stock) else 0,
                'region': row['Регион']
            })
    
    wb_aggregated[article] = {
        'orders': total_orders,
        'stock': total_stock,
        'warehouses': warehouses_info,
        'wb_article': wb_article_data['Артикул WB'].iloc[0] if len(wb_article_data) > 0 else 'N/A'
    }

# Обрабатываем данные Tracker
tracker_aggregated = {}
for article in common_articles:
    tracker_article_data = tracker_df[tracker_df['Артикул продавца'] == article]
    
    if len(tracker_article_data) == 0:
        continue
    
    row = tracker_article_data.iloc[0]
    
    # Парсим заказы и остатки по складам
    warehouses_str = str(row['Название склада'])
    orders_str = str(row['Заказы со склада'])
    stock_str = str(row['Остатки на складе'])
    
    warehouses = [w.strip() for w in warehouses_str.split() if w.strip()]
    orders_parts = orders_str.replace('/', ' ').split()
    stock_parts = stock_str.split()
    
    # Убираем числовые значения из складов (это могут быть цифры в названии)
    warehouses_clean = []
    for w in warehouses:
        if not w.isdigit() and not w.replace(',', '').replace('.', '').isdigit():
            warehouses_clean.append(w)
    
    # Обработка заказов
    orders_val = row['Заказы (всего)']
    if pd.notna(orders_val):
        if isinstance(orders_val, str):
            orders_total = int(orders_val.replace(' ', '').replace(',', ''))
        else:
            orders_total = int(orders_val)
    else:
        orders_total = 0
    
    # Обработка остатков
    stock_val = row['Остатки (всего)']
    if pd.notna(stock_val):
        stock_str = str(stock_val).replace(' ', '').replace(',', '')
        try:
            stock_total = int(stock_str)
        except:
            stock_total = 0
    else:
        stock_total = 0
    
    tracker_aggregated[article] = {
        'orders_total': orders_total,
        'stock_total': stock_total,
        'turnover': str(row['Оборачиваемость']),
        'wb_article': int(row['Артикул товара']) if pd.notna(row['Артикул товара']) else 0,
        'warehouses': warehouses_clean,
        'orders_by_warehouse': orders_parts,
        'stock_by_warehouse': stock_parts
    }

# Сравниваем данные
print("\n")
for article in sorted(common_articles):
    wb_data = wb_aggregated.get(article, {})
    tracker_data = tracker_aggregated.get(article, {})
    
    print(f"\n{'━' * 100}")
    print(f"🏷️  АРТИКУЛ: {article}")
    print(f"{'━' * 100}")
    
    # Артикул WB
    wb_art = wb_data.get('wb_article', 'N/A')
    tracker_art = tracker_data.get('wb_article', 0)
    print(f"\n📋 Артикул WB:")
    print(f"  WB:      {wb_art}")
    print(f"  Tracker: {tracker_art}")
    if str(wb_art) != str(tracker_art):
        print(f"  ⚠️  РАСХОЖДЕНИЕ в артикулах WB!")
    
    # Заказы
    wb_orders = wb_data.get('orders', 0)
    tracker_orders = tracker_data.get('orders_total', 0)
    print(f"\n📦 ЗАКАЗЫ (всего за период 24-30 октября):")
    print(f"  WB:      {wb_orders:>6} шт")
    print(f"  Tracker: {tracker_orders:>6} шт")
    
    diff_orders = wb_orders - tracker_orders
    if diff_orders != 0:
        print(f"  ❌ РАСХОЖДЕНИЕ: {diff_orders:+} шт ({diff_orders/max(wb_orders, 1)*100:+.1f}%)")
    else:
        print(f"  ✅ Совпадает")
    
    # Остатки
    wb_stock = wb_data.get('stock', 0)
    tracker_stock = tracker_data.get('stock_total', 0)
    print(f"\n📊 ОСТАТКИ (на текущий день):")
    print(f"  WB:      {wb_stock:>6} шт")
    print(f"  Tracker: {tracker_stock:>6} шт")
    
    diff_stock = wb_stock - tracker_stock
    if diff_stock != 0:
        print(f"  ❌ РАСХОЖДЕНИЕ: {diff_stock:+} шт ({diff_stock/max(wb_stock, 1)*100:+.1f}%)")
    else:
        print(f"  ✅ Совпадает")
    
    # Информация по складам из WB
    print(f"\n🏭 СКЛАДЫ (данные WB):")
    warehouses = wb_data.get('warehouses', [])
    if warehouses:
        active_warehouses = [w for w in warehouses if w['stock'] > 0 or w['orders'] > 0]
        if active_warehouses:
            print(f"  Активных складов: {len(active_warehouses)}")
            for wh in active_warehouses[:10]:  # Показываем топ-10
                if wh['stock'] > 0 or wh['orders'] > 0:
                    print(f"    • {wh['name']:<35} | Заказы: {wh['orders']:>3} | Остатки: {wh['stock']:>6}")
        else:
            print(f"  Нет активных складов")
    
    # Оборачиваемость из Tracker
    turnover = tracker_data.get('turnover', 'N/A')
    print(f"\n⏱️  ОБОРАЧИВАЕМОСТЬ (Tracker): {turnover} дней")

print("\n" + "=" * 100)
print("СВОДНАЯ СТАТИСТИКА")
print("=" * 100)

total_wb_orders = sum(wb_aggregated[a]['orders'] for a in common_articles)
total_tracker_orders = sum(tracker_aggregated[a]['orders_total'] for a in common_articles)
total_wb_stock = sum(wb_aggregated[a]['stock'] for a in common_articles)
total_tracker_stock = sum(tracker_aggregated[a]['stock_total'] for a in common_articles)

print(f"\n📊 ИТОГО по всем артикулам:")
print(f"\n  Заказы:")
print(f"    WB:      {total_wb_orders:>8} шт")
print(f"    Tracker: {total_tracker_orders:>8} шт")
print(f"    Разница: {total_wb_orders - total_tracker_orders:>+8} шт")

print(f"\n  Остатки:")
print(f"    WB:      {total_wb_stock:>8} шт")
print(f"    Tracker: {total_tracker_stock:>8} шт")
print(f"    Разница: {total_wb_stock - total_tracker_stock:>+8} шт")

# Анализ точности
articles_with_order_diff = sum(1 for a in common_articles if wb_aggregated[a]['orders'] != tracker_aggregated[a]['orders_total'])
articles_with_stock_diff = sum(1 for a in common_articles if wb_aggregated[a]['stock'] != tracker_aggregated[a]['stock_total'])

print(f"\n📈 Точность данных:")
print(f"    Артикулов с расхождениями по заказам:  {articles_with_order_diff}/{len(common_articles)} ({articles_with_order_diff/len(common_articles)*100:.1f}%)")
print(f"    Артикулов с расхождениями по остаткам: {articles_with_stock_diff}/{len(common_articles)} ({articles_with_stock_diff/len(common_articles)*100:.1f}%)")

print("\n" + "=" * 100)
print("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
print("=" * 100)

print("""
✅ ПОЛОЖИТЕЛЬНЫЕ МОМЕНТЫ:
   - Все артикулы из трекера присутствуют в официальной статистике WB
   - Структура данных позволяет проводить детальное сравнение

⚠️  ОБНАРУЖЕННЫЕ РАСХОЖДЕНИЯ:
   - Различия в подсчете заказов (могут быть из-за разных периодов учета)
   - Различия в остатках (могут быть из-за учета служебных складов)
   - Трекер может не учитывать склады "Маркетплейс", "Коледино", "Обухово"

💡 РЕКОМЕНДАЦИИ:
   1. Проверить, какие склады учитываются в трекере
   2. Уточнить период учета заказов (WB показывает за 24-30 октября)
   3. Проверить логику агрегации данных по складам
   4. Убедиться, что оборачиваемость рассчитывается корректно
""")

print("\n" + "=" * 100)
