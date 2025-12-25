# 🚀 ФИНАЛЬНАЯ ИНСТРУКЦИЯ: Деплой Telegram бота на сервер

## ✅ Что уже проверено и работает

### Локальная проверка (25 декабря 2025):
- ✅ Все handlers работают корректно
- ✅ PostgreSQL подключение к Yandex Cloud (158.160.188.247:5432/stocktracker)
- ✅ Google Sheets Service Account работает
- ✅ Wildberries API интеграция готова
- ✅ Database models и CRUD операции протестированы
- ✅ Кодировка UTF-8 исправлена для Windows
- ✅ Emoji заменены на текстовые метки в логах
- ✅ Все зависимости установлены

### ⚠️ Известные проблемы (не критично):
- OAuth токен устарел (для создания новых таблиц)
  - Service Account работает для чтения/обновления
  - Можно обновить позже через `get_oauth_token.py`

---

## 📦 Подготовка к деплою

### 1. Файлы для загрузки на сервер:

```
telegram-bot/
├── app/                          # Весь код приложения
├── requirements.txt              # Зависимости Python
├── .env                         # Конфигурация (ВАЖНО!)
├── credentials.json             # Google Service Account (ВАЖНО!)
├── token.json                   # OAuth токен (опционально)
├── deploy.sh                    # Скрипт автоматического деплоя
└── stock-tracker-bot.service   # Systemd service файл
```

### 2. Проверьте .env файл:

```bash
# Откройте и проверьте:
cat telegram-bot/.env
```

Должно быть:
```env
BOT_TOKEN=8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms
DATABASE_URL=postgresql+asyncpg://stocktracker:StockTracker2024@158.160.188.247:5432/stocktracker
DB_HOST=158.160.188.247
DB_PORT=5432
DB_NAME=stocktracker
DB_USER=stocktracker
DB_PASSWORD=StockTracker2024
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/...
GOOGLE_DRIVE_FOLDER_ID=1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA
LOG_LEVEL=INFO
```

---

## 🖥️ Деплой на сервер (2 варианта)

### Вариант A: Автоматический деплой (Рекомендуется)

#### 1. Подключитесь к серверу:
```bash
ssh root@158.160.188.247
# или
ssh your-username@158.160.188.247
```

#### 2. Загрузите файлы на сервер:

**Из Windows PowerShell:**
```powershell
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\telegram-bot"

# Создаем архив
Compress-Archive -Path app,requirements.txt,.env,credentials.json,token.json,deploy.sh,stock-tracker-bot.service -DestinationPath telegram-bot.zip

# Загружаем на сервер
scp telegram-bot.zip root@158.160.188.247:/tmp/
```

**Или используйте SFTP клиент (WinSCP, FileZilla)**

#### 3. На сервере распакуйте и запустите деплой:
```bash
cd /tmp
unzip telegram-bot.zip -d telegram-bot
cd telegram-bot
chmod +x deploy.sh
sudo ./deploy.sh
```

Скрипт автоматически:
- Создаст пользователя `stock-bot`
- Установит зависимости
- Создаст systemd service
- Запустит бота 24/7

---

### Вариант B: Ручной деплой

#### 1. Установка зависимостей:
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip postgresql-client
```

#### 2. Создание структуры:
```bash
sudo useradd -r -s /bin/bash -d /opt/stock-tracker-bot stock-bot
sudo mkdir -p /opt/stock-tracker-bot
sudo mkdir -p /var/log/stock-tracker-bot
```

#### 3. Копирование файлов:
```bash
# Загрузите файлы через scp/sftp в /tmp
sudo cp -r /tmp/telegram-bot/app /opt/stock-tracker-bot/
sudo cp /tmp/telegram-bot/requirements.txt /opt/stock-tracker-bot/
sudo cp /tmp/telegram-bot/.env /opt/stock-tracker-bot/
sudo cp /tmp/telegram-bot/credentials.json /opt/stock-tracker-bot/
sudo cp /tmp/telegram-bot/token.json /opt/stock-tracker-bot/
```

#### 4. Создание виртуального окружения:
```bash
cd /opt/stock-tracker-bot
sudo python3.11 -m venv venv
sudo -u stock-bot venv/bin/pip install --upgrade pip
sudo -u stock-bot venv/bin/pip install -r requirements.txt
```

#### 5. Установка прав:
```bash
sudo chown -R stock-bot:stock-bot /opt/stock-tracker-bot
sudo chown -R stock-bot:stock-bot /var/log/stock-tracker-bot
sudo chmod 600 /opt/stock-tracker-bot/.env
sudo chmod 600 /opt/stock-tracker-bot/credentials.json
```

#### 6. Создание systemd service:
```bash
sudo cp stock-tracker-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stock-tracker-bot
sudo systemctl start stock-tracker-bot
```

---

## 📊 Проверка работы

### 1. Статус сервиса:
```bash
sudo systemctl status stock-tracker-bot
```

Должно показать: `Active: active (running)`

### 2. Логи бота:
```bash
# Последние 50 строк
sudo journalctl -u stock-tracker-bot -n 50

# Живые логи
sudo journalctl -u stock-tracker-bot -f

# Файлы логов
sudo tail -f /var/log/stock-tracker-bot/bot.log
sudo tail -f /var/log/stock-tracker-bot/error.log
```

### 3. Проверка через Telegram:
```
1. Откройте бота: @WildBStockBot
2. Отправьте: /start
3. Бот должен ответить главным меню
```

### 4. Проверка PostgreSQL подключения:
```bash
cd /opt/stock-tracker-bot
sudo -u stock-bot venv/bin/python -c "
import asyncio
from app.database.database import init_db
asyncio.run(init_db())
print('Database: OK')
"
```

---

## 🔧 Управление сервисом

### Основные команды:
```bash
# Запуск
sudo systemctl start stock-tracker-bot

# Остановка
sudo systemctl stop stock-tracker-bot

# Перезапуск
sudo systemctl restart stock-tracker-bot

# Статус
sudo systemctl status stock-tracker-bot

# Включить автозапуск
sudo systemctl enable stock-tracker-bot

# Отключить автозапуск
sudo systemctl disable stock-tracker-bot
```

### Просмотр логов:
```bash
# Все логи
sudo journalctl -u stock-tracker-bot

# Последние N строк
sudo journalctl -u stock-tracker-bot -n 100

# Следить за логами в реальном времени
sudo journalctl -u stock-tracker-bot -f

# Логи за сегодня
sudo journalctl -u stock-tracker-bot --since today

# Логи с определенного времени
sudo journalctl -u stock-tracker-bot --since "2025-12-25 18:00"
```

---

## 🚨 Решение проблем

### Бот не запускается:

1. **Проверьте логи:**
```bash
sudo journalctl -u stock-tracker-bot -n 50 --no-pager
```

2. **Проверьте .env файл:**
```bash
sudo cat /opt/stock-tracker-bot/.env
```

3. **Проверьте права:**
```bash
ls -la /opt/stock-tracker-bot/
```

4. **Проверьте подключение к БД:**
```bash
cd /opt/stock-tracker-bot
sudo -u stock-bot venv/bin/python -c "
from app.config import settings
print('DB URL:', settings.get_database_url())
"
```

### Конфликт с другим экземпляром:

Если видите ошибку `TelegramConflictError`:
```bash
# Проверьте, что старый бот остановлен
sudo systemctl status stock-tracker-bot

# Очистите webhook
curl "https://api.telegram.org/bot8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms/deleteWebhook?drop_pending_updates=true"

# Перезапустите
sudo systemctl restart stock-tracker-bot
```

### База данных недоступна:

1. **Проверьте подключение к PostgreSQL:**
```bash
psql -h 158.160.188.247 -p 5432 -U stocktracker -d stocktracker -c "SELECT 1;"
```

2. **Проверьте настройки firewall на сервере БД**

3. **Проверьте, что сервер БД запущен в Yandex Cloud**

---

## 📈 Мониторинг

### Создание скрипта проверки здоровья:

```bash
sudo nano /opt/stock-tracker-bot/health_check.sh
```

Содержимое:
```bash
#!/bin/bash

if systemctl is-active --quiet stock-tracker-bot; then
    echo "[OK] Bot is running"
    exit 0
else
    echo "[ERROR] Bot is not running!"
    sudo systemctl start stock-tracker-bot
    exit 1
fi
```

```bash
sudo chmod +x /opt/stock-tracker-bot/health_check.sh
```

### Добавление в cron:
```bash
sudo crontab -e
```

Добавьте:
```
# Проверка каждые 5 минут
*/5 * * * * /opt/stock-tracker-bot/health_check.sh >> /var/log/stock-tracker-bot/health_check.log 2>&1
```

---

## 🔄 Обновление бота

### 1. Загрузите новые файлы:
```bash
# Остановите бота
sudo systemctl stop stock-tracker-bot

# Сделайте backup
sudo cp -r /opt/stock-tracker-bot /opt/stock-tracker-bot.backup

# Загрузите новые файлы через scp
# Скопируйте в /opt/stock-tracker-bot

# Установите новые зависимости (если изменились)
cd /opt/stock-tracker-bot
sudo -u stock-bot venv/bin/pip install -r requirements.txt

# Запустите
sudo systemctl start stock-tracker-bot
```

### 2. Откат на предыдущую версию:
```bash
sudo systemctl stop stock-tracker-bot
sudo rm -rf /opt/stock-tracker-bot
sudo mv /opt/stock-tracker-bot.backup /opt/stock-tracker-bot
sudo systemctl start stock-tracker-bot
```

---

## ✅ Чеклист финального деплоя

- [ ] Файлы загружены на сервер
- [ ] .env файл настроен с правильными credentials
- [ ] credentials.json загружен
- [ ] PostgreSQL доступен с сервера
- [ ] Systemd service установлен
- [ ] Бот запущен и работает
- [ ] Логи показывают успешный запуск
- [ ] Бот отвечает в Telegram на /start
- [ ] Автозапуск при перезагрузке включен
- [ ] Monitoring/health check настроен

---

## 📞 Контакты и поддержка

При проблемах:
1. Проверьте логи: `sudo journalctl -u stock-tracker-bot -f`
2. Проверьте статус: `sudo systemctl status stock-tracker-bot`
3. Проверьте подключение к БД
4. Проверьте, что порт 5432 доступен из сервера

---

## 🎉 Готово!

После успешного деплоя бот будет работать 24/7 автоматически:
- ✅ Автозапуск при перезагрузке сервера
- ✅ Автоматический перезапуск при сбоях (через 10 секунд)
- ✅ Логирование всех событий
- ✅ Подключение к production PostgreSQL
- ✅ Интеграция с Google Sheets
- ✅ Обработка Wildberries API

**Бот готов к production использованию!**
