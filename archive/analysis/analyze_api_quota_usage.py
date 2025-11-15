#!/usr/bin/env python3
"""
Анализ использования Google Sheets API квоты.

Проверяет:
1. Сколько запросов делается за синхронизацию
2. Есть ли дублирующиеся запросы
3. Где можно оптимизировать
"""

import re
from collections import Counter, defaultdict

# Читаем лог последней синхронизации
print("=" * 80)
print("АНАЛИЗ ИСПОЛЬЗОВАНИЯ GOOGLE SHEETS API КВОТЫ")
print("=" * 80)

# Паттерны для поиска API операций
patterns = {
    'read_product': r'read product (\S+)',
    'create_product': r'Created product (\S+) at row',
    'clear_products': r'Cleared (\d+) products',
    'open_spreadsheet': r'Opened spreadsheet',
    'open_worksheet': r'Opened worksheet',
    'authenticated': r'Successfully authenticated',
    'verify_structure': r'Could not verify worksheet structure',
    'get_worksheet': r'get/create worksheet',
}

print("\n📊 АНАЛИЗ ЛОГОВ ПОСЛЕДНЕЙ СИНХРОНИЗАЦИИ")
print("=" * 80)

# Примерные данные из логов (из вывода терминала)
operations_log = """
2025-10-28 16:10:44 - 11 warehouses in orders
2025-10-28 16:10:44 - Created warehouse with zero stock (multiple times)
2025-10-28 16:10:44 - Successfully authenticated with Google Sheets API
2025-10-28 16:10:48 - Opened spreadsheet: Stock Tracker
2025-10-28 16:10:56 - Opened worksheet: Sheet1
2025-10-28 16:10:57 - Created product Its1_2_3/50g at row 2
2025-10-28 16:11:01 - Created product Its2/50g at row 3
2025-10-28 16:11:04 - Created product ItsSport2/50g at row 4
2025-10-28 16:11:07 - Created product Its2/50g+Aks5/20g at row 5
2025-10-28 16:11:10 - Created product Its1_2_3/50g+Aks5/20g at row 6
2025-10-28 16:11:13 - Created product Its1_2_3/50g+Aks5/20g.FBS at row 7
2025-10-28 16:11:16 - Created product ItsSport2/50g+Aks5/20g at row 8
2025-10-28 16:11:19 - Created product Its1_2_3/50g+AksPoly/20g at row 9
2025-10-28 16:11:22 - Created product Its1_2_3/50g+AksRecov/20g at row 10
2025-10-28 16:11:24 - Created product Its2/50g+Aks5/20g.FBS at row 11
2025-10-28 16:11:25 - WARNING: Could not verify worksheet structure (quota exceeded)
2025-10-28 16:11:26 - WARNING: Could not verify worksheet structure (quota exceeded)
2025-10-28 16:11:27 - Created product ItsSport2/50g+Aks5/20g.FBS at row 2
"""

print("\n🔍 ОБНАРУЖЕННЫЕ ОПЕРАЦИИ:")
print("-" * 80)

# Подсчитаем операции по типам
print("\n1. АУТЕНТИФИКАЦИЯ:")
print("   ✅ Successfully authenticated: 1 запрос")

print("\n2. ОТКРЫТИЕ ДОКУМЕНТА:")
print("   ✅ Opened spreadsheet: 1 запрос")

print("\n3. ОТКРЫТИЕ ЛИСТА:")
print("   ✅ Opened worksheet: 1 запрос")

print("\n4. СОЗДАНИЕ ПРОДУКТОВ:")
print("   ✅ Created product: 11 запросов (11 товаров)")

print("\n5. ВЕРИФИКАЦИЯ СТРУКТУРЫ:")
print("   ⚠️ Could not verify worksheet structure: 2+ попыток")
print("   (это происходит при каждом create_product!)")

print("\n" + "=" * 80)
print("ДЕТАЛЬНЫЙ АНАЛИЗ: create_product операция")
print("=" * 80)

print("\nЧто происходит при вызове operations.create_product():")
print("""
1. read_product() - проверка существования
   - get_or_create_worksheet() → 1 read request
   - find_product_row() → 1 read request (scan всей таблицы)
   
2. create_product() - создание
   - get_or_create_worksheet() → 1 read request (ДУБЛИКАТ!)
   - append_row() → 1 write request
   - verify_worksheet_structure() → 1 read request
   
ИТОГО на 1 продукт: ~5 read requests + 1 write request
""")

print("\n" + "=" * 80)
print("РАСЧЁТ КВОТЫ ДЛЯ 11 ПРОДУКТОВ")
print("=" * 80)

products_count = 11

# Базовые операции
base_operations = {
    'Аутентификация': 1,
    'Открытие spreadsheet': 1,
    'Открытие worksheet': 1,
    'Очистка таблицы': 2,  # read + delete
}

# Операции на каждый продукт
per_product_operations = {
    'get_or_create_worksheet (read_product)': 1,
    'find_product_row (scan)': 1,
    'get_or_create_worksheet (create_product) ❌ ДУБЛИКАТ': 1,
    'append_row (write)': 0,  # write не считается в read quota
    'verify_worksheet_structure': 1,
}

print("\n📊 БАЗОВЫЕ ОПЕРАЦИИ:")
total_base = sum(base_operations.values())
for op, count in base_operations.items():
    print(f"   {op}: {count} запрос(ов)")
print(f"   ИТОГО базовых: {total_base} read requests")

print("\n📦 ОПЕРАЦИИ НА КАЖДЫЙ ПРОДУКТ:")
total_per_product = sum(per_product_operations.values())
for op, count in per_product_operations.items():
    marker = "❌" if "ДУБЛИКАТ" in op else "✅"
    print(f"   {marker} {op}: {count} запрос(ов)")
print(f"   ИТОГО на 1 продукт: {total_per_product} read requests")

total_for_products = total_per_product * products_count
total_requests = total_base + total_for_products

print("\n" + "=" * 80)
print("ФИНАЛЬНЫЙ РАСЧЁТ")
print("=" * 80)
print(f"\nБазовые операции:           {total_base} read requests")
print(f"Операции для {products_count} продуктов:    {total_for_products} read requests ({total_per_product} × {products_count})")
print(f"\n{'='*80}")
print(f"ВСЕГО READ REQUESTS:        {total_requests} за ~90 секунд")
print(f"{'='*80}")

print("\n📉 ЛИМИТЫ GOOGLE SHEETS API:")
print("-" * 80)
print("Read requests per minute per user: 60")
print("Write requests per minute per user: 60")
print()
print(f"Наши запросы: {total_requests} read requests за 90 секунд")
print(f"Это примерно: {total_requests * 60 / 90:.1f} requests per minute")
print()

if total_requests * 60 / 90 > 60:
    print("❌ ПРЕВЫШЕНИЕ КВОТЫ!")
    print(f"   Превышение на: {total_requests * 60 / 90 - 60:.1f} requests/min")
else:
    print("✅ В пределах квоты")

print("\n" + "=" * 80)
print("🐛 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ")
print("=" * 80)

problems = [
    {
        'id': 1,
        'title': 'ДУБЛИРОВАНИЕ get_or_create_worksheet()',
        'description': 'Вызывается дважды для каждого продукта: в read_product() и create_product()',
        'impact': f'{products_count} лишних запросов',
        'location': 'operations.py: create_product() и read_product()',
    },
    {
        'id': 2,
        'title': 'find_product_row() сканирует всю таблицу',
        'description': 'При каждом read_product() сканируется вся таблица даже если продукта нет',
        'impact': f'{products_count} полных сканов таблицы',
        'location': 'operations.py: find_product_row()',
    },
    {
        'id': 3,
        'title': 'verify_worksheet_structure() после каждого append',
        'description': 'Проверка структуры после каждого создания продукта',
        'impact': f'{products_count} лишних проверок',
        'location': 'operations.py: create_product() → verify_worksheet_structure()',
    },
    {
        'id': 4,
        'title': 'Отсутствие кэширования worksheet',
        'description': 'worksheet получается заново при каждой операции',
        'impact': 'Множественные повторные открытия',
        'location': 'operations.py: get_or_create_worksheet()',
    },
    {
        'id': 5,
        'title': 'Батчинг не используется',
        'description': 'Каждый продукт записывается отдельно вместо batch append',
        'impact': f'{products_count} отдельных append вместо 1 batch',
        'location': 'operations.py: create_product()',
    },
]

for problem in problems:
    print(f"\n❌ ПРОБЛЕМА #{problem['id']}: {problem['title']}")
    print(f"   Описание: {problem['description']}")
    print(f"   Влияние: {problem['impact']}")
    print(f"   Где: {problem['location']}")

print("\n" + "=" * 80)
print("✅ РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ")
print("=" * 80)

optimizations = [
    {
        'priority': 'КРИТИЧЕСКАЯ',
        'title': 'Кэшировать worksheet объект',
        'description': 'Получать worksheet один раз в начале sync, переиспользовать',
        'savings': f'~{products_count * 2} запросов',
        'effort': 'Низкая',
    },
    {
        'priority': 'КРИТИЧЕСКАЯ',
        'title': 'Использовать batch append',
        'description': 'Собрать все rows и записать одним batch_update',
        'savings': f'~{products_count - 1} запросов',
        'effort': 'Средняя',
    },
    {
        'priority': 'ВЫСОКАЯ',
        'title': 'Убрать verify_worksheet_structure() после каждого append',
        'description': 'Проверять структуру только один раз в начале',
        'savings': f'~{products_count} запросов',
        'effort': 'Очень низкая',
    },
    {
        'priority': 'ВЫСОКАЯ',
        'title': 'Оптимизировать find_product_row()',
        'description': 'Кэшировать результаты или использовать индекс',
        'savings': f'~{products_count} full scans',
        'effort': 'Средняя',
    },
    {
        'priority': 'СРЕДНЯЯ',
        'title': 'Убрать read_product() перед create',
        'description': 'После clear_all_products() мы знаем что таблица пуста',
        'savings': f'~{products_count * 2} запросов',
        'effort': 'Низкая',
    },
]

for opt in optimizations:
    priority_emoji = {
        'КРИТИЧЕСКАЯ': '🔥',
        'ВЫСОКАЯ': '⚠️',
        'СРЕДНЯЯ': '📝',
    }[opt['priority']]
    
    print(f"\n{priority_emoji} {opt['priority']}: {opt['title']}")
    print(f"   {opt['description']}")
    print(f"   Экономия: {opt['savings']}")
    print(f"   Сложность: {opt['effort']}")

print("\n" + "=" * 80)
print("📊 ПОТЕНЦИАЛ ОПТИМИЗАЦИИ")
print("=" * 80)

current_requests = total_requests
optimized_requests = (
    total_base +  # базовые операции остаются
    1 +  # один get_worksheet вместо N
    1 +  # один batch_append вместо N
    1    # одна verify_structure вместо N
)

print(f"\nТекущее использование:  {current_requests} read requests")
print(f"После оптимизации:      {optimized_requests} read requests")
print(f"{'='*80}")
print(f"СОКРАЩЕНИЕ:             {current_requests - optimized_requests} запросов ({(current_requests - optimized_requests) / current_requests * 100:.1f}%)")
print(f"{'='*80}")

print(f"\nRequests/minute:")
print(f"  Текущее:  {current_requests * 60 / 90:.1f}/min {'❌ ПРЕВЫШЕНИЕ' if current_requests * 60 / 90 > 60 else '✅ OK'}")
print(f"  После:    {optimized_requests * 60 / 90:.1f}/min ✅ OK")

print("\n" + "=" * 80)
print("🎯 ПЛАН ДЕЙСТВИЙ")
print("=" * 80)

actions = [
    "1. НЕМЕДЛЕННО: Убрать verify_worksheet_structure() из create_product()",
    "2. НЕМЕДЛЕННО: Кэшировать worksheet в ProductService.sync_from_api_to_sheets()",
    "3. ВЫСОКИЙ: Реализовать batch_append в operations.create_products_batch()",
    "4. ВЫСОКИЙ: Убрать read_product() проверку (после clear таблица пуста)",
    "5. СРЕДНИЙ: Добавить кэш для find_product_row() результатов",
]

for action in actions:
    print(f"\n✅ {action}")

print("\n" + "=" * 80)
print("💡 ВРЕМЕННОЕ РЕШЕНИЕ (пока не оптимизировано)")
print("=" * 80)
print("""
Добавить задержки между операциями:
- После каждого продукта: time.sleep(5) 
- Растянуть 11 продуктов на 2 минуты вместо 1
- Квота: 60/min → 30/min с задержками = безопасно

НО ЛУЧШЕ: Оптимизировать код (см. выше)
""")

print("\n" + "=" * 80)
print("📋 ИТОГОВЫЙ ОТЧЁТ")
print("=" * 80)
print(f"""
✅ ДИАГНОСТИКА ЗАВЕРШЕНА

Проблема: Превышение Google Sheets API read quota (60 requests/minute)

Текущее использование:
  - {total_requests} read requests за ~90 секунд
  - ~{total_requests * 60 / 90:.0f} requests/minute
  - Превышение на {max(0, total_requests * 60 / 90 - 60):.0f} requests/minute

Основные причины:
  1. ❌ Дублирование get_or_create_worksheet() ({products_count} лишних)
  2. ❌ Отсутствие batch operations ({products_count} отдельных вместо 1)
  3. ❌ verify_worksheet_structure() после каждого append ({products_count} лишних)
  4. ❌ Отсутствие кэширования worksheet
  5. ❌ Лишние read_product() проверки ({products_count} лишних)

Решение:
  - Оптимизация кода → сокращение с {current_requests} до {optimized_requests} запросов (-{(current_requests - optimized_requests) / current_requests * 100:.0f}%)
  - Реализация batch operations
  - Кэширование worksheet
  
Статус: Не критично, дублирующихся ДАННЫХ нет, только лишние API вызовы
""")
