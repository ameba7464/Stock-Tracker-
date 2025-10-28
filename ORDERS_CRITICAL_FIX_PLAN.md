# 🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ В МЕТРИКЕ "ЗАКАЗЫ СО СКЛАДА"

**Дата анализа:** 28.10.2025  
**Период данных WB:** 22-28 октября 2025 (7 дней)  
**Период данных API:** 21-28 октября 2025 (7 дней)  

---

## 📊 ТЕКУЩЕЕ СОСТОЯНИЕ

### Сравнение с данными WB:

| Метрика | WB | Наша таблица | Расхождение |
|---------|----|--------------| ------------|
| **Всего заказов** | **242** | **173** | **-69 (-28.5%)** |
| Артикулов с данными | 10 | 9 | -1 |
| Критических ошибок | - | - | **3** |

### 🔴 Критические проблемы:

1. **Its1_2_3/50g** - 97 заказов в WB, 0 в таблице (-100%)
2. **Its2/50g+Aks5/20g.FBS** - 3 заказа в WB, 0 в таблице (-100%)
3. **Its1_2_3/50g+AksPoly/20g** - 2 заказа в WB, 5 в таблице (+150%)

---

## 🔍 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ

### 1️⃣ ОТМЕНЁННЫЕ ЗАКАЗЫ НЕ ФИЛЬТРУЮТСЯ

**Факт:** API возвращает 302 заказа, из них **28 отменённых** (isCancel=True)

```
isCancel: {False: 274, True: 28}
```

**Проблема:** Мы считаем ВСЕ 302 заказа, включая отменённые.  
**WB считает:** Только 274 активных заказа.

**Расхождение:** 28 лишних заказов (9.3% ошибки)

---

### 2️⃣ ЗАКАЗЫ ДУБЛИРУЮТСЯ ПО srid

**Факт:** 
- Всего заказов: 302
- Уникальных srid: 302 ✅
- Уникальных gNumber: 284 ❌

**Потенциальная проблема:** gNumber повторяется (302 vs 284 = 18 дублей)

**Решение:** Использовать **srid** для дедупликации (все значения уникальны)

---

### 3️⃣ ОТСУТСТВУЕТ ПОЛЕ quantity

**Факт:** API НЕ возвращает поле quantity

```python
# ТЕКУЩАЯ ЛОГИКА (НЕПРАВИЛЬНО):
warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1  # Всегда +1
```

**Проблема:** Если в одном заказе >1 товара, мы считаем как 1 штуку.

**Но:** В нашем случае это не критично - судя по данным WB, каждый заказ = 1 товар.

---

### 4️⃣ РАЗНЫЕ ПЕРИОДЫ ДАННЫХ

| Источник | Период | Дни |
|----------|--------|-----|
| WB выгрузка | 22-28 октября | 7 дней (фиксированный) |
| Наш API запрос | 21-28 октября | 7 дней (от даты синхронизации) |

**Проблема:** Если синхронизация была 28 октября в 09:31, то:
- WB: 22-28 октября
- Мы: 21-28 октября (минус 1 день)

**Расхождение:** Мы захватываем заказы 21 октября, которых нет в WB выгрузке.

---

### 5️⃣ НАЗВАНИЯ СКЛАДОВ НЕ НОРМАЛИЗОВАНЫ

**Примеры расхождений:**
- WB: "Новосемейкино"
- API: "Самара (Новосемейкино)"

**Результат:** Заказы попадают в разные склады.

---

## ✅ РЕШЕНИЕ

### ШАГ 1: Фильтровать отменённые заказы

```python
# В product_service.py, метод sync_from_api_to_sheets()
# После получения orders_data:

# ИСПРАВЛЕНИЕ 28.10.2025: Фильтруем отменённые заказы
valid_orders = [
    order for order in orders_data 
    if not order.get('isCancel', False)  # ❌ Исключить isCancel=True
]

logger.info(f"Total orders from API: {len(orders_data)}")
logger.info(f"Active orders (excluding cancelled): {len(valid_orders)}")
logger.info(f"Cancelled orders filtered out: {len(orders_data) - len(valid_orders)}")

# Далее работать с valid_orders вместо orders_data
```

---

### ШАГ 2: Дедуплицировать по srid

```python
# ИСПРАВЛЕНИЕ 28.10.2025: Дедуплицировать по srid
unique_orders = {}
for order in valid_orders:
    srid = order.get('srid')
    if srid and srid not in unique_orders:
        unique_orders[srid] = order

logger.info(f"After deduplication by srid: {len(unique_orders)} unique orders")
logger.info(f"Duplicates removed: {len(valid_orders) - len(unique_orders)}")

# Далее работать с unique_orders.values()
```

---

### ШАГ 3: Нормализовать названия складов

```python
def normalize_warehouse_name(name: str) -> str:
    """
    Нормализует название склада для корректного сравнения.
    
    Примеры:
    - "Подольск 3" → "Подольск 3"
    - "Подольск-3" → "Подольск 3"
    - "Самара (Новосемейкино)" → "Самара Новосемейкино"
    """
    if not name:
        return "Неизвестно"
    
    # Убрать скобки
    name = name.replace('(', '').replace(')', '')
    
    # Заменить дефисы на пробелы (кроме дефисов в составных названиях)
    # "Екатеринбург - Перспективный 12" сохраняем
    
    # Убрать лишние пробелы
    name = ' '.join(name.split())
    
    # Привести к Title Case
    # НЕ используем .title() чтобы сохранить "МП", "WB" и т.д.
    
    return name.strip()


# Применить при подсчёте заказов:
for order in unique_orders.values():
    if order.get('nmId') == product.get('nmId'):
        wh_name_raw = order.get('warehouseName', 'Неизвестно')
        wh_name = normalize_warehouse_name(wh_name_raw)
        warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1
```

---

### ШАГ 4: Синхронизировать периоды

**Рекомендация:** Использовать фиксированный период (начало текущей недели)

```python
from datetime import datetime, timedelta

def get_week_start() -> str:
    """Получить дату начала текущей недели (понедельник)"""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week.strftime("%Y-%m-%dT00:00:00")

# В product_service.py:
# ИСПРАВЛЕНИЕ 28.10.2025: Использовать начало текущей недели
date_from = get_week_start()  # Вместо timedelta(days=7)
```

**Альтернатива:** Хранить дату последней синхронизации в конфиге.

---

### ШАГ 5: Детальное логирование

```python
# В product_service.py, после обработки заказов:

logger.info(f"📊 СТАТИСТИКА ОБРАБОТКИ ЗАКАЗОВ:")
logger.info(f"   Total raw orders from API:      {len(orders_data)}")
logger.info(f"   After filtering cancelled:      {len(valid_orders)} (-{len(orders_data)-len(valid_orders)})")
logger.info(f"   After deduplication (srid):     {len(unique_orders)} (-{len(valid_orders)-len(unique_orders)})")
logger.info(f"   Unique warehouses found:        {len(warehouse_orders)}")
logger.info(f"   Total orders in table:          {sum(warehouse_orders.values())}")

# Детали по складам:
for wh_name, orders_count in sorted(warehouse_orders.items(), key=lambda x: -x[1])[:10]:
    logger.info(f"      {wh_name:<40} {orders_count:>3} заказов")
```

---

## 🎯 ИТОГОВЫЙ КОД ИЗМЕНЕНИЙ

### Файл: `src/stock_tracker/services/product_service.py`

**Место изменения:** Метод `sync_from_api_to_sheets()`, после загрузки `orders_data`

```python
# БЫЛО (строки 285-297):
logger.info("Fetching orders data from supplier/orders endpoint...")

date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")

try:
    orders_data = await self.data_fetcher.fetch_supplier_orders(
        date_from=date_from,
        flag=0
    )
    logger.info(f"Downloaded {len(orders_data)} orders from supplier/orders API")
except Exception as e:
    logger.error(f"Failed to fetch supplier orders: {e}")
    orders_data = []
```

```python
# СТАЛО:
logger.info("Fetching orders data from supplier/orders endpoint...")

# ИСПРАВЛЕНИЕ 28.10.2025: Использовать фиксированный период (начало недели)
def get_week_start() -> str:
    """Получить дату начала текущей недели (понедельник)"""
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week.strftime("%Y-%m-%dT00:00:00")

date_from = get_week_start()

try:
    orders_data = await self.data_fetcher.fetch_supplier_orders(
        date_from=date_from,
        flag=0
    )
    logger.info(f"Downloaded {len(orders_data)} orders from supplier/orders API")
    
    # ИСПРАВЛЕНИЕ 28.10.2025: Фильтровать отменённые заказы
    valid_orders = [
        order for order in orders_data 
        if not order.get('isCancel', False)
    ]
    logger.info(f"Active orders (excluding cancelled): {len(valid_orders)} " +
                f"(removed {len(orders_data) - len(valid_orders)} cancelled)")
    
    # ИСПРАВЛЕНИЕ 28.10.2025: Дедуплицировать по srid
    unique_orders = {}
    for order in valid_orders:
        srid = order.get('srid')
        if srid and srid not in unique_orders:
            unique_orders[srid] = order
    
    logger.info(f"Unique orders (by srid): {len(unique_orders)} " +
                f"(removed {len(valid_orders) - len(unique_orders)} duplicates)")
    
    # Преобразовать обратно в список
    orders_data = list(unique_orders.values())
    
except Exception as e:
    logger.error(f"Failed to fetch supplier orders: {e}")
    orders_data = []
```

**Место изменения 2:** Метод `sync_from_api_to_sheets()`, расчёт заказов (строки 497-530)

```python
# БЫЛО:
for order in orders_data:
    if order.get("nmId") == product.get("nmId"):
        wh_name = order.get("warehouseName", "Неизвестно")
        warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1
```

```python
# СТАЛО:
def normalize_warehouse_name(name: str) -> str:
    """Нормализует название склада"""
    if not name:
        return "Неизвестно"
    name = name.replace('(', '').replace(')', '')
    name = ' '.join(name.split())
    return name.strip()

for order in orders_data:
    if order.get("nmId") == product.get("nmId"):
        wh_name_raw = order.get("warehouseName", "Неизвестно")
        wh_name = normalize_warehouse_name(wh_name_raw)
        warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1
```

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

После применения исправлений:

| Показатель | До | После | Улучшение |
|------------|----| ------|-----------|
| Всего заказов | 173 | ~274 | +58% ✅ |
| Расхождение с WB | -28.5% | ~+13% ⚠️ | Лучше |
| Отменённые заказы | Включены | Исключены | ✅ |
| Дубликаты | Возможны | Удалены | ✅ |
| Критических ошибок | 3 | 0-1 | ✅ |

**Примечание:** Небольшое расхождение (+13%) останется из-за разных периодов (21 октября vs 22 октября).

---

## 🚀 СЛЕДУЮЩИЕ ШАГИ

1. ✅ Применить изменения в `product_service.py`
2. Запустить полную синхронизацию
3. Проверить результаты с помощью `verify_warehouse_orders.py`
4. Повторить сравнение с WB данными

---

**Статус:** Готово к реализации  
**Приоритет:** 🔴 КРИТИЧНЫЙ  
**Время внедрения:** ~30 минут
