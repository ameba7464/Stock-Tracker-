# Архитектура Системы Подписок

## Текущее Состояние (25 декабря 2025)

### 🎯 Важно: Бот Временно Бесплатный

**На данный момент Telegram-бот предоставляет бесплатный доступ ко всем функциям.**

- Все новые пользователи получают доступ сразу после регистрации
- `payment_status` автоматически устанавливается в `"completed"` (временный статус)
- Оплата не требуется (MVP-версия)
- Подготовлена инфраструктура для будущего перехода на платную модель

---

## Проблема: Две Разные Системы Подписок

### 1. **Telegram Bot** (`telegram-bot/app/`)

**Таблица:** `users`  
**Поле:** `payment_status` (enum в колонке users)

```python
class PaymentStatus(enum.Enum):
    free = "free"           # Пользователь не оплатил
    pending = "pending"     # Ожидание оплаты
    active = "active"       # Активная подписка
    expired = "expired"     # Истекшая подписка
    PAID = "PAID"          # Legacy значение из БД
```

**Текущая логика:**
- Новый пользователь → `payment_status = "free"`
- После регистрации → **сразу** → `payment_status = "completed"` (временно для MVP)
- Проверка доступа: `if user.payment_status == 'completed'`

**Файлы:**
- `telegram-bot/app/database/models.py` - модель User с payment_status
- `telegram-bot/app/database/crud.py` - `update_user_payment_status()`
- `telegram-bot/app/bot/handlers/registration.py` - автоматическая установка "completed"
- `telegram-bot/app/config.py` - `payment_enabled: bool = False`

---

### 2. **Backend/Admin Panel** (`src/stock_tracker/`)

**Таблица:** `subscriptions` (отдельная таблица)  
**Поля:** `has_access`, `status`

```python
class PaymentStatus(str, enum.Enum):
    FREE = "FREE"
    TRIAL = "TRIAL"
    PAID = "PAID"
    EXPIRED = "EXPIRED"

class Subscription(Base):
    user_id = Column(UUID, ForeignKey("users.id"), unique=True)
    has_access = Column(Boolean, default=False)
    status = Column(String, default='unpaid')  # 'paid' или 'unpaid'
```

**Методы:**
- `subscription.grant_access()` → `has_access=True, status='paid'`
- `subscription.revoke_access()` → `has_access=False, status='unpaid'`

**Проблема:** Эта система НЕ используется telegram-ботом!

---

## Конфликты и Риски

### ⚠️ Критические Проблемы

1. **Дублирование логики:**
   - Telegram bot проверяет `users.payment_status`
   - Backend может проверять `subscriptions.has_access`
   - Два источника правды → несогласованность данных

2. **Разные enum'ы:**
   - Bot: `"free"`, `"pending"`, `"completed"` (строки в нижнем регистре)
   - Backend: `"FREE"`, `"PAID"`, `"TRIAL"` (капс, другие значения)
   - Невозможно напрямую синхронизировать

3. **Временный статус "completed":**
   - Используется ТОЛЬКО для MVP (бесплатный доступ)
   - Не является частью финальной схемы подписок
   - Придется мигрировать при переходе на оплату

4. **Feature flag не используется:**
   - `payment_enabled = False` в конфиге
   - Но код бота НЕ проверяет этот флаг
   - Невозможно динамически включить оплату без изменения кода

---

## Решение: Унифицированная Архитектура

### Принципы

1. **Single Source of Truth:** Таблица `subscriptions` как единственный источник правды о доступе
2. **Feature Flag:** Динамическое включение/выключение платной модели через конфиг
3. **Backward Compatibility:** Существующие бесплатные пользователи сохраняют доступ
4. **Easy Transition:** Один конфиг-флаг для перехода free → paid

---

## Целевая Архитектура

### 1. Таблица `subscriptions` (Расширенная)

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Статус подписки (единственный источник правды)
    status VARCHAR(20) NOT NULL DEFAULT 'FREE',  -- FREE, TRIAL, PAID, EXPIRED
    has_access BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Даты для управления доступом
    trial_ends_at TIMESTAMPTZ,
    subscription_starts_at TIMESTAMPTZ,
    subscription_ends_at TIMESTAMPTZ,
    
    -- Метаданные для платежей (будущее)
    payment_provider VARCHAR(50),  -- 'yookassa', 'stripe', etc.
    payment_external_id VARCHAR(255),
    last_payment_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Индексы
    CONSTRAINT valid_status CHECK (status IN ('FREE', 'TRIAL', 'PAID', 'EXPIRED'))
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_access ON subscriptions(has_access) WHERE has_access = TRUE;
```

---

### 2. Модель User (Упрощенная)

```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    
    # ⚠️ DEPRECATED: Используется только для Legacy
    # TODO: Удалить после миграции всех пользователей на subscriptions
    payment_status = Column(String(20), nullable=True)  
    
    # Relationship
    subscription = relationship("Subscription", back_populates="user", uselist=False)
```

---

### 3. Feature Flag в Config

```python
class Settings(BaseSettings):
    # Payment Configuration
    payment_enabled: bool = False  # FALSE = бесплатный доступ для всех
    payment_provider: str = "yookassa"
    payment_token: str = ""
    
    # Subscription Settings
    free_trial_days: int = 7
    subscription_price: int = 299  # Руб/мес
```

---

### 4. Логика Доступа (Unified)

```python
async def check_user_access(user_id: UUID, session: AsyncSession) -> bool:
    """
    Единая проверка доступа пользователя.
    
    Логика:
    - Если payment_enabled=False → все имеют доступ (MVP)
    - Если payment_enabled=True → проверяем subscription.has_access
    """
    # MVP режим: все имеют доступ
    if not settings.payment_enabled:
        return True
    
    # Продакшн режим: проверяем подписку
    subscription = await session.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
    )
    sub = subscription.scalar_one_or_none()
    
    if not sub:
        # Нет записи о подписке → создаем с бесплатным доступом (legacy users)
        sub = Subscription(user_id=user_id, status='FREE', has_access=True)
        session.add(sub)
        await session.commit()
        return True
    
    return sub.has_access
```

---

### 5. Регистрация Пользователя (Обновленная)

```python
async def complete_registration(message: Message, state: FSMContext, session: AsyncSession, phone: str):
    """Завершение регистрации с поддержкой feature flag."""
    data = await state.get_data()
    telegram_id = message.from_user.id
    
    # Создаем пользователя
    user, was_created = await get_or_create_user(
        session=session,
        telegram_id=telegram_id,
        name=data['name'],
        email=data['email'],
        phone=phone
    )
    
    # Создаем запись подписки
    subscription = await get_or_create_subscription(session, user.id)
    
    # ============================================
    # FEATURE FLAG: Платежи включены?
    # ============================================
    if settings.payment_enabled:
        # Продакшн: отправляем инвойс для оплаты
        await send_payment_invoice(message, user, subscription)
        await state.set_state(RegistrationStates.PAYMENT_PENDING)
        return
    else:
        # MVP: сразу даем бесплатный доступ
        subscription.status = 'FREE'
        subscription.has_access = True
        await session.commit()
        
        await send_google_sheet(message, session, user, data['name'])
    
    await state.clear()
```

---

## План Миграции

### Фаза 1: Подготовка (Текущая - MVP)

**Статус:** ✅ Реализовано

1. ✅ Бот работает бесплатно
2. ✅ `payment_enabled = False` в конфиге
3. ✅ Пользователи получают `payment_status = "completed"` (временно)
4. ⚠️ Таблица `subscriptions` существует, но не используется ботом

**Что нужно сделать:**

- [ ] Создать записи в `subscriptions` для всех существующих пользователей
- [ ] Перевести бота на проверку `subscriptions.has_access` вместо `payment_status`
- [ ] Обновить все хендлеры бота для работы с unified функцией `check_user_access()`

---

### Фаза 2: Унификация (Следующий шаг)

**Цель:** Перевести бота на использование таблицы `subscriptions`

1. **Миграция данных:**
   ```sql
   -- Создать записи subscriptions для всех telegram пользователей
   INSERT INTO subscriptions (user_id, status, has_access, created_at)
   SELECT 
       id,
       'FREE'::subscription_status,
       TRUE,  -- Все существующие пользователи получают бесплатный доступ
       NOW()
   FROM users
   WHERE telegram_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM subscriptions WHERE subscriptions.user_id = users.id);
   ```

2. **Обновить код бота:**
   - Заменить проверки `payment_status` на `check_user_access()`
   - Удалить `update_user_payment_status()` из CRUD
   - Добавить `get_or_create_subscription()`

3. **Добавить middleware:**
   ```python
   class SubscriptionMiddleware(BaseMiddleware):
       async def __call__(self, handler, event, data):
           user_id = data.get("user_id")
           session = data.get("session")
           
           # Проверяем доступ
           has_access = await check_user_access(user_id, session)
           data["has_access"] = has_access
           
           return await handler(event, data)
   ```

4. **Тестирование:**
   - Проверить регистрацию новых пользователей
   - Проверить доступ существующих пользователей
   - Убедиться, что `payment_enabled=False` работает корректно

---

### Фаза 3: Переход на Платную Модель (Будущее)

**Когда:** По решению владельца

**Как включить подписку:**

1. **В `.env` файле:**
   ```env
   PAYMENT_ENABLED=true
   PAYMENT_PROVIDER=yookassa
   PAYMENT_TOKEN=your_yookassa_token
   SUBSCRIPTION_PRICE=299
   FREE_TRIAL_DAYS=7
   ```

2. **Поведение системы изменится автоматически:**
   - Новые пользователи → получают 7 дней триала
   - После триала → запрос оплаты
   - Существующие пользователи → сохраняют бесплатный доступ (grandfathered)

3. **Код ничего менять не нужно!** Логика управляется через feature flag.

---

## Преимущества Решения

### ✅ Для Текущего MVP (Бесплатный Бот)

1. **Не ломает существующую работу:** Бот продолжает работать как есть
2. **Все пользователи имеют доступ:** `payment_enabled=False` → доступ для всех
3. **Простота:** Минимум изменений в текущем коде

---

### ✅ Для Будущего (Платная Модель)

1. **Один переключатель:** `PAYMENT_ENABLED=true` → включается оплата
2. **Защита существующих пользователей:** Legacy users получают `status=FREE` с `has_access=True`
3. **Гибкость:** Можно добавить разные тарифы (FREE, TRIAL, PAID)
4. **Масштабируемость:** Легко интегрировать Stripe, YooKassa, Telegram Stars

---

### ✅ Для Разработки

1. **Единый источник правды:** Таблица `subscriptions`
2. **Нет конфликтов:** Backend и Bot используют одну логику
3. **Тестируемость:** Легко переключаться между режимами
4. **Расширяемость:** Можно добавить analytics, referrals, discounts

---

## Чек-лист Внедрения

### Немедленные Действия (Фаза 2)

- [ ] Создать миграцию `20251225_unify_subscriptions.py`
- [ ] Заполнить `subscriptions` для всех telegram пользователей
- [ ] Создать `check_user_access()` в `telegram-bot/app/services/subscription.py`
- [ ] Обновить `registration.py` для использования unified логики
- [ ] Обновить `menu.py` для проверки через `check_user_access()`
- [ ] Добавить `SubscriptionMiddleware` для автоматической проверки
- [ ] Протестировать на staging с `payment_enabled=False`
- [ ] Задеплоить на production

---

### Подготовка к Платежам (Фаза 3)

- [ ] Интегрировать YooKassa API
- [ ] Создать handler для payment callbacks
- [ ] Добавить логику триального периода
- [ ] Создать админку для управления подписками
- [ ] Настроить email уведомления о истечении подписки
- [ ] Добавить команду `/subscribe` в бота
- [ ] Протестировать полный цикл оплаты на staging
- [ ] Написать документацию для пользователей

---

## Rollback План

Если что-то пойдет не так после миграции:

1. **Откатить миграцию:**
   ```bash
   alembic downgrade -1
   ```

2. **Вернуть старую логику в коде:**
   - Закомментировать `check_user_access()`
   - Вернуть проверку `payment_status == 'completed'`

3. **Убедиться что `payment_enabled=False`:**
   - Проверить `.env` файл
   - Перезапустить бота

---

## FAQ

### Q: Почему не удалить `payment_status` из таблицы `users`?

**A:** Legacy compatibility. Можно удалить после того как убедимся что миграция прошла успешно и все пользователи работают через `subscriptions`.

---

### Q: Что произойдет с существующими пользователями при включении `payment_enabled=True`?

**A:** Ничего! Они получат `status='FREE'` с `has_access=True` и продолжат пользоваться бесплатно (grandfathered users).

---

### Q: Можно ли включить оплату только для новых пользователей?

**A:** Да! Именно так и работает система:
```python
if subscription.status == 'FREE' and subscription.has_access:
    # Legacy user - бесплатный доступ навсегда
    return True
```

---

### Q: Как протестировать платежи без production токена?

**A:** YooKassa и Stripe предоставляют sandbox режим. Используйте тестовые токены в `.env`.

---

## Заключение

**Текущее состояние:**
- ✅ Бот работает бесплатно
- ✅ Все пользователи имеют доступ
- ⚠️ Две системы подписок не синхронизированы
- ⚠️ Нужна унификация перед включением платежей

**Следующий шаг:**
- Выполнить Фазу 2 (Унификация)
- После чего можно будет легко включить платную модель через один feature flag

**Ключевое преимущество:**
- Одна строка в конфиге → переключение между free и paid
- Никаких изменений кода при переходе на оплату
- Защита существующих пользователей

---

**Документ создан:** 25 декабря 2025  
**Версия:** 1.0  
**Автор:** Database Architecture Expert
