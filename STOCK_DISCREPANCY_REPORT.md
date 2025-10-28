# 🔍 ОТЧЁТ: Расхождение остатков - Диагностика и решение

**Дата**: 28 октября 2025  
**Товар**: Its1_2_3/50g (WB nmId: 163383326)  
**Проблема**: Остатки в таблице НЕ соответствуют данным на Wildberries

---

## 📊 СИМПТОМЫ

### Что показывает Wildberries:
- **Остатки (всего)**: 3,459 шт
- **Из них МП/FBS**: 2,984 шт
- **Остатки на складах WB (FBO)**: ~475 шт

### Что показывает таблица:
- **Остатки (всего)**: 475 шт ❌ НЕВЕРНО
- **Склады**: Только склады WB (FBO)
- **МП/FBS**: Отсутствует ❌ НЕ УЧИТЫВАЮТСЯ

### Расхождение:
```
WB:      3,459 остатков
Таблица:   475 остатков
-------
Потеря:  2,984 остатков (-86%)
```

---

## 🔍 КОРЕНЬ ПРОБЛЕМЫ

### Текущая архитектура (НЕВЕРНАЯ):

```
┌─────────────────────────────────────┐
│  ProductService.sync_from_api...    │
├─────────────────────────────────────┤
│                                     │
│  1. Warehouse API v1                │
│     ├─ FBO остатки (склады WB)      │ ← ТОЛЬКО ЭТИ ДАННЫЕ
│     └─ НЕТ FBS/МП                   │
│                                     │
│  2. Orders API v1                   │
│     └─ Заказы (всё корректно)       │
│                                     │
│  3. Calculate total_stock           │
│     = sum(FBO остатки)              │ ← НЕВЕРНЫЙ РАСЧЁТ
│     = 475 (вместо 3,459)            │
└─────────────────────────────────────┘
```

### Почему это происходит:

**Warehouse API v1** (`/api/v1/warehouse_remains`) возвращает:
- ✅ Остатки на **складах Wildberries** (FBO)
- ❌ **НЕ возвращает** остатки на **вашем складе** (FBS/МП)

**Analytics API v2** (`/api/v2/stocks-report/products`) возвращает:
- ✅ Остатки **FBO** (склады WB)
- ✅ Остатки **FBS/МП** (ваш склад)
- ✅ **ИТОГО** = FBO + FBS/МП = полные остатки

**Код использует:**
```python
# product_service.py:270-290
warehouse_remains = await self.wb_client.download_warehouse_remains(task_id)
# ← Это ТОЛЬКО FBO остатки!

# Затем:
total_stock = sum(wh.get('quantity') for wh in warehouse['warehouses'])
# ← Сумма ТОЛЬКО FBO остатков = 475 вместо 3,459
```

---

## ✅ ПРАВИЛЬНАЯ АРХИТЕКТУРА

```
┌──────────────────────────────────────────────────────────┐
│  ProductService.sync_from_api... (ИСПРАВЛЕННЫЙ)          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. Analytics API v2 (НОВОЕ!)                           │
│     └─ total_stock = 3,459 (FBO + FBS)                  │ ← ПОЛНЫЕ ОСТАТКИ
│                                                          │
│  2. Warehouse API v1                                    │
│     └─ FBO breakdown по складам WB = 475                 │ ← BREAKDOWN FBO
│                                                          │
│  3. Calculate FBS/МП (НОВОЕ!)                           │
│     = total_stock - sum(FBO остатки)                    │
│     = 3,459 - 475 = 2,984                               │ ← ВЫЧИСЛЯЕМ FBS
│                                                          │
│  4. Create Product                                       │
│     ├─ total_stock = 3,459 (из Analytics v2)            │
│     ├─ warehouses[FBO] = 475 (из Warehouse v1)          │
│     └─ warehouses[FBS/МП] = 2,984 (вычисл.)             │ ← ВСЕ ОСТАТКИ
└──────────────────────────────────────────────────────────┘
```

---

## 🔧 ТРЕБУЕМЫЕ ИЗМЕНЕНИЯ

### Изменение 1: Получать total_stock из Analytics API v2

**Файл**: `src/stock_tracker/services/product_service.py`  
**Метод**: `sync_from_api_to_sheets()`

**БЫЛО:**
```python
async def sync_from_api_to_sheets(self, skip_existence_check: bool = False):
    # Step 1: Fetch warehouse remains (stocks) from V1 API
    warehouse_remains = await self.wb_client.download_warehouse_remains(task_id)
    
    # Calculate total_stock
    for record in warehouse_remains:
        total_stock = sum(wh.get('quantity') for wh in record['warehouses'])
        # ← НЕВЕРНО: только FBO остатки
```

**ДОЛЖНО БЫТЬ:**
```python
async def sync_from_api_to_sheets(self, skip_existence_check: bool = False):
    # Step 1: Fetch FULL stocks from Analytics API v2
    analytics_data = await self.wb_client.get_all_product_stock_data()
    
    # Step 2: Fetch FBO warehouse breakdown from Warehouse API v1
    warehouse_remains = await self.wb_client.download_warehouse_remains(task_id)
    
    # Step 3: Combine data
    for analytics_item in analytics_data:
        nm_id = analytics_item.get('nmID')
        
        # ПОЛНЫЕ остатки из Analytics v2
        metrics = analytics_item.get('metrics', {})
        total_stock_full = metrics.get('stockCount', 0)  # FBO + FBS
        
        # FBO breakdown из Warehouse v1
        warehouse_record = find_warehouse_record(warehouse_remains, nm_id)
        fbo_warehouses = warehouse_record.get('warehouses', [])
        fbo_stock_sum = sum(wh.get('quantity') for wh in fbo_warehouses)
        
        # ВЫЧИСЛЯЕМ FBS/МП остатки
        fbs_stock = total_stock_full - fbo_stock_sum
        
        # Создаём Product с ПОЛНЫМИ остатками
        product = Product(
            total_stock=total_stock_full,  # ← 3,459 вместо 475
            warehouses=[
                *fbo_warehouses,  # FBO склады WB
                Warehouse(name="МП/FBS (на складе продавца)", 
                         stock=fbs_stock,  # ← 2,984
                         orders=fbs_orders)
            ]
        )
```

### Изменение 2: Добавить строку "МП/FBS" в таблицу

Результат в Google Sheets должен выглядеть так:

```
Артикул       | WB ID      | Заказы | Остатки | Склады
              |            | (всего)| (всего) |
--------------+------------+--------+---------+------------------------
Its1_2_3/50g  | 163383326  | 105    | 3,459   | Краснодар: 11/51
              |            |        |         | Чехов 1: 4/193
              |            |        |         | Рязань: 15/50
              |            |        |         | ...
              |            |        |         | МП/FBS: 0/2,984 ← НОВОЕ!
```

---

## 📋 ПЛАН РЕАЛИЗАЦИИ

### Фаза 1: Быстрое исправление (1-2 часа)

1. ✅ Добавить вызов `get_all_product_stock_data()` в начале синхронизации
2. ✅ Использовать `metrics.stockCount` для `total_stock`
3. ✅ Вычислить FBS/МП остатки = `total_stock - sum(FBO stocks)`
4. ✅ Добавить warehouse "МП/FBS (на складе продавца)" с вычисленными остатками

### Фаза 2: Оптимизация (3-4 часа)

1. Добавить кэширование Analytics API v2 данных
2. Оптимизировать комбинацию двух источников
3. Добавить валидацию (total_stock >= sum(warehouse stocks))

---

## 🧪 ТЕСТИРОВАНИЕ

### Тест 1: Проверка полных остатков

```python
# После исправления:
product = operations.read_product(spreadsheet_id, "Its1_2_3/50g")

assert product.total_stock == 3459  # Было 475
assert len([wh for wh in product.warehouses if "МП/FBS" in wh.name]) == 1
```

### Тест 2: Сумма остатков по складам = total_stock

```python
warehouse_stock_sum = sum(wh.stock for wh in product.warehouses)
assert warehouse_stock_sum == product.total_stock  # Должно сходиться
```

---

## 💰 ВЛИЯНИЕ НА БИЗНЕС

### ДО исправления:
- ❌ Остатки занижены на **86%** (2,984 из 3,459)
- ❌ Неверные данные для аналитики
- ❌ Невозможно планировать закупки
- ❌ Риск упущенных продаж (не видите реальные остатки)

### ПОСЛЕ исправления:
- ✅ Остатки **100% точные** (3,459 шт)
- ✅ Видны остатки **FBO** и **FBS/МП** отдельно
- ✅ Корректная аналитика оборачиваемости
- ✅ Правильное планирование закупок

---

## 🎯 NEXT STEPS

1. **Реализовать исправление** согласно плану
2. **Протестировать** на товаре Its1_2_3/50g
3. **Проверить** все остальные товары
4. **Обновить документацию**

---

**Автор**: GitHub Copilot  
**Дата**: 28 октября 2025  
**Приоритет**: 🔥 КРИТИЧЕСКИЙ  
**Статус**: Готово к реализации
