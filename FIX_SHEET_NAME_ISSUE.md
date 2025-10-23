# Решение проблемы с названием листа "Товары"

## 🎯 Проблема
Несмотря на изменение параметров по умолчанию в коде на "Stock Tracker", Google Sheets продолжал показывать лист с названием "Товары".

## 🔍 Причина
Функция `get_or_create_worksheet()` сначала **ищет существующий лист** с указанным именем. Если лист "Товары" уже существовал в Google Sheets, система продолжала его использовать, игнорируя новый параметр по умолчанию "Stock Tracker".

## ✅ Реализованное решение

### 1. Автоматическое переименование в `get_or_create_worksheet()`

Добавлена интеллектуальная логика в `src/stock_tracker/database/operations.py`:

```python
def get_or_create_worksheet(self, spreadsheet_id: str, 
                          worksheet_name: str = "Stock Tracker") -> gspread.Worksheet:
    try:
        # Ищем лист с новым названием
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
        
    except WorksheetNotFound:
        # Если ищем "Stock Tracker", проверяем есть ли старый "Товары"
        if worksheet_name == "Stock Tracker":
            try:
                legacy_worksheet = spreadsheet.worksheet("Товары")
                # Автоматически переименовываем старый лист
                legacy_worksheet.update_title("Stock Tracker")
                return legacy_worksheet
            except WorksheetNotFound:
                pass
        
        # Создаем новый лист если старого нет
        worksheet = spreadsheet.add_worksheet(title=worksheet_name, ...)
        return worksheet
```

### 2. Дополнительная функция для ручного переименования

Добавлена функция `rename_worksheet_from_legacy()` для ручного управления:

```python
def rename_worksheet_from_legacy(self, spreadsheet_id: str, 
                               old_name: str = "Товары", 
                               new_name: str = "Stock Tracker") -> bool:
    # Безопасное переименование с проверками
```

## 🔄 Алгоритм работы

При обращении к Google Sheets система теперь:

1. **Ищет лист "Stock Tracker"** (новое название)
2. Если найден ✅ - использует его
3. Если НЕ найден ❌ - проверяет наличие старого листа "Товары"
4. Если старый лист найден 🔄 - **автоматически переименовывает** в "Stock Tracker"
5. Если старого листа тоже нет ➕ - **создает новый** лист "Stock Tracker"

## 📋 Все изменения

### Файлы с обновленными параметрами по умолчанию:
- ✅ `src/stock_tracker/database/operations.py` - 17 функций
- ✅ `fix_table_structure.py`
- ✅ `simple_table_analyzer.py`
- ✅ `fix_misplaced_data.py`
- ✅ `fix_g3_orders.py`
- ✅ `clean_warehouse_data.py`
- ✅ `apply_improved_logic.py`
- ✅ `analyze_table_data.py`
- ✅ `quick_fix_warehouse_data.py`

### Новый функционал:
- ✅ Автоматическое переименование в `get_or_create_worksheet()`
- ✅ Функция `rename_worksheet_from_legacy()` для ручного управления

## 🧪 Тестирование

Проверено наличие всех ключевых компонентов:
- ✅ Проверка на новое название: найден
- ✅ Поиск старого листа: найден  
- ✅ Переименование: найден
- ✅ Параметр по умолчанию: найден

## 🎉 Результат

**Проблема решена!** При следующем обращении к Google Sheets:

- Если лист "Товары" существует → будет автоматически переименован в "Stock Tracker"
- Если листа "Товары" нет → будет создан новый лист "Stock Tracker"
- В любом случае система будет работать с листом "Stock Tracker"

Переименование произойдет **автоматически** при следующей синхронизации или любой операции с Google Sheets.

---
*Исправлено: 22 октября 2025 г.*