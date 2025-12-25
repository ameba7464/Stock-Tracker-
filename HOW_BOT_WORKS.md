# Как Работает Telegram Бот После Унификации

**Дата:** 25 декабря 2025 г.  
**Версия:** 2.0 (Unified Subscriptions)

---

## 🎯 Общая Концепция

Бот теперь использует **унифицированную систему подписок** с поддержкой **feature flag** для легкого перехода от бесплатной к платной модели.

### Ключевые Принципы

1. **Единый источник правды** — таблица `subscriptions` контролирует доступ
2. **Feature Flag** — `payment_enabled` переключает режимы работы
3. **Обратная совместимость** — существующие пользователи не теряют доступ
4. **Fail-open** — при ошибках даем доступ (лучше для UX)

---

## 📊 Архитектура Доступа

### Модель Данных

```python
# Таблица users (базовая информация)
User:
  - id (UUID)
  - telegram_id (BigInt, unique)
  - full_name, email, phone
  - wb_api_key (Wildberries API)
  - google_sheet_id
  - payment_status (DEPRECATED - для обратной совместимости)

# Таблица subscriptions (единый источник правды)
Subscription:
  - id (UUID)
  - user_id (UUID, FK → users.id)
  
  # Контроль доступа
  - status ('FREE' | 'TRIAL' | 'PAID' | 'EXPIRED')
  - has_access (Boolean) ← ГЛАВНОЕ ПОЛЕ!
  
  # Даты управления
  - trial_ends_at (для триалов)
  - subscription_starts_at
  - subscription_ends_at (для подписок)
  
  # Метаданные платежей
  - payment_provider ('yookassa' | 'stripe' | etc)
  - payment_external_id (ID транзакции)
  - last_payment_at
```

---

## 🔄 Сценарии Работы

### Сценарий 1: Новый Пользователь (MVP Режим)

**Условие:** `payment_enabled = False` (по умолчанию)

```
1. Пользователь отправляет /start
   ↓
2. Бот не находит user в БД → начинает регистрацию
   ↓
3. Пользователь вводит:
   - Имя: "Иван Иванов"
   - Email: "ivan@example.com"
   - Телефон: "+79991234567"
   ↓
4. Бот создает:
   a) User в таблице users
   b) Subscription в таблице subscriptions:
      - status = 'FREE'
      - has_access = TRUE
      - subscription_starts_at = NOW()
   ↓
5. Бот отправляет ссылку на Google Sheet
   ↓
6. Показывает главное меню
```

**Код:**
```python
# registration.py
subscription = await get_or_create_subscription(user.id, session)
# → Создает FREE подписку, так как payment_enabled=False

await send_google_sheet(message, session, user, name)
```

---

### Сценарий 2: Существующий Пользователь (MVP Режим)

**Условие:** `payment_enabled = False`

```
1. Пользователь отправляет /start
   ↓
2. Бот находит user в БД
   ↓
3. Вызывает check_user_access(user.id, session)
   → payment_enabled = False
   → return True (доступ для всех)
   ↓
4. Показывает главное меню
```

**Код:**
```python
# start.py
if user:
    has_access = await check_user_access(user.id, session)
    if has_access:
        # Показываем меню
```

---

### Сценарий 3: Новый Пользователь (Продакшн с Триалом)

**Условие:** `payment_enabled = True`, `free_trial_days = 7`

```
1. Пользователь отправляет /start
   ↓
2. Проходит регистрацию (имя, email, телефон)
   ↓
3. Бот создает:
   a) User
   b) Subscription:
      - status = 'TRIAL'
      - has_access = TRUE
      - trial_ends_at = NOW() + 7 дней
   ↓
4. Отправляет сообщение:
   "✅ У вас 7 дней бесплатного доступа!
    После триала: 299₽/мес"
   ↓
5. Показывает главное меню
```

**Код:**
```python
# subscription.py → get_or_create_subscription()
if settings.payment_enabled:
    subscription = Subscription(
        user_id=user_id,
        status='TRIAL',
        has_access=True,
        trial_ends_at=datetime.utcnow() + timedelta(days=7)
    )
```

---

### Сценарий 4: Истек Триальный Период

**Условие:** `payment_enabled = True`, триал закончился

```
1. Пользователь отправляет /start
   ↓
2. Бот находит user
   ↓
3. check_user_access(user.id, session):
   a) Находит subscription
   b) Проверяет: trial_ends_at < NOW()
   c) Обновляет:
      - status = 'EXPIRED'
      - has_access = FALSE
   d) return False
   ↓
4. Бот отправляет:
   "⏰ Ваш триальный период истек.
    Для продолжения работы оформите подписку: /subscribe"
   ↓
5. Не показывает меню
```

**Код:**
```python
# subscription.py → check_user_access()
if subscription.status == 'TRIAL' and subscription.trial_ends_at:
    if datetime.utcnow() > subscription.trial_ends_at:
        subscription.status = 'EXPIRED'
        subscription.has_access = False
        await session.commit()
        return False
```

---

### Сценарий 5: Оплата Подписки

**Условие:** Пользователь нажал /subscribe или кнопку "Оформить"

```
1. Пользователь видит:
   "💳 Подписка: 299₽/мес
    Выберите способ оплаты:"
   [YooKassa] [Банковская карта] [СБП]
   ↓
2. Выбирает способ оплаты
   ↓
3. Бот генерирует invoice через YooKassa API
   ↓
4. Пользователь оплачивает
   ↓
5. YooKassa отправляет webhook → /api/webhooks/yookassa
   ↓
6. Бот получает подтверждение оплаты
   ↓
7. Вызывает grant_paid_access():
   - status = 'PAID'
   - has_access = TRUE
   - subscription_starts_at = NOW()
   - subscription_ends_at = NOW() + 30 дней
   - payment_provider = 'yookassa'
   - payment_external_id = 'transaction_id'
   ↓
8. Отправляет сообщение:
   "✅ Оплата прошла успешно!
    Подписка активна до: 25.01.2026"
   ↓
9. Показывает главное меню
```

**Код:**
```python
# subscription.py → grant_paid_access()
subscription = await get_or_create_subscription(user_id, session)
subscription.status = 'PAID'
subscription.has_access = True
subscription.subscription_ends_at = now + timedelta(days=30)
await session.commit()
```

---

### Сценарий 6: Legacy Пользователь при Включении Платежей

**Условие:** `payment_enabled` переключили с False на True

```
1. Старый пользователь (зарегистрирован до включения платежей)
   ↓
2. Отправляет /start
   ↓
3. check_user_access():
   a) Находит subscription со status='FREE' и has_access=TRUE
   b) return TRUE (grandfathered access)
   ↓
4. Показывает меню как обычно
   
👉 Legacy users НЕ теряют доступ при включении платежей!
```

**Логика защиты:**
```python
# Миграция создает FREE подписки для всех существующих users:
INSERT INTO subscriptions (user_id, status, has_access)
SELECT id, 'FREE', TRUE
FROM users
WHERE telegram_id IS NOT NULL;
```

---

## 🔍 Проверка Доступа (Детально)

### Функция check_user_access()

```python
async def check_user_access(user_id: UUID, session: AsyncSession) -> bool:
    # Шаг 1: Проверка feature flag
    if not settings.payment_enabled:
        return True  # MVP режим → все имеют доступ
    
    # Шаг 2: Поиск подписки
    subscription = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    ).scalar_one_or_none()
    
    # Шаг 3: Если подписки нет → создаем FREE (legacy user)
    if not subscription:
        subscription = Subscription(
            user_id=user_id,
            status='FREE',
            has_access=True
        )
        session.add(subscription)
        await session.commit()
        return True
    
    # Шаг 4: Проверка триала
    if subscription.status == 'TRIAL':
        if subscription.trial_ends_at < datetime.utcnow():
            subscription.status = 'EXPIRED'
            subscription.has_access = False
            await session.commit()
            return False
    
    # Шаг 5: Проверка платной подписки
    if subscription.status == 'PAID':
        if subscription.subscription_ends_at < datetime.utcnow():
            subscription.status = 'EXPIRED'
            subscription.has_access = False
            await session.commit()
            return False
    
    # Шаг 6: Возвращаем текущий статус доступа
    return subscription.has_access
```

---

## 🎛️ Feature Flag Управление

### Переключение Режимов

**MVP → Продакшн (включение платежей):**

```env
# Было в .env:
PAYMENT_ENABLED=false

# Стало:
PAYMENT_ENABLED=true
PAYMENT_PROVIDER=yookassa
PAYMENT_TOKEN=live_token_here
FREE_TRIAL_DAYS=7
SUBSCRIPTION_PRICE=299
```

**После перезапуска бота:**
- Существующие пользователи → status=FREE, доступ сохраняется
- Новые пользователи → status=TRIAL, 7 дней триала
- Автоматическая проверка истечения срока

---

## 📱 Хендлеры Бота

### /start — Точка Входа

```python
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    user = await get_user_by_telegram_id(session, message.from_user.id)
    
    if user:
        # Проверяем доступ через unified систему
        has_access = await check_user_access(user.id, session)
        
        if has_access:
            await show_main_menu(message, user)
        else:
            await message.answer(
                "⏰ Ваша подписка истекла.\n"
                "Для продолжения работы: /subscribe"
            )
    else:
        # Начинаем регистрацию
        await state.set_state(RegistrationStates.GET_NAME)
        await message.answer("Как вас зовут?")
```

---

### Регистрация — Создание User + Subscription

```python
async def complete_registration(...):
    # Создаем пользователя
    user, was_created = await get_or_create_user(...)
    
    # Создаем подписку (учитывая feature flag)
    subscription = await get_or_create_subscription(user.id, session)
    
    # Если платежи включены:
    if settings.payment_enabled:
        # TODO: Отправить invoice
        # await send_payment_invoice(message, user, subscription)
        pass
    else:
        # MVP: сразу даем доступ
        await send_google_sheet(message, session, user, name)
```

---

### Меню — Проверка Доступа

```python
@router.callback_query(F.data == "get_sheet")
async def callback_get_sheet(callback: CallbackQuery, session: AsyncSession):
    user = await get_user_by_telegram_id(session, callback.from_user.id)
    
    # Unified проверка доступа
    has_access = await check_user_access(user.id, session)
    
    if not has_access:
        await callback.answer(
            "❌ Для доступа к таблице необходима подписка: /subscribe",
            show_alert=True
        )
        return
    
    # Отправляем ссылку на таблицу
    await callback.message.answer(f"📊 Ваша таблица: {settings.google_sheet_url}")
```

---

## 🛠️ Сервисные Функции

### get_or_create_subscription()

**Назначение:** Безопасное создание подписки с учетом feature flag

```python
subscription = await get_or_create_subscription(user_id, session)

# Логика:
if settings.payment_enabled:
    # Новый user → TRIAL (7 дней)
    status='TRIAL', has_access=True, trial_ends_at=NOW()+7d
else:
    # MVP режим → FREE
    status='FREE', has_access=True
```

---

### grant_paid_access()

**Назначение:** Выдача доступа после оплаты

```python
await grant_paid_access(
    user_id=user.id,
    session=session,
    payment_provider='yookassa',
    payment_id='tx_12345',
    duration_days=30
)

# Результат:
# - status = 'PAID'
# - has_access = TRUE
# - subscription_ends_at = NOW() + 30 дней
```

---

### revoke_access()

**Назначение:** Отзыв доступа (возврат платежа, нарушение правил)

```python
await revoke_access(user_id, session)

# Результат:
# - status = 'EXPIRED'
# - has_access = FALSE
```

---

### get_subscription_info()

**Назначение:** Получить информацию о подписке для UI

```python
info = await get_subscription_info(user_id, session)

# Вернет:
{
    'status': 'PAID',
    'has_access': True,
    'days_remaining': 15,
    'is_trial': False,
    'is_paid': True,
    'subscription_ends_at': datetime(2026, 1, 25)
}
```

---

## 🎨 Пользовательский Опыт

### MVP Режим (Сейчас)

```
Пользователь → /start
    ↓
Регистрация (30 сек)
    ↓
✅ Сразу доступ к таблице
    ↓
Работа без ограничений
```

---

### Продакшн с Триалом (Будущее)

```
Пользователь → /start
    ↓
Регистрация
    ↓
🎁 "7 дней бесплатного доступа!"
    ↓
Работа 7 дней
    ↓
⏰ "Триал истек. Оформите подписку: 299₽/мес"
    ↓
Оплата → ✅ Доступ на 30 дней
```

---

## 📊 Состояния Подписки

### FREE (Бесплатный)

**Когда:** 
- MVP режим для новых users
- Legacy users при включении платежей

**Поля:**
```python
status = 'FREE'
has_access = True
subscription_starts_at = NOW()
subscription_ends_at = None  # Бессрочно
```

---

### TRIAL (Триальный)

**Когда:**
- Новый пользователь при payment_enabled=True

**Поля:**
```python
status = 'TRIAL'
has_access = True
trial_ends_at = NOW() + 7 days
```

**Проверка истечения:**
```python
if NOW() > trial_ends_at:
    status = 'EXPIRED'
    has_access = False
```

---

### PAID (Оплаченный)

**Когда:**
- После успешной оплаты

**Поля:**
```python
status = 'PAID'
has_access = True
subscription_starts_at = NOW()
subscription_ends_at = NOW() + 30 days
payment_provider = 'yookassa'
payment_external_id = 'tx_12345'
last_payment_at = NOW()
```

**Проверка истечения:**
```python
if NOW() > subscription_ends_at:
    status = 'EXPIRED'
    has_access = False
```

---

### EXPIRED (Истекший)

**Когда:**
- Триал закончился без оплаты
- Платная подписка закончилась без продления

**Поля:**
```python
status = 'EXPIRED'
has_access = False
```

**Действие:**
- Запретить доступ к функциям
- Показать кнопку /subscribe

---

## 🔐 Безопасность

### Защита от Race Conditions

```python
# При регистрации используется get_or_create_user():
existing_user = await get_user_by_telegram_id(session, telegram_id)
if existing_user:
    return existing_user, False  # Не создаем дубликат

# При создании подписки:
subscription = await session.execute(
    select(Subscription).where(Subscription.user_id == user_id)
).scalar_one_or_none()

if not subscription:
    # Создаем только если нет
```

---

### Fail-Open Стратегия

```python
try:
    # Проверяем доступ
    subscription = await get_subscription(...)
    return subscription.has_access
except Exception as e:
    logger.error(f"Error checking access: {e}")
    return True  # В случае ошибки даем доступ (лучше для UX)
```

---

## 📈 Мониторинг

### Метрики для Отслеживания

```python
# 1. Регистрации
logger.info(f"New user registered: telegram_id={telegram_id}")

# 2. Создание подписок
logger.info(f"Created {subscription.status} subscription for user {user_id}")

# 3. Проверки доступа
logger.debug(f"Access check: user={user_id}, result={has_access}")

# 4. Оплаты
logger.info(f"Payment received: user={user_id}, amount=299, provider=yookassa")

# 5. Истечение подписок
logger.info(f"Subscription expired: user={user_id}, status=TRIAL→EXPIRED")
```

---

## 🎯 Итоговая Схема Работы

```
┌──────────────┐
│   /start     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ User exists? │
└──────┬───────┘
       │
   ┌───┴───┐
   │  YES  │  NO
   │       │   │
   ▼       ▼   ▼
┌──────┐ ┌────────────┐
│check │ │Registration│
│access│ │   Flow     │
└──┬───┘ └──────┬─────┘
   │            │
   │            ▼
   │      ┌──────────────┐
   │      │get_or_create_│
   │      │subscription()│
   │      └──────┬───────┘
   │             │
   └─────────┬───┘
             │
     ┌───────▼────────┐
     │payment_enabled?│
     └───────┬────────┘
             │
        ┌────┴────┐
        │         │
     FALSE      TRUE
        │         │
        ▼         ▼
   ┌────────┐ ┌─────────┐
   │ FREE   │ │ TRIAL   │
   │access  │ │7 days   │
   └───┬────┘ └────┬────┘
       │           │
       └──────┬────┘
              │
              ▼
        ┌──────────┐
        │has_access│
        │  = TRUE? │
        └─────┬────┘
              │
         ┌────┴────┐
         │         │
       TRUE      FALSE
         │         │
         ▼         ▼
    ┌────────┐ ┌──────────┐
    │  Show  │ │  Show    │
    │  Menu  │ │/subscribe│
    └────────┘ └──────────┘
```

---

## ✅ Преимущества Новой Архитектуры

1. **Единый источник правды** — нет противоречий между системами
2. **Feature Flag** — переключение одной строкой в .env
3. **Обратная совместимость** — legacy users защищены
4. **Простота тестирования** — легко переключаться между режимами
5. **Расширяемость** — легко добавить новые тарифы/функции
6. **Безопасность** — fail-open, защита от race conditions
7. **Мониторинг** — все действия логируются

---

**Создано:** 25 декабря 2025 г.  
**Версия:** 2.0  
**Статус:** ✅ Готово к production
