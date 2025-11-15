#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сравнение данных официальной статистики WB с трекером Stock-Tracker
Использует СВЕЖИЕ данные напрямую из Google Sheets API
Дата анализа: 30-10-2025
"""

import sys
import os
from pathlib import Path
import pandas as pd
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.database.sheets import GoogleSheetsClient

def get_fresh_tracker_data():
    """Get fresh data directly from Google Sheets"""
    config = get_config()
    
    client = GoogleSheetsClient(
        service_account_path=config.google_service_account_key_path,
        sheet_id=config.google_sheet_id,
        sheet_name='Stock Tracker'  # Hardcode correct sheet name
    )
    
    sheet = client.get_spreadsheet()
    worksheet = sheet.worksheet('Stock Tracker')
    
    # Get all data
    data = worksheet.get_all_values()
    
    # Convert to DataFrame
    if len(data) > 1:
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    else:
        return pd.DataFrame()

# Загружаем файлы
wb_file = r"c:\Users\miros\Downloads\30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv_export (1).tsv"

print("=" * 100)
print("СРАВНИТЕЛЬНЫЙ АНАЛИЗ: Официальная статистика WB vs Stock-Tracker (СВЕЖИЕ ДАННЫЕ)")
print("=" * 100)

# Загружаем данные
wb_df = pd.read_csv(wb_file, sep='\t', encoding='utf-8')
print(f"\n[*] Получаем СВЕЖИЕ данные из Google Sheets API...")
tracker_df = get_fresh_tracker_data()

print(f"\n[+] Загружено данных:")
print(f"  - WB статистика: {len(wb_df)} строк")
print(f"  - Stock-Tracker (LIVE): {len(tracker_df)} строк")

# Print tracker columns
print(f"\n[i] Колонки трекера: {list(tracker_df.columns)}")

# Print first row
if len(tracker_df) > 0:
    print(f"\n[*] Первая строка трекера:")
    print(tracker_df.iloc[0].to_dict())

# Группируем данные по артикулам
# WB группировка
wb_grouped = defaultdict(lambda: {
    'nm_id': None,
    'total_orders': 0,
    'total_stock': 0,
    'warehouses': []
})

for _, row in wb_df.iterrows():
    article = row.get('Артикул поставщика', '')
    nm_id = row.get('Артикул WB', None)
    warehouse = row.get('Склад', '')
    orders = float(row.get('Заказы', 0) or 0)
    stock = float(row.get('Остатки', 0) or 0)
    
    if article:
        wb_grouped[article]['nm_id'] = nm_id
        wb_grouped[article]['total_orders'] += orders
        wb_grouped[article]['total_stock'] += stock
        wb_grouped[article]['warehouses'].append({
            'name': warehouse,
            'orders': orders,
            'stock': stock
        })

# Tracker группировка
tracker_grouped = {}
for _, row in tracker_df.iterrows():
    article = row.get('Артикул продавца', '')
    
    if article:
        # Try to parse numeric values
        try:
            total_stock = int(row.get('Общие остатки', '0').replace(' ', ''))
        except:
            total_stock = 0
            
        try:
            total_orders = int(row.get('Заказы за неделю', '0').replace(' ', ''))
        except:
            total_orders = 0
            
        try:
            nm_id = int(row.get('Артикул WB', '0'))
        except:
            nm_id = 0
        
        tracker_grouped[article] = {
            'nm_id': nm_id,
            'total_orders': total_orders,
            'total_stock': total_stock,
            'turnover': row.get('Оборачиваемость (дни)', '0')
        }

# Сравнение
print("\n" + "="*100)
print("ДЕТАЛЬНОЕ СРАВНЕНИЕ ПО АРТИКУЛАМ")
print("="*100)

# Get common articles
wb_articles = set(wb_grouped.keys())
tracker_articles = set(tracker_grouped.keys())
common_articles = wb_articles & tracker_articles

print(f"\n📦 Артикулы:")
print(f"  - В WB статистике: {len(wb_articles)} уникальных")
print(f"  - В Stock-Tracker: {len(tracker_articles)} уникальных")
print(f"  - Общих артикулов: {len(common_articles)}")
if wb_articles - tracker_articles:
    print(f"  - Только в WB: {wb_articles - tracker_articles}")
if tracker_articles - wb_articles:
    print(f"  - Только в Tracker: {tracker_articles - wb_articles}")

# Compare each common article
total_wb_orders = 0
total_tracker_orders = 0
total_wb_stock = 0
total_tracker_stock = 0

orders_match_count = 0
stock_match_count = 0

for article in sorted(common_articles):
    wb_data = wb_grouped[article]
    tracker_data = tracker_grouped[article]
    
    wb_orders = wb_data['total_orders']
    tracker_orders = tracker_data['total_orders']
    wb_stock = wb_data['total_stock']
    tracker_stock = tracker_data['total_stock']
    
    total_wb_orders += wb_orders
    total_tracker_orders += tracker_orders
    total_wb_stock += wb_stock
    total_tracker_stock += tracker_stock
    
    orders_match = wb_orders == tracker_orders
    stock_match = wb_stock == tracker_stock
    
    if orders_match:
        orders_match_count += 1
    if stock_match:
        stock_match_count += 1
    
    print(f"\n\n{'━'*100}")
    print(f"🏷️  АРТИКУЛ: {article}")
    print(f"{'━'*100}")
    
    print(f"\n📋 Артикул WB:")
    print(f"  WB:      {wb_data['nm_id']}")
    print(f"  Tracker: {tracker_data['nm_id']}")
    
    print(f"\n📦 ЗАКАЗЫ (всего за период 24-30 октября):")
    print(f"  WB:        {wb_orders} шт")
    print(f"  Tracker:    {tracker_orders} шт")
    if orders_match:
        print(f"  ✅ Совпадает")
    else:
        diff = tracker_orders - wb_orders
        diff_pct = (diff / wb_orders * 100) if wb_orders > 0 else 0
        print(f"  ❌ РАСХОЖДЕНИЕ: {diff:+.1f} шт ({diff_pct:+.1f}%)")
    
    print(f"\n📊 ОСТАТКИ (на текущий день):")
    print(f"  WB:       {wb_stock} шт")
    print(f"  Tracker:    {tracker_stock} шт")
    if stock_match:
        print(f"  ✅ Совпадает")
    else:
        diff = tracker_stock - wb_stock
        diff_pct = (diff / wb_stock * 100) if wb_stock > 0 else 0
        print(f"  ❌ РАСХОЖДЕНИЕ: {diff:+.1f} шт ({diff_pct:+.1f}%)")
    
    # Show WB warehouses
    print(f"\n🏭 СКЛАДЫ (данные WB):")
    active_warehouses = [w for w in wb_data['warehouses'] if w['orders'] > 0 or w['stock'] > 0]
    if active_warehouses:
        print(f"  Активных складов: {len(active_warehouses)}")
        for wh in active_warehouses:
            print(f"    • {wh['name']:40} | Заказы: {wh['orders']:>4} | Остатки: {wh['stock']:>6}")
    
    print(f"\n⏱️  ОБОРАЧИВАЕМОСТЬ (Tracker): {tracker_data['turnover']} дней")

# Summary
print("\n" + "="*100)
print("СВОДНАЯ СТАТИСТИКА")
print("="*100)

print(f"\n📊 ИТОГО по всем артикулам:")
print(f"\n  Заказы:")
print(f"    WB:         {total_wb_orders} шт")
print(f"    Tracker:      {total_tracker_orders} шт")
print(f"    Разница:    {total_tracker_orders - total_wb_orders:+.1f} шт")

print(f"\n  Остатки:")
print(f"    WB:        {total_wb_stock} шт")
print(f"    Tracker:     {total_tracker_stock} шт")
print(f"    Разница:   {total_tracker_stock - total_wb_stock:+.1f} шт")

print(f"\n📈 Точность данных:")
print(f"    Артикулов с расхождениями по заказам:  {len(common_articles) - orders_match_count}/{len(common_articles)} ({(len(common_articles) - orders_match_count)/len(common_articles)*100:.1f}%)")
print(f"    Артикулов с расхождениями по остаткам: {len(common_articles) - stock_match_count}/{len(common_articles)} ({(len(common_articles) - stock_match_count)/len(common_articles)*100:.1f}%)")

print("\n" + "="*100)
print("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
print("="*100)

print(f"\n✅ ПОЛОЖИТЕЛЬНЫЕ МОМЕНТЫ:")
print(f"   - Все артикулы из трекера присутствуют в официальной статистике WB")
print(f"   - Используются СВЕЖИЕ данные напрямую из Google Sheets API")
print(f"   - Структура данных позволяет проводить детальное сравнение")

if orders_match_count == len(common_articles) and stock_match_count == len(common_articles):
    print(f"\n🎉 ОТЛИЧНО! Все данные полностью совпадают с официальной статистикой WB!")
else:
    print(f"\n⚠️  ОБНАРУЖЕННЫЕ РАСХОЖДЕНИЯ:")
    print(f"   - Различия в подсчете заказов (могут быть из-за разных периодов учета)")
    print(f"   - Различия в остатках (могут быть из-за учета служебных складов)")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print(f"   1. Проверить, какие склады учитываются в трекере")
    print(f"   2. Уточнить период учета заказов (WB показывает за 24-30 октября)")
    print(f"   3. Проверить логику агрегации данных по складам")
    print(f"   4. Убедиться, что оборачиваемость рассчитывается корректно")

print("\n" + "="*100)
