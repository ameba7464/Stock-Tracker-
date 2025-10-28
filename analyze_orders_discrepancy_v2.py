#!/usr/bin/env python3
"""
Анализ расхождений в метрике "Заказы со склада" между данными WB и нашей таблицей
"""

import csv
from collections import defaultdict

# Paths
wb_file = r"c:\Users\miros\Downloads\28-10-2025 История остатков с 22-10-2025 по 28-10-2025_export.csv"
our_file = r"c:\Users\miros\Downloads\Stock Tracker - Stock Tracker (3).csv"

print("="*100)
print("🔍 АНАЛИЗ РАСХОЖДЕНИЙ В МЕТРИКЕ 'ЗАКАЗЫ СО СКЛАДА'")
print("="*100)
print()

# Parse WB data
wb_data = defaultdict(lambda: defaultdict(int))
wb_total_by_article = defaultdict(int)

print("📊 Загрузка данных от WILDBERRIES...")
with open(wb_file, 'r', encoding='utf-8-sig') as f:
    # Skip first line (it's a title, not headers)
    f.readline()
    reader = csv.DictReader(f)
    for row in reader:
        article = row['Артикул продавца']
        warehouse = row['Склад']
        orders_str = row['Заказали, шт'].strip()
        
        if orders_str and orders_str.isdigit():
            orders = int(orders_str)
            wb_data[article][warehouse] += orders
            wb_total_by_article[article] += orders

print(f"✅ Загружено данных по {len(wb_data)} артикулам")
print()

# Parse our data
our_data = defaultdict(lambda: defaultdict(int))
our_total_by_article = defaultdict(int)

print("📊 Загрузка данных из НАШЕЙ ТАБЛИЦЫ...")
with open(our_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        article = row['Артикул продавца']
        
        # Parse warehouses and their orders
        warehouses_str = row['Название склада']
        orders_str = row['Заказы со склада']
        
        if not warehouses_str or not orders_str:
            continue
            
        warehouses_list = [w.strip() for w in warehouses_str.split('\n') if w.strip()]
        orders_list = [o.strip() for o in orders_str.split('\n') if o.strip()]
        
        for wh, ord_str in zip(warehouses_list, orders_list):
            if ord_str.isdigit():
                orders = int(ord_str)
                our_data[article][wh] += orders
                our_total_by_article[article] += orders

print(f"✅ Загружено данных по {len(our_data)} артикулам")
print()

# Compare data
print("="*100)
print("📊 СРАВНЕНИЕ ПО АРТИКУЛАМ:")
print("="*100)
print()

all_articles = sorted(set(wb_data.keys()) | set(our_data.keys()))

total_wb_orders = 0
total_our_orders = 0
critical_errors = []

for article in all_articles:
    wb_total = wb_total_by_article.get(article, 0)
    our_total = our_total_by_article.get(article, 0)
    
    total_wb_orders += wb_total
    total_our_orders += our_total
    
    if wb_total == 0 and our_total == 0:
        continue
    
    diff = our_total - wb_total
    diff_percent = ((our_total - wb_total) / wb_total * 100) if wb_total > 0 else 0
    
    # Status
    if wb_total > 0 and our_total == 0:
        status = "🔴 КРИТИЧНО - НЕТ ДАННЫХ В ТАБЛИЦЕ"
        critical_errors.append({
            'article': article,
            'wb': wb_total,
            'ours': our_total,
            'diff': diff,
            'diff_percent': diff_percent,
            'reason': 'Нет данных в таблице'
        })
    elif abs(diff_percent) > 50:
        status = "🔴 КРИТИЧНО - РАСХОЖДЕНИЕ >50%"
        critical_errors.append({
            'article': article,
            'wb': wb_total,
            'ours': our_total,
            'diff': diff,
            'diff_percent': diff_percent,
            'reason': f'Расхождение {diff_percent:.1f}%'
        })
    elif abs(diff_percent) > 20:
        status = "⚠️  ПРЕДУПРЕЖДЕНИЕ - РАСХОЖДЕНИЕ >20%"
    elif abs(diff_percent) > 5:
        status = "⚠️  Небольшое расхождение"
    else:
        status = "✅ OK"
    
    print(f"📦 {article}")
    print(f"   WB:           {wb_total:4d} заказов")
    print(f"   Таблица:      {our_total:4d} заказов")
    print(f"   Разница:      {diff:+4d} заказов ({diff_percent:+.1f}%)")
    print(f"   Статус:       {status}")
    
    # Show warehouse details for critical errors
    if "КРИТИЧНО" in status or "ПРЕДУПРЕЖДЕНИЕ" in status:
        all_warehouses = set(wb_data[article].keys()) | set(our_data[article].keys())
        print(f"   Склады:")
        for wh in sorted(all_warehouses):
            wb_orders = wb_data[article].get(wh, 0)
            our_orders = our_data[article].get(wh, 0)
            if wb_orders > 0 or our_orders > 0:
                symbol = "❌" if wb_orders != our_orders else "✓"
                print(f"      {symbol} {wh:<40} WB: {wb_orders:3d}  Таблица: {our_orders:3d}")
    print()

print("="*100)
print("📈 ИТОГОВАЯ СТАТИСТИКА:")
print("="*100)
print(f"Всего заказов по WB:        {total_wb_orders}")
print(f"Всего заказов в таблице:    {total_our_orders}")
print(f"Расхождение:                {total_our_orders - total_wb_orders:+d} ({(total_our_orders - total_wb_orders)/total_wb_orders*100:+.1f}%)" if total_wb_orders > 0 else "Нет данных WB")
print(f"Критических ошибок:         {len(critical_errors)}")
print()

if critical_errors:
    print("="*100)
    print("🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ:")
    print("="*100)
    for i, err in enumerate(critical_errors, 1):
        print(f"\n{i}. {err['article']}")
        print(f"   WB: {err['wb']} заказов")
        print(f"   Таблица: {err['ours']} заказов")
        print(f"   Проблема: {err['reason']}")

print("\n")
print("="*100)
print("🔍 ДИАГНОСТИКА ПРОБЛЕМЫ:")
print("="*100)
print("""
ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ:

1️⃣  ПЕРИОД ДАННЫХ НЕ СОВПАДАЕТ
   WB выгрузка: 22-28 октября 2025 (7 дней, фиксированный период)
   Наша таблица: dateFrom = 7 дней назад от момента синхронизации
   
   ❌ ПРОБЛЕМА: Если синхронизация была 27 октября, то период 20-27 октября
                WB показывает 22-28, мы считаем 20-27 - РАЗНЫЕ ПЕРИОДЫ!

2️⃣  API ENDPOINT НЕ ДОКУМЕНТИРОВАН ПОЛНОСТЬЮ
   Используем: GET /api/v1/supplier/orders?dateFrom=2025-10-20T00:00:00&flag=0
   
   ❓ НЕЯСНО:
   - Что означает flag=0? (может быть flag=1 даёт другие данные)
   - Включаются ли отменённые заказы?
   - Учитывается ли quantity в заказе или только count?
   - Могут ли быть дубликаты заказа в разных статусах?

3️⃣  ЛОГИКА ПОДСЧЁТА УПРОЩЕНА
   Текущая реализация: COUNT(orders WHERE nmId=X AND warehouseName=Y)
   
   ❌ НЕ УЧИТЫВАЕМ:
   - Поле is_cancel (отменённые заказы)
   - Поле quantity (количество в заказе - может быть >1)
   - Дубликаты по уникальному ID заказа
   - Статусы заказа

4️⃣  НАЗВАНИЯ СКЛАДОВ МОГУТ НЕ СОВПАДАТЬ
   WB: "Подольск 3"
   API может вернуть: "Подольск-3" или "Подольск 3 "
""")

print("\n" + "="*100)
print("💡 ПЛАН ИСПРАВЛЕНИЯ:")
print("="*100)
print("""
ШАГ 1: ИЗУЧИТЬ РЕАЛЬНУЮ СТРУКТУРУ ОТВЕТА API
----------------------------------------------
Нужно:
- Запросить реальные данные от /api/v1/supplier/orders
- Вывести JSON одной записи заказа
- Проверить какие поля доступны:
  • srid, odid, gNumber (уникальный ID)
  • is_cancel (отменён ли заказ)
  • quantity (количество товара)
  • warehouseName (название склада)
  • date, lastChangeDate (даты для фильтрации)

ШАГ 2: ДОБАВИТЬ ПРАВИЛЬНУЮ ФИЛЬТРАЦИЮ
----------------------------------------------
Изменить логику в product_service.py:

```python
# Фильтровать отменённые заказы
valid_orders = [
    order for order in orders_data 
    if not order.get('is_cancel', False)  # Исключить отменённые
]

# Дедуплицировать по уникальному ID
unique_orders = {}
for order in valid_orders:
    order_id = order.get('srid') or order.get('odid') or order.get('gNumber')
    if order_id and order_id not in unique_orders:
        unique_orders[order_id] = order

# Подсчитать с учётом quantity
for order_id, order in unique_orders.items():
    nm_id = order.get('nmId')
    wh_name = order.get('warehouseName')
    quantity = order.get('quantity', 1)  # Может быть >1!
    
    warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + quantity
```

ШАГ 3: СИНХРОНИЗИРОВАТЬ ПЕРИОДЫ
----------------------------------------------
Опции:
A) Хранить дату последней синхронизации в конфиге
B) Использовать фиксированный период (начало текущей недели/месяца)
C) Параметризовать период через config

Рекомендация: Вариант B - считать за текущую неделю (понедельник-воскресенье)

ШАГ 4: ДОБАВИТЬ ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
----------------------------------------------
```python
logger.info(f"Fetched {len(orders_data)} orders from API")
logger.info(f"After filtering cancelled: {len(valid_orders)} orders")
logger.info(f"After deduplication: {len(unique_orders)} unique orders")
logger.info(f"Total quantity: {sum(o.get('quantity', 1) for o in unique_orders.values())}")
```

ШАГ 5: НОРМАЛИЗАЦИЯ НАЗВАНИЙ СКЛАДОВ
----------------------------------------------
Создать функцию:
```python
def normalize_warehouse_name(name: str) -> str:
    # Убрать лишние пробелы
    name = name.strip()
    # Заменить дефисы
    name = name.replace('-', ' ')
    # Привести к единому регистру первых букв
    return ' '.join(word.capitalize() for word in name.split())
```
""")

print("\n" + "="*100)
print("🎯 ПЕРВЫЙ ШАГ: Изучить структуру ответа API")
print("="*100)
print("""
Запустите диагностический скрипт для просмотра реальной структуры:

```bash
python debug_supplier_orders_structure.py
```

Этот скрипт выведет:
- Пример одного заказа (все поля)
- Список всех уникальных полей во всех заказах
- Статистику по полям (сколько заказов имеют каждое поле)
""")

print("\n" + "="*100)
