# 🚀 Краткая инструкция: Использование оптимизации API

## Для обычного использования

### ✅ Рекомендуется: После очистки таблицы

Когда вы знаете, что таблица пуста или только что очищена:

```python
# Очищаем таблицу
operations.clear_all_products(spreadsheet_id, worksheet_name)

# Синхронизация с оптимизацией (экономия 58% API запросов)
sync_session = await product_service.sync_from_api_to_sheets(
    skip_existence_check=True  # ← Пропустить проверку существования
)
```

**Эффект**: 58% меньше API запросов, в 2.4 раза быстрее

---

### ⚠️ Стандартный режим: При инкрементальном обновлении

Когда нужно обновить только некоторые товары (не все):

```python
# Синхронизация без оптимизации (стандартное поведение)
sync_session = await product_service.sync_from_api_to_sheets()
# или явно:
sync_session = await product_service.sync_from_api_to_sheets(
    skip_existence_check=False
)
```

**Эффект**: Проверка существования каждого товара, обновление только изменённых

---

## Прямое использование в коде

### ✅ После clear_all_products():

```python
# 1. Очистили таблицу
operations.clear_all_products(spreadsheet_id, worksheet_name)

# 2. Добавляем товары с оптимизацией
for product in products:
    operations.create_or_update_product(
        spreadsheet_id,
        product,
        worksheet_name="Stock Tracker",
        skip_existence_check=True  # ← Экономия API!
    )
```

### ⚠️ При смешанном обновлении:

```python
# Обычное использование (проверяет существование)
operations.create_or_update_product(
    spreadsheet_id,
    product,
    worksheet_name="Stock Tracker"
    # skip_existence_check=False по умолчанию
)
```

---

## Когда использовать оптимизацию?

### ✅ ИСПОЛЬЗУЙТЕ `skip_existence_check=True`:

- ✅ После `clear_all_products()`
- ✅ При первоначальной загрузке данных в пустую таблицу
- ✅ При полном обновлении всех товаров
- ✅ Когда точно знаете, что товара нет в таблице

### ❌ НЕ ИСПОЛЬЗУЙТЕ `skip_existence_check=True`:

- ❌ При инкрементальном обновлении (обновление только некоторых товаров)
- ❌ Когда не уверены, есть ли товар в таблице
- ❌ При добавлении новых товаров к существующим (без очистки)
- ❌ В критичных операциях, где важна проверка дубликатов

---

## Эффект оптимизации

| Сценарий | API запросов (11 товаров) | Время |
|----------|---------------------------|-------|
| **БЕЗ оптимизации** | 38 requests | ~90 сек |
| **С оптимизацией** | 16 requests | ~38 сек |
| **Экономия** | -22 requests (-58%) | -52 сек (-58%) |

---

## Примеры из реального кода

### Пример 1: update_table_fixed.py (РЕКОМЕНДУЕТСЯ)

```python
async def update_table_data_async(spreadsheet_id, worksheet_name):
    # Очищаем старые данные
    operations.clear_all_products(spreadsheet_id, worksheet_name)
    
    # ОПТИМИЗАЦИЯ: таблица пуста, проверка не нужна
    sync_session = await product_service.sync_from_api_to_sheets(
        skip_existence_check=True  # ← Экономия 58%!
    )
```

### Пример 2: Инкрементальное обновление (стандартно)

```python
async def update_single_product(product):
    # Обновляем один товар (может существовать или нет)
    success = operations.create_or_update_product(
        spreadsheet_id,
        product
        # skip_existence_check=False (по умолчанию)
    )
```

### Пример 3: Batch обновление после очистки

```python
async def refresh_all_products(products):
    # Очищаем таблицу
    operations.clear_all_products(spreadsheet_id, worksheet_name)
    
    # Добавляем все товары с оптимизацией
    for product in products:
        operations.create_or_update_product(
            spreadsheet_id,
            product,
            skip_existence_check=True  # ← Быстрее!
        )
```

---

## ⚠️ ВАЖНО: Безопасность

### Безопасно использовать оптимизацию:
- ✅ Когда таблица гарантированно пуста (после `clear_all_products()`)
- ✅ При первом запуске приложения с пустой таблицей
- ✅ В тестах, где контролируется начальное состояние

### НЕ безопасно:
- ❌ Когда в таблице могут быть данные
- ❌ При одновременном доступе нескольких процессов
- ❌ Если не уверены в состоянии таблицы

---

## 📊 Мониторинг

Проверьте логи после синхронизации:

```
✅ Оптимизированная синхронизация:
   Creating product (skipping existence check): WB001
   Creating product (skipping existence check): WB002
   ...

⚠️ Стандартная синхронизация:
   Updating existing product: WB001
   Creating new product: WB002
   ...
```

---

## 🧪 Тестирование

Запустите тесты для проверки:

```bash
python test_optimization.py
```

Ожидаемый результат:
```
✅ Пройдено: 4/4
💰 ЭКОНОМИЯ: 22 requests (58%)
```

---

## 📞 Поддержка

Если возникли вопросы:
1. Проверьте `API_QUOTA_OPTIMIZATION_PHASE1_COMPLETED.md` - полный отчёт
2. Изучите `API_QUOTA_ANALYSIS_REPORT.md` - детальный анализ
3. Запустите `test_optimization.py` - проверка работоспособности

---

**Версия**: 1.0  
**Дата**: 28 октября 2025  
**Статус**: ✅ Готово к использованию
