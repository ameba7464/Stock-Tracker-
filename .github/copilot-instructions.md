# Stock Tracker - Multi-Tenant SaaS Platform

## Architecture Overview

**Multi-tenant FastAPI SaaS** for Wildberries/Ozon marketplace sellers with Telegram bot integration, background task processing (Celery), subscription billing (Stripe), and enterprise monitoring.

### Core Components
- **FastAPI (src/stock_tracker/api/)**: REST API with JWT auth, tenant isolation middleware
- **Celery Workers (src/stock_tracker/workers/)**: Background sync tasks (3 queues: sync, maintenance, default)
- **PostgreSQL**: Multi-tenant data with row-level isolation via `tenant_id` foreign keys
- **Redis**: Cache layer, Celery broker, rate limiting (sliding window)
- **Telegram Bot (telegram-bot/)**: Standalone aiogram bot for user registration and notifications
- **Google Sheets Integration**: Horizontal layout with 2-header rows, warehouses in separate columns

### Key Design Patterns

**1. Multi-Tenancy**: All models (Product, SyncLog, etc.) include `tenant_id` FK to `tenants` table. Middleware extracts tenant from JWT and validates access. Never query products without tenant context.

**2. Credential Encryption**: API keys stored encrypted via Fernet (`security.encrypt_credential()`). Decrypt in services before external API calls.

**3. Middleware Order** (from `src/stock_tracker/api/main.py`):
```python
ErrorHandlerMiddleware → MetricsMiddleware → RateLimitMiddleware → TenantContextMiddleware
```

**4. Background Tasks**: Sync operations must run in Celery workers, not FastAPI routes. Use `sync_tenant_products.delay(tenant_id)` from routes, implement logic in `SyncService` (synchronous methods for Celery compatibility).

## Development Workflow

### Local Development
```bash
# Start infrastructure (PostgreSQL + Redis + monitoring)
docker-compose up postgres redis -d

# Run FastAPI with hot-reload
uvicorn stock_tracker.api.main:app --reload --app-dir src

# Start Celery worker in separate terminal
celery -A stock_tracker.workers.celery_app worker --loglevel=info --concurrency=4

# Start Celery Beat for scheduled tasks
celery -A stock_tracker.workers.celery_app beat --loglevel=info
```

### Database Migrations
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Testing
```bash
# Run all tests with coverage (pytest.ini: 80% threshold)
pytest

# Run specific test categories (markers: unit, integration, e2e, slow)
pytest -m unit
pytest tests/integration/test_celery_tasks_v2.py -v

# Watch mode during development
pytest-watch
```

## Critical Conventions

### Model Structure
All database models in `src/stock_tracker/database/models/` follow this pattern:
- UUID primary keys (`Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`)
- Timezone-aware timestamps (`DateTime(timezone=True)`)
- Foreign keys with CASCADE delete: `ForeignKey("tenants.id", ondelete="CASCADE")`
- See `src/stock_tracker/database/models/product.py` for warehouse JSONB storage

### API Routes
- Prefix all routes with `/api/v1/`
- Use dependency injection: `db: Session = Depends(get_db)`, `user: User = Depends(get_current_user)`
- Tenant isolation handled by middleware - user's tenant available via `user.tenant_id`
- Return Pydantic response models (defined in `src/stock_tracker/api/schemas.py`)

### Celery Tasks
- Inherit from `DatabaseTask` for automatic session management (see `src/stock_tracker/workers/tasks.py`)
- Use `bind=True` and `base=DatabaseTask` decorator parameters
- Task timeout: 10min hard limit (600s), 9min soft limit (540s)
- Queue routing: sync operations → `sync` queue, maintenance → `maintenance` queue

### Error Handling
- Custom exceptions in `utils/exceptions.py`: `WildberriesAPIError`, `SheetsAPIError`, etc.
- Middleware catches all exceptions, logs with Sentry, returns JSON error responses
- Never expose internal details (DB connection strings, encryption keys) in error messages

## External Integrations

### Wildberries API
- Base URL: `https://suppliers-api.wildberries.ru/`
- Auth: `Authorization: {encrypted_api_key}` (decrypt before use)
- Client in `marketplaces/wildberries/client.py`
- Rate limits: Use Redis cache to prevent duplicate calls within 5min window

### Google Sheets (v2.0 Horizontal Layout)
- 2 header rows: Row 1 = categories, Row 2 = field names
- Warehouses in separate columns (not nested in one cell)
- Service account auth via encrypted JSON in `tenant.google_service_account_encrypted`
- Implementation: `src/stock_tracker/services/google_sheets_service.py`
- Migration script: `scripts/migrate_sheets_to_horizontal_layout.py`

### Stripe Billing
- Plans: FREE (0), STARTER ($9.90), PRO ($29.90), ENTERPRISE ($99.90)
- Subscription model: One subscription per user (changed from tenant-based in migration `20251207_2140`)
- Webhooks handled in `src/stock_tracker/api/routes/billing.py`

## Docker & Production

**Multi-stage Dockerfile**: `base` → `dependencies` → `development`/`production`/`testing`
- Production uses Gunicorn + Uvicorn workers (4 workers)
- Health checks at `/api/v1/health/` (liveness), `/api/v1/health/ready` (readiness)
- Monitoring stack: Prometheus (port 9090), Grafana (port 3000), Flower (port 5555)

## Telegram Bot Integration
Separate aiogram bot in `telegram-bot/` directory:
- Standalone PostgreSQL connection (not shared with FastAPI)
- User model in `telegram-bot/app/database/models.py` (different from main app)
- Communication with FastAPI via REST API calls (`STOCK_TRACKER_API_URL` env var)
- Start: `cd telegram-bot && python -m app.main`

## Common Pitfalls

1. **Tenant Isolation**: Never query `Product.query.all()` - always filter by `tenant_id`
2. **Async/Sync Mismatch**: Celery tasks are synchronous - use `SyncService`, not async FastAPI services
3. **Encryption**: Always encrypt before storing credentials, decrypt before external API calls
4. **Migration Conflicts**: Check `migrations/versions/` for latest revision before creating new migration
5. **Google Sheets API Quota**: Cache reads for 5 minutes, batch writes to avoid quota exhaustion

## Key Files Reference
- `README.md`: Complete setup guide and feature documentation
- `FASTAPI_SETUP.md`: Multi-tenant architecture details
- `docs/GOOGLE_SHEETS_QUICKSTART.md`: Google Sheets integration guide
- `docker-compose.yml`: Full infrastructure definition
- `alembic.ini`: Database migration configuration

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
