# 📊 ОТЧЁТ: Анализ превышения квоты Google Sheets API

**Дата**: 28 октября 2025  
**Проблема**: Превышение read quota (60 requests/minute)  
**Статус**: ✅ Диагностирована, дублирующихся ДАННЫХ нет

---

## 🔍 EXECUTIVE SUMMARY

### Ключевые находки:

✅ **Дублирующихся ДАННЫХ нет** - все 11 товаров уникальны, данные корректны  
❌ **Дублирующиеся API ВЫЗОВЫ** - 49 read requests вместо оптимальных 8  
📊 **Текущее использование**: ~33 requests/minute (формально в пределах 60/min)  
⚠️ **Проблема**: При пиковых нагрузках легко превысить лимит

### Вердикт:

**Проблема НЕ критична**, но требует оптимизации:
- Данные в таблице **корректные** (282 заказа, 11 товаров)
- API вызовы **избыточные** но не критичные
- **84% потенциал оптимизации** (49 → 8 requests)

---

## 📈 ДЕТАЛЬНЫЙ АНАЛИЗ КВОТЫ

### Текущее использование (на 11 продуктов):

| Операция | Кол-во | Тип | Комментарий |
|----------|--------|-----|-------------|
| **Базовые операции** |
| Аутентификация | 1 | read | ✅ Необходимо |
| Открытие spreadsheet | 1 | read | ✅ Необходимо |
| Открытие worksheet | 1 | read | ✅ Необходимо |
| Очистка таблицы | 2 | read | ✅ Необходимо |
| **Операции на каждый продукт (×11)** |
| get_worksheet (read_product) | 11 | read | ❌ **ДУБЛИКАТ #1** |
| find_product_row (scan) | 11 | read | ⚠️ Можно оптимизировать |
| get_worksheet (create_product) | 11 | read | ❌ **ДУБЛИКАТ #2** |
| verify_structure | 11 | read | ❌ **ДУБЛИКАТ #3** |
| **ИТОГО** | **49** | **read** | **Можно сократить до 8** |

### Расчёт requests/minute:

```
49 requests за 90 секунд = 32.7 requests/minute
Лимит: 60 requests/minute
Запас: 27.3 requests/minute (45%)
```

**Вывод**: Формально в пределах квоты, но:
- ⚠️ Запас маленький (45%)
- ⚠️ При 20+ товарах превысим лимит
- ⚠️ Retry механизмы могут добавить запросы

---

## 🐛 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ

### Проблема #1: Дублирование get_or_create_worksheet() 🔥 КРИТИЧЕСКАЯ

**Где**: `operations.py:647` → `create_or_update_product()`

**Что происходит**:
```python
def create_or_update_product():
    # ШАГ 1: Проверка существования
    existing_product = self.read_product(...)  # → get_worksheet() #1
    
    if existing_product:
        self.update_product(...)  # → get_worksheet() #2 ❌ ДУБЛИКАТ
    else:
        self.create_product(...)  # → get_worksheet() #3 ❌ ДУБЛИКАТ
```

**Влияние**: 
- 2 лишних запроса на каждый продукт
- **22 лишних запроса** для 11 товаров
- **45% всех запросов**

**Решение**:
```python
def create_or_update_product():
    worksheet = self.get_or_create_worksheet(...)  # ОДИН РАЗ
    existing_row = self._find_product_row(worksheet, ...)
    
    if existing_row:
        self._update_product_row(worksheet, existing_row, ...)
    else:
        self._append_product_row(worksheet, ...)
```

---

### Проблема #2: find_product_row() сканирует всю таблицу ⚠️ ВЫСОКАЯ

**Где**: `operations.py` → вызывается в `read_product()`, `create_product()`, `update_product()`

**Что происходит**:
```python
def _find_product_row(worksheet, seller_article):
    all_values = worksheet.get_all_values()  # ← Полный скан!
    for i, row in enumerate(all_values):
        if row[0] == seller_article:
            return i + 1
    return None
```

**Влияние**:
- 11 полных сканов таблицы
- **11 запросов**, каждый читает ВСЕ данные
- Растёт линейно с размером таблицы

**Решение** (выбрать один):

**Вариант A: Кэш** (быстро)
```python
class SheetsOperations:
    def __init__(self):
        self._product_row_cache = {}  # seller_article → row_number
    
    def _find_product_row_cached(self, worksheet, seller_article):
        if seller_article in self._product_row_cache:
            return self._product_row_cache[seller_article]
        
        row = self._find_product_row(worksheet, seller_article)
        if row:
            self._product_row_cache[seller_article] = row
        return row
    
    def clear_cache(self):
        self._product_row_cache = {}
```

**Вариант B: Batch read** (надёжнее)
```python
def _find_products_batch(worksheet, seller_articles: List[str]):
    """Найти все продукты одним запросом"""
    all_values = worksheet.get_all_values()  # ОДИН скан для всех
    
    result = {}
    for i, row in enumerate(all_values):
        if row and row[0] in seller_articles:
            result[row[0]] = i + 1
    
    return result
```

---

### Проблема #3: verify_worksheet_structure() после каждого append ⚠️ ВЫСОКАЯ

**Где**: `operations.py` → вызывается в `create_product()`

**Что происходит**:
```python
def create_product():
    # ... создание продукта
    worksheet.update(range_name, [row_data])
    
    # Попытка верификации (часто падает с quota error)
    try:
        self.verify_worksheet_structure(...)  # ❌ Лишняя проверка
    except:
        pass  # Игнорируем ошибку
```

**Влияние**:
- 11 лишних проверок структуры
- **11 запросов**
- Часто приводит к quota errors (видно в логах)

**Решение**:
```python
def sync_from_api_to_sheets():
    # Проверить структуру ОДИН РАЗ в начале
    self.verify_worksheet_structure(...)
    
    # Записывать продукты без проверки
    for product in products:
        self.create_product(...)  # БЕЗ verify
```

---

### Проблема #4: Отсутствие batch operations 🔥 КРИТИЧЕСКАЯ

**Где**: `product_service.py:380-400` → цикл `for api_record in api_data`

**Что происходит**:
```python
for api_record in api_data:  # 11 итераций
    product = self._convert_api_record_to_product(...)
    
    self.operations.create_or_update_product(...)  # ← Отдельный вызов!
    # = 4 read requests на каждый продукт
```

**Влияние**:
- 11 отдельных операций вместо 1 batch
- **44 запроса** вместо ~5

**Решение**:

**ШАГ 1**: Использовать существующий `create_products_batch()`:
```python
# Вместо:
for api_record in api_data:
    product = convert(api_record)
    self.operations.create_or_update_product(...)

# Использовать:
products = [convert(record) for record in api_data]
self.operations.create_products_batch(
    spreadsheet_id,
    products,
    worksheet_name
)
```

**ШАГ 2**: Оптимизировать `create_products_batch()`:
```python
def create_products_batch(self, spreadsheet_id, products, worksheet_name):
    worksheet = self.get_or_create_worksheet(...)  # ОДИН РАЗ
    
    # ОДИН скан для проверки дубликатов
    existing_articles = set(self._get_all_seller_articles(worksheet))
    
    # Фильтровать новые продукты
    new_products = [p for p in products if p.seller_article not in existing_articles]
    
    # ОДИН batch append для всех
    if new_products:
        rows = [self.formatter.format_product_for_sheets(p) for p in new_products]
        next_row = self._find_next_empty_row(worksheet)
        worksheet.append_rows(rows)  # ← BATCH!
    
    return len(new_products)
```

---

### Проблема #5: Лишние read_product() после clear_all_products() 📝 СРЕДНЯЯ

**Где**: `operations.py:647` → `create_or_update_product()` вызывает `read_product()`

**Контекст**:
```python
# update_table_fixed.py
operations.clear_all_products(...)  # Таблица пуста!

# Потом для каждого продукта:
operations.create_or_update_product(...)  # Зачем проверять существование?
    └→ read_product(...)  # ← 100% вернёт None (таблица пуста!)
       └→ create_product(...)
```

**Влияние**:
- 11 бесполезных read_product() вызовов
- **22 запроса** (get_worksheet + find_row)
- **45% всех запросов**

**Решение**:
```python
# После clear_all_products() использовать прямой create
operations.clear_all_products(...)

for product in products:
    operations.create_product(...)  # Напрямую, без read_product
```

Или добавить флаг:
```python
def create_or_update_product(self, ..., skip_existence_check=False):
    if not skip_existence_check:
        existing_product = self.read_product(...)
    else:
        # Сразу создаём
        return self.create_product(...)
```

---

## 📊 СРАВНИТЕЛЬНАЯ ТАБЛИЦА

| Метрика | Текущее | После оптимизации | Улучшение |
|---------|---------|-------------------|-----------|
| Read requests (11 товаров) | 49 | 8 | **-84%** |
| Requests/minute | 32.7 | 5.3 | **-84%** |
| Время синхронизации | 90 сек | 15 сек | **-83%** |
| Запас до лимита (60/min) | 45% | 91% | **+102%** |
| Макс товаров без превышения | 18 | 113 | **+528%** |

---

## 🎯 ПЛАН ДЕЙСТВИЙ

### Фаза 1: Быстрые исправления (1-2 часа) 🔥

**1.1. Убрать verify_worksheet_structure() из create_product()**
- **Файл**: `src/stock_tracker/database/operations.py`
- **Строка**: ~250 (внутри create_product)
- **Действие**: Закомментировать или удалить вызов
- **Эффект**: -11 requests, -22%

**1.2. Добавить skip_existence_check флаг**
- **Файл**: `src/stock_tracker/database/operations.py:647`
- **Действие**: Добавить параметр в `create_or_update_product()`
- **Эффект**: -22 requests, -45%

**1.3. Использовать в update_table_fixed.py**
- **Файл**: `update_table_fixed.py`
- **Действие**:
  ```python
  operations.clear_all_products(...)
  
  for product in products:
      operations.create_or_update_product(
          ..., 
          skip_existence_check=True  # ← НОВЫЙ ПАРАМЕТР
      )
  ```
- **Эффект**: Сразу -33 requests (-67%)

### Фаза 2: Средние оптимизации (3-4 часа) ⚠️

**2.1. Добавить кэш worksheet**
- **Файл**: `src/stock_tracker/services/product_service.py`
- **Действие**:
  ```python
  async def sync_from_api_to_sheets(self):
      # Получить worksheet ОДИН РАЗ
      worksheet = self.operations.get_or_create_worksheet(...)
      
      # Передать во все операции
      for product in products:
          self.operations.create_product_direct(worksheet, product)
  ```
- **Эффект**: -11 requests, дополнительно -22%

**2.2. Реализовать _find_products_batch()**
- **Файл**: `src/stock_tracker/database/operations.py`
- **Действие**: Добавить метод для batch поиска
- **Эффект**: -10 requests (1 скан вместо 11)

### Фаза 3: Глубокая оптимизация (8+ часов) 📝

**3.1. Переписать на batch operations**
- **Файлы**: 
  - `src/stock_tracker/services/product_service.py:380-400`
  - `src/stock_tracker/database/operations.py:275-340`
- **Действие**: Использовать `create_products_batch()` вместо цикла
- **Эффект**: Итоговые 8 requests вместо 49

**3.2. Добавить batch update для Google Sheets**
- **Файл**: `src/stock_tracker/database/operations.py`
- **Действие**: Использовать `worksheet.batch_update()` вместо отдельных `update()`
- **Эффект**: Ещё быстрее, меньше latency

---

## 💡 ВРЕМЕННОЕ РЕШЕНИЕ (пока не оптимизировано)

Если нужно **СЕЙЧАС** избежать quota errors:

```python
# update_table_fixed.py

import time

async def update_table_data_async(...):
    # ... существующий код ...
    
    for i, product in enumerate(products):
        sync_session = await product_service.sync_from_api_to_sheets()
        
        # Добавить задержку после каждого 5-го продукта
        if (i + 1) % 5 == 0:
            print(f"⏸️  Пауза после {i+1} продуктов для квоты...")
            time.sleep(10)  # 10 секунд задержки
```

**Эффект**: Растягивает 11 товаров на 2 минуты вместо 1.5 минут = гарантированно в пределах квоты.

---

## 📋 ЧЕКЛИСТ ВЫПОЛНЕНИЯ

### Немедленно (Фаза 1):
- [ ] Удалить `verify_worksheet_structure()` из `create_product()`
- [ ] Добавить `skip_existence_check` параметр
- [ ] Обновить `update_table_fixed.py` использовать новый параметр
- [ ] Протестировать синхронизацию
- [ ] Проверить квоту (должно быть ~16 requests вместо 49)

### В течение недели (Фаза 2):
- [ ] Реализовать кэш worksheet
- [ ] Добавить `_find_products_batch()`
- [ ] Рефакторинг `create_or_update_product()` использовать кэш
- [ ] Протестировать с 20+ товарами
- [ ] Проверить квоту (должно быть ~10 requests)

### В течение месяца (Фаза 3):
- [ ] Переписать на `create_products_batch()`
- [ ] Добавить batch update в Google Sheets
- [ ] Полное тестирование
- [ ] Замерить производительность
- [ ] Обновить документацию

---

## 📊 МЕТРИКИ УСПЕХА

### До оптимизации:
- ❌ 49 read requests за 90 секунд
- ❌ 32.7 requests/minute
- ❌ Запас 45% (легко превысить при пиках)
- ❌ Макс 18 товаров без превышения

### После Фазы 1 (быстрые исправления):
- ✅ 16 read requests за 90 секунд
- ✅ 10.7 requests/minute
- ✅ Запас 82%
- ✅ Макс 56 товаров

### После Фазы 2 (средние оптимизации):
- ✅ 10 read requests за 90 секунд
- ✅ 6.7 requests/minute
- ✅ Запас 89%
- ✅ Макс 90 товаров

### После Фазы 3 (глубокая оптимизация):
- ✅✅ 8 read requests за 90 секунд
- ✅✅ 5.3 requests/minute
- ✅✅ Запас 91%
- ✅✅ Макс 113 товаров

---

## 🎬 ЗАКЛЮЧЕНИЕ

### Основные выводы:

1. ✅ **Дублирующихся данных НЕТ**
   - Все 11 товаров уникальны
   - 282 заказа корректны
   - Таблица содержит правильную информацию

2. ⚠️ **Дублирующиеся API вызовы ЕСТЬ**
   - 49 запросов вместо 8 (-84% potential)
   - Основная причина: отсутствие batch operations
   - Вторая причина: дублирование get_worksheet()

3. 🎯 **Решение простое и чёткое**
   - Фаза 1 (1-2 часа) → -67% requests
   - Фаза 2 (3-4 часа) → -80% requests
   - Фаза 3 (8+ часов) → -84% requests

4. 💪 **Проблема НЕ критична**
   - Текущие 33 req/min < лимит 60 req/min
   - Но запас маленький (45%)
   - При росте товаров (20+) будут проблемы

### Рекомендация:

**Выполнить Фазу 1 немедленно** (1-2 часа работы):
- Убрать verify_worksheet_structure()
- Добавить skip_existence_check
- Сразу получить -67% запросов

**Фазы 2 и 3 - по мере необходимости.**

---

**Автор**: AI Assistant  
**Дата**: 28 октября 2025, 16:15  
**Версия**: 1.0 FINAL
