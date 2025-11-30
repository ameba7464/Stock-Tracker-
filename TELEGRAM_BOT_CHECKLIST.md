# ✅ Чеклист Запуска Telegram Bot

## Перед запуском

- [x] Код бота создан и готов
- [x] Docker образ подготовлен  
- [x] `.env` файл создан
- [x] Stock Tracker API запущен ✅
- [x] PostgreSQL запущен ✅
- [x] Redis запущен ✅
- [ ] **BOT_TOKEN получен от @BotFather**
- [ ] **BOT_TOKEN добавлен в telegram-bot/.env**

## Шаги запуска

### 1. Получите Bot Token (5 минут) ⏳

```
1. Откройте @BotFather в Telegram
2. /newbot
3. Введите название: Stock Tracker Bot
4. Введите username: my_stock_tracker_bot
5. Скопируйте токен
```

### 2. Добавьте токен в .env ⏳

```
Файл: telegram-bot\.env
Строка: BOT_TOKEN=your_token_here
```

### 3. Запустите бота ⏳

```powershell
cd "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"
docker-compose --profile bot up -d
```

### 4. Проверьте логи ⏳

```powershell
docker logs -f stock-tracker-telegram-bot
```

Ожидаемый вывод:
```
INFO - Starting Stock Tracker Bot...
INFO - Database initialized
INFO - Bot is running...
```

### 5. Протестируйте в Telegram ⏳

```
1. Найдите бота: @my_stock_tracker_bot
2. /start
3. Пройдите регистрацию
```

---

## Быстрая Проверка

```powershell
# Все контейнеры
docker ps

# Только бот
docker ps | Select-String "telegram"

# Логи
docker logs stock-tracker-telegram-bot --tail 50

# Здоровье API
curl http://localhost:8000/api/v1/health/
```

---

## Готово? ✅

После успешного запуска:

- ✅ Бот отвечает в Telegram
- ✅ Регистрация работает  
- ✅ Можно добавить WB API ключ
- ✅ Синхронизация запускается

---

## Проблемы?

**Бот не запускается:**
```powershell
docker logs stock-tracker-telegram-bot
```

**API недоступен:**
```powershell
docker logs stock-tracker-api
```

**База данных:**
```powershell
docker logs stock-tracker-postgres
```

---

## Документация

📚 **Полная инструкция:** `TELEGRAM_BOT_START_GUIDE.md`
📚 **Документация бота:** `telegram-bot/README.md`
📚 **Быстрый старт:** `telegram-bot/QUICKSTART.md`

---

**Текущий статус:** Ждем BOT_TOKEN от @BotFather! 🤖
