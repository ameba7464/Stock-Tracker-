# MULTI-TENANT MIGRATION GUIDE

Руководство по миграции Stock Tracker из однопользовательского режима в мультитенантную SaaS-платформу.

## Обзор изменений

### Архитектурные изменения
- **Было:** Один API ключ в `.env`, одна Google Sheet
- **Стало:** PostgreSQL для метаданных, изолированные credentials per tenant, GraphQL API

### Новые компоненты
1. **PostgreSQL** - хранение tenants, users, subscriptions
2. **Redis** - кэширование, rate limiting, Celery queue
3. **FastAPI + GraphQL** - RESTful API endpoint
4. **Celery** - фоновые задачи синхронизации
5. **Fernet encryption** - шифрование credentials

## Требования

### Инфраструктура
- PostgreSQL 14+ (Railway provides managed instance)
- Redis 7+ (для кэша и Celery broker)
- Python 3.10+

### Новые environment variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/stock_tracker

# Redis
REDIS_URL=redis://localhost:6379/0

# Encryption
ENCRYPTION_MASTER_KEY=<generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'>

# FastAPI
SECRET_KEY=<random secret for JWT>
API_HOST=0.0.0.0
API_PORT=8000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Optional: Stripe for billing
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Шаги миграции

### 1. Установка зависимостей

```bash
# Обновить requirements
pip install -r requirements.txt

# Или установить только новые зависимости
pip install sqlalchemy alembic psycopg2-binary fastapi uvicorn strawberry-graphql python-jose passlib redis celery
```

### 2. Настройка PostgreSQL

```bash
# Локально через Docker
docker run --name postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:14

# Или использовать Railway managed database
# DATABASE_URL автоматически добавится в env
```

### 3. Инициализация базы данных

```bash
# Создать таблицы через Alembic
alembic upgrade head

# Или напрямую через SQLAlchemy (для development)
python -c "from src.stock_tracker.database.connection import init_db; init_db()"
```

### 4. Генерация encryption key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Скопировать output в ENCRYPTION_MASTER_KEY environment variable
```

### 5. Миграция существующих credentials

```python
# migrations/scripts/migrate_legacy_to_multitenant.py
python migrations/scripts/migrate_legacy_to_multitenant.py

# Скрипт автоматически:
# 1. Читает .env (WILDBERRIES_API_KEY, GOOGLE_SHEET_ID)
# 2. Создает первый Tenant с зашифрованными credentials
# 3. Создает User с ролью OWNER
# 4. Создает FREE Subscription
```

### 6. Запуск FastAPI сервера

```bash
# Development
uvicorn src.stock_tracker.api.main:app --reload --port 8000

# Production (Railway Procfile)
web: uvicorn src.stock_tracker.api.main:app --host 0.0.0.0 --port $PORT
```

### 7. Запуск Celery worker

```bash
# В отдельном терминале
celery -A src.stock_tracker.workers.celery_app worker --loglevel=info

# Production (Railway)
worker: celery -A src.stock_tracker.workers.celery_app worker -l info
```

### 8. Запуск Celery Beat (scheduler)

```bash
celery -A src.stock_tracker.workers.celery_app beat --loglevel=info
```

## Тестирование миграции

### 1. Проверка database connection
```bash
python -c "from src.stock_tracker.database.connection import engine; print(engine.connect())"
```

### 2. Проверка encryption
```python
from src.stock_tracker.security import encrypt_credential, decrypt_credential

encrypted = encrypt_credential("test_api_key")
print(f"Encrypted: {encrypted}")

decrypted = decrypt_credential(encrypted)
print(f"Decrypted: {decrypted}")
assert decrypted == "test_api_key"
```

### 3. Тест GraphQL API
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { types { name } } }"}'
```

### 4. Тест JWT authentication
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secure123", "full_name": "Test User"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secure123"}'
```

## Обратная совместимость

### CLI mode (legacy)
```bash
# Старый CLI все еще работает
python -m stock_tracker.main --sync-now

# Использует DATABASE_URL для получения credentials первого tenant
```

### Migration flag
```python
# В коде проверяется наличие DATABASE_URL
if os.getenv("DATABASE_URL"):
    # Multi-tenant mode
    use_postgres_config()
else:
    # Legacy mode
    use_env_file_config()
```

## Rollback plan

Если миграция не удалась:

1. **Остановить новые сервисы:**
   ```bash
   # Stop FastAPI
   pkill -f uvicorn
   
   # Stop Celery
   pkill -f celery
   ```

2. **Удалить DATABASE_URL из environment:**
   ```bash
   unset DATABASE_URL
   ```

3. **Использовать legacy `.env`:**
   ```bash
   # Старые environment variables все еще работают
   python -m stock_tracker.main --sync-now
   ```

## Известные проблемы

### 1. SQLAlchemy import errors
**Причина:** SQLAlchemy не установлен  
**Решение:** `pip install sqlalchemy psycopg2-binary`

### 2. Redis connection refused
**Причина:** Redis не запущен  
**Решение:** `docker run -p 6379:6379 redis:7` или установить локально

### 3. Alembic migration conflicts
**Причина:** Ручные изменения в database  
**Решение:** `alembic stamp head` или `drop all tables` и `alembic upgrade head`

## Поддержка

При проблемах с миграцией:
1. Проверить логи: `logs/stock_tracker.log`
2. Проверить database connection: `psql $DATABASE_URL`
3. Проверить environment variables: `env | grep -E '(DATABASE|REDIS|ENCRYPTION)'`

## Next Steps

После успешной миграции:
1. Настроить Stripe billing (опционально)
2. Добавить webhook endpoints для уведомлений
3. Настроить Prometheus metrics
4. Добавить Sentry для error tracking
5. Настроить CI/CD через GitHub Actions
