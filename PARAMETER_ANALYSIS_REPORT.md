# Отчет по Анализу Параметров API Wildberries
## Глубокое исследование некорректных параметров таблицы

**Дата анализа:** 22 октября 2025  
**Исследованные инструменты:** Анализ кода, Postman, Chrome DevTools  
**Фокус:** Определение некорректных параметров таблицы в проекте Stock Tracker

---

## 🔍 КРИТИЧЕСКИЕ ОБНАРУЖЕНИЯ

### 1. **КАРДИНАЛЬНОЕ НЕСООТВЕТСТВИЕ ВЕРСИЙ API**

**Проблема:** Текущая реализация использует устаревший API v1, в то время как доступен API v2 с принципиально иной структурой параметров.

**Текущая реализация (УСТАРЕВШАЯ):**
```python
# client.py - использует старый API v1
def create_warehouse_remains_task(self):
    url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains"
    params = {
        'locale': 'ru',
        'groupByNm': True,  # ← УСТАРЕВШИЙ параметр
        'groupBySa': True   # ← УСТАРЕВШИЙ параметр
    }
```

**Новый Analytics API v2 (ПРАВИЛЬНЫЙ):**
```json
POST https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products
{
  "currentPeriod": {
    "start": "2025-10-21",
    "end": "2025-10-21"
  },
  "stockType": "",
  "skipDeletedNm": true,
  "availabilityFilters": ["actual", "balanced", "deficient"],
  "orderBy": {
    "field": "stockCount",
    "mode": "desc"
  },
  "limit": 100,
  "offset": 0
}
```

---

## 📊 ДЕТАЛЬНОЕ СРАВНЕНИЕ ПАРАМЕТРОВ

### **Параметры периода (КРИТИЧЕСКОЕ ИЗМЕНЕНИЕ)**

| Аспект | V1 API (Текущий) | V2 API (Правильный) |
|--------|------------------|---------------------|
| **Формат даты** | Нет строгих требований | `<date>` формат, строгие ограничения |
| **Ограничения** | Не документированы | Не ранее 3 месяцев от текущей даты |
| **Структура** | Простые параметры | Объект `currentPeriod` с `start`/`end` |
| **Валидация** | Нет | `start` не позднее `end` |

### **Новые обязательные параметры (ОТСУТСТВУЮТ в V1)**

#### `stockType` (required enum)
- `""` — все склады
- `"wb"` — Склады WB  
- `"mp"` — Склады Маркетплейс (FBS)

#### `skipDeletedNm` (required boolean)
- `true` — скрыть удалённые товары
- `false` — показать все товары

#### `availabilityFilters` (required array)
Допустимые значения:
- `"deficient"` — Дефицит
- `"actual"` — Актуальный
- `"balanced"` — Баланс  
- `"nonActual"` — Неактуальный
- `"nonLiquid"` — Неликвид
- `"invalidData"` — Не рассчитано

#### `orderBy` (required object)
```json
{
  "field": "ordersCount|ordersSum|avgOrders|buyoutCount|buyoutSum|buyoutPercent|stockCount|stockSum|saleRate|avgStockTurnover|toClientCount|fromClientCount|minPrice|maxPrice|officeMissingTime|lostOrdersCount|lostOrdersSum|lostBuyoutsCount|lostBuyoutsSum",
  "mode": "asc|desc"
}
```

### **Структура ответа (КАРДИНАЛЬНО ИЗМЕНЕНА)**

**V1 API структура:**
```json
[
  {
    "vendorCode": "string",
    "nmId": 12345,
    "warehouses": [...]
  }
]
```

**V2 API структура:**
```json
{
  "data": {
    "items": [
      {
        "nmID": 12345,
        "subjectID": 123,
        "brandName": "string", 
        "tagID": 456,
        "ordersCount": 10,
        "stockCount": 50,
        "// много новых полей..."
      }
    ]
  }
}
```

---

## 🛠️ ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ В КОДЕ

### **1. Файл: `src/stock_tracker/api/client.py`**

**Проблема:** Использование устаревших эндпоинтов
```python
# НЕПРАВИЛЬНО - старый API
def create_warehouse_remains_task(self):
    url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains"
    
# НЕПРАВИЛЬНО - старые параметры  
def get_supplier_orders(self, date_from: str):
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/orders"
```

**Решение:** Мигрировать на аналитические эндпоинты v2

### **2. Файл: `src/stock_tracker/database/structure.py`**

**Проблема:** Структура колонок не соответствует новым данным API v2
```python
# Текущие колонки могут не покрывать новые поля
COLUMNS = [
    ColumnDefinition("seller_article", "Артикул продавца"),
    ColumnDefinition("wb_article", "Артикул WB"), 
    # Отсутствуют: subjectID, brandName, tagID, stockType и др.
]
```

### **3. Файл: `src/stock_tracker/core/models.py`**

**Проблема:** Модели данных не включают новые поля API v2
```python
@dataclass
class WarehouseData:
    # Модель не содержит новые поля из v2 API
    # subjectID, brandName, tagID, availabilityFilters и др.
```

---

## 🚨 ЛИМИТЫ И ОГРАНИЧЕНИЯ API V2

### **Rate Limiting (КРИТИЧНО)**
- **Лимит:** 3 запроса в минуту
- **Интервал:** 20 секунд между запросами  
- **Burst:** 3 запроса максимум

### **Ограничения по датам**
- Максимум 3 месяца от текущей даты
- Формат строго `YYYY-MM-DD`
- `start` не должно быть позднее `end`

### **Пагинация**
- `limit`: максимум 1000 товаров
- `offset`: для получения следующих страниц

---

## 🎯 ПЛАН ИСПРАВЛЕНИЯ

### **Фаза 1: Обновление API клиента**
1. Создать новый клиент для Analytics API v2
2. Реализовать правильные параметры запросов
3. Добавить обработку новых ограничений дат
4. Внедрить rate limiting

### **Фаза 2: Обновление моделей данных**
1. Расширить `WarehouseData` новыми полями
2. Добавить модели для `stockType`, `availabilityFilters`
3. Обновить валидацию данных

### **Фаза 3: Обновление структуры таблицы**
1. Добавить колонки для новых полей API v2
2. Обновить маппинг данных
3. Внедрить поддержку сортировки

### **Фаза 4: Тестирование**
1. Протестировать новые параметры через Postman
2. Валидировать ответы API v2
3. Проверить корректность заполнения таблицы

---

## 🔗 СОЗДАННЫЕ ТЕСТОВЫЕ ЗАПРОСЫ

### **Postman Collection: "Wildberries API Research"**
ID: `69f078fa-ee55-4c4f-8167-06e48b07fdf5`

#### Запросы:
1. **Warehouse Remains - Create Task** (V1 API)
2. **Warehouse Remains - Download Results** (V1 API)  
3. **Supplier Orders** (V1 API)
4. **Analytics v2 - Product Stock Data** (V2 API) ← **НОВЫЙ ТЕСТОВЫЙ ЗАПРОС**

### **Тестовый запрос V2 API:**
```bash
POST https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products
Authorization: Bearer {{api_key}}
Content-Type: application/json

{
  "currentPeriod": {
    "start": "2025-10-21",
    "end": "2025-10-21"
  },
  "stockType": "",
  "skipDeletedNm": true,
  "availabilityFilters": ["actual", "balanced", "deficient"],
  "orderBy": {
    "field": "stockCount", 
    "mode": "desc"
  },
  "limit": 10,
  "offset": 0
}
```

---

## 📈 ЗАКЛЮЧЕНИЕ

**ГЛАВНЫЙ ВЫВОД:** Параметры таблицы некорректны из-за использования устаревшего API v1 вместо современного Analytics API v2.

**КРИТИЧНОСТЬ:** Высокая - текущая реализация может работать нестабильно и предоставлять неполные данные.

**РЕКОМЕНДАЦИЯ:** Немедленная миграция на API v2 с соблюдением всех новых требований к параметрам и ограничениям.

**СЛЕДУЮЩИЕ ШАГИ:**
1. Тестирование созданного Postman запроса с реальным API ключом
2. Анализ реальных ответов API v2  
3. Реализация миграции кода на новый API
4. Обновление структуры таблицы под новые данные

---

**Отчет подготовлен с использованием:**
- ✅ Анализ кода проекта
- ✅ Официальная документация Wildberries API  
- ✅ Chrome DevTools для исследования параметров
- ✅ Postman коллекция для тестирования
- ✅ Сравнительный анализ API v1 vs v2