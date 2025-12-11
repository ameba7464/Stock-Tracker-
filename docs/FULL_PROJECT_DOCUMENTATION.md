# 📦 Stock Tracker - Полная документация проекта

**Версия документации:** 2.0  
**Дата обновления:** 4 декабря 2025 г.  
**Автор:** Stock Tracker Team

---

## 📋 Оглавление

1. [Обзор проекта](#1-обзор-проекта)
2. [Архитектура системы](#2-архитектура-системы)
3. [Технологический стек](#3-технологический-стек)
4. [Структура проекта](#4-структура-проекта)
5. [Backend (FastAPI)](#5-backend-fastapi)
6. [Telegram Bot](#6-telegram-bot)
7. [Google Sheets интеграция](#7-google-sheets-интеграция)
8. [Wildberries API интеграция](#8-wildberries-api-интеграция)
9. [База данных](#9-база-данных)
10. [Background Processing (Celery)](#10-background-processing-celery)
11. [Мониторинг и логирование](#11-мониторинг-и-логирование)
12. [Docker и развертывание](#12-docker-и-развертывание)
13. [Безопасность](#13-безопасность)
14. [Тестирование](#14-тестирование)
15. [Быстрый старт](#15-быстрый-старт)
16. [API Reference](#16-api-reference)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Обзор проекта

### Что такое Stock Tracker?

**Stock Tracker** — это мультитенантная SaaS-платформа для автоматизации учета товаров на маркетплейсах (Wildberries, Ozon). Система предоставляет:

- 🤖 **Telegram Bot** для регистрации продавцов и управления API ключами
- 📊 **Автоматическая синхронизация** данных о товарах, остатках и заказах
- 📋 **Google Sheets интеграция** — персональные таблицы для каждого продавца
- ⚙️ **FastAPI Backend** — RESTful API для программного доступа
- 📈 **Аналитика** — метрики по складам, оборачиваемости, заказам

### Основные возможности

| Функциональность | Описание |
|------------------|----------|
| **Multi-Tenant** | Поддержка 20-30+ продавцов одновременно |
| **Telegram Bot** | Воронка регистрации, добавление API ключей, уведомления |
| **Auto-Sync** | Автоматическое обновление данных каждые 24 часа |
| **Google Sheets** | Персональная таблица для каждого продавца |
| **Wildberries API v2/v3** | Sales Funnel, Warehouse Remains, Supplier Orders |
| **Analytics** | Оборачиваемость, конверсия, детализация по складам |

### Целевая аудитория

- **Селлеры Wildberries** — получают автоматизированный учет товаров
- **Аналитики** — получают готовые данные в Google Sheets
- **Разработчики** — могут интегрироваться через REST API

---

## 2. Архитектура системы

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         КЛИЕНТЫ                                      │
├─────────────────────────────────────────────────────────────────────┤
│  [Telegram Bot]      [Google Sheets]       [REST API Clients]        │
│       ↓                    ↑                      ↓                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │  FastAPI     │    │  Telegram    │    │   Celery     │          │
│   │  REST API    │    │  Bot (aiogram)│   │   Workers    │          │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
│          │                   │                   │                   │
│          └───────────────────┼───────────────────┘                   │
│                              ↓                                       │
│                    ┌──────────────────┐                              │
│                    │  SERVICES LAYER  │                              │
│                    │ • SyncService    │                              │
│                    │ • GoogleSheets   │                              │
│                    │ • WBIntegration  │                              │
│                    └──────────────────┘                              │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               │
┌──────────────────────────────┼───────────────────────────────────────┐
│                         STORAGE                                      │
├──────────────────────────────┼───────────────────────────────────────┤
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │  PostgreSQL  │    │    Redis     │    │ Google Sheets │         │
│   │  (Primary DB)│    │ (Cache/Queue)│    │ (User Tables) │         │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL APIs                                   │
├─────────────────────────────────────────────────────────────────────┤
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│   │ Wildberries  │    │  Google API  │    │   Stripe     │          │
│   │  API v2/v3   │    │   (Sheets)   │    │  (Billing)   │          │
│   └──────────────┘    └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Регистрация пользователя**: Telegram Bot → PostgreSQL
2. **Добавление API ключа**: Telegram Bot → Валидация через WB API → PostgreSQL
3. **Создание таблицы**: Bot → Google Sheets API → Сохранение sheet_id в PostgreSQL
4. **Синхронизация данных**: 
   - Scheduler (Celery Beat/APScheduler) → Trigger sync
   - WB API (v2/v3) → Получение данных
   - SyncService → Обработка и сохранение в PostgreSQL
   - GoogleSheetsService → Обновление таблицы пользователя

---

## 3. Технологический стек

### Backend

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| Web Framework | FastAPI | 0.104+ | Async REST API |
| ORM | SQLAlchemy | 2.0+ | Работа с БД |
| Migrations | Alembic | 1.12+ | Миграции БД |
| Task Queue | Celery | 5.3+ | Background tasks |
| Scheduler | APScheduler | 3.10+ | Периодические задачи |
| Cache | Redis | 7.0+ | Кеширование и очереди |

### Telegram Bot

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| Bot Framework | aiogram | 3.x | Telegram Bot API |
| FSM Storage | MemoryStorage | - | Состояния диалогов |
| DB Driver | asyncpg | - | Async PostgreSQL |
| ORM | SQLAlchemy | 2.0+ | Async models |

### База данных

| Компонент | Технология | Версия | Назначение |
|-----------|------------|--------|------------|
| Primary DB | PostgreSQL | 15+ | Основное хранилище |
| Cache/Queue | Redis | 7+ | Celery broker, caching |

### Интеграции

| Сервис | API | Назначение |
|--------|-----|------------|
| Wildberries | Analytics API v2/v3 | Данные о товарах |
| Google Sheets | gspread + OAuth | Таблицы пользователей |
| Stripe | Payments API | Биллинг (опционально) |

### DevOps

| Компонент | Технология | Назначение |
|-----------|------------|------------|
| Containerization | Docker | Упаковка приложений |
| Orchestration | Docker Compose | Локальный deployment |
| Monitoring | Prometheus + Grafana | Метрики |
| Error Tracking | Sentry | Отслеживание ошибок |
| Task Monitor | Flower | UI для Celery |

---

## 4. Структура проекта

```
Stock-Tracker/
├── alembic.ini                 # Конфигурация Alembic
├── docker-compose.yml          # Docker orchestration
├── Dockerfile                  # Build image
├── requirements.txt            # Python зависимости
├── main.py                     # Entry point (dev)
│
├── config/                     # Конфигурация
│   └── service-account.json    # Google Service Account
│
├── docs/                       # Документация
│   ├── GOOGLE_SHEETS_QUICKSTART.md
│   ├── GOOGLE_SHEETS_HORIZONTAL_LAYOUT.md
│   └── FULL_PROJECT_DOCUMENTATION.md
│
├── migrations/                 # Alembic миграции
│   ├── env.py
│   ├── script.py.mako
│   └── versions/               # Версии миграций
│
├── scripts/                    # Утилиты
│   ├── migrate_sheets_to_horizontal_layout.py
│   ├── backup_postgres.sh
│   └── restore_postgres.sh
│
├── src/stock_tracker/          # Основной пакет
│   ├── api/                    # FastAPI endpoints
│   │   ├── main.py             # FastAPI app
│   │   ├── client.py           # WB API client
│   │   ├── routes/             # API routes
│   │   │   ├── auth.py         # Аутентификация
│   │   │   ├── products.py     # Управление товарами
│   │   │   ├── tenants.py      # Управление tenant'ами
│   │   │   ├── sheets.py       # Google Sheets
│   │   │   └── billing.py      # Биллинг
│   │   └── middleware/         # Middleware
│   │
│   ├── auth/                   # Аутентификация
│   │   └── jwt.py              # JWT tokens
│   │
│   ├── cache/                  # Redis cache
│   │   └── redis_cache.py
│   │
│   ├── core/                   # Core models
│   │   └── models.py           # Domain models
│   │
│   ├── database/               # Database layer
│   │   ├── connection.py       # DB connection
│   │   └── models/             # SQLAlchemy models
│   │       ├── tenant.py       # Tenant model
│   │       ├── user.py         # User model
│   │       ├── product.py      # Product model
│   │       └── subscription.py # Subscription model
│   │
│   ├── marketplaces/           # Marketplace clients
│   │   ├── base.py             # Base client
│   │   ├── factory.py          # Client factory
│   │   └── wildberries_client.py
│   │
│   ├── services/               # Business logic
│   │   ├── sync_service.py     # Синхронизация
│   │   ├── google_sheets_service.py
│   │   ├── tenant_credentials.py
│   │   ├── webhook_dispatcher.py
│   │   └── billing/            # Stripe billing
│   │
│   ├── workers/                # Celery tasks
│   │   ├── celery_app.py       # Celery config
│   │   └── tasks.py            # Background tasks
│   │
│   └── utils/                  # Utilities
│       ├── logger.py
│       ├── config.py
│       └── exceptions.py
│
├── telegram-bot/               # Telegram Bot (отдельный модуль)
│   ├── app/
│   │   ├── main.py             # Bot entry point
│   │   ├── config.py           # Bot config
│   │   ├── bot/
│   │   │   ├── handlers/       # Message handlers
│   │   │   │   ├── start.py    # /start, /help
│   │   │   │   ├── registration.py
│   │   │   │   ├── menu.py     # Main menu
│   │   │   │   └── api_key.py  # API key management
│   │   │   ├── keyboards/      # Inline/Reply keyboards
│   │   │   ├── middlewares/    # DB, Payment middlewares
│   │   │   └── states.py       # FSM states
│   │   ├── database/
│   │   │   ├── models.py       # User model
│   │   │   ├── database.py     # Async DB connection
│   │   │   └── crud.py         # CRUD operations
│   │   └── services/
│   │       ├── wb_integration.py     # WB API client
│   │       ├── google_sheets.py      # Sheets service
│   │       ├── scheduler.py          # Auto-update scheduler
│   │       └── wildberries_complete_data_collector.py
│   ├── credentials.json        # Google Service Account
│   ├── token.json              # OAuth token
│   └── requirements.txt
│
└── tests/                      # Тесты
    └── ...
```

---

## 5. Backend (FastAPI)

### Описание

FastAPI Backend предоставляет REST API для:
- Аутентификации пользователей (JWT)
- Управления tenant'ами и их credentials
- Просмотра и управления товарами
- Запуска синхронизации
- Работы с Google Sheets

### Основные модули

#### 5.1 API Routes (`src/stock_tracker/api/routes/`)

| Route | Файл | Описание |
|-------|------|----------|
| `/api/v1/auth/` | `auth.py` | Регистрация, логин, refresh tokens |
| `/api/v1/tenants/` | `tenants.py` | Управление tenant'ами |
| `/api/v1/products/` | `products.py` | CRUD для товаров |
| `/api/v1/sheets/` | `sheets.py` | Google Sheets операции |
| `/api/v1/billing/` | `billing.py` | Stripe subscriptions |
| `/api/v1/health/` | `health.py` | Health checks |

#### 5.2 Authentication (`src/stock_tracker/auth/`)

**JWT Token Flow:**
1. Пользователь отправляет email/password на `/auth/login`
2. Сервер возвращает `access_token` (15 min) + `refresh_token` (7 days)
3. Клиент использует `access_token` в заголовке `Authorization: Bearer <token>`
4. При истечении — refresh через `/auth/refresh`

**Пример запроса:**
```bash
# Регистрация
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "securepass123",
    "company_name": "My Shop",
    "marketplace_type": "wildberries"
  }'

# Логин
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "seller@example.com",
    "password": "securepass123"
  }'
```

#### 5.3 Sync Service (`src/stock_tracker/services/sync_service.py`)

**Основные функции:**
- `sync_products()` — синхронизация товаров из маркетплейса
- `_upsert_product()` — создание/обновление товара в БД
- `_index_warehouse_data()` — индексация данных по складам

**Поток синхронизации:**
```
1. SyncService.sync_products()
   ↓
2. WildberriesMarketplaceClient.fetch_products()
   ↓
3. Получение данных из Analytics API v2
   ↓
4. Получение остатков из Warehouse API v1
   ↓
5. _upsert_product() — сохранение в PostgreSQL
   ↓
6. GoogleSheetsService.sync_products_to_sheet()
```

---

## 6. Telegram Bot

### Описание

Telegram Bot — основной интерфейс для селлеров Wildberries. Предоставляет:

- 📝 Воронку регистрации (имя, email, телефон)
- 🔑 Управление WB API ключами
- 📊 Генерацию персональных Google Sheets
- 🔄 Автоматическое обновление таблиц

### Архитектура бота

```
telegram-bot/app/
├── main.py                 # Entry point, Dispatcher setup
├── config.py               # Settings (pydantic-settings)
│
├── bot/
│   ├── handlers/           # Message/Callback handlers
│   │   ├── start.py        # /start, /help commands
│   │   ├── registration.py # User registration FSM
│   │   ├── menu.py         # Main menu callbacks
│   │   ├── api_key.py      # API key management
│   │   └── profile.py      # User profile
│   │
│   ├── keyboards/
│   │   ├── inline.py       # InlineKeyboardMarkup
│   │   └── reply.py        # ReplyKeyboardMarkup
│   │
│   ├── middlewares/
│   │   ├── db.py           # Database session injection
│   │   └── payment.py      # Payment middleware (placeholder)
│   │
│   └── states.py           # FSM States
│
├── database/
│   ├── models.py           # User SQLAlchemy model
│   ├── database.py         # Async engine, session
│   └── crud.py             # CRUD operations
│
├── services/
│   ├── wb_integration.py               # WB API + Sheets
│   ├── google_sheets.py                # gspread wrapper
│   ├── scheduler.py                    # APScheduler
│   └── wildberries_complete_data_collector.py
│
└── utils/
    └── logger.py           # Logging configuration
```

### FSM States (Finite State Machine)

**Регистрация:**
```python
class RegistrationStates(StatesGroup):
    GET_NAME = State()      # Ожидание имени
    GET_EMAIL = State()     # Ожидание email
    GET_PHONE = State()     # Ожидание телефона
```

**API Key:**
```python
class ApiKeyStates(StatesGroup):
    WAITING_FOR_API_KEY = State()  # Ожидание ключа
```

**Google Sheets:**
```python
class GoogleSheetStates(StatesGroup):
    GENERATING_TABLE = State()  # Генерация таблицы
```

### Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать регистрацию или показать главное меню |
| `/help` | Показать справку |

### Главное меню (Inline Keyboard)

**Для пользователей без API ключа:**
- 🔑 Добавить API ключ
- ℹ️ О сервисе
- ❓ Помощь

**Для пользователей с API ключом:**
- 📊 Получить мою таблицу
- ⚙️ Настройки
  - 👤 Профиль
  - 🔑 API ключ (Обновить/Удалить/Проверить)
- ℹ️ О сервисе
- ❓ Помощь

### Автообновление таблиц

**Scheduler (APScheduler):**
- Запускается при старте бота
- Обновляет все таблицы в 00:01 по Москве
- Поддерживает ручной запуск для тестирования

```python
# Код из scheduler.py
self.scheduler.add_job(
    self.update_all_user_tables,
    trigger=CronTrigger(hour=0, minute=1, timezone='Europe/Moscow'),
    id='daily_update'
)
```

### Запуск бота

```bash
cd telegram-bot
pip install -r requirements.txt
python -m app.main
```

**Переменные окружения (.env):**
```env
BOT_TOKEN=your_telegram_bot_token
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tgstock
DB_USER=postgres
DB_PASSWORD=your_password
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

---

## 7. Google Sheets интеграция

### Описание

Каждый пользователь получает персональную Google Таблицу с данными о товарах:

- **Автоматическое создание** при первом запросе
- **Автоматическое обновление** каждые 24 часа
- **Горизонтальная структура** с детализацией по складам

### Новая структура таблицы (v2.0)

**Строка 1: Группы колонок (объединённые ячейки)**
```
| Основная информация | Общие метрики        | Коледино    | Подольск    | ... |
| (A1:D1)            | (E1:I1)              | (J1:L1)     | (M1:O1)     | ... |
```

**Строка 2: Названия колонок**
```
| Бренд | Предмет | Артикул продавца | NM ID | В пути | Конв. | Заказы | Остатки | Обор. | Ост. | Зак. | Обор. | ...
```

**Строка 3+: Данные товаров**

### Структура колонок

| Группа | Колонки | Описание |
|--------|---------|----------|
| **Основная информация** (4 кол.) | Бренд, Предмет, Артикул продавца, NM ID | Идентификаторы товара |
| **Общие метрики** (5 кол.) | В пути до покупателя, В пути конв., Заказы, Остатки, Оборачиваемость | Агрегированные данные |
| **Склад N** (3 кол. каждый) | Остатки, Заказы, Оборачиваемость | Детализация по складам |

### Настройка Google Sheets API

#### Service Account (для обновления таблиц)

1. Создайте проект в Google Cloud Console
2. Включите Google Sheets API и Google Drive API
3. Создайте Service Account
4. Скачайте JSON ключ → `telegram-bot/credentials.json`
5. Дайте Service Account доступ к папке Drive

#### OAuth (для создания таблиц)

1. Создайте OAuth 2.0 Client ID
2. Скачайте → `telegram-bot/oauth_credentials.json`
3. Запустите `python get_oauth_token.py`
4. Авторизуйтесь → создастся `token.json`

### Код интеграции

**Сервис: `telegram-bot/app/services/google_sheets.py`**

```python
class GoogleSheetsService:
    async def create_sheet(self, user_name, telegram_id, data) -> Optional[str]:
        """Создание новой таблицы"""
        
    async def update_sheet(self, sheet_id, data) -> bool:
        """Обновление существующей таблицы"""
        
    def _setup_headers(self, worksheet, warehouses):
        """Настройка 2-строчных заголовков"""
        
    def _format_sheet(self, worksheet):
        """Применение форматирования"""
```

---

## 8. Wildberries API интеграция

### Используемые API endpoints

| API | Endpoint | Данные |
|-----|----------|--------|
| **Analytics API v3** | `/api/analytics/v3/sales-funnel/products` | Заказы, конверсия, выручка |
| **Warehouse Remains API v1** | `/api/v1/warehouse_remains` | Остатки по складам |
| **Statistics API v1** | `/api/v1/supplier/orders` | Заказы (дополнительно) |

### Rate Limits

- **Analytics API**: 3 запроса/минуту, интервал 20 секунд
- **Warehouse Remains**: асинхронный (создание задачи → скачивание результата)

### Клиент: `WildberriesDataCollector`

**Файл:** `telegram-bot/app/services/wildberries_complete_data_collector.py`

```python
class WildberriesDataCollector:
    def get_sales_funnel_data(self, period_start, period_end):
        """Получить данные воронки продаж"""
        
    def get_warehouse_remains(self):
        """Получить остатки по складам"""
        
    def collect_all_data(self) -> List[ProductMetrics]:
        """Собрать все данные и объединить"""
```

### ProductMetrics (результат)

```python
@dataclass
class ProductMetrics:
    # Идентификаторы
    brand: str
    subject: str
    vendor_code: str
    nm_id: int
    
    # Заказы
    orders_total: int
    orders_wb_warehouses: int
    orders_fbs_warehouses: int
    orders_by_warehouse: Dict[str, int]
    
    # Остатки
    stocks_total: int
    stocks_wb: int
    stocks_mp: int
    stocks_by_warehouse: Dict[str, int]
    
    # Логистика
    in_transit_to_customer: int
    in_transit_to_wb_warehouse: int
    
    # Аналитика
    turnover_days: int
    avg_orders_per_day: float
    conversion_to_cart: int
    buyout_percent: int
```

---

## 9. База данных

### PostgreSQL Schema

#### Tenant (Продавец/Компания)

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    marketplace_type ENUM('wildberries', 'ozon'),
    credentials_encrypted JSONB,        -- Зашифрованные API ключи
    google_sheet_id VARCHAR(255),
    google_service_account_encrypted TEXT,
    auto_sync_enabled BOOLEAN DEFAULT TRUE,
    sync_schedule VARCHAR(100),         -- Cron expression
    last_sync_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### User (Пользователь)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    role ENUM('owner', 'admin', 'viewer'),
    telegram_id BIGINT UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### Product (Товар)

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    marketplace_article VARCHAR(100),   -- nmID
    seller_article VARCHAR(255),        -- Артикул продавца
    nm_id INTEGER,
    
    -- Product details
    brand VARCHAR(255),
    subject VARCHAR(255),
    
    -- Stock
    total_stock INTEGER DEFAULT 0,
    stocks_wb INTEGER DEFAULT 0,
    stocks_mp INTEGER DEFAULT 0,
    
    -- Orders
    total_orders INTEGER DEFAULT 0,
    orders_wb_warehouses INTEGER DEFAULT 0,
    orders_fbs_warehouses INTEGER DEFAULT 0,
    
    -- Logistics
    in_way_to_client INTEGER DEFAULT 0,
    in_way_from_client INTEGER DEFAULT 0,
    
    -- Analytics
    turnover_days FLOAT,
    
    -- Warehouse breakdown (JSONB)
    stocks_by_warehouse JSONB,
    orders_by_warehouse JSONB,
    
    last_synced_at TIMESTAMP,
    created_at TIMESTAMP
);
```

### Telegram Bot Database (SQLite/PostgreSQL)

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    wb_api_key TEXT,                    -- API ключ WB
    google_sheet_id VARCHAR(255),       -- ID таблицы
    payment_status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Миграции

```bash
# Создать миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head

# Откатить
alembic downgrade -1
```

---

## 10. Background Processing (Celery)

### Конфигурация

**Файл:** `src/stock_tracker/workers/celery_app.py`

```python
celery_app = Celery(
    "stock_tracker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
    include=["stock_tracker.workers.tasks"]
)

# Queues
task_queues = (
    Queue("sync"),        # Синхронизация товаров
    Queue("maintenance"), # Очистка, health checks
    Queue("default"),     # Остальные задачи
)
```

### Tasks

| Task | Описание |
|------|----------|
| `sync_tenant_products` | Синхронизация товаров tenant'а |
| `cleanup_old_logs` | Очистка старых логов (ежедневно в 3:00) |
| `health_check` | Проверка здоровья (каждые 5 минут) |

### Beat Schedule (Periodic Tasks)

```python
beat_schedule = {
    "cleanup-old-logs": {
        "task": "stock_tracker.workers.tasks.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0),
    },
    "health-check": {
        "task": "stock_tracker.workers.tasks.health_check",
        "schedule": crontab(minute="*/5"),
    },
}
```

### Запуск

```bash
# Worker
celery -A stock_tracker.workers.celery_app worker --loglevel=info

# Beat (scheduler)
celery -A stock_tracker.workers.celery_app beat --loglevel=info

# Flower (monitoring UI)
celery -A stock_tracker.workers.celery_app flower --port=5555
```

---

## 11. Мониторинг и логирование

### Prometheus Metrics

**Доступны на:** `http://localhost:8000/metrics`

| Метрика | Тип | Описание |
|---------|-----|----------|
| `http_requests_total` | Counter | Всего HTTP запросов |
| `http_request_duration_seconds` | Histogram | Длительность запросов |
| `sync_tasks_total` | Counter | Всего sync задач |
| `sync_duration_seconds` | Histogram | Длительность синхронизации |
| `products_synced_total` | Counter | Синхронизировано товаров |

### Grafana Dashboards

**Доступны на:** `http://localhost:3000` (admin/admin)

- **API Performance** — latency, requests/sec, errors
- **Celery Tasks** — pending, running, completed
- **Database** — connections, queries/sec
- **Redis** — memory, hits/misses

### Logging

**Структура логов:**
```json
{
  "timestamp": "2025-12-04T12:00:00Z",
  "level": "INFO",
  "logger": "stock_tracker.services.sync_service",
  "message": "Sync completed for tenant abc-123",
  "tenant_id": "abc-123",
  "products_synced": 150,
  "duration_seconds": 45.2
}
```

**Файлы логов:**
```
logs/
├── stock_tracker.log           # Main application
├── celery_worker.log           # Celery worker
├── celery_beat.log             # Celery beat
└── api_errors.log              # API errors
```

### Sentry

**Интеграция:**
```python
import sentry_sdk
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    traces_sample_rate=0.1
)
```

---

## 12. Docker и развертывание

### Docker Compose Services

```yaml
services:
  postgres:        # PostgreSQL 15
  redis:           # Redis 7
  api:             # FastAPI (4 workers)
  worker:          # Celery Worker
  beat:            # Celery Beat
  flower:          # Celery UI
  prometheus:      # Metrics
  grafana:         # Dashboards
```

### Порты

| Service | Port |
|---------|------|
| FastAPI | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Flower | 5555 |
| Prometheus | 9090 |
| Grafana | 3000 |

### Запуск

```bash
# Все сервисы
docker-compose up -d

# Только БД и Redis
docker-compose up -d postgres redis

# Логи
docker-compose logs -f api

# Остановка
docker-compose down
```

### Переменные окружения

```env
# Database
POSTGRES_USER=stock_tracker
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=stock_tracker

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secret-key-32-chars
FERNET_KEY=your-fernet-key

# Monitoring
SENTRY_DSN=https://...
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin
```

---

## 13. Безопасность

### Authentication

- **JWT Tokens**: access (15 min) + refresh (7 days)
- **Password Hashing**: bcrypt, 12 rounds
- **Token Rotation**: при refresh создается новый refresh token

### Encryption

- **Fernet Encryption**: для API ключей маркетплейсов
- **HTTPS**: обязательно в production
- **Secrets**: хранятся в переменных окружения

### Rate Limiting

```python
# Redis sliding window
RATE_LIMIT_GLOBAL = 1000  # req/min globally
RATE_LIMIT_TENANT = 100   # req/min per tenant
```

### CORS

```python
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]
```

---

## 14. Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С coverage
pytest --cov=stock_tracker

# Конкретный файл
pytest tests/test_sync_service.py -v

# Async тесты
pytest tests/test_api.py -v --asyncio-mode=auto
```

### Структура тестов

```
tests/
├── conftest.py              # Fixtures
├── test_api/
│   ├── test_auth.py
│   ├── test_products.py
│   └── test_tenants.py
├── test_services/
│   ├── test_sync_service.py
│   └── test_sheets_service.py
└── test_workers/
    └── test_tasks.py
```

---

## 15. Быстрый старт

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+ (или Docker)
- Redis 7+ (или Docker)

### Шаг 1: Клонирование

```bash
git clone https://github.com/your-repo/stock-tracker.git
cd stock-tracker
```

### Шаг 2: Настройка окружения

```bash
cp .env.docker .env
# Отредактируйте .env, добавьте секретные ключи
```

### Шаг 3: Запуск через Docker

```bash
docker-compose up -d
docker-compose exec api alembic upgrade head
```

### Шаг 4: Проверка

- API: http://localhost:8000/docs
- Flower: http://localhost:5555
- Grafana: http://localhost:3000

### Telegram Bot (отдельно)

```bash
cd telegram-bot
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Настройте BOT_TOKEN и DB credentials
python -m app.main
```

---

## 16. API Reference

### Authentication

#### POST /api/v1/auth/register
Регистрация нового tenant'а и пользователя.

**Request:**
```json
{
  "email": "seller@example.com",
  "password": "securepass123",
  "company_name": "My Shop",
  "marketplace_type": "wildberries"
}
```

**Response (201):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /api/v1/auth/login
Авторизация пользователя.

### Products

#### GET /api/v1/products/
Список товаров с пагинацией.

**Query params:**
- `page` (int): Номер страницы
- `page_size` (int): Размер страницы (max 200)
- `search` (str): Поиск по артикулу/названию
- `min_stock`, `max_stock` (int): Фильтр по остаткам
- `low_stock_only` (bool): Только товары с низким остатком

**Response:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

### Tenants

#### GET /api/v1/tenants/me
Информация о текущем tenant'е.

#### PATCH /api/v1/tenants/me/credentials
Обновление API ключей.

---

## 17. Troubleshooting

### Telegram Bot не запускается

1. Проверьте `BOT_TOKEN` в `.env`
2. Убедитесь что бот создан в @BotFather
3. Проверьте логи: `logs/bot.log`

### Google Sheets не создаются

1. Проверьте `credentials.json` (Service Account)
2. Запустите `python get_oauth_token.py` для OAuth
3. Проверьте права Service Account на папку Drive
4. Включите Google Sheets API и Drive API в Cloud Console

### Синхронизация не работает

1. Проверьте валидность WB API ключа
2. Проверьте rate limits (3 req/min для Analytics API)
3. Посмотрите логи sync задачи в Flower
4. Проверьте подключение к Redis

### База данных недоступна

1. Проверьте `DATABASE_URL` в `.env`
2. Убедитесь что PostgreSQL запущен
3. Примените миграции: `alembic upgrade head`

### Celery tasks не выполняются

1. Проверьте подключение к Redis
2. Запустите worker: `celery -A stock_tracker.workers.celery_app worker`
3. Проверьте логи в Flower (http://localhost:5555)

---

## Changelog

### v2.0 (23.11.2025)
- Новая горизонтальная структура Google Sheets
- 2 строки заголовков с объединением ячеек
- Детализация по складам (Остатки, Заказы, Оборачиваемость)
- Улучшенное форматирование

### v1.0 (Initial)
- Multi-tenant architecture
- Telegram Bot integration
- Wildberries API v2/v3
- Basic Google Sheets sync

---

© 2025 Stock Tracker Team. MIT License.
