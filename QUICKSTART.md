# 📚 Quick Start Guide - Stock Tracker

Быстрый старт для разработчиков и пользователей Stock Tracker.

## 🎯 Что это?

**Stock Tracker** — мультитенантная SaaS платформа для автоматизации учета товаров на маркетплейсах (Wildberries, Ozon) с интеграцией через Telegram бота.

### Основные возможности

✅ **Multi-tenant архитектура** — поддержка 20-30+ продавцов  
✅ **Telegram бот интеграция** — добавление API ключей через бота  
✅ **Автоматическая синхронизация** — фоновая обработка через Celery  
✅ **Шифрование credentials** — безопасное хранение API ключей  
✅ **Rate limiting** — защита от превышения лимитов  
✅ **Мониторинг** — Prometheus + Grafana + Sentry  
✅ **JWT аутентификация** — безопасный доступ к API  

---

## 🚀 Быстрый старт (Docker)

### 1. Установка

```bash
# Клонируйте репозиторий
git clone https://github.com/yourusername/stock-tracker.git
cd stock-tracker

# Скопируйте пример конфигурации
cp .env.docker .env
```

### 2. Генерация секретных ключей

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Вставьте ключи в `.env` файл.

### 3. Запуск

```bash
# Запустите все сервисы
docker-compose up -d

# Примените миграции
docker-compose exec api alembic upgrade head

# Проверьте здоровье
curl http://localhost:8000/api/v1/health/
```

### 4. Создание первого пользователя

```bash
# Через API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "SecurePassword123!",
    "full_name": "Seller Name",
    "company_name": "My Store"
  }'
```

### 5. Получение токена

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=seller@example.com&password=SecurePassword123!"
```

---

## 🔧 Разработка

### Локальная разработка (без Docker)

#### Требования

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

#### Установка зависимостей

```bash
# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

#### Настройка БД

```bash
# Создайте БД
psql -U postgres
CREATE DATABASE stock_tracker;
CREATE USER stock_tracker WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE stock_tracker TO stock_tracker;
\q

# Примените миграции
alembic upgrade head
```

#### Запуск сервисов

```bash
# Terminal 1: API Server
uvicorn stock_tracker.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery Worker
celery -A stock_tracker.workers.celery_app worker --loglevel=info

# Terminal 3: Celery Beat (Scheduler)
celery -A stock_tracker.workers.celery_app beat --loglevel=info
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты с coverage
pytest -v --cov=stock_tracker --cov-report=html

# Только unit tests
pytest tests/unit/ -v

# Только integration tests
pytest tests/integration/ -v

# Конкретный тест
pytest tests/integration/test_auth_flow.py::TestAuthenticationFlow::test_login_success -v
```

### Coverage отчет

```bash
pytest --cov=stock_tracker --cov-report=html
open htmlcov/index.html  # Windows: start htmlcov\index.html
```

---

## 📖 API Документация

### Автоматическая документация

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Основные endpoints

#### Authentication

```bash
# Регистрация
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "password",
  "full_name": "User Name",
  "company_name": "Company"
}

# Логин
POST /api/v1/auth/login
username=user@example.com&password=password

# Получить текущего пользователя
GET /api/v1/auth/me
Authorization: Bearer <token>

# Refresh token
POST /api/v1/auth/refresh
{"refresh_token": "..."}

# Logout
POST /api/v1/auth/logout
Authorization: Bearer <token>
```

#### Products

```bash
# Получить список продуктов (с кешем)
GET /api/v1/products/
Authorization: Bearer <token>

# Запустить синхронизацию
POST /api/v1/products/sync
Authorization: Bearer <token>

# Статус синхронизации
GET /api/v1/sync/status/{sync_id}
Authorization: Bearer <token>

# История синхронизаций
GET /api/v1/sync/history
Authorization: Bearer <token>
```

#### Credentials (через Telegram бота)

```bash
# Сохранить API ключ
POST /api/v1/credentials/
Authorization: Bearer <token>
{
  "marketplace": "wildberries",
  "api_key": "your_api_key"
}

# Статус credentials
GET /api/v1/credentials/status
Authorization: Bearer <token>

# Удалить credentials
DELETE /api/v1/credentials/wildberries
Authorization: Bearer <token>
```

#### Health & Monitoring

```bash
# Health check
GET /api/v1/health/

# Readiness check (для K8s)
GET /api/v1/health/ready

# Liveness check (для K8s)
GET /api/v1/health/live

# Prometheus metrics
GET /metrics
```

---

## 🤖 Telegram Bot интеграция

### Настройка бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен
3. Добавьте токен в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

### Использование бота

```
/start - Начать работу с ботом
/add_api_key - Добавить API ключ маркетплейса
/status - Проверить статус синхронизации
/sync - Запустить синхронизацию вручную
/help - Помощь
```

Подробнее: [TELEGRAM_BOT_INTEGRATION.md](TELEGRAM_BOT_INTEGRATION.md)

---

## 📊 Мониторинг

### Grafana Dashboards

**URL:** http://localhost:3000  
**Login:** admin  
**Password:** (из .env файла)

Дашборды включают:
- Request Rate (запросов/сек)
- Request Duration (p95, p99)
- Error Rate
- Active Tenants
- Cache Hit Rate
- Sync Duration

### Prometheus Metrics

**URL:** http://localhost:9090

Доступные метрики:
- `stock_tracker_requests_total` - Общее количество запросов
- `stock_tracker_request_duration_seconds` - Время обработки запросов
- `stock_tracker_sync_duration_seconds` - Время синхронизации
- `stock_tracker_errors_total` - Количество ошибок
- `stock_tracker_active_tenants` - Активные тенанты
- `stock_tracker_cache_hits_total` / `cache_misses_total` - Эффективность кеша

### Flower (Celery UI)

**URL:** http://localhost:5555

Мониторинг Celery задач:
- Активные задачи
- Очереди (sync, maintenance, default)
- Статистика воркеров
- История выполнения задач

### Sentry Error Tracking

```bash
# Добавьте DSN в .env
SENTRY_DSN=https://xxx@sentry.io/project

# Перезапустите сервисы
docker-compose restart api worker beat
```

---

## 🗂️ Структура проекта

```
stock-tracker/
├── src/stock_tracker/
│   ├── api/                    # FastAPI приложение
│   │   ├── main.py            # Entry point
│   │   ├── routes/            # API endpoints
│   │   └── middleware/        # Middleware (auth, rate limit)
│   ├── db/                     # База данных
│   │   ├── models.py          # SQLAlchemy модели
│   │   └── session.py         # DB session
│   ├── core/                   # Ядро приложения
│   │   ├── security.py        # JWT, password hashing
│   │   ├── cache.py           # Redis cache
│   │   └── encryption.py      # Fernet encryption
│   ├── services/               # Бизнес-логика
│   │   ├── product_service.py
│   │   ├── marketplace_clients/
│   │   └── webhook_dispatcher.py
│   ├── workers/                # Celery workers
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── monitoring/             # Мониторинг
│       ├── prometheus_metrics.py
│       └── sentry_config.py
├── tests/                      # Тесты
│   ├── unit/
│   └── integration/
├── monitoring/                 # Конфигурация мониторинга
│   ├── prometheus.yml
│   └── grafana/
├── migrations/                 # Alembic миграции
├── docker-compose.yml          # Docker Compose
├── Dockerfile                  # Multi-stage Dockerfile
├── requirements.txt            # Python зависимости
└── .env.docker                 # Пример конфигурации
```

---

## 🔐 Безопасность

### Лучшие практики

1. **Никогда не коммитьте `.env` файлы**
2. **Генерируйте уникальные SECRET_KEY и FERNET_KEY**
3. **Используйте сильные пароли для БД**
4. **Включите HTTPS в production**
5. **Ограничьте CORS только вашими доменами**
6. **Регулярно обновляйте зависимости**
7. **Мониторьте Sentry на предмет ошибок безопасности**

### Rate Limiting

По умолчанию:
- **Global:** 1000 запросов/минуту
- **Per Tenant:** 100 запросов/минуту
- **Per User:** настраивается через декоратор

Настройка в `.env`:
```
RATE_LIMIT_GLOBAL=1000
RATE_LIMIT_TENANT=100
```

---

## 📝 CI/CD

GitHub Actions автоматически:
- ✅ Проверяет код (lint, type checking)
- ✅ Запускает тесты с coverage
- ✅ Сканирует безопасность (safety, bandit)
- ✅ Собирает Docker образ
- ✅ Деплоит на staging (ветка `develop`)
- ✅ Деплоит на production (ветка `main`)

Настройте GitHub Secrets:
```
DOCKER_USERNAME
DOCKER_PASSWORD
STAGING_HOST
STAGING_USERNAME
STAGING_SSH_KEY
PRODUCTION_HOST
PRODUCTION_USERNAME
PRODUCTION_SSH_KEY
SENTRY_ORG
SENTRY_AUTH_TOKEN
```

---

## 🆘 Troubleshooting

### Проблема: "ModuleNotFoundError"

```bash
# Убедитесь, что все зависимости установлены
pip install -r requirements.txt
```

### Проблема: "Connection refused" к PostgreSQL

```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps postgres

# Проверьте DATABASE_URL в .env
echo $DATABASE_URL
```

### Проблема: Redis connection failed

```bash
# Проверьте, что Redis запущен
docker-compose ps redis

# Проверьте REDIS_URL в .env
echo $REDIS_URL
```

### Проблема: 401 Unauthorized

```bash
# Проверьте токен
# Токен истекает через 30 минут по умолчанию
# Используйте refresh token для получения нового
```

Подробнее: [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)

---

## 📚 Дополнительная документация

- [PHASE4_COMPLETION_REPORT.md](PHASE4_COMPLETION_REPORT.md) - Celery workers и ProductService
- [PHASE5_COMPLETION_REPORT.md](PHASE5_COMPLETION_REPORT.md) - Rate limiting и мониторинг
- [TELEGRAM_BOT_INTEGRATION.md](TELEGRAM_BOT_INTEGRATION.md) - Интеграция Telegram бота
- [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) - Production deployment
- [GitHub Actions](.github/workflows/) - CI/CD конфигурация

---

## 🤝 Contributing

1. Fork репозиторий
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

---

## 📄 License

MIT License - см. [LICENSE](LICENSE) файл

---

## 👨‍💻 Контакты

- **GitHub:** https://github.com/yourusername/stock-tracker
- **Email:** support@stock-tracker.example.com
- **Documentation:** https://docs.stock-tracker.example.com

