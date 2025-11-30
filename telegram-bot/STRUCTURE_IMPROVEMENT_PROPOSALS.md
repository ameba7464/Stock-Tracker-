# Предложения по Улучшению Структуры Telegram-Бота

## Текущая структура (для справки)

```
app/
├── main.py
├── config.py
├── bot/
│   ├── handlers/
│   ├── keyboards/
│   ├── middlewares/
│   └── states.py
├── database/
├── services/
└── utils/
```

---

## 🏆 Вариант 1: Enterprise-архитектура с чистыми слоями (Рекомендуемый)

**Подходит для:** Масштабирования, работы в команде, долгосрочного развития

```
telegram-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                    # Точка входа
│   │
│   ├── core/                      # 🔧 Ядро приложения
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings
│   │   ├── exceptions.py          # Кастомные исключения
│   │   ├── constants.py           # Константы (тексты, лимиты)
│   │   └── logging.py             # Настройка логирования
│   │
│   ├── domain/                    # 📦 Бизнес-логика (чистый Python)
│   │   ├── __init__.py
│   │   ├── entities/              # Бизнес-сущности
│   │   │   ├── user.py            # @dataclass User
│   │   │   └── stock_data.py      # @dataclass StockData
│   │   ├── repositories/          # Интерфейсы репозиториев (ABC)
│   │   │   └── user_repository.py # AbstractUserRepository
│   │   └── services/              # Бизнес-сервисы
│   │       ├── user_service.py
│   │       └── analytics_service.py
│   │
│   ├── infrastructure/            # 🔌 Внешние зависимости
│   │   ├── __init__.py
│   │   ├── database/
│   │   │   ├── models.py          # SQLAlchemy ORM модели
│   │   │   ├── session.py         # Async session factory
│   │   │   └── repositories/      # Реализации репозиториев
│   │   │       └── user_repo.py   # UserRepository(AbstractUserRepository)
│   │   ├── external/
│   │   │   ├── wildberries/       # WB API клиент
│   │   │   │   ├── client.py
│   │   │   │   ├── models.py      # Pydantic модели ответов
│   │   │   │   └── exceptions.py
│   │   │   └── google_sheets/     # Google Sheets клиент
│   │   │       ├── client.py
│   │   │       └── formatters.py
│   │   └── scheduler/
│   │       └── tasks.py           # APScheduler задачи
│   │
│   ├── presentation/              # 🎨 Telegram Bot (UI)
│   │   ├── __init__.py
│   │   ├── bot.py                 # Bot + Dispatcher factory
│   │   ├── handlers/
│   │   │   ├── __init__.py        # include_routers()
│   │   │   ├── common.py          # /start, /help
│   │   │   ├── registration/      # Воронка регистрации
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   ├── states.py
│   │   │   │   └── callbacks.py
│   │   │   ├── api_key/           # Управление API ключом
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py
│   │   │   │   └── states.py
│   │   │   └── analytics/         # Таблицы и аналитика
│   │   │       └── router.py
│   │   ├── keyboards/
│   │   │   ├── __init__.py
│   │   │   ├── builders.py        # KeyboardBuilder фабрики
│   │   │   ├── main_menu.py
│   │   │   └── inline.py
│   │   ├── middlewares/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── logging.py
│   │   │   └── throttling.py      # Антифлуд
│   │   ├── filters/               # Кастомные фильтры
│   │   │   ├── admin.py
│   │   │   └── registered.py
│   │   └── utils/
│   │       ├── messages.py        # Шаблоны сообщений
│   │       └── formatters.py      # Форматирование данных
│   │
│   └── di/                        # 💉 Dependency Injection
│       ├── __init__.py
│       └── container.py           # Контейнер зависимостей
│
├── alembic/                       # Миграции БД
├── tests/                         # Тесты
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── scripts/                       # Утилиты
│   ├── setup_oauth.py
│   └── db_seed.py
├── pyproject.toml                 # Poetry / UV
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

### Ключевые преимущества:
- ✅ **Чистая архитектура** — бизнес-логика не зависит от фреймворков
- ✅ **Тестируемость** — легко мокать репозитории и сервисы
- ✅ **Масштабируемость** — легко добавлять новые фичи
- ✅ **Dependency Injection** — управление зависимостями

### Пример Dependency Injection (dishka):

```python
# src/di/container.py
from dishka import Container, Provider, provide, Scope

class DatabaseProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def get_session(self, engine: AsyncEngine) -> AsyncSession:
        async with AsyncSession(engine) as session:
            yield session

class RepositoryProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_user_repo(self, session: AsyncSession) -> UserRepository:
        return SQLAlchemyUserRepository(session)

container = Container(DatabaseProvider(), RepositoryProvider())
```

---

## 🎯 Вариант 2: aiogram-dialog для сложных интерфейсов

**Подходит для:** Сложных форм, многошаговых процессов, динамических меню

```
telegram-bot/
├── src/
│   ├── main.py
│   ├── config.py
│   │
│   ├── dialogs/                   # 🎭 Диалоги (aiogram-dialog)
│   │   ├── __init__.py
│   │   ├── registration/          # Диалог регистрации
│   │   │   ├── __init__.py
│   │   │   ├── dialog.py          # Dialog(Window(...))
│   │   │   ├── getters.py         # async def get_data(...)
│   │   │   ├── handlers.py        # on_click, on_input
│   │   │   └── states.py          # StatesGroup
│   │   ├── api_key/               # Диалог API ключа
│   │   │   ├── dialog.py
│   │   │   ├── getters.py
│   │   │   └── states.py
│   │   ├── analytics/             # Диалог аналитики
│   │   │   ├── dialog.py
│   │   │   └── widgets/           # Кастомные виджеты
│   │   │       └── progress.py
│   │   └── common/                # Общие компоненты
│   │       ├── widgets.py
│   │       └── keyboards.py
│   │
│   ├── handlers/                  # Обычные хендлеры
│   │   └── commands.py            # /start, /help
│   │
│   ├── services/
│   ├── database/
│   └── integrations/
│
└── ...
```

### Пример диалога регистрации:

```python
# src/dialogs/registration/dialog.py
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Row, Cancel
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const, Format

class RegistrationSG(StatesGroup):
    name = State()
    email = State()
    phone = State()
    confirm = State()

async def on_name_success(message, widget, manager, text):
    manager.dialog_data["name"] = text
    await manager.next()

async def getter(dialog_manager, **kwargs):
    return {
        "name": dialog_manager.dialog_data.get("name", ""),
        "email": dialog_manager.dialog_data.get("email", ""),
        "phone": dialog_manager.dialog_data.get("phone", ""),
    }

registration_dialog = Dialog(
    Window(
        Const("👤 <b>Шаг 1/3: Как вас зовут?</b>"),
        TextInput(id="name_input", on_success=on_name_success),
        Cancel(Const("❌ Отмена")),
        state=RegistrationSG.name,
        parse_mode="HTML",
    ),
    Window(
        Format("✅ Привет, {name}!\n\n📧 <b>Шаг 2/3: Ваш email:</b>"),
        TextInput(id="email_input", on_success=on_email_success),
        Row(
            Button(Const("⬅️ Назад"), id="back", on_click=go_back),
            Cancel(Const("❌ Отмена")),
        ),
        state=RegistrationSG.email,
        getter=getter,
        parse_mode="HTML",
    ),
    Window(
        Format(
            "📋 <b>Подтвердите данные:</b>\n\n"
            "👤 Имя: {name}\n"
            "📧 Email: {email}\n"
            "📱 Телефон: {phone}"
        ),
        Row(
            Button(Const("✅ Подтвердить"), id="confirm", on_click=on_confirm),
            Button(Const("🔄 Изменить"), id="restart", on_click=restart),
        ),
        state=RegistrationSG.confirm,
        getter=getter,
        parse_mode="HTML",
    ),
)
```

### Преимущества aiogram-dialog:
- ✅ **Декларативный UI** — описание интерфейса, а не логики
- ✅ **Встроенная навигация** — Back, Cancel, SwitchTo
- ✅ **Виджеты** — Select, Multiselect, Calendar, Scrolling
- ✅ **Getters** — отделение данных от представления

---

## 🚀 Вариант 3: Feature-based (по фичам)

**Подходит для:** Микросервисной архитектуры, независимых модулей

```
telegram-bot/
├── src/
│   ├── main.py
│   ├── common/                    # 🔧 Общее
│   │   ├── config.py
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   └── base_model.py
│   │   ├── middlewares/
│   │   └── utils/
│   │
│   ├── features/                  # 📦 Фичи (каждая - автономный модуль)
│   │   ├── __init__.py            # register_all_features()
│   │   │
│   │   ├── auth/                  # 🔐 Аутентификация
│   │   │   ├── __init__.py        # router
│   │   │   ├── router.py
│   │   │   ├── states.py
│   │   │   ├── keyboards.py
│   │   │   ├── models.py          # User ORM
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── texts.py           # Тексты сообщений
│   │   │
│   │   ├── wildberries/           # 📊 WB интеграция
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── client.py          # WB API Client
│   │   │   ├── models.py          # Pydantic модели
│   │   │   ├── service.py
│   │   │   └── texts.py
│   │   │
│   │   ├── google_sheets/         # 📋 Google Sheets
│   │   │   ├── __init__.py
│   │   │   ├── router.py
│   │   │   ├── client.py
│   │   │   ├── formatters.py
│   │   │   └── service.py
│   │   │
│   │   ├── analytics/             # 📈 Аналитика
│   │   │   ├── router.py
│   │   │   └── service.py
│   │   │
│   │   └── scheduler/             # ⏰ Автообновление
│   │       ├── __init__.py
│   │       └── tasks.py
│   │
│   └── shared/                    # 🔗 Shared между фичами
│       ├── keyboards/
│       └── filters/
│
└── ...
```

### Пример регистрации фич:

```python
# src/features/__init__.py
from aiogram import Dispatcher

from .auth import router as auth_router
from .wildberries import router as wb_router
from .google_sheets import router as sheets_router
from .analytics import router as analytics_router

def register_all_features(dp: Dispatcher):
    """Регистрация всех фич в диспетчере."""
    dp.include_routers(
        auth_router,
        wb_router,
        sheets_router,
        analytics_router,
    )
```

```python
# src/features/auth/__init__.py
from .router import router

__all__ = ["router"]
```

### Преимущества:
- ✅ **Автономность** — каждая фича самодостаточна
- ✅ **Параллельная разработка** — разные люди работают над разными фичами
- ✅ **Легкий рефакторинг** — переместить/удалить фичу просто

---

## 📱 Вариант 4: Monorepo с FastAPI Backend

**Подходит для:** Добавления REST API, веб-дашборда, множественных клиентов

```
stock-tracker/
├── packages/
│   ├── core/                      # 🔧 Shared business logic
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── stock_tracker_core/
│   │           ├── domain/
│   │           ├── services/
│   │           └── repositories/
│   │
│   ├── telegram-bot/              # 🤖 Telegram Bot
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── stock_tracker_bot/
│   │           ├── main.py
│   │           ├── handlers/
│   │           └── ...
│   │
│   ├── api/                       # 🌐 FastAPI REST API
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── stock_tracker_api/
│   │           ├── main.py
│   │           ├── routes/
│   │           ├── schemas/
│   │           └── dependencies.py
│   │
│   └── web/                       # 💻 Frontend (React/Vue)
│       ├── package.json
│       └── src/
│
├── docker-compose.yml
├── pyproject.toml                 # Root (uv workspaces)
└── README.md
```

### Структура Core пакета:

```python
# packages/core/src/stock_tracker_core/services/analytics.py
class AnalyticsService:
    def __init__(self, user_repo: UserRepository, wb_client: WBClient):
        self._user_repo = user_repo
        self._wb_client = wb_client
    
    async def generate_report(self, user_id: int) -> Report:
        user = await self._user_repo.get_by_id(user_id)
        data = await self._wb_client.fetch_data(user.api_key)
        return Report.from_wb_data(data)
```

```python
# packages/telegram-bot/src/stock_tracker_bot/handlers/analytics.py
from stock_tracker_core.services import AnalyticsService

@router.callback_query(F.data == "generate_report")
async def generate_report(callback: CallbackQuery, analytics: AnalyticsService):
    report = await analytics.generate_report(callback.from_user.id)
    await callback.message.answer(report.to_telegram_message())
```

```python
# packages/api/src/stock_tracker_api/routes/analytics.py
from stock_tracker_core.services import AnalyticsService

@router.get("/reports/{user_id}")
async def get_report(user_id: int, analytics: AnalyticsService = Depends()):
    report = await analytics.generate_report(user_id)
    return report.to_dict()
```

### Преимущества:
- ✅ **DRY** — бизнес-логика в одном месте
- ✅ **Множественные клиенты** — бот, API, веб
- ✅ **Масштабирование** — микросервисы из монолита

---

## 🛠 Рекомендуемые библиотеки

### Dependency Injection
```toml
# pyproject.toml
[tool.poetry.dependencies]
dishka = "^1.3.0"        # Современный DI для aiogram
# или
dependency-injector = "^4.41.0"  # Классический DI
```

### Улучшенные диалоги
```toml
aiogram-dialog = "^2.2.0"    # Декларативные интерфейсы
```

### Валидация
```toml
pydantic = "^2.5.0"          # Модели данных
pydantic-settings = "^2.1.0" # Конфигурация
```

### Логирование
```toml
structlog = "^24.1.0"        # Структурированное логирование
loguru = "^0.7.0"            # Альтернатива
```

### Тестирование
```toml
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
aiogram-tests = "^1.0.0"     # Мокирование aiogram
```

### База данных
```toml
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
alembic = "^1.13.0"
asyncpg = "^0.29.0"          # PostgreSQL async
# или
piccolo = "^1.4.0"           # Альтернатива SQLAlchemy
```

---

## 🔄 План миграции (поэтапный)

### Этап 1: Рефакторинг текстов и констант
```python
# src/core/texts.py
class Texts:
    WELCOME = "👋 <b>Добро пожаловать!</b>"
    
    class Registration:
        ASK_NAME = "✍️ Как вас зовут?"
        ASK_EMAIL = "📧 Введите email:"
        SUCCESS = "✅ Регистрация завершена!"
```

### Этап 2: Выделение сервисов
```python
# src/domain/services/user_service.py
class UserService:
    def __init__(self, user_repo: UserRepository):
        self._repo = user_repo
    
    async def register(self, data: RegistrationData) -> User:
        ...
```

### Этап 3: Внедрение DI
```python
# src/main.py
from dishka.integrations.aiogram import setup_dishka

container = make_container()
setup_dishka(container, dp)
```

### Этап 4: Миграция на aiogram-dialog (опционально)
```python
# Постепенная замена FSM на Dialog
```

---

## 📊 Сравнительная таблица

| Критерий | Текущий | Вариант 1 | Вариант 2 | Вариант 3 | Вариант 4 |
|----------|---------|-----------|-----------|-----------|-----------|
| Сложность | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Масштабируемость | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Тестируемость | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Скорость разработки | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| UI/UX возможности | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Командная работа | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🎯 Моя рекомендация

Для вашего проекта **Stock Tracker** рекомендую **комбинацию Вариант 1 + Вариант 2**:

1. **Enterprise-архитектура** для бизнес-логики и инфраструктуры
2. **aiogram-dialog** для сложных пользовательских интерфейсов

Это даст:
- Чистый, тестируемый код
- Красивые интерфейсы с кнопками, формами, навигацией
- Возможность легко масштабировать проект
