# 🚀 Чеклист быстрого деплоя на сервер

**Дата:** 25 декабря 2025  
**Статус проверки:** ✅ Все тесты пройдены

---

## ⚡ Быстрый старт (5 минут)

### Шаг 1: Подготовка файлов (локально)

```powershell
# Убедитесь, что все файлы на месте:
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\telegram-bot"
Get-ChildItem -Recurse -Include deploy.sh,stock-tracker-bot.service,update.sh,.env,credentials.json
```

**Обязательные файлы для загрузки:**
- [ ] `app/` (вся папка с кодом)
- [ ] `requirements.txt`
- [ ] `.env` (с production настройками)
- [ ] `credentials.json` (Google Service Account)
- [ ] `deploy.sh` ✅ (создан)
- [ ] `stock-tracker-bot.service` ✅ (создан)
- [ ] `update.sh` ✅ (создан)

---

### Шаг 2: Загрузка на сервер

```bash
# На локальной машине (PowerShell/CMD):
# Замените YOUR_SERVER_IP на IP вашего сервера в Yandex Cloud

# Способ 1: SCP (если есть SSH доступ)
scp -r telegram-bot root@YOUR_SERVER_IP:/tmp/

# Способ 2: SFTP или любой FTP клиент
# Загрузите папку telegram-bot целиком
```

**После загрузки на сервере должна быть структура:**
```
/tmp/telegram-bot/
├── app/
├── .env
├── credentials.json
├── requirements.txt
├── deploy.sh
├── stock-tracker-bot.service
└── update.sh
```

---

### Шаг 3: Подключение к серверу

```bash
# SSH в сервер Yandex Cloud
ssh root@YOUR_SERVER_IP

# Или используйте Yandex Cloud Console для подключения
```

---

### Шаг 4: Запуск автоматического деплоя

```bash
# На сервере:
cd /tmp/telegram-bot

# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запустить деплой (требуется root)
sudo ./deploy.sh
```

**Что делает deploy.sh:**
1. ✅ Создает пользователя `stock-bot`
2. ✅ Устанавливает Python 3.11+ и зависимости
3. ✅ Копирует код в `/opt/stock-tracker-bot/`
4. ✅ Устанавливает Python пакеты
5. ✅ Настраивает systemd service
6. ✅ Запускает бота
7. ✅ Включает автозапуск

---

### Шаг 5: Проверка работы

```bash
# Проверить статус бота
sudo systemctl status stock-tracker-bot

# Посмотреть логи (последние 50 строк)
sudo journalctl -u stock-tracker-bot -n 50

# Следить за логами в реальном времени
sudo journalctl -u stock-tracker-bot -f
```

**Ожидаемый вывод:**
```
● stock-tracker-bot.service - Stock Tracker Telegram Bot
     Loaded: loaded (/etc/systemd/system/stock-tracker-bot.service; enabled)
     Active: active (running) since ...
```

---

### Шаг 6: Проверка в Telegram

1. Откройте Telegram
2. Найдите бота: `@WildBStockBot`
3. Отправьте команду: `/start`
4. Бот должен ответить в течение 1-2 секунд

**Команды для проверки:**
- `/start` - Приветствие
- `/menu` - Главное меню
- `/profile` - Профиль пользователя

---

## 🔧 Управление ботом на сервере

### Основные команды:

```bash
# Запустить бота
sudo systemctl start stock-tracker-bot

# Остановить бота
sudo systemctl stop stock-tracker-bot

# Перезапустить бота
sudo systemctl restart stock-tracker-bot

# Статус бота
sudo systemctl status stock-tracker-bot

# Просмотр логов
sudo journalctl -u stock-tracker-bot -f

# Отключить автозапуск
sudo systemctl disable stock-tracker-bot

# Включить автозапуск
sudo systemctl enable stock-tracker-bot
```

---

## 🔄 Быстрое обновление кода

Когда нужно обновить код без полного переразвертывания:

```bash
# На сервере:
cd /tmp/telegram-bot
chmod +x update.sh
sudo ./update.sh
```

**Что делает update.sh:**
1. ✅ Создает backup текущей версии
2. ✅ Обновляет код
3. ✅ Устанавливает новые зависимости
4. ✅ Тестирует бота
5. ✅ Автоматически откатывается при ошибках

---

## ⚠️ Важные замечания

### 1. НЕ запускайте бота локально!
```bash
# ❌ НЕ ДЕЛАЙТЕ ТАК:
python -m app.main

# Причина: Конфликт с облачным ботом
# Telegram API не поддерживает несколько polling экземпляров
```

### 2. База данных
- ✅ PostgreSQL в Yandex Cloud: `158.160.188.247:5432/stocktracker`
- ✅ Подключение уже настроено в `.env`
- ✅ Все миграции применены

### 3. Google Sheets
- ✅ Service Account настроен
- ✅ Файл `credentials.json` включен
- ⚠️ OAuth токен устарел (не критично)
  - Для создания НОВЫХ таблиц нужно обновить через `get_oauth_token.py`
  - Для чтения/обновления существующих работает Service Account

### 4. Безопасность
- ✅ Бот работает от непривилегированного пользователя `stock-bot`
- ✅ Логи пишутся в `/var/log/stock-tracker-bot/`
- ✅ Auto-restart при падении (RestartSec=10)

---

## 📊 Мониторинг

### Проверка здоровья бота:

```bash
# 1. Проверить процесс
ps aux | grep python | grep stock-tracker-bot

# 2. Проверить использование ресурсов
sudo systemctl show stock-tracker-bot --property=MemoryCurrent,CPUUsageNSec

# 3. Проверить последние ошибки
sudo journalctl -u stock-tracker-bot --priority=err -n 20

# 4. Статистика запросов к API
tail -f /var/log/stock-tracker-bot/bot.log | grep "API request"
```

### Проверка подключений:

```bash
# PostgreSQL
PGPASSWORD=StockTracker2024 psql -h 158.160.188.247 -U stocktracker -d stocktracker -c "SELECT version();"

# Telegram API
curl "https://api.telegram.org/bot8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms/getMe"
```

---

## 🚨 Troubleshooting

### Бот не отвечает

1. **Проверить статус:**
   ```bash
   sudo systemctl status stock-tracker-bot
   ```

2. **Посмотреть логи:**
   ```bash
   sudo journalctl -u stock-tracker-bot -n 100 --no-pager
   ```

3. **Проверить конфликты:**
   ```bash
   # Убедиться, что только один экземпляр запущен
   ps aux | grep "python.*app.main"
   ```

4. **Перезапустить:**
   ```bash
   sudo systemctl restart stock-tracker-bot
   sudo journalctl -u stock-tracker-bot -f
   ```

### Ошибки базы данных

```bash
# Проверить подключение
PGPASSWORD=StockTracker2024 psql -h 158.160.188.247 -U stocktracker -d stocktracker -c "\dt"

# Проверить .env файл
cat /opt/stock-tracker-bot/.env | grep DATABASE_URL
```

### Бот падает при старте

```bash
# Проверить зависимости
cd /opt/stock-tracker-bot
source .venv/bin/activate
pip list | grep -E "aiogram|sqlalchemy|asyncpg"

# Переустановить зависимости
pip install -r requirements.txt --force-reinstall
```

---

## ✅ Финальный чеклист

После деплоя проверьте:

- [ ] `systemctl status stock-tracker-bot` показывает `active (running)`
- [ ] Логи не содержат ошибок: `journalctl -u stock-tracker-bot -n 50`
- [ ] Бот отвечает на `/start` в Telegram
- [ ] База данных доступна: `psql -h 158.160.188.247 ...`
- [ ] Google Sheets Service Account работает (проверить через бота)
- [ ] Автозапуск включен: `systemctl is-enabled stock-tracker-bot`
- [ ] Логи пишутся: `ls -lah /var/log/stock-tracker-bot/`

---

## 📚 Дополнительная документация

- **Полная инструкция:** [PRODUCTION_DEPLOY_FINAL.md](PRODUCTION_DEPLOY_FINAL.md)
- **Troubleshooting:** [TROUBLESHOOTING_BOT_NOT_RESPONDING.md](TROUBLESHOOTING_BOT_NOT_RESPONDING.md)
- **Критические правила:** [../CRITICAL_RULES.md](../CRITICAL_RULES.md)
- **История изменений:** [../CHANGELOG.md](../CHANGELOG.md)

---

## 🎉 Готово!

Бот работает 24/7 в Yandex Cloud и автоматически перезапускается при падении.

**Контакты:**
- Telegram Bot: [@WildBStockBot](https://t.me/WildBStockBot)
- Bot ID: 8558236991
- Database: 158.160.188.247:5432/stocktracker

---

**Версия:** 2.1.1  
**Дата последнего обновления:** 25 декабря 2025  
**Статус:** ✅ Production Ready
