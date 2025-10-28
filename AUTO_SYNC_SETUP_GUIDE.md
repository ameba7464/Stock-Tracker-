# ✅ АВТОМАТИЧЕСКАЯ СИНХРОНИЗАЦИЯ - ИНСТРУКЦИЯ

**Дата:** 28.10.2025  
**Статус:** ✅ Готово к использованию

---

## 📋 РЕЗУЛЬТАТЫ ПОЛНОЙ СИНХРОНИЗАЦИИ

### Итоги обновления:

✅ **Статус:** COMPLETED (100% успешно)  
✅ **Продуктов обработано:** 11 из 11  
✅ **Время выполнения:** 136 секунд (~2.3 минуты)  
✅ **Ошибок:** 0

### Статистика заказов:

```
Total raw orders from API:      61
After filtering cancelled:      57 (-4 отменённых)
After deduplication (srid):     57 (-0 дубликатов)
Final orders_data count:        57
```

### Топ складов по заказам:

| Склад | Заказов | Остатков | Продуктов |
|-------|---------|----------|-----------|
| **Обухово МП** | 17 | 0 | 6 |
| Самара (Новосемейкино) | 9 | 157 | 2 |
| Котовск | 8 | 191 | 3 |

### Текущие показатели таблицы:

- **Всего продуктов:** 12
- **Всего остатков:** 1,221 шт
- **Всего заказов:** 59 шт
- **Средняя оборачиваемость:** 0.008

---

## 🔄 НАСТРОЙКА АВТОМАТИЧЕСКОЙ СИНХРОНИЗАЦИИ

### Метод 1: Windows Task Scheduler (Рекомендуется)

**Для настройки (требуются права администратора):**

1. **Откройте PowerShell от имени администратора**
   ```powershell
   # Правый клик на PowerShell -> "Запуск от имени администратора"
   ```

2. **Перейдите в папку проекта**
   ```powershell
   cd "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"
   ```

3. **Запустите скрипт настройки**
   ```powershell
   .\setup_windows_task.ps1
   ```

4. **Проверьте задачу**
   ```powershell
   Get-ScheduledTask -TaskName "Stock Tracker Auto Sync"
   ```

**Параметры задачи:**
- ⏰ **Расписание:** Ежедневно в 2:00 AM
- 🔁 **Повтор:** Один раз в день
- 📂 **Скрипт:** `auto_sync.bat`
- 🔋 **Питание:** Запускается даже от батареи
- 🌐 **Сеть:** Только при наличии интернета

---

### Метод 2: Ручной запуск через BAT-файл

**Для разовой синхронизации:**

1. **Двойной клик на файл:**
   ```
   C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\auto_sync.bat
   ```

2. **Или через командную строку:**
   ```cmd
   cd "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"
   auto_sync.bat
   ```

**Создайте ярлык на рабочем столе:**
- Правый клик на `auto_sync.bat` → "Создать ярлык"
- Переместите ярлык на рабочий стол
- При необходимости переименуйте: "Stock Tracker - Обновить данные"

---

### Метод 3: Python-скрипт напрямую

**Для разработчиков:**

```bash
# Активировать виртуальное окружение
.venv\Scripts\activate

# Запустить полную синхронизацию
python run_full_sync.py

# Или краткий вариант
python -c "import asyncio; from run_full_sync import run_full_synchronization; asyncio.run(run_full_synchronization())"
```

---

## 📅 РЕКОМЕНДУЕМЫЕ РАСПИСАНИЯ

### Для разных сценариев:

| Сценарий | Расписание | Описание |
|----------|------------|----------|
| **Ежедневное обновление** | `2:00 AM каждый день` | ✅ Рекомендуется |
| Дважды в день | `2:00 AM и 2:00 PM` | Актуальные данные |
| Рабочие часы | `9:00 AM (Пн-Пт)` | Только в будни |
| Еженедельно | `2:00 AM понедельник` | Минимальная нагрузка |

**Наша текущая настройка:** ✅ Ежедневно в 2:00 AM

---

## 🔧 УПРАВЛЕНИЕ ЗАДАЧЕЙ

### Команды PowerShell:

```powershell
# Проверить статус задачи
Get-ScheduledTask -TaskName "Stock Tracker Auto Sync"

# Запустить задачу вручную (тест)
Start-ScheduledTask -TaskName "Stock Tracker Auto Sync"

# Отключить автоматический запуск
Disable-ScheduledTask -TaskName "Stock Tracker Auto Sync"

# Включить автоматический запуск
Enable-ScheduledTask -TaskName "Stock Tracker Auto Sync"

# Удалить задачу
Unregister-ScheduledTask -TaskName "Stock Tracker Auto Sync" -Confirm:$false
```

### Через Task Scheduler GUI:

1. **Открыть Task Scheduler:**
   - Нажмите `Win + R`
   - Введите: `taskschd.msc`
   - Нажмите Enter

2. **Найти задачу:**
   - В списке найдите: "Stock Tracker Auto Sync"

3. **Изменить расписание:**
   - Правый клик → Properties
   - Вкладка "Triggers" → Edit
   - Измените время/частоту

4. **Просмотр истории:**
   - Вкладка "History"
   - Проверьте успешные/неуспешные запуски

---

## 📊 МОНИТОРИНГ

### Проверка логов:

**Файл логов:**
```
C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\logs\stock_tracker.log
```

**Посмотреть последние записи (PowerShell):**
```powershell
Get-Content ".\logs\stock_tracker.log" -Tail 50
```

**Фильтр только ошибок:**
```powershell
Get-Content ".\logs\stock_tracker.log" | Select-String "ERROR"
```

### Что проверять:

✅ **Успешная синхронизация:**
- `Status: COMPLETED`
- `Products processed: X`
- `Products failed: 0`

⚠️ **Возможные проблемы:**
- `APIError: [429]` - Превышена квота Google API (подождите)
- `APIError: [403]` - Проблема с доступом к API
- `Connection error` - Нет интернета

---

## 🎯 ПРОВЕРКА РЕЗУЛЬТАТОВ

### Сразу после синхронизации:

1. **Откройте Google Sheets:**
   - Ссылка: https://docs.google.com/spreadsheets/d/1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho

2. **Проверьте данные:**
   - ✅ Колонка "Заказы со склада" заполнена (не 0)
   - ✅ Новые склады появились (Обухово МП, Подольск 3)
   - ✅ Даты обновлены

3. **Сравните с предыдущими значениями:**
   - Было: ~173 заказа
   - Стало: ~59 заказов (но это 27-28 октября, а не 22-28)

---

## ⚙️ ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ

### Изменение периода синхронизации:

**Файл:** `src/stock_tracker/services/product_service.py`  
**Строка:** ~310

```python
# Текущая настройка: начало текущей недели (понедельник)
def get_week_start() -> str:
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    return start_of_week.strftime("%Y-%m-%dT00:00:00")

# Альтернатива: фиксированное количество дней назад
# date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
```

### Уведомления при ошибках:

Добавьте в конец `auto_sync.bat`:

```batch
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Sync failed! | msg %username% /time:10
)
```

---

## 📝 БЫСТРЫЕ КОМАНДЫ

### Ежедневное использование:

```powershell
# 1. Проверить статус последней синхронизации
Get-Content ".\logs\stock_tracker.log" -Tail 20

# 2. Запустить синхронизацию вручную
.\auto_sync.bat

# 3. Проверить задачу в планировщике
Get-ScheduledTask -TaskName "Stock Tracker Auto Sync"
```

---

## ✅ ИТОГИ

### Что настроено:

✅ **Скрипт синхронизации:** `run_full_sync.py`  
✅ **BAT-файл для запуска:** `auto_sync.bat`  
✅ **Скрипт настройки Task Scheduler:** `setup_windows_task.ps1`  
✅ **Логирование:** `logs/stock_tracker.log`

### Рекомендуемые действия:

1. ✅ **Настроить Task Scheduler** (требует прав администратора)
2. ⏭️ **Проверить работу через неделю** (посмотреть логи)
3. ⏭️ **Мониторить квоту Google API** (60 запросов/минута)

### Текущий статус:

🟢 **Синхронизация работает корректно**  
🟢 **Все исправления применены**  
🟢 **Google Sheets обновлена**  
🟡 **Автозапуск требует настройки Task Scheduler с правами администратора**

---

**Дата создания:** 28.10.2025 15:40  
**Последняя синхронизация:** 28.10.2025 15:39  
**Следующая рекомендуемая синхронизация:** 29.10.2025 02:00
