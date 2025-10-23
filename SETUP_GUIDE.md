# Инструкция по настройке обновления таблицы

## 🚨 Проблемы и их решения

### Проблема 1: "Spreadsheet ID not configured"

**Ошибка:**
```
[ERROR] Spreadsheet ID not configured. Please set GOOGLE_SHEET_ID in environment
```

**Решение:**
1. Откройте файл `.env` в корневой папке проекта
2. Найдите строку `GOOGLE_SHEET_ID=1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho`
3. Убедитесь, что значение соответствует вашему реальному Google Sheets документу

### Проблема 2: "update_table.bat не найдена"

**Ошибка в PowerShell:**
```
update_table.bat : Имя "update_table.bat" не распознано как имя командлета
```

**Решение:**
В PowerShell нужно использовать `.\` перед именем файла:
```powershell
.\update_table.bat
```

## ✅ Пошаговая настройка

### Шаг 1: Проверьте .env файл

Убедитесь, что ваш `.env` файл содержит:

```bash
# Wildberries API ключ
WILDBERRIES_API_KEY=ваш_ключ_здесь

# Google Sheets ID - замените на свой реальный ID документа
GOOGLE_SHEET_ID=ваш_google_sheets_id_здесь

# Остальные настройки
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=./config/service-account.json
LOG_LEVEL=INFO
```

### Шаг 2: Получите Google Sheets ID

1. Откройте ваш Google Sheets документ в браузере
2. Скопируйте ID из URL. Пример URL:
   ```
   https://docs.google.com/spreadsheets/d/1ABC123def456GHI789jkl/edit
   ```
   ID = `1ABC123def456GHI789jkl` (часть между `/d/` и `/edit`)
3. Вставьте этот ID в .env файл

### Шаг 3: Настройте Google Service Account

1. Убедитесь, что файл `config/service-account.json` существует
2. Этот файл должен содержать ключи сервисного аккаунта Google
3. Сервисный аккаунт должен иметь доступ к вашему Google Sheets документу

### Шаг 4: Проверьте настройки

Запустите проверку конфигурации:
```bash
python -c "from src.stock_tracker.utils.config import get_config; config = get_config(); print(f'Google Sheet ID: {config.google_sheet_id}')"
```

## 🚀 Способы запуска обновления

### 1. Через командную строку (рекомендуемый)
```bash
python -m src.stock_tracker.main --update-table
```

### 2. Через Python скрипт
```bash
python update_table.py
```

### 3. Через bat-файл (Windows)
```bash
# В Command Prompt
update_table.bat

# В PowerShell
.\update_table.bat
```

### 4. С указанием конкретного ID документа
```bash
python update_table.py 1ABC123def456GHI789jkl "Stock Tracker"
```

## 🔧 Диагностика проблем

### Проверить наличие файлов
```bash
# Проверить .env
dir .env

# Проверить service account
dir config\service-account.json

# Проверить структуру проекта
dir src\stock_tracker\main.py
```

### Проверить конфигурацию
```bash
python -c "
from src.stock_tracker.utils.config import get_config
try:
    config = get_config()
    print('✅ Конфигурация загружена')
    print(f'Google Sheet ID: {config.google_sheet_id}')
    print(f'Service Account Path: {config.google_service_account_key_path}')
except Exception as e:
    print(f'❌ Ошибка конфигурации: {e}')
"
```

### Проверить доступ к Google Sheets
```bash
python -c "
from src.stock_tracker.database.sheets import GoogleSheetsClient
try:
    client = GoogleSheetsClient('config/service-account.json')
    print('✅ Google Sheets клиент инициализирован')
except Exception as e:
    print(f'❌ Ошибка Google Sheets: {e}')
"
```

## 📝 Частые ошибки и решения

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `GOOGLE_SHEET_ID not configured` | Не настроен ID документа | Добавьте правильный ID в .env |
| `Service account key file not found` | Нет файла сервисного аккаунта | Добавьте service-account.json в config/ |
| `Permission denied` | Нет доступа к документу | Дайте доступ сервисному аккаунту к Google Sheets |
| `API key invalid` | Неверный Wildberries API ключ | Проверьте и обновите WILDBERRIES_API_KEY |
| `Module not found` | Проблемы с путями | Запускайте из корневой папки проекта |

## 💡 Рекомендации

1. **Всегда запускайте из корневой папки проекта**
2. **Проверьте настройки .env файла перед запуском**
3. **Убедитесь в наличии интернет-соединения**
4. **Дайте процессу 30-60 секунд на выполнение**
5. **Проверьте логи в случае ошибок**

## 🔐 Безопасность

- ❌ **НЕ** публикуйте .env файл с реальными API ключами
- ❌ **НЕ** публикуйте service-account.json файл
- ✅ Используйте разные ключи для разработки и продакшена
- ✅ Регулярно обновляйте API ключи