# Google Sheets Integration Guide

## 📋 Обзор

Stock Tracker автоматически синхронизирует данные о товарах в Google Таблицы. Каждый селлер получает свою собственную таблицу с данными о товарах, которая обновляется автоматически после каждой синхронизации с Wildberries.

## 🏗️ Архитектура

```
Wildberries API → PostgreSQL → Google Sheets
                      ↓
                 Celery Task
                      ↓
              GoogleSheetsService
```

### Компоненты:

1. **GoogleSheetsService** (`src/stock_tracker/services/google_sheets_service.py`)
   - Создание новых таблиц
   - Форматирование заголовков
   - Синхронизация данных
   - Условное форматирование (низкий остаток = красный)

2. **Celery Task** (`src/stock_tracker/workers/tasks.py`)
   - После успешной синхронизации с Wildberries
   - Автоматически обновляет Google Sheet
   - Обрабатывает ошибки без провала основной синхронизации

3. **REST API** (`src/stock_tracker/api/routes/sheets.py`)
   - `POST /api/v1/sheets/credentials` - Загрузка Service Account credentials
   - `POST /api/v1/sheets/create` - Создание новой таблицы
   - `GET /api/v1/sheets/info` - Информация о таблице
   - `POST /api/v1/sheets/test` - Тест подключения
   - `POST /api/v1/sheets/sync` - Ручная синхронизация

## 🚀 Setup: Как настроить Google Sheets для селлера

### Шаг 1: Создать Google Service Account

1. Перейти в [Google Cloud Console](https://console.cloud.google.com/)
2. Создать новый проект или выбрать существующий
3. Включить **Google Sheets API** и **Google Drive API**:
   - APIs & Services → Enable APIs and Services
   - Найти "Google Sheets API" → Enable
   - Найти "Google Drive API" → Enable

4. Создать Service Account:
   - IAM & Admin → Service Accounts
   - Create Service Account
   - Name: `stock-tracker-{tenant_name}`
   - Role: **Editor** (для создания файлов в Drive)
   - Create Key → JSON

5. Скачать JSON файл с credentials

### Шаг 2: Загрузить credentials через API

```bash
# Пример JSON credentials (service-account.json):
{
  "type": "service_account",
  "project_id": "stock-tracker-123456",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "stock-tracker-seller@project.iam.gserviceaccount.com",
  "client_id": "123456789...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/..."
}
```

```powershell
# Загрузить credentials (без sheet_id - создадим таблицу позже)
$CREDENTIALS_JSON = Get-Content -Raw service-account.json
$BODY = @{
    google_credentials_json = $CREDENTIALS_JSON
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/credentials" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" } `
    -Body $BODY `
    -ContentType "application/json"
```

### Шаг 3: Создать новую Google Sheet

```powershell
# Создать таблицу с именем и расшарить селлеру
$BODY = @{
    title = "My Company - Stock Tracker"
    share_with_email = "seller@example.com"
} | ConvertTo-Json

$RESULT = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/create" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" } `
    -Body $BODY `
    -ContentType "application/json"

Write-Host "Sheet URL: $($RESULT.sheet_url)"
```

**Результат:**
- Создана новая Google Sheet
- Заголовки отформатированы (синий фон, белый текст, жирный шрифт)
- Sheet ID сохранен в базе данных
- Таблица расшарена с email селлера
- Селлер получит email-уведомление с ссылкой

### Шаг 4: Протестировать подключение

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/test" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" }
```

**Ожидаемый ответ:**
```json
{
    "success": true,
    "sheet_title": "My Company - Stock Tracker",
    "sheet_url": "https://docs.google.com/spreadsheets/d/...",
    "worksheet_title": "Products",
    "row_count": 1000,
    "col_count": 8
}
```

### Шаг 5: Запустить первую синхронизацию

```powershell
# Сначала синхронизация с Wildberries
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/products/sync" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" }

# Затем ручная синхронизация в Google Sheets (если нужно немедленно)
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/sync" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" }
```

**Автоматическая синхронизация:**
После настройки, Google Sheet будет обновляться автоматически после каждой успешной синхронизации с Wildberries (через Celery tasks).

## 📊 Структура данных в Google Sheet

### Колонки:

| Column | Description | Format |
|--------|-------------|--------|
| **ID товара WB** | marketplace_article | Plain text |
| **Артикул продавца** | seller_article | Plain text |
| **Название товара** | product_name | Plain text |
| **Общий остаток** | total_stock | Number, conditional formatting |
| **Общие заказы** | total_orders | Number |
| **В пути к клиенту** | in_way_to_client | Number |
| **В пути от клиента** | in_way_from_client | Number |
| **Последнее обновление** | updated_at | Datetime (YYYY-MM-DD HH:MM:SS) |

### Условное форматирование:

- 🔴 **Красный фон**: Остаток < 10 (критический)
- 🟡 **Желтый фон**: Остаток 10-20 (низкий)
- ⚪ **Без цвета**: Остаток > 20 (нормально)

### Пример данных:

```
| ID товара WB | Артикул продавца | Название товара      | Общий остаток | Общие заказы | В пути к клиенту | В пути от клиента | Последнее обновление    |
|-------------|------------------|---------------------|---------------|--------------|-----------------|------------------|------------------------|
| 163383326   | ART-001          | Футболка мужская    | 5             | 120          | 10              | 2                | 2025-01-21 19:54:04   |
| 163383327   | ART-002          | Футболка женская    | 15            | 95           | 5               | 1                | 2025-01-21 19:54:04   |
```

## 🔄 Автоматическая синхронизация

### Как работает:

1. **Celery Beat** запускает `sync_tenant_products` task по расписанию (каждый час)
2. Task синхронизирует данные с Wildberries → PostgreSQL
3. После успешной синхронизации с БД:
   - Проверяется наличие `google_sheet_id` и `google_service_account_encrypted`
   - Если настроено → запускается `GoogleSheetsService.sync_products_to_sheet()`
   - Все продукты из PostgreSQL записываются в Google Sheet
   - Применяется условное форматирование

4. **Если синхронизация с Google Sheets падает:**
   - Ошибка логируется
   - Основная синхронизация НЕ падает
   - Webhook получает `google_sheets: {success: false, error: "..."}}`

### Логи синхронизации:

```
INFO: Starting product sync for tenant 3eb1c21d-3538-4cab-a98a-9894460e2c4d (Test Seller)
INFO: Completed sync for tenant 3eb1c21d-3538-4cab-a98a-9894460e2c4d: 2 products in 3.82s
INFO: Syncing 2 products to Google Sheet for tenant 3eb1c21d-3538-4cab-a98a-9894460e2c4d
INFO: ✅ Google Sheets sync completed: 2 products in 1.45s
```

## 🧪 Testing

### Test Script: `test_sheets_api.ps1`

```powershell
# 1. Login and get token
$LOGIN_BODY = @{
    username = "test@example.com"
    password = "password123"
} | ConvertTo-Json

$LOGIN_RESPONSE = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -Body $LOGIN_BODY `
    -ContentType "application/json"

$TOKEN = $LOGIN_RESPONSE.access_token

# 2. Upload Google credentials
$CREDENTIALS_JSON = Get-Content -Raw service-account.json
$BODY = @{
    google_credentials_json = $CREDENTIALS_JSON
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/credentials" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" } `
    -Body $BODY `
    -ContentType "application/json"

# 3. Create new sheet
$BODY = @{
    title = "Test Company - Stock Tracker"
    share_with_email = "test@example.com"
} | ConvertTo-Json

$RESULT = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/create" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" } `
    -Body $BODY `
    -ContentType "application/json"

Write-Host "✅ Sheet created: $($RESULT.sheet_url)"

# 4. Test connection
$TEST_RESULT = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/test" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" }

Write-Host "✅ Connection test: $($TEST_RESULT.success)"

# 5. Manual sync
$SYNC_RESULT = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/sheets/sync" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $TOKEN" }

Write-Host "✅ Synced $($SYNC_RESULT.products_synced) products"
```

## 🔐 Security

### Шифрование credentials:

- Service Account JSON хранится в `tenant.google_service_account_encrypted` (Text)
- Используется Fernet symmetric encryption
- Encryption key из переменной окружения `ENCRYPTION_KEY`
- Расшифровка происходит только при синхронизации

### Права доступа:

- **Service Account** имеет доступ только к созданным им таблицам
- **Селлер** получает права **Writer** на свою таблицу
- Таблица НЕ публичная (только для Service Account и селлера)

## 📈 Мониторинг

### Metrics (Prometheus):

```
# Количество успешных синхронизаций в Google Sheets
sheets_sync_success_total{tenant_id="..."}

# Количество неудачных синхронизаций
sheets_sync_failure_total{tenant_id="..."}

# Время синхронизации (секунды)
sheets_sync_duration_seconds{tenant_id="..."}
```

### Webhooks:

После каждой синхронизации отправляется webhook `sync_completed`:

```json
{
    "event_type": "sync_completed",
    "tenant_id": "3eb1c21d-3538-4cab-a98a-9894460e2c4d",
    "products_count": 2,
    "duration_seconds": 3.82,
    "completed_at": "2025-01-21T19:54:04",
    "google_sheets": {
        "success": true,
        "products_synced": 2,
        "duration_seconds": 1.45,
        "sheet_url": "https://docs.google.com/spreadsheets/d/..."
    }
}
```

## 🐛 Troubleshooting

### Ошибка: "Google credentials not configured"

**Решение:** Загрузить Service Account credentials через `POST /api/v1/sheets/credentials`

### Ошибка: "Google Sheet ID not set"

**Решение:** Создать новую таблицу через `POST /api/v1/sheets/create`

### Ошибка: "Permission denied" при создании таблицы

**Причина:** Service Account не имеет прав на Google Drive

**Решение:** Убедиться, что включены **Google Drive API** и роль **Editor**

### Ошибка: "Insufficient space" при записи данных

**Решение:** GoogleSheetsService автоматически расширяет таблицу (+300 строк buffer)

Если проблема сохраняется → проверить логи:

```bash
docker logs stock-tracker-worker-1 | grep "Google Sheets"
```

### Данные не обновляются автоматически

**Проверить:**
1. Celery Worker работает: `docker ps | grep worker`
2. Последняя синхронизация: `GET /api/v1/analytics/sync-history`
3. Google credentials настроены: `GET /api/v1/sheets/info`

## 🎯 API Reference

### POST /api/v1/sheets/credentials

Upload Google Service Account credentials.

**Request:**
```json
{
    "google_sheet_id": "1abc...xyz", // Optional
    "google_credentials_json": "{...}" // Service Account JSON
}
```

**Response:**
```json
{
    "message": "Google Sheets credentials updated successfully",
    "tenant_id": "3eb1c21d-3538-4cab-a98a-9894460e2c4d",
    "sheet_id": "1abc...xyz"
}
```

### POST /api/v1/sheets/create

Create new Google Sheet for tenant.

**Request:**
```json
{
    "title": "My Company - Stock Tracker", // Optional
    "share_with_email": "seller@example.com" // Optional
}
```

**Response:**
```json
{
    "sheet_id": "1abc...xyz",
    "sheet_url": "https://docs.google.com/spreadsheets/d/1abc...xyz",
    "title": "My Company - Stock Tracker",
    "worksheet_name": "Products",
    "message": "Google Sheet created successfully! Access it at: https://..."
}
```

### GET /api/v1/sheets/info

Get information about tenant's Google Sheet.

**Response:**
```json
{
    "sheet_id": "1abc...xyz",
    "sheet_url": "https://docs.google.com/spreadsheets/d/1abc...xyz",
    "title": "My Company - Stock Tracker",
    "worksheet_name": "Products",
    "row_count": 1000,
    "col_count": 8,
    "data_rows": 2,
    "last_updated": "2025-01-21T19:54:04",
    "is_configured": true
}
```

### POST /api/v1/sheets/test

Test connection to Google Sheet.

**Response:**
```json
{
    "success": true,
    "sheet_title": "My Company - Stock Tracker",
    "sheet_url": "https://docs.google.com/spreadsheets/d/...",
    "worksheet_title": "Products",
    "row_count": 1000,
    "col_count": 8
}
```

### POST /api/v1/sheets/sync

Manually sync products to Google Sheet.

**Response:**
```json
{
    "success": true,
    "products_synced": 2,
    "duration_seconds": 1.45,
    "sheet_url": "https://docs.google.com/spreadsheets/d/...",
    "message": "Successfully synced 2 products to Google Sheet"
}
```

## 🚀 Deployment Checklist

- [ ] Google Cloud Project создан
- [ ] Google Sheets API включен
- [ ] Google Drive API включен
- [ ] Service Account создан с ролью Editor
- [ ] Service Account JSON скачан
- [ ] `ENCRYPTION_KEY` установлен в `.env`
- [ ] Celery Worker запущен
- [ ] Credentials загружены через API
- [ ] Google Sheet создана
- [ ] Connection test успешен
- [ ] Первая синхронизация выполнена

## 📚 Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [gspread Python Library](https://docs.gspread.org/)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-accounts)

---

**Status:** ✅ Implementation Complete  
**Version:** 2.0.0  
**Last Updated:** 2025-01-21
