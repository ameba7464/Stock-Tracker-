# Фаза 2 Завершена: FastAPI + JWT Аутентификация ✅

## 📦 Созданные Компоненты

### 1. Authentication Layer (`src/stock_tracker/auth/`)

#### `jwt_manager.py` - JWT Token Management
```python
class JWTManager:
    - create_access_token(user_id, tenant_id, role) → token (TTL: 15min)
    - create_refresh_token(user_id) → token (TTL: 30 days)
    - verify_token(token, type) → payload
```

**Особенности:**
- Поддержка HS256/RS256 алгоритмов
- Уникальные JTI (JWT ID) для каждого токена
- Автоматические timestamps (iat, exp)
- Payload включает: sub, tenant_id, role, type

#### `password.py` - Password Security
```python
class PasswordManager:
    - hash(password) → bcrypt hash (12 rounds)
    - verify(plain, hashed) → bool
    - needs_rehash(hashed) → bool
```

**Безопасность:**
- Bcrypt с 12 rounds (баланс скорость/безопасность)
- Минимум 8 символов
- Auto-detection устаревших хешей
- Graceful error handling

### 2. FastAPI Application (`src/stock_tracker/api/`)

#### `main.py` - Core Application
```python
app = FastAPI(
    title="Stock Tracker API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
```

**Middleware Stack:**
1. **CORS** - Разрешенные origins из env
2. **GZip** - Сжатие ответов >1KB
3. **ErrorHandler** - Централизованная обработка ошибок
4. **TenantContext** - Извлечение tenant из JWT

**Lifespan Manager:**
- Startup tasks (логирование, инициализация)
- Shutdown tasks (cleanup)
- Graceful shutdown

#### Middleware

**`tenant_context.py`** - Tenant Isolation
```python
class TenantContextMiddleware:
    - Извлекает Authorization header
    - Верифицирует JWT token
    - Загружает Tenant + User из БД
    - Устанавливает context variables
    - Пропускает публичные endpoints
```

**Dependencies:**
```python
get_current_user() → User      # Требует валидный JWT
get_current_tenant() → Tenant  # Требует активный tenant
```

**Public Endpoints (без auth):**
- `/` - Root info
- `/docs`, `/redoc`, `/openapi.json`
- `/api/v1/auth/login`
- `/api/v1/auth/register`
- `/api/v1/health/*`

**`error_handler.py`** - Global Error Handling
- ValidationError → 422
- AuthenticationError → 401
- APIError → 502
- DatabaseError → 500
- SQLAlchemyError → 500
- Request logging (method, path, status, duration)

### 3. API Routes (`src/stock_tracker/api/routes/`)

#### `auth.py` - Authentication Endpoints

**POST /api/v1/auth/register**
```json
Request:
{
  "email": "owner@example.com",
  "password": "strongpass123",
  "company_name": "My Company",
  "marketplace_type": "wildberries"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Создает:**
- Tenant (company)
- User (owner role)
- Subscription (FREE plan)
- Refresh token в БД

**POST /api/v1/auth/login**
```json
Request:
{
  "email": "owner@example.com",
  "password": "strongpass123"
}

Response: (same as register)
```

**Проверяет:**
- Email/password корректность
- User.is_active = true
- Tenant.is_active = true

**POST /api/v1/auth/refresh**
```json
Request:
{
  "refresh_token": "eyJ..."
}

Response:
{
  "access_token": "eyJ...",  # новый
  "refresh_token": "eyJ..."   # новый
}
```

**Логика:**
- Верифицирует refresh_token
- Проверяет token_hash в БД
- Revokes старый token
- Создает новую пару токенов

**POST /api/v1/auth/logout** 🔒
```json
Response:
{
  "message": "Logged out successfully"
}
```

**Действия:**
- Revokes все refresh_tokens пользователя
- Не invalidates access_token (он истечет через 15 мин)

#### `tenants.py` - Tenant Management

**GET /api/v1/tenants/me** 🔒
```json
Response:
{
  "id": "uuid",
  "name": "My Company",
  "marketplace_type": "wildberries",
  "is_active": true,
  "created_at": "2025-11-20T..."
}
```

**PATCH /api/v1/tenants/me/credentials** 🔒 (owner/admin)
```json
Request:
{
  "wildberries_api_key": "new-key",
  "google_sheet_id": "sheet-id",
  "google_credentials_json": "{...}"
}

Response:
{
  "message": "Credentials updated successfully"
}
```

**Безопасность:**
- Credentials шифруются Fernet перед сохранением в `wb_credentials_encrypted`
- Требуется role: owner или admin

**PATCH /api/v1/tenants/me** 🔒 (owner only)
```json
Request:
{
  "name": "New Company Name"
}
```

#### `products.py` - Product Management (Placeholder)

**GET /api/v1/products/** 🔒
```json
Response: []  # TODO: интеграция с ProductService
```

**POST /api/v1/products/sync** 🔒 (owner/admin)
```json
Response:
{
  "message": "Sync started",
  "tenant_id": "uuid",
  "status": "pending"
}
```

**TODO:** Интеграция с Celery tasks

#### `health.py` - Health Checks

**GET /api/v1/health/**
```json
Response:
{
  "status": "healthy",
  "timestamp": "2025-11-20T...",
  "service": "stock-tracker-api"
}
```

**GET /api/v1/health/ready**
```json
Response:
{
  "status": "ready",
  "checks": {
    "database": "connected"
  },
  "timestamp": "2025-11-20T..."
}
```

**Проверяет:**
- Подключение к PostgreSQL (SELECT 1)
- Используется в Kubernetes readiness probes

### 4. Schemas (`src/stock_tracker/api/schemas.py`)

**Pydantic Models:**
```python
# Auth
RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest

# Users
UserBase, UserCreate, UserResponse

# Tenants
TenantBase, TenantCreate, TenantResponse

# Products
ProductBase, ProductResponse

# Enums
UserRole: owner, admin, user, viewer
MarketplaceType: wildberries, ozon
SubscriptionPlan: FREE, STARTER, PRO, ENTERPRISE
```

### 5. Testing & Documentation

**`test_api_components.py`** - Comprehensive Test Script
- Тестирует auth modules (password hashing)
- Проверяет импорты database models
- Валидирует marketplace clients
- Загружает FastAPI app и подсчитывает routes
- Проверяет environment variables

**`FASTAPI_SETUP.md`** - Complete Setup Guide
- Архитектура и flow диаграммы
- API endpoints таблица
- Примеры curl запросов
- Deployment инструкции
- Troubleshooting tips

**`.env.example`** - Configuration Template
- Database URL
- Security keys
- Redis URLs
- Celery configuration
- Monitoring settings

## 🔒 Безопасность

### JWT Tokens
- **Access Token**: 15 минут TTL, содержит user_id + tenant_id + role
- **Refresh Token**: 30 дней TTL, хранится хешированным в БД
- **Token Rotation**: Старый refresh_token revokes при использовании
- **JTI**: Уникальный ID для каждого токена (future: blacklist)

### Password Security
- **Bcrypt**: 12 rounds (2^12 = 4096 iterations)
- **Min Length**: 8 символов
- **Auto-rehashing**: Если алгоритм устарел
- **Error Handling**: Graceful failures без раскрытия информации

### Credentials Encryption
- **Fernet**: Симметричное шифрование
- **Master Key**: Из env ENCRYPTION_MASTER_KEY
- **At Rest**: Все API keys/credentials шифруются перед save в БД
- **In Transit**: HTTPS (production)

### Role-Based Access Control (RBAC)
```
owner:  Полный доступ к tenant
admin:  Управление продуктами, credentials, sync
user:   Просмотр продуктов, чтение данных
viewer: Только чтение
```

## 📊 Архитектура

```
                        Client
                          |
                      [FastAPI App]
                          |
        +-----------------+------------------+
        |                 |                  |
    [Middlewares]     [Routes]         [Dependencies]
        |                 |                  |
  - CORS                - /auth          - get_db()
  - GZip                - /tenants       - get_current_user()
  - ErrorHandler        - /products      - get_current_tenant()
  - TenantContext       - /health
        |
   [Database]
        |
  - PostgreSQL (models)
  - SQLAlchemy ORM
  - Alembic migrations
```

## 🚀 Deployment

### Development Mode
```bash
# Install deps
pip install -r requirements.txt

# Setup database
createdb stock_tracker
alembic upgrade head

# Run server
uvicorn stock_tracker.api.main:app --reload --port 8000
```

### Production Mode
```bash
# Run with Gunicorn + Uvicorn workers
gunicorn stock_tracker.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker (TODO)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "stock_tracker.api.main:app", "--host", "0.0.0.0"]
```

## 🧪 Testing Examples

### Register Tenant
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test12345678",
    "company_name": "Test Company",
    "marketplace_type": "wildberries"
  }'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "test12345678"
  }'
```

### Get Tenant Info (with token)
```bash
TOKEN="your-access-token-here"

curl -X GET http://localhost:8000/api/v1/tenants/me \
  -H "Authorization: Bearer $TOKEN"
```

### Update Credentials
```bash
curl -X PATCH http://localhost:8000/api/v1/tenants/me/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "wildberries_api_key": "your-api-key",
    "google_sheet_id": "your-sheet-id"
  }'
```

## 📝 Environment Variables

### Required
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/stock_tracker
SECRET_KEY=<generate with: openssl rand -hex 32>
ENCRYPTION_MASTER_KEY=<generate with: Fernet.generate_key()>
```

### Optional
```bash
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
DEBUG=true
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
SENTRY_DSN=https://...
```

## 🎯 Следующие Этапы

### Фаза 3: Redis Caching Layer
- [ ] RedisCache class с get/set/delete
- [ ] @cached decorator для часто используемых queries
- [ ] Cache invalidation hooks
- [ ] Cache warming strategy для top tenants
- [ ] Connection pooling (max_connections=50)

### Фаза 4: Refactor ProductService
- [ ] Изменить __init__(self, tenant: Tenant, db_session: Session)
- [ ] Использовать marketplace factory вместо прямого API client
- [ ] Inject tenant context во все sync операции
- [ ] Добавить SyncLog для каждой синхронизации
- [ ] Обновить 1800+ строк для multi-tenancy

### Фаза 5: Celery Background Workers
- [ ] celery_app.py конфигурация
- [ ] Tasks: sync_tenant_products, send_notification
- [ ] Celery Beat scheduler (cron from Tenant.sync_schedule)
- [ ] Обновить Procfile для multi-process deployment
- [ ] Task result backend + Flower monitoring

### Фаза 6: Rate Limiting & Monitoring
- [ ] Rate limiting middleware (Redis sliding window)
- [ ] Prometheus metrics endpoint
- [ ] Sentry error tracking integration
- [ ] Request/response logging
- [ ] Performance metrics (latency, throughput)

## ✅ Завершено в Фазе 2

- ✅ JWT authentication (access + refresh tokens)
- ✅ Password hashing (bcrypt)
- ✅ Fernet encryption для credentials
- ✅ FastAPI app с middleware stack
- ✅ Tenant context middleware
- ✅ Error handling middleware
- ✅ Auth routes (register, login, refresh, logout)
- ✅ Tenant routes (info, credentials update)
- ✅ Product routes (placeholder)
- ✅ Health check routes
- ✅ Pydantic schemas
- ✅ RBAC dependencies (get_current_user, get_current_tenant)
- ✅ Environment configuration (.env.example)
- ✅ Documentation (FASTAPI_SETUP.md)
- ✅ Testing scripts (test_api_components.py)

## 🎉 Статус Проекта

**Фаза 1 (Infrastructure):** ✅ Завершена
**Фаза 2 (API + Auth):** ✅ Завершена
**Фаза 3 (Caching):** ⏳ Следующая
**Фаза 4 (Service Refactor):** ⏳ Pending
**Фаза 5 (Workers):** ⏳ Pending

**Прогресс:** 60% базовой инфраструктуры для мультитенантности
