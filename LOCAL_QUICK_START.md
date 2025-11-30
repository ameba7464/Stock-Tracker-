# 🚀 Local Quick Start (Без Docker)

Быстрый запуск для тестирования API без Docker, PostgreSQL и Redis.

## ✅ Что у вас уже есть:
- Python 3.13 ✅
- Virtual environment активирован ✅

---

## 📦 Шаг 1: Установка зависимостей

```powershell
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"
pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart aiosqlite
```

---

## ⚙️ Шаг 2: Создание минимального .env для локального запуска

```powershell
# Создайте файл .env.local со следующим содержимым:
```

```env
# Local Development Configuration (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./stock_tracker_local.db

# Security Keys (уже сгенерированные)
SECRET_KEY=76rfb9Nciv5TJrs_uZwOnQ-OVF1rm_uJ7HZjFJDYPvc
FERNET_KEY=OyHSswYCisSoYUidPu0KBAMBs7ooeGRRGUwtLGRuU4A=

# App Settings
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# JWT
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Wildberries API
WILDBERRIES_API_KEY=eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjUwOTA0djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc3NjM3NjUyNywiaWQiOiIwMTk5ZWM3Mi0yNGRjLTcxMjItYjk0ZC0zNDFiYzM3YmFhYTIiLCJpaWQiOjEwMjEwNTIyNSwib2lkIjoxMjc4Njk0LCJzIjoxMDczNzQyOTcyLCJzaWQiOiJiYmY1MWY5MS0zYjFhLTQ5MGMtOGE4Ni1hNzNkYjgxZTlmNjkiLCJ0IjpmYWxzZSwidWlkIjoxMDIxMDUyMjV9.mPrskzcbBDjUj5lxTcJjmjaPtt2Mx5C0aeok7HytpUk2eWRYngILZotCc1oXVoIoAWJclh-4t0E4F4xeCgOtPg

# Отключаем опциональные сервисы
REDIS_URL=
CELERY_BROKER_URL=
SENTRY_DSN=
TELEGRAM_BOT_TOKEN=
```

---

## 🗄️ Шаг 3: Инициализация базы данных

```powershell
# Применить миграции (создаст SQLite базу)
alembic upgrade head
```

---

## 🚀 Шаг 4: Запуск API сервера

```powershell
# Запустить FastAPI сервер
uvicorn src.stock_tracker.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎯 Шаг 5: Проверка работы

Откройте браузер:
- **API Docs (Swagger):** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/api/v1/health/

---

## 📝 Быстрый тест через curl/PowerShell:

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/" -Method Get

# Регистрация пользователя
$body = @{
    email = "test@example.com"
    password = "TestPassword123!"
    telegram_id = 12345
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" -Method Post -Body $body -ContentType "application/json"
```

---

## ⚠️ Ограничения локального запуска:

- ❌ Нет Redis → нет кеширования
- ❌ Нет Celery → нет фоновых задач
- ❌ Нет Grafana/Prometheus → нет мониторинга
- ✅ Но API работает и можно тестировать endpoints!

---

## 🐳 Когда Docker заработает:

После того как Docker Desktop запустится, вы сможете:
```powershell
docker compose up -d
docker compose exec api alembic upgrade head
```

И получите полный production-like опыт со всеми сервисами!

---

**Удачи! 🚀**
