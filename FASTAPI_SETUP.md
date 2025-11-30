# FastAPI Multi-Tenant Setup

## 🎉 Completed Phase 2: FastAPI + JWT Authentication

Реализован базовый FastAPI API с JWT аутентификацией и мультитенантной архитектурой.

### ✅ Созданные компоненты

#### 1. **Authentication (`src/stock_tracker/auth/`)**

- `jwt_manager.py` - JWT токены (access + refresh)
  - RS256/HS256 algorithm support
  - Access token TTL: 15 минут
  - Refresh token TTL: 30 дней
  - Уникальные JTI для каждого токена

- `password.py` - Хеширование паролей
  - bcrypt с 12 rounds
  - Валидация минимум 8 символов
  - Auto-rehashing при устаревших алгоритмах

#### 2. **FastAPI Application (`src/stock_tracker/api/`)**

- `main.py` - Основное приложение
  - CORS middleware
  - GZip compression
  - Lifespan manager
  - Global exception handler
  - Swagger UI на `/docs`

- **Middleware** (`middleware/`)
  - `tenant_context.py` - Извлечение tenant из JWT
  - `error_handler.py` - Централизованная обработка ошибок

- **Routes** (`routes/`)
  - `auth.py` - Регистрация, логин, refresh, logout
  - `tenants.py` - Управление tenant (credentials, info)
  - `products.py` - Список продуктов, синхронизация (placeholder)
  - `health.py` - Health checks для Kubernetes

#### 3. **Schemas (`src/stock_tracker/api/schemas.py`)**

Pydantic модели для валидации:
- `RegisterRequest`, `LoginRequest`, `TokenResponse`
- `UserResponse`, `TenantResponse`
- `ProductResponse`
- Enums: `UserRole`, `MarketplaceType`, `SubscriptionPlan`

### 🔐 Аутентификация Flow

```
1. POST /api/v1/auth/register
   → Создает Tenant + User (owner) + Subscription (FREE)
   → Возвращает access_token + refresh_token

2. POST /api/v1/auth/login
   → Проверяет email/password
   → Возвращает access_token + refresh_token

3. Защищенные endpoints
   → Authorization: Bearer <access_token>
   → Middleware извлекает tenant_id из JWT
   → Dependencies: get_current_user(), get_current_tenant()

4. POST /api/v1/auth/refresh
   → Обменивает refresh_token на новые токены
   → Revokes старый refresh_token

5. POST /api/v1/auth/logout
   → Revokes все refresh_tokens пользователя
```

### 📋 API Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/` | Root info | ❌ |
| GET | `/docs` | Swagger UI | ❌ |
| GET | `/api/v1/health/` | Health check | ❌ |
| GET | `/api/v1/health/ready` | Readiness check | ❌ |
| POST | `/api/v1/auth/register` | Register tenant | ❌ |
| POST | `/api/v1/auth/login` | Login user | ❌ |
| POST | `/api/v1/auth/refresh` | Refresh token | ❌ |
| POST | `/api/v1/auth/logout` | Logout user | ✅ |
| GET | `/api/v1/tenants/me` | Get tenant info | ✅ |
| PATCH | `/api/v1/tenants/me` | Update tenant | ✅ (owner) |
| PATCH | `/api/v1/tenants/me/credentials` | Update credentials | ✅ (owner/admin) |
| GET | `/api/v1/products/` | List products | ✅ |
| POST | `/api/v1/products/sync` | Trigger sync | ✅ (owner/admin) |

### 🚀 Запуск приложения

1. **Установить зависимости**
```bash
pip install -r requirements.txt
```

2. **Настроить .env**
```bash
cp .env.example .env
# Отредактировать .env с реальными значениями
```

Генерация ключей:
```bash
# SECRET_KEY
openssl rand -hex 32

# ENCRYPTION_MASTER_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

3. **Создать базу данных**
```bash
# Создать PostgreSQL базу
createdb stock_tracker

# Применить миграции
alembic upgrade head
```

4. **Запустить API**
```bash
# Development mode с hot reload
uvicorn stock_tracker.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn stock_tracker.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

5. **Протестировать**
```bash
python test_startup.py
```

Swagger UI: http://localhost:8000/docs

### 🧪 Примеры запросов

**Регистрация:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "strongpassword123",
    "company_name": "My Company",
    "marketplace_type": "wildberries"
  }'
```

**Логин:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@example.com",
    "password": "strongpassword123"
  }'
```

**Получить информацию о tenant:**
```bash
curl -X GET http://localhost:8000/api/v1/tenants/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 📊 Архитектура

```
FastAPI App
├── Middleware
│   ├── CORS
│   ├── GZip
│   ├── ErrorHandler (custom)
│   └── TenantContext (JWT → tenant_id)
├── Routes
│   ├── /auth (register, login, refresh, logout)
│   ├── /tenants (info, credentials)
│   ├── /products (list, sync - placeholder)
│   └── /health (readiness checks)
└── Dependencies
    ├── get_db() → SQLAlchemy session
    ├── get_current_user() → User from JWT
    └── get_current_tenant() → Tenant from user
```

### 🔒 Безопасность

- JWT tokens с коротким TTL (15 мин access, 30 дней refresh)
- Refresh tokens хранятся хешированными в БД
- Все credentials шифруются Fernet перед сохранением
- Password hashing с bcrypt (12 rounds)
- RBAC с 4 ролями: owner, admin, user, viewer
- Rate limiting (TODO - следующий этап)

### 🎯 Следующие шаги

- [ ] Redis caching layer
- [ ] Celery background workers
- [ ] Интеграция ProductService с marketplace factory
- [ ] Rate limiting middleware
- [ ] Webhook dispatcher
- [ ] Prometheus metrics
- [ ] Integration tests

### 📝 Важные заметки

1. **Tenant Isolation**: Все запросы проверяют tenant_id из JWT
2. **Role-Based Access**: Некоторые endpoints требуют определенных ролей
3. **Token Rotation**: Refresh tokens автоматически revoke при использовании
4. **Database Sessions**: Каждый request получает новую DB session через dependency injection

### 🐛 Troubleshooting

**"Could not resolve import 'sqlalchemy'"**
```bash
pip install sqlalchemy alembic psycopg2-binary
```

**"DATABASE_URL not found"**
```bash
cp .env.example .env
# Edit .env with your PostgreSQL connection string
```

**"RefreshToken has no attribute 'expires_at'"**
- Убедитесь, что миграции применены: `alembic upgrade head`
