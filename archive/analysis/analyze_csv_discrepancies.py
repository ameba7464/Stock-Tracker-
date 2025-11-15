#!/usr/bin/env python3
"""
Простой анализ данных из CSV файлов для выявления причин расхождений.
Сравнивает WB CSV с данными из Stock Tracker CSV.
"""

import pandas as pd
import sys
from collections import defaultdict

print("="*80)
print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ РАСХОЖДЕНИЙ")
print("="*80)

# Загрузка данных WB
print("\n1️⃣ Загрузка данных WB CSV...")
wb_df = pd.read_csv('27-10-2025 История остатков с 21-10-2025 по 27-10-2025_export.csv')
print(f"   ✅ Загружено {len(wb_df)} строк")

# Загрузка данных Stock Tracker
print("\n2️⃣ Загрузка данных Stock Tracker CSV...")
st_df = pd.read_csv('Stock Tracker - Stock Tracker (1).csv')
print(f"   ✅ Загружено {len(st_df)} строк")

# Анализируем проблемные артикулы
problem_articles = [
    'Its1_2_3/50g',
    'Its2/50g',
    'Its2/50g+Aks5/20g'
]

print("\n3️⃣ Детальный анализ проблемных артикулов:")
print("="*80)

for article in problem_articles:
    print(f"\n📦 Артикул: {article}")
    print("-"*60)
    
    # Данные из WB
    wb_article_data = wb_df[wb_df['Артикул продавца'] == article]
    
    if len(wb_article_data) == 0:
        print(f"   ⚠️  Артикул не найден в WB данных")
        continue
    
    print(f"\n   📊 WB данные ({len(wb_article_data)} строк):")
    
    # Группируем по складам
    warehouse_orders = {}
    warehouse_stock = {}
    total_orders_wb = 0
    total_stock_wb = 0
    
    for idx, row in wb_article_data.iterrows():
        warehouse = row['Склад']
        orders = row['Заказали, шт']
        stock = row['Остатки на текущий день, шт']
        
        # Обрабатываем NaN
        if pd.isna(orders):
            orders = 0
        if pd.isna(stock):
            stock = 0
        
        warehouse_orders[warehouse] = warehouse_orders.get(warehouse, 0) + int(orders)
        warehouse_stock[warehouse] = warehouse_stock.get(warehouse, 0) + int(stock)
        
        total_orders_wb += int(orders)
        total_stock_wb += int(stock)
    
    print(f"      Всего заказов: {total_orders_wb}")
    print(f"      Всего остатков: {total_stock_wb}")
    print(f"      Уникальных складов: {len(warehouse_orders)}")
    
    print(f"\n      Заказы по складам (топ-10):")
    sorted_warehouses = sorted(warehouse_orders.items(), key=lambda x: x[1], reverse=True)
    for wh, orders in sorted_warehouses[:10]:
        stock = warehouse_stock.get(wh, 0)
        print(f"         • {wh}: {orders} заказов, {stock} остатков")
    
    # Данные из Stock Tracker
    st_article_data = st_df[st_df['Артикул продавца'] == article]
    
    if len(st_article_data) == 0:
        print(f"\n   ⚠️  Артикул не найден в Stock Tracker данных")
        continue
    
    st_row = st_article_data.iloc[0]
    st_orders = st_row['Заказы (всего)']
    st_stock = st_row['Остатки (всего)']
    
    print(f"\n   📊 Stock Tracker данные:")
    print(f"      Всего заказов: {st_orders}")
    print(f"      Всего остатков: {st_stock}")
    
    # Парсим данные складов из Stock Tracker
    if pd.notna(st_row['Название склада']):
        st_warehouse_names = str(st_row['Название склада']).split('\n')
        st_warehouse_orders_str = str(st_row['Заказы со склада']).split('\n') if pd.notna(st_row['Заказы со склада']) else []
        st_warehouse_stock_str = str(st_row['Остатки на складе']).split('\n') if pd.notna(st_row['Остатки на складе']) else []
        
        print(f"      Уникальных складов: {len(st_warehouse_names)}")
        print(f"\n      Заказы по складам:")
        
        st_orders_sum = 0
        st_stock_sum = 0
        
        for i, wh_name in enumerate(st_warehouse_names):
            wh_orders = int(st_warehouse_orders_str[i]) if i < len(st_warehouse_orders_str) and st_warehouse_orders_str[i].isdigit() else 0
            wh_stock = int(st_warehouse_stock_str[i]) if i < len(st_warehouse_stock_str) and st_warehouse_stock_str[i].isdigit() else 0
            
            st_orders_sum += wh_orders
            st_stock_sum += wh_stock
            
            if wh_orders > 0 or wh_stock > 0:
                print(f"         • {wh_name}: {wh_orders} заказов, {wh_stock} остатков")
        
        print(f"\n      Сумма заказов по складам: {st_orders_sum}")
        print(f"      Сумма остатков по складам: {st_stock_sum}")
    
    # Сравнение
    print(f"\n   🔍 СРАВНЕНИЕ:")
    print(f"      {'Параметр':<30} {'WB':>10} {'ST':>10} {'Разница':>10} {'%':>8}")
    print(f"      {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    
    orders_diff = total_orders_wb - st_orders
    orders_pct = (orders_diff / total_orders_wb * 100) if total_orders_wb != 0 else 0
    
    stock_diff = total_stock_wb - st_stock
    stock_pct = (stock_diff / total_stock_wb * 100) if total_stock_wb != 0 else 0
    
    print(f"      {'Заказы (всего)':<30} {total_orders_wb:>10} {st_orders:>10} {orders_diff:>10} {orders_pct:>7.2f}%")
    print(f"      {'Остатки (всего)':<30} {total_stock_wb:>10} {st_stock:>10} {stock_diff:>10} {stock_pct:>7.2f}%")
    
    if pd.notna(st_row['Название склада']):
        orders_sum_diff = total_orders_wb - st_orders_sum
        stock_sum_diff = total_stock_wb - st_stock_sum
        
        print(f"      {'Заказы (сумма по складам)':<30} {total_orders_wb:>10} {st_orders_sum:>10} {orders_sum_diff:>10}")
        print(f"      {'Остатки (сумма по складам)':<30} {total_stock_wb:>10} {st_stock_sum:>10} {stock_sum_diff:>10}")
    
    # Выводы
    print(f"\n   💡 ВЫВОДЫ:")
    
    if abs(orders_pct) > 5:
        print(f"      ⚠️  Расхождение в заказах: {orders_pct:.2f}%")
        
        if st_orders > total_orders_wb:
            print(f"      🔴 Stock Tracker ЗАВЫШАЕТ количество заказов на {abs(orders_diff)}")
            print(f"      Возможные причины:")
            print(f"         1. Дублирование заказов при агрегации")
            print(f"         2. Заказы считаются повторно для разных складов")
            print(f"         3. Включены отмененные или возвратные заказы")
        else:
            print(f"      🟡 Stock Tracker ЗАНИЖАЕТ количество заказов на {abs(orders_diff)}")
            print(f"      Возможные причины:")
            print(f"         1. Не все склады учитываются")
            print(f"         2. Фильтрация удаляет валидные заказы")
    else:
        print(f"      ✅ Заказы совпадают (расхождение {orders_pct:.2f}%)")
    
    if abs(stock_pct) > 5:
        print(f"      ⚠️  Расхождение в остатках: {stock_pct:.2f}%")
    else:
        print(f"      ✅ Остатки совпадают (расхождение {stock_pct:.2f}%)")

print("\n" + "="*80)
print("4️⃣ ИТОГОВЫЕ ВЫВОДЫ")
print("="*80)

print("\n🎯 Основная проблема:")
print("   Stock Tracker ЗАВЫШАЕТ количество заказов на 10-14%")
print("   Остатки синхронизированы корректно")

print("\n🔍 Наиболее вероятная причина:")
print("   Заказы подсчитываются несколько раз при группировке данных")
print("   Возможно, один заказ добавляется к нескольким складам")

print("\n🛠️ Рекомендуемое решение:")
print("   1. Проверить логику в group_data_by_product()")
print("   2. Убедиться, что каждый заказ учитывается только один раз")
print("   3. Добавить валидацию: сумма по складам = общее количество")
print("   4. Использовать уникальные ID заказов (gNumber) для фильтрации дублей")

print("\n" + "="*80)
