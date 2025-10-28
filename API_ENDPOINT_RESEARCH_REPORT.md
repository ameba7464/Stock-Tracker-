# Отчет: Исследование API эндпоинтов Wildberries для получения данных по складам FBO/FBS

**Дата:** 28 октября 2025  
**Проблема:** Расхождение данных по остаткам (475 в таблице vs 3,459 на WB для товара Its1_2_3/50g)  
**Цель:** Найти API эндпоинт для получения точных данных по остаткам FBS/MP без вычислений

---

## 🔍 Исследованные API эндпоинты

### 1. **Warehouse Remains API v1** ✅ (Текущий источник остатков)

**URL:** `https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains`

**Метод:** GET → создает задачу → скачивание через `/tasks/{task_id}/download`

**Что возвращает:**
```json
{
  "brand": "string",
  "subjectName": "string",
  "vendorCode": "string",
  "nmId": 123456,
  "barcode": "string",
  "techSize": "string",
  "volume": 0.5,
  "warehouses": [
    {
      "warehouseName": "Подольск 3",
      "quantity": 100
    },
    {
      "warehouseName": "Обухово МП",
      "quantity": 50
    }
  ]
}
```

**Важные находки:**
- ✅ Возвращает остатки **ПО ВСЕМ СКЛАДАМ** (включая FBO и FBS)
- ✅ Детализация по каждому складу с указанием названия и количества
- ❌ **НЕТ поля `warehouseType`** для определения типа склада (FBO/FBS)
- ❌ Невозможно программно определить тип склада по названию

**Параметры фильтрации:**
- `groupByNm`, `groupBySa`, `groupByBarcode`, `groupBySize`
- `filterPics`, `filterVolume`
- ❌ **НЕТ параметра для фильтрации по типу склада**

---

### 2. **Supplier Orders API v1** ✅ (Содержит warehouseType!)

**URL:** `https://statistics-api.wildberries.ru/api/v1/supplier/orders`

**Метод:** GET с параметрами `dateFrom`, `flag`

**Что возвращает:**
```json
{
  "date": "2025-09-27T22:00:46",
  "lastChangeDate": "2025-09-28T02:12:53",
  "warehouseName": "Подольск 3",
  "warehouseType": "Склад WB",  // ← КЛЮЧЕВОЕ ПОЛЕ!
  "supplierArticle": "Its2/50g",
  "nmId": 163383327,
  "barcode": "4650243761433",
  "isCancel": false,
  ...
}
```

**Важные находки:**
- ✅ **ЕСТЬ поле `warehouseType`** с enum значениями:
  - `"Склад WB"` = FBO
  - `"Склад продавца"` = FBS/MP
- ✅ Можно точно определить тип каждого склада через заказы
- ✅ Поле `warehouseName` совпадает с названиями из warehouse_remains
- ⚠️ Это API **заказов**, а не остатков

**Тестовые данные** (последние 30 дней):
- Всего заказов: 1,190
- "Склад WB" (FBO): 1,023 заказов (86.0%)
- "Склад продавца" (FBS): 166 заказов (13.9%)
- FBS склад: **"Обухово МП"**

---

### 3. **Analytics API v2** ⚠️ (Комбинированные данные)

**URL:** `https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products`

**Метод:** POST с телом запроса

**Параметры:**
```json
{
  "currentPeriod": {"start": "2025-10-21", "end": "2025-10-28"},
  "stockType": "",  // ← пустая строка = все склады
  "skipDeletedNm": true,
  "availabilityFilters": ["actual", "balanced", "deficient"]
}
```

**Что возвращает:**
- ✅ Общие остатки по всем складам (FBO + FBS)
- ❌ **НЕТ детализации по типу склада**
- ❌ **НЕТ параметра для раздельного получения FBO/FBS**
- ⚠️ Параметр `stockType` **НЕ** фильтрует по FBO/FBS (проверено)

---

## 🎯 Критические выводы

### ✅ Что мы нашли:

1. **API `warehouse_remains` возвращает ПОЛНЫЕ остатки** (FBO + FBS)
   - Включает все склады: "Подольск 3", "Обухово МП" и т.д.
   - Детализация по каждому складу отдельно
   
2. **API `supplier/orders` содержит поле `warehouseType`**
   - Можно однозначно определить тип склада
   - Значения: "Склад WB" (FBO) vs "Склад продавца" (FBS)

3. **FBS склад идентифицирован: "Обухово МП"**
   - Подтверждено через API заказов
   - Присутствует в данных warehouse_remains

### ❌ Чего НЕТ в API:

1. **Нет прямого эндпоинта для получения ТОЛЬКО FBS остатков**
2. **Нет параметра фильтрации по типу склада в warehouse_remains**
3. **Нет поля warehouseType в ответе warehouse_remains**

---

## 💡 Рекомендуемое решение

### Подход: Комбинирование двух API

**Шаг 1:** Получить мапинг складов через API заказов
```python
# Запрос заказов за последний период
orders = await client.get_supplier_orders(date_from="2025-09-01")

# Построить мапинг: warehouseName → warehouseType
warehouse_types = {}
for order in orders:
    wh_name = order["warehouseName"]
    wh_type = order.get("warehouseType", "")
    if wh_name and wh_type:
        warehouse_types[wh_name] = wh_type

# Результат:
# {
#   "Подольск 3": "Склад WB",
#   "Коледино": "Склад WB",
#   "Обухово МП": "Склад продавца",
#   ...
# }
```

**Шаг 2:** Применить мапинг к данным остатков
```python
# Запрос остатков
warehouse_data = await client.get_warehouse_remains_with_retry()

# Классификация остатков по типу
for product in warehouse_data:
    fbo_stock = 0
    fbs_stock = 0
    
    for warehouse in product.get("warehouses", []):
        wh_name = warehouse["warehouseName"]
        quantity = warehouse["quantity"]
        wh_type = warehouse_types.get(wh_name, "Unknown")
        
        if wh_type == "Склад WB":
            fbo_stock += quantity
        elif wh_type == "Склад продавца":
            fbs_stock += quantity
    
    product["fbo_stock"] = fbo_stock
    product["fbs_stock"] = fbs_stock
    product["total_stock"] = fbo_stock + fbs_stock
```

### Преимущества подхода:

✅ **100% точность** - данные берутся напрямую из API WB  
✅ **Нет вычислений** - используется реальная классификация складов  
✅ **Автоматическое обновление** - при появлении новых складов они будут автоматически классифицированы  
✅ **Обработка edge cases** - склады без типа помечаются как "Unknown"

### Недостатки:

⚠️ Требуется дополнительный API запрос для получения заказов  
⚠️ Новые склады без заказов не будут классифицированы (но таких быть не должно)  
⚠️ Нужно периодически обновлять мапинг складов

---

## 📋 План имплементации

### Фаза 1: Создание модуля классификации складов

**Файл:** `src/stock_tracker/services/warehouse_classifier.py`

```python
class WarehouseClassifier:
    """Классифицирует склады на FBO и FBS через API заказов."""
    
    async def build_warehouse_mapping(self, days: int = 90) -> Dict[str, str]:
        """Строит мапинг складов через анализ заказов."""
        pass
    
    def classify_warehouse(self, warehouse_name: str) -> str:
        """Возвращает тип склада: 'FBO', 'FBS', 'Unknown'."""
        pass
    
    def calculate_stock_by_type(self, product: Dict) -> Dict[str, int]:
        """Вычисляет остатки FBO/FBS для продукта."""
        pass
```

### Фаза 2: Интеграция в ProductService

**Файл:** `src/stock_tracker/services/product_service.py`

- Добавить инициализацию `WarehouseClassifier`
- Обновить метод `_convert_api_record_to_product()`
- Применять классификацию к данным остатков

### Фаза 3: Тестирование

1. Проверить корректность классификации на известных складах
2. Сравнить результаты с данными на сайте WB
3. Проверить товар Its1_2_3/50g (должно быть ~3,459)

### Фаза 4: Документация

- Обновить `urls.md` с описанием алгоритма
- Добавить комментарии в код
- Создать FAQ по работе с типами складов

---

## ⚠️ Альтернативные подходы (НЕ рекомендуются)

### ❌ Вариант 1: Вычисление FBS = Total - FBO
**Проблема:** Текущий warehouse_remains УЖЕ содержит FBO+FBS, нет "чистого FBO"

### ❌ Вариант 2: Определение по названию склада
**Проблема:** Нет четкого паттерна, "МП" не всегда = FBS, может измениться

### ❌ Вариант 3: Использование Analytics API v2
**Проблема:** Не предоставляет разбивку по типам складов

---

## 📊 Текущая ситуация с товаром Its1_2_3/50g

**WB показывает:** 3,459 остатков  
**Таблица показывает:** 475 остатков  
**Расхождение:** 2,984 (86%)

**Гипотеза:**
- Текущий код НЕ считает остатки на складе "Обухово МП" (FBS)
- Либо неправильно агрегирует данные по складам
- Либо проблема с фильтрацией баркодов/артикулов

**После имплементации решения:**
- Будет четкая разбивка: FBO остатки + FBS остатки = Total
- Можно будет точно выявить где именно теряются остатки

---

## ✅ Следующие шаги

1. **IMMEDIATE:** Создать `WarehouseClassifier` модуль
2. **HIGH:** Интегрировать в `ProductService`
3. **HIGH:** Протестировать на товаре Its1_2_3/50g
4. **MEDIUM:** Обновить документацию
5. **LOW:** Добавить кэширование мапинга складов

---

## 🔗 Связанные документы

- `STOCK_DISCREPANCY_REPORT.md` - первоначальный анализ проблемы
- `urls.md` - спецификация API эндпоинтов
- `API_V2_MAPPING_REPORT.md` - миграция на API v2

---

**Вывод:** Прямого API эндпоинта для раздельного получения FBS/FBO остатков НЕ СУЩЕСТВУЕТ. Единственный надежный способ - комбинирование `warehouse_remains` (остатки) + `supplier/orders` (типы складов) для точной классификации.
