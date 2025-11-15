# 🔧 Исправление проблемы аутентификации на Railway

## Проблема

В логах Railway видна ошибка:
```
Service account file not found: {JSON содержимое}
```

Это означает, что переменная окружения `GOOGLE_SERVICE_ACCOUNT` настроена неправильно.

## Решение

### Шаг 1: Откройте Railway Dashboard

1. Перейдите на https://railway.app
2. Откройте ваш проект **Stock-Tracker-**
3. Перейдите во вкладку **Variables**

### Шаг 2: Проверьте переменные окружения

Убедитесь, что у вас есть следующие переменные:

#### ✅ Обязательные переменные:

```
WILDBERRIES_API_KEY=eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ...
GOOGLE_SHEET_ID=1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho
GOOGLE_SHEET_NAME=Stock Tracker
```

#### 🔑 Главная переменная - GOOGLE_SERVICE_ACCOUNT:

**Важно!** Эта переменная должна содержать **весь JSON** из файла `config/service-account.json` **БЕЗ** переносов строк и **БЕЗ** лишних пробелов.

### Шаг 3: Правильно настройте GOOGLE_SERVICE_ACCOUNT

#### Вариант 1: Через Railway Dashboard (рекомендуется)

1. В Railway Dashboard → **Variables**
2. Нажмите **New Variable**
3. **Variable Name:** `GOOGLE_SERVICE_ACCOUNT`
4. **Value:** вставьте JSON **одной строкой**:

```json
{"type":"service_account","project_id":"your-project-id","private_key_id":"your-key-id","private_key":"-----BEGIN PRIVATE KEY-----\n...your private key...\n-----END PRIVATE KEY-----\n","client_email":"your-service-account@your-project.iam.gserviceaccount.com","client_id":"your-client-id","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com","universe_domain":"googleapis.com"}
```

**Важно!** Замените на ваши реальные данные из `config/service-account.json`

5. Нажмите **Add**

#### Вариант 2: Через PowerShell (создать минифицированный JSON)

Запустите в PowerShell:

```powershell
# Перейдите в папку проекта
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"

# Создайте минифицированный JSON (одна строка)
$json = Get-Content "config\service-account.json" | ConvertFrom-Json | ConvertTo-Json -Compress

# Скопируйте в буфер обмена
$json | Set-Clipboard

Write-Host "✅ JSON скопирован в буфер обмена!"
Write-Host "Теперь вставьте его в Railway как значение переменной GOOGLE_SERVICE_ACCOUNT"
```

### Шаг 4: Удалите неправильную переменную (если есть)

Если у вас уже есть переменная `GOOGLE_SERVICE_ACCOUNT_KEY_PATH` - **удалите её**. На Railway она не нужна, потому что мы используем `GOOGLE_SERVICE_ACCOUNT` напрямую.

### Шаг 5: Проверьте другие переменные

Убедитесь, что установлены:

```
LOG_LEVEL=INFO
TZ=Europe/Moscow
WILDBERRIES_BASE_URL=https://seller-analytics-api.wildberries.ru
WILDBERRIES_STATISTICS_BASE_URL=https://statistics-api.wildberries.ru
```

### Шаг 6: Перезапустите деплой

1. В Railway Dashboard нажмите **Settings**
2. Прокрутите вниз до **Danger Zone**
3. Нажмите **Restart Deployment**

Или просто сделайте новый коммит:

```bash
git commit --allow-empty -m "chore: trigger Railway redeploy"
git push origin main
```

### Шаг 7: Проверьте логи

1. Railway Dashboard → **Deployments**
2. Нажмите на последний деплой
3. Смотрите логи

**Должны увидеть:**
```
✅ Создан временный файл service account: /tmp/service-account-xxxxx.json
✅ Конфигурация загружена успешно
📊 Подключение к Google Sheets...
✅ Подключение к Google Sheets установлено
```

## Проверка конфигурации

Чтобы убедиться, что всё настроено правильно, проверьте логи на наличие:

### ✅ Правильно:
```
✅ Создан временный файл service account: /tmp/service-account-xxxxx.json
✅ Конфигурация загружена успешно
```

### ❌ Неправильно:
```
Service account file not found: {JSON содержимое}
```

## Если проблема сохраняется

### 1. Проверьте формат JSON

Убедитесь, что JSON в `GOOGLE_SERVICE_ACCOUNT`:
- Не содержит лишних переносов строк
- Все escape-последовательности (`\n`) сохранены
- Закрывающие кавычки и скобки на месте

### 2. Проверьте, что JSON валиден

Вставьте содержимое `GOOGLE_SERVICE_ACCOUNT` в https://jsonlint.com/ и проверьте, что нет ошибок.

### 3. Пересоздайте переменную

Если ничего не помогло:
1. Удалите переменную `GOOGLE_SERVICE_ACCOUNT` в Railway
2. Создайте её заново, внимательно скопировав JSON

### 4. Проверьте права доступа

Убедитесь, что service account имеет права на вашу Google таблицу:
1. Откройте файл `config/service-account.json`
2. Найдите `client_email`: `stock-tracker@named-deck-463213-s2.iam.gserviceaccount.com`
3. Откройте вашу Google таблицу
4. Нажмите **Share** (Поделиться)
5. Добавьте этот email с правами **Editor** (Редактор)

## Дополнительная информация

- Файл конфигурации: `src/stock_tracker/utils/config.py`
- Документация: `AUTONOMOUS_DEPLOYMENT_GUIDE.md`
- Быстрый старт: `RAILWAY_QUICK_START.md`

---

**Создано**: 15 ноября 2025  
**Проблема**: Authentication failed - service account not found  
**Решение**: Правильная настройка переменной GOOGLE_SERVICE_ACCOUNT на Railway
