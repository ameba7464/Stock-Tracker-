#!/usr/bin/env python3
"""
Анализ расхождений в метрике "Заказы со склада" между данными WB и нашей таблицей
"""

import csv
from collections import defaultdict
from pathlib import Path

# Paths
wb_file = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export.csv"
our_file = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (3).csv"

print("="*100)
print("🔍 АНАЛИЗ РАСХОЖДЕНИЙ В МЕТРИКЕ 'ЗАКАЗЫ СО СКЛАДА'")
print("="*100)
print()

# Parse WB data
wb_data = defaultdict(lambda: defaultdict(int))
print("📊 ДАННЫЕ ОТ WILDBERRIES (22-28 октября 2025):")
print("-" * 100)

with open(wb_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        article = row['Артикул продавца']
        warehouse = row['Склад']
        orders_str = row['Заказали, шт']
        
        # Skip empty orders
        if not orders_str or orders_str == '':
            continue
            
        orders = int(orders_str)
        wb_data[article][warehouse] = orders

# Print WB data summary
for article in sorted(wb_data.keys()):
    warehouses = wb_data[article]
    total_orders = sum(warehouses.values())
    print(f"\n📦 {article}: ВСЕГО {total_orders} заказов")
    for wh, orders in sorted(warehouses.items(), key=lambda x: -x[1])[:5]:  # Top 5
        print(f"   └─ {wh}: {orders} заказов")

print("\n")
print("="*100)
print("📊 НАША ТАБЛИЦА (Stock Tracker):")
print("-" * 100)

# Parse our data
our_data = defaultdict(lambda: defaultdict(int))

with open(our_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        article = row['Артикул продавца']
        total_orders_str = row['Заказы (всего)']
        
        if not total_orders_str or total_orders_str == '':
            continue
            
        total_orders = int(total_orders_str)
        
        # Parse warehouses and their orders
        warehouses_str = row['Название склада']
        orders_str = row['Заказы со склада']
        
        if not warehouses_str or not orders_str:
            continue
            
        warehouses_list = [w.strip() for w in warehouses_str.split('\n')]
        orders_list = [o.strip() for o in orders_str.split('\n')]
        
        for wh, ord_str in zip(warehouses_list, orders_list):
            if ord_str and ord_str.isdigit():
                our_data[article][wh] = int(ord_str)

# Print our data summary
for article in sorted(our_data.keys()):
    warehouses = our_data[article]
    total_orders = sum(warehouses.values())
    print(f"\n📦 {article}: ВСЕГО {total_orders} заказов")
    for wh, orders in sorted(warehouses.items(), key=lambda x: -x[1])[:5]:  # Top 5
        print(f"   └─ {wh}: {orders} заказов")

print("\n")
print("="*100)
print("⚠️  АНАЛИЗ РАСХОЖДЕНИЙ:")
print("-" * 100)

# Compare data
all_articles = set(wb_data.keys()) | set(our_data.keys())

total_wb_orders = 0
total_our_orders = 0
total_missing_orders = 0
critical_errors = []

for article in sorted(all_articles):
    wb_total = sum(wb_data[article].values())
    our_total = sum(our_data[article].values())
    
    total_wb_orders += wb_total
    total_our_orders += our_total
    
    if wb_total == 0 and our_total == 0:
        continue
    
    diff = our_total - wb_total
    diff_percent = ((our_total - wb_total) / wb_total * 100) if wb_total > 0 else 0
    
    print(f"\n📦 {article}:")
    print(f"   WB данные:      {wb_total} заказов")
    print(f"   Наша таблица:   {our_total} заказов")
    print(f"   Расхождение:    {diff:+d} заказов ({diff_percent:+.1f}%)")
    
    if abs(diff_percent) > 20:
        status = "🔴 КРИТИЧНО"
        critical_errors.append({
            'article': article,
            'wb': wb_total,
            'ours': our_total,
            'diff': diff,
            'diff_percent': diff_percent
        })
    elif abs(diff_percent) > 10:
        status = "⚠️  ПРЕДУПРЕЖДЕНИЕ"
    else:
        status = "✅ ОК"
    
    print(f"   Статус:         {status}")
    
    # Compare warehouses
    all_warehouses = set(wb_data[article].keys()) | set(our_data[article].keys())
    
    for wh in sorted(all_warehouses):
        wb_orders = wb_data[article].get(wh, 0)
        our_orders = our_data[article].get(wh, 0)
        
        if wb_orders != our_orders:
            print(f"      └─ {wh}: WB={wb_orders}, Таблица={our_orders} ({our_orders-wb_orders:+d})")

print("\n")
print("="*100)
print("📈 ИТОГОВАЯ СТАТИСТИКА:")
print("-" * 100)
print(f"Всего заказов по WB:        {total_wb_orders}")
print(f"Всего заказов в таблице:    {total_our_orders}")
print(f"Расхождение:                {total_our_orders - total_wb_orders:+d} ({(total_our_orders - total_wb_orders)/total_wb_orders*100:+.1f}%)")
print(f"Критических ошибок:         {len(critical_errors)}")
print()

if critical_errors:
    print("="*100)
    print("🔴 КРИТИЧЕСКИЕ ОШИБКИ (расхождение > 20%):")
    print("-" * 100)
    for err in critical_errors:
        print(f"\n📦 {err['article']}")
        print(f"   WB: {err['wb']} заказов")
        print(f"   Таблица: {err['ours']} заказов")
        print(f"   Разница: {err['diff']:+d} заказов ({err['diff_percent']:+.1f}%)")

print("\n")
print("="*100)
print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ:")
print("-" * 100)

# Check period
print("\n1️⃣  ПЕРИОД ДАННЫХ:")
print("   WB выгрузка: 22-28 октября 2025 (7 дней)")
print("   Наша таблица: Последняя синхронизация с API")
print("   ⚠️  ПРОБЛЕМА: Данные из разных временных окон!")
print()

# Check API source
print("2️⃣  ИСТОЧНИК ДАННЫХ API:")
print("   Текущая реализация: supplier/orders с dateFrom = 7 дней назад")
print("   WB выгрузка: История остатков за конкретный период")
print("   ⚠️  ПРОБЛЕМА: Разные endpoints и периоды!")
print()

# Check calculation method
print("3️⃣  МЕТОД РАСЧЁТА:")
print("   Наша реализация: COUNT(orders WHERE nmId=X AND warehouseName=Y)")
print("   WB выгрузка: 'Заказали, шт' - уже агрегированные данные")
print("   ⚠️  ПРОБЛЕМА: Можем считать дубликаты или пропускать записи!")
print()

print("="*100)
print("💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ:")
print("-" * 100)

print("""
1️⃣  ПРОБЛЕМА С ПЕРИОДОМ:
   ❌ Сейчас: dateFrom = 7 дней назад (постоянно меняется)
   ✅ Нужно: Синхронизировать период с таблицей WB или хранить дату последней синхронизации
   
   Решение:
   - Добавить в конфиг период для статистики (например, "за последние 7 дней")
   - Или использовать фиксированную дату начала (начало месяца/недели)
   - Или хранить timestamp последней синхронизации

2️⃣  ПРОБЛЕМА С ENDPOINT:
   ❌ Сейчас: GET /api/v1/supplier/orders?dateFrom=...&flag=0
   ⚠️  Возможные причины расхождений:
      - flag=0 vs flag=1 (разные наборы данных)
      - Заказы могут дублироваться (несколько статусов)
      - Отменённые заказы включаются/исключаются
   
   Решение:
   - Проверить документацию WB для точного описания flag параметра
   - Возможно, нужно фильтровать по статусу заказа (is_cancel, is_realization)
   - Дедуплицировать заказы по уникальному ID (srid, odid, gNumber)

3️⃣  ПРОБЛЕМА С ПОДСЧЁТОМ:
   ❌ Сейчас: Просто COUNT(orders)
   ⚠️  Не учитываем:
      - Отменённые заказы (is_cancel)
      - Статус реализации (is_realization)
      - Дубликаты по одному и тому же заказу
   
   Решение:
   - Фильтровать: WHERE is_cancel = False OR is_cancel IS NULL
   - Использовать уникальный ID заказа для дедупликации
   - Проверить поле для подсчёта (может быть quantity, а не просто count)

4️⃣  ПРОБЛЕМА С МАППИНГОМ СКЛАДОВ:
   ❌ Сейчас: warehouseName напрямую из API
   ⚠️  Названия могут отличаться:
      - "Подольск 3" vs "Подольск-3"
      - "Екатеринбург - Перспективный 12" vs "Екатеринбург"
   
   Решение:
   - Нормализовать названия складов
   - Создать mapping таблицу для соответствия названий
""")

print("\n")
print("="*100)
print("🎯 ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ:")
print("-" * 100)
print("""
1. Изучить структуру ответа от /api/v1/supplier/orders
   - Какие поля доступны?
   - Что означает flag=0 vs flag=1?
   - Есть ли поле is_cancel, is_realization?
   - Какой уникальный ID заказа (srid, odid, gNumber)?

2. Добавить фильтрацию отменённых заказов
   - WHERE is_cancel = False

3. Добавить дедупликацию по уникальному ID
   - Использовать set() или dict для хранения уникальных заказов

4. Синхронизировать периоды
   - Использовать фиксированную дату или хранить last_sync

5. Добавить детальное логирование
   - Сколько заказов загружено
   - Сколько отфильтровано (отменены)
   - Сколько задедуплицировано
   - Итоговое количество по каждому складу
""")

print("\n" + "="*100)
