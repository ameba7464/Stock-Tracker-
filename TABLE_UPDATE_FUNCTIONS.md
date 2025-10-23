# Функции обновления таблицы

**Дата создания:** 22 октября 2025 г.  
**Задача:** Добавить функции для автоматического обновления таблицы при запуске

## Описание

Добавлены новые функции для обновления таблицы Google Sheets свежими данными из Wildberries API. Эти функции позволяют автоматически получать актуальные данные об остатках, заказах и рассчитывать показатели оборачиваемости при запуске приложения.

## Новые функции

### 1. SheetsOperations.refresh_table_data()

**Файл:** `src/stock_tracker/database/operations.py`

```python
def refresh_table_data(self, spreadsheet_id: str, 
                      worksheet_name: str = "Stock Tracker",
                      clear_existing: bool = True) -> Dict[str, Any]
```

**Описание:** Обновляет таблицу свежими данными из Wildberries API

**Параметры:**
- `spreadsheet_id` - ID Google Sheets документа
- `worksheet_name` - Название листа для обновления (по умолчанию "Stock Tracker")
- `clear_existing` - Очистить существующие данные перед обновлением (по умолчанию True)

**Возвращает:** Dict с результатами обновления

**Что делает:**
1. ✅ Подключается к Wildberries API
2. ✅ Создает задачу получения остатков складов
3. ✅ Ждет обработки задачи (20 секунд)
4. ✅ Скачивает данные остатков
5. ✅ Получает данные заказов за последние 7 дней
6. ✅ Обрабатывает данные в объекты Product
7. ✅ Записывает продукты в Google Sheets батчами

### 2. SheetsOperations.update_table_on_startup()

**Файл:** `src/stock_tracker/database/operations.py`

```python
def update_table_on_startup(self, spreadsheet_id: str,
                           worksheet_name: str = "Stock Tracker") -> bool
```

**Описание:** Удобная функция для обновления данных при старте приложения

**Параметры:**
- `spreadsheet_id` - ID Google Sheets документа
- `worksheet_name` - Название листа

**Возвращает:** True если обновление прошло успешно, False иначе

### 3. main.update_table()

**Файл:** `src/stock_tracker/main.py`

```python
async def update_table() -> None
```

**Описание:** Асинхронная функция для обновления таблицы через командную строку

**Что делает:**
1. ✅ Загружает конфигурацию
2. ✅ Проверяет наличие spreadsheet_id
3. ✅ Инициализирует Google Sheets клиент
4. ✅ Запускает обновление таблицы

## Способы использования

### 1. Через командную строку

```bash
# Обновить таблицу
python -m src.stock_tracker.main --update-table

# Показать справку
python -m src.stock_tracker.main --help
```

### 2. Через Python скрипт

```bash
# Запустить отдельный скрипт обновления
python update_table.py

# С параметрами
python update_table.py [spreadsheet_id] [worksheet_name]
```

### 3. Через bat-файл (Windows)

```bash
# Двойной клик или запуск из командной строки
update_table.bat
```

### 4. Программно

```python
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations

# Инициализация
sheets_client = GoogleSheetsClient("config/service-account.json")
operations = SheetsOperations(sheets_client)

# Обновление таблицы
result = operations.refresh_table_data(
    spreadsheet_id="your_spreadsheet_id",
    worksheet_name="Stock Tracker",
    clear_existing=True
)

print(f"Обновлено продуктов: {result.get('products_updated', 0)}")
```

## Конфигурация

### Обязательные параметры

1. **Google Sheets API**
   - Файл `config/service-account.json` с ключами сервисного аккаунта

2. **Wildberries API**
   - `WB_API_KEY` в переменных окружения или .env файле

3. **Google Sheets ID**
   - `SPREADSHEET_ID` в переменных окружения или .env файле

### Пример .env файла

```bash
# Wildberries API
WB_API_KEY=your_wildberries_api_key_here

# Google Sheets
SPREADSHEET_ID=1abc123def456ghi789jkl_your_spreadsheet_id

# Опционально
LOG_LEVEL=INFO
```

## Результат работы

После успешного обновления таблица будет содержать:

| Столбец | Описание | Пример |
|---------|----------|---------|
| A | Артикул продавца | WB001 |
| B | Артикул товара (nmId) | 12345678 |
| C | Заказы (всего) | 156 |
| D | Остатки (всего) | 1200 |
| E | Оборачиваемость (целое число) | 0 |
| F | Название склада | СЦ Волгоград<br>СЦ Москва |
| G | Заказы со склада | 89<br>67 |
| H | Остатки на складе | 650<br>550 |

## Логирование

Функции создают подробные логи процесса обновления:

```
[INFO] Starting table data refresh for worksheet 'Stock Tracker'
[INFO] Clearing existing data...
[INFO] Fetching fresh data from Wildberries API...
[INFO] Created API task: task_12345
[INFO] Downloaded 45 warehouse items
[INFO] Downloaded 128 orders
[INFO] Processed 23 products from API data
[INFO] Successfully updated table with 23 products
[INFO] Table refresh completed successfully
```

## Обработка ошибок

Функции включают обработку типичных ошибок:

- ❌ Отсутствие конфигурации API ключей
- ❌ Недоступность Google Sheets API
- ❌ Ошибки сети при обращении к Wildberries API
- ❌ Неверный ID Google Sheets документа
- ❌ Отсутствие файла сервисного аккаунта

## Производительность

- **Время выполнения:** ~30-60 секунд (включая ожидание обработки задачи WB API)
- **Пакетная запись:** Данные записываются батчами для оптимизации
- **Автоматическая очистка:** Старые данные удаляются перед записью новых
- **Валидация данных:** Все данные проходят валидацию перед записью

## Безопасность

- ✅ API ключи не попадают в логи
- ✅ Валидация всех входных параметров
- ✅ Защита от SQL-инъекций (не применимо, но принцип соблюден)
- ✅ Graceful обработка ошибок без раскрытия внутренней логики

## Заключение

Добавленные функции обновления таблицы предоставляют:

1. **Простоту использования** - обновление одной командой
2. **Гибкость** - можно использовать программно или через CLI
3. **Надежность** - полная обработка ошибок и валидация
4. **Производительность** - оптимизированная пакетная запись
5. **Мониторинг** - подробное логирование всех операций

Эти функции идеально подходят для регулярного обновления данных при запуске приложения или по расписанию.