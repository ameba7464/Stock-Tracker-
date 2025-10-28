# 🚨 КРИТИЧЕСКАЯ ДИАГНОСТИКА: ЛОГИКА "ЗАКАЗЫ СО СКЛАДА"

**Дата:** 27 октября 2025 г.  
**Статус:** МНОЖЕСТВЕННЫЕ КРИТИЧЕСКИЕ ОШИБКИ НАЙДЕНЫ

---

## 🔍 НАЙДЕННЫЕ ПРОБЛЕМЫ

### ❌ ПРОБЛЕМА #1: Заказы берутся из НЕПРАВИЛЬНОГО источника (КРИТИЧНО!)

**Местоположение:** `src/stock_tracker/services/product_service.py:463-495`

**Текущая НЕПРАВИЛЬНАЯ логика:**
```python
# ❌ ОШИБКА: Используется warehouse_remains вместо supplier/orders
warehouse_remains = await self.wb_client.download_warehouse_remains(task_id)

# ❌ ОШИБКА: orders_data пустой!
orders_data = []  # Orders data не нужен - заказы уже встроены в warehouse_remains

# ❌ ОШИБКА: Заказы берутся из виртуального склада
if warehouse_name == "В пути до получателей":
    warehouse_orders = warehouse_quantity  # ЭТО ЛОГИСТИКА, НЕ ЗАКАЗЫ!
```

**Что происходит:**
1. Код НЕ вызывает `/supplier/orders` эндпоинт
2. Пытается взять "заказы" из quantity виртуального склада "В пути до получателей"
3. Это **транзитные товары**, а НЕ активные заказы от клиентов

**Правильная логика из urls.md:**
```
Заказы:
- Всего по товару: количество записей в /supplier/orders с nmId
- По складу: количество записей где совпадают nmId + warehouseName

Источник: /supplier/orders эндпоинт
```

**Почему значения абсолютно неправильные:**
- "В пути до получателей" - это товары в логистике WB
- Реальные заказы клиентов находятся в `/supplier/orders`
- Количество в транзите ≠ количество заказов

---

### ❌ ПРОБЛЕМА #2: Склады с нулевыми остатками НЕ отображаются

**Местоположение:** `src/stock_tracker/core/calculator.py:535-565`

**Проблемный код:**
```python
# Process warehouse remains data
for warehouse in item["warehouses"]:
    warehouse_name = normalize_warehouse_name(warehouse_name_raw)
    quantity = warehouse.get("quantity", 0)
    
    if warehouse_name and is_real_warehouse(warehouse_name):
        # ❌ ОШИБКА: Создается склад ТОЛЬКО если есть остатки
        if warehouse_name not in group["warehouses"]:
            group["warehouses"][warehouse_name] = {
                "stock": 0,
                "orders": 0,
                ...
            }
        group["warehouses"][warehouse_name]["stock"] += quantity
```

**Что происходит:**
1. Склад создается только при обработке `warehouse_remains`
2. Если на складе нет остатков (quantity=0), он НЕ попадает в response
3. Потом при обработке `orders_data` заказы для несуществующего склада теряются

**Сценарий потери данных:**
```
1. Склад "Новосибирск": stock=0 (нет в warehouse_remains)
2. Заказы на "Новосибирск": 15 заказов (есть в supplier/orders)
3. РЕЗУЛЬТАТ: Склад НЕ отображается, заказы потеряны
```

**Правильная логика:**
- Нужно создавать склады ИЗ ОБОИХ источников:
  1. warehouse_remains (для остатков)
  2. supplier/orders (для заказов)
- Склад должен отображаться, даже если stock=0, но orders>0

---

### ❌ ПРОБЛЕМА #3: Неправильная интерпретация V1 API

**Файл с ошибочным отчётом:** `V1_API_ORDERS_FIX_REPORT.md`

**Ошибочное утверждение:**
> "В пути до получателей" (quantity=70) = ТЕКУЩИЕ ЗАКАЗЫ в пути к клиентам

**ПРАВДА:**
- "В пути до получателей" - это **ТРАНЗИТ**, а не заказы
- Это товары, которые УЖЕ отправлены из склада WB клиенту
- Настоящие заказы (которые нужно отобразить) находятся в `/supplier/orders`

**Структура V1 API warehouse_remains:**
```json
{
  "warehouses": [
    {
      "warehouseName": "В пути до получателей",
      "quantity": 70  ← ТРАНЗИТ (товары в пути)
    },
    {
      "warehouseName": "Краснодар", 
      "quantity": 52  ← ОСТАТКИ на складе
    }
  ]
}
```

**Структура supplier/orders (ПРАВИЛЬНЫЙ источник):**
```json
{
  "nmId": 123456,
  "supplierArticle": "WB001",
  "warehouseName": "Краснодар",  ← Склад где размещен заказ
  "isCancel": false
}
```

---

### ❌ ПРОБЛЕМА #4: orders_data НЕ используется

**Местоположение:** `src/stock_tracker/services/product_service.py:297`

```python
# Orders data не нужен - заказы уже встроены в warehouse_remains
orders_data = []  # ❌ КРИТИЧЕСКАЯ ОШИБКА!
```

**Комментарий НЕПРАВИЛЬНЫЙ:**
- Заказы НЕ встроены в warehouse_remains
- warehouse_remains содержит ТОЛЬКО остатки + логистику
- Заказы ДОЛЖНЫ браться из supplier/orders

---

### ❌ ПРОБЛЕМА #5: Конфликт с urls.md спецификацией

**urls.md чётко указывает:**
```markdown
Заказы:
Всего по товару: подсчитывается количество записей в /supplier/orders с nmId
По складу: подсчитывается количество записей где совпадают nmId + warehouseName

Источник: /supplier/orders эндпоинт
```

**Текущий код НАРУШАЕТ спецификацию:**
- НЕ использует /supplier/orders
- НЕ считает записи
- Берет quantity из виртуального склада

---

## ✅ ПРАВИЛЬНОЕ РЕШЕНИЕ

### Шаг 1: Вызвать supplier/orders API

```python
# ИСПРАВИТЬ в product_service.py
async def sync_from_api_to_sheets(self) -> SyncSession:
    # ... получение warehouse_remains ...
    
    # ✅ ДОБАВИТЬ: Получить заказы
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    orders_data = await self.wb_client.get_supplier_orders(date_from)
    logger.info(f"Downloaded {len(orders_data)} orders from supplier/orders")
    
    # ✅ ИСПОЛЬЗОВАТЬ оба источника
    for api_record in warehouse_remains:
        product = self._convert_api_record_to_product(
            api_record, 
            orders_data  # ← Передать реальные заказы!
        )
```

### Шаг 2: Правильно обработать warehouse_remains

```python
# ИСПРАВИТЬ в _convert_api_record_to_product
if 'warehouses' in api_record:
    for wh in api_record['warehouses']:
        warehouse_name = wh.get('warehouseName', 'Unknown')
        
        # ✅ УДАЛИТЬ неправильную логику с "В пути до получателей"
        # ❌ УБРАТЬ: if warehouse_name == "В пути до получателей": ...
        
        # ✅ ПРАВИЛЬНО: Фильтровать только реальные склады
        if not is_real_warehouse(warehouse_name):
            continue
        
        # ✅ Остатки берем из warehouse_remains
        warehouse_stock = wh.get('quantity', 0)
        
        # ✅ Заказы будут добавлены позже из orders_data
        warehouse_orders = 0  # Пока 0, заполним из orders_data
```

### Шаг 3: Обработать заказы из supplier/orders

```python
# ИСПРАВИТЬ: Использовать calculator для подсчета заказов
from stock_tracker.core.calculator import WildberriesCalculator

calculator = WildberriesCalculator()

# ✅ Для каждого склада посчитать заказы
for warehouse in product.warehouses:
    orders_count = calculator.calculate_warehouse_orders(
        orders_data, 
        nm_id, 
        warehouse.name
    )
    warehouse.orders = orders_count
```

### Шаг 4: Создавать склады даже с нулевыми остатками

```python
# ИСПРАВИТЬ в calculator.py
# Process orders data - создавать склады если их нет
for order in orders_data:
    warehouse_name = normalize_warehouse_name(order.get("warehouseName", ""))
    
    if warehouse_name and is_real_warehouse(warehouse_name):
        # ✅ СОЗДАТЬ склад если его нет (даже с нулевым stock)
        if warehouse_name not in group["warehouses"]:
            group["warehouses"][warehouse_name] = {
                "stock": 0,  # ← Нет остатков, но есть заказы!
                "orders": 0,
                "warehouse_type": order.get("warehouseType", ""),
                "is_fbs": is_marketplace_warehouse(warehouse_name)
            }
        
        group["warehouses"][warehouse_name]["orders"] += 1
```

---

## 🎯 ПЛАН ИСПРАВЛЕНИЯ

### Приоритет 1: КРИТИЧНО - Использовать supplier/orders

1. ✅ Вызвать `get_supplier_orders()` в `sync_from_api_to_sheets()`
2. ✅ Передать `orders_data` в `_convert_api_record_to_product()`
3. ✅ Использовать `calculator.calculate_warehouse_orders()`

### Приоритет 2: КРИТИЧНО - Убрать неправильную логику

1. ✅ Удалить код с "В пути до получателей" = заказы
2. ✅ Убрать комментарий "заказы встроены в warehouse_remains"
3. ✅ Исправить V1_API_ORDERS_FIX_REPORT.md

### Приоритет 3: Важно - Склады с нулевыми остатками

1. ✅ Создавать склады из orders_data даже если нет в warehouse_remains
2. ✅ Показывать склады с stock=0, orders>0

---

## 📊 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

### После исправления:

**Колонка "Заказы со склада":**
```
Краснодар
Чехов 1
Новосибирск  ← Будет отображаться даже если stock=0
```

**Значения заказов:**
```
5   ← Реальное количество записей в supplier/orders для Краснодара
12  ← Реальное количество записей для Чехова
3   ← Реальное количество записей для Новосибирска (был скрыт!)
```

**Источник данных:**
- ✅ Из `/supplier/orders` эндпоинта (правильно!)
- ✅ Подсчёт записей по nmId + warehouseName
- ✅ Соответствует urls.md спецификации

---

## 🔧 ФАЙЛЫ ДЛЯ ИСПРАВЛЕНИЯ

1. **src/stock_tracker/services/product_service.py**
   - Строки 270-300: Добавить вызов get_supplier_orders()
   - Строки 463-495: Убрать логику "В пути до получателей"
   - Строки 428-530: Использовать calculator для заказов

2. **src/stock_tracker/core/calculator.py**
   - Строки 535-665: Создавать склады из orders_data

3. **V1_API_ORDERS_FIX_REPORT.md**
   - Исправить ошибочную информацию о структуре API

---

**Автор диагностики:** GitHub Copilot  
**Дата:** 27.10.2025 21:30  
**Статус:** Готово к исправлению
