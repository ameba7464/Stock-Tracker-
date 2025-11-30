# Telegram Bot Integration Guide

## 📱 Интеграция с Telegram Bot

### Архитектура

```
Telegram Bot (ваш проект)
    ↓
    Получает API ключ от селлера
    ↓
    POST /api/v1/tenants/me/credentials
    Authorization: Bearer <access_token>
    {
      "wildberries_api_key": "ключ-от-селлера"
    }
    ↓
Stock Tracker API
    ↓
    Шифрует ключ (Fernet)
    ↓
    Сохраняет в БД: tenant.wb_credentials_encrypted
    ↓
ProductService берет ключ из БД
    ↓
Делает запросы к Wildberries API
```

## 🔐 Flow для селлера

### 1. Селлер регистрируется через бот
Бот вызывает:
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "seller@example.com",
  "password": "генерируется-ботом",
  "company_name": "Название магазина",
  "marketplace_type": "wildberries"
}

Response:
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**Важно:** Сохраните `access_token` для дальнейших запросов!

### 2. Селлер отправляет API ключ в бот
Бот получает сообщение: `/set_api_key YOUR_WB_API_KEY`

### 3. Бот сохраняет ключ через API
```bash
PATCH /api/v1/tenants/me/credentials
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "wildberries_api_key": "YOUR_WB_API_KEY"
}

Response:
{
  "message": "Credentials updated successfully",
  "tenant_id": "uuid-tenant-id"
}
```

### 4. Ключ зашифрован и сохранен в БД
```python
# Внутри API происходит:
credentials = {"api_key": "YOUR_WB_API_KEY"}
encrypted = fernet.encrypt(json.dumps(credentials))
tenant.wb_credentials_encrypted = encrypted
db.commit()
```

### 5. ProductService автоматически использует ключ
```python
# В коде Stock Tracker:
marketplace_client = create_marketplace_client(tenant)
# ↓ Автоматически расшифровывает ключ из БД
# ↓ Создает WildberriesAPIClient с этим ключом
products = await marketplace_client.fetch_products()
```

## 💻 Пример кода для Telegram Bot

### Python (aiogram 3.x)
```python
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
import httpx

# Ваши константы
STOCK_TRACKER_API = "http://localhost:8000"

# Хранилище токенов (в проде используйте БД)
user_tokens = {}

@dp.message(commands=["start"])
async def cmd_start(message: Message):
    """Регистрация нового селлера."""
    # Генерируем пароль
    import secrets
    password = secrets.token_urlsafe(16)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{STOCK_TRACKER_API}/api/v1/auth/register",
            json={
                "email": f"tg{message.from_user.id}@stocktracker.local",
                "password": password,
                "company_name": f"Магазин @{message.from_user.username}",
                "marketplace_type": "wildberries"
            }
        )
        
        if response.status_code == 201:
            data = response.json()
            
            # Сохраняем токен
            user_tokens[message.from_user.id] = data["access_token"]
            
            await message.answer(
                "✅ Регистрация успешна!\n"
                "Теперь отправьте свой API ключ Wildberries командой:\n"
                "/set_api_key YOUR_API_KEY"
            )
        else:
            await message.answer(
                f"❌ Ошибка регистрации: {response.text}"
            )

@dp.message(commands=["set_api_key"])
async def cmd_set_api_key(message: Message):
    """Сохранение API ключа."""
    user_id = message.from_user.id
    
    # Проверяем наличие токена
    if user_id not in user_tokens:
        await message.answer("⚠️ Сначала зарегистрируйтесь: /start")
        return
    
    # Извлекаем API ключ из сообщения
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Формат: /set_api_key YOUR_API_KEY")
        return
    
    api_key = parts[1].strip()
    
    # Отправляем в Stock Tracker API
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{STOCK_TRACKER_API}/api/v1/tenants/me/credentials",
            headers={
                "Authorization": f"Bearer {user_tokens[user_id]}"
            },
            json={
                "wildberries_api_key": api_key
            }
        )
        
        if response.status_code == 200:
            await message.answer(
                "✅ API ключ сохранен!\n"
                "Теперь можете запустить синхронизацию: /sync"
            )
        else:
            await message.answer(
                f"❌ Ошибка сохранения: {response.text}"
            )

@dp.message(commands=["sync"])
async def cmd_sync(message: Message):
    """Запуск синхронизации товаров."""
    user_id = message.from_user.id
    
    if user_id not in user_tokens:
        await message.answer("⚠️ Сначала зарегистрируйтесь: /start")
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{STOCK_TRACKER_API}/api/v1/products/sync",
            headers={
                "Authorization": f"Bearer {user_tokens[user_id]}"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            await message.answer(
                f"✅ Синхронизация запущена!\n"
                f"Tenant ID: {data['tenant_id']}\n"
                f"Статус: {data['status']}"
            )
        else:
            await message.answer(
                f"❌ Ошибка синхронизации: {response.text}"
            )

@dp.message(commands=["status"])
async def cmd_status(message: Message):
    """Получить информацию о tenant."""
    user_id = message.from_user.id
    
    if user_id not in user_tokens:
        await message.answer("⚠️ Сначала зарегистрируйтесь: /start")
        return
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{STOCK_TRACKER_API}/api/v1/tenants/me",
            headers={
                "Authorization": f"Bearer {user_tokens[user_id]}"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            await message.answer(
                f"📊 Ваш аккаунт:\n"
                f"ID: {data['id']}\n"
                f"Название: {data['name']}\n"
                f"Маркетплейс: {data['marketplace_type']}\n"
                f"Активен: {'Да' if data['is_active'] else 'Нет'}\n"
                f"Создан: {data['created_at']}"
            )
        else:
            await message.answer(f"❌ Ошибка: {response.text}")
```

### Node.js (Grammy)
```javascript
const { Bot } = require('grammy');
const axios = require('axios');

const bot = new Bot('YOUR_BOT_TOKEN');
const STOCK_TRACKER_API = 'http://localhost:8000';
const userTokens = new Map();

bot.command('start', async (ctx) => {
  const userId = ctx.from.id;
  const password = Math.random().toString(36).substring(2, 18);
  
  try {
    const response = await axios.post(`${STOCK_TRACKER_API}/api/v1/auth/register`, {
      email: `tg${userId}@stocktracker.local`,
      password: password,
      company_name: `Магазин @${ctx.from.username}`,
      marketplace_type: 'wildberries'
    });
    
    userTokens.set(userId, response.data.access_token);
    
    await ctx.reply(
      '✅ Регистрация успешна!\n' +
      'Теперь отправьте свой API ключ: /set_api_key YOUR_KEY'
    );
  } catch (error) {
    await ctx.reply(`❌ Ошибка: ${error.response?.data || error.message}`);
  }
});

bot.command('set_api_key', async (ctx) => {
  const userId = ctx.from.id;
  const token = userTokens.get(userId);
  
  if (!token) {
    return ctx.reply('⚠️ Сначала зарегистрируйтесь: /start');
  }
  
  const apiKey = ctx.match?.trim();
  if (!apiKey) {
    return ctx.reply('❌ Формат: /set_api_key YOUR_API_KEY');
  }
  
  try {
    await axios.patch(
      `${STOCK_TRACKER_API}/api/v1/tenants/me/credentials`,
      { wildberries_api_key: apiKey },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    
    await ctx.reply('✅ API ключ сохранен!');
  } catch (error) {
    await ctx.reply(`❌ Ошибка: ${error.response?.data || error.message}`);
  }
});

bot.start();
```

## 🔒 Безопасность

### 1. Токены должны храниться безопасно
```python
# ❌ НЕ ХРАНИТЬ ТАК:
user_tokens = {}  # Потеряются при рестарте

# ✅ ХРАНИТЬ В БД:
# PostgreSQL, Redis, или другая персистентная БД
```

### 2. Refresh токены для долговременного доступа
```python
@dp.message(commands=["refresh_token"])
async def refresh_access_token(message: Message, db: Database):
    """Обновление access token когда истекает."""
    user_id = message.from_user.id
    
    # Получаем refresh token из БД
    refresh_token = await db.get_refresh_token(user_id)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{STOCK_TRACKER_API}/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Сохраняем новые токены
            await db.save_tokens(
                user_id,
                data["access_token"],
                data["refresh_token"]
            )
```

### 3. Валидация API ключей
```python
@dp.message(commands=["validate_api_key"])
async def validate_api_key(message: Message):
    """Проверка что API ключ работает."""
    user_id = message.from_user.id
    
    async with httpx.AsyncClient() as client:
        # Пытаемся получить продукты
        response = await client.get(
            f"{STOCK_TRACKER_API}/api/v1/products/",
            headers={"Authorization": f"Bearer {user_tokens[user_id]}"}
        )
        
        if response.status_code == 200:
            await message.answer("✅ API ключ валиден!")
        elif response.status_code == 401:
            await message.answer("❌ Неверный API ключ!")
        else:
            await message.answer(f"⚠️ Ошибка проверки: {response.text}")
```

## 📊 Мониторинг

### Webhook для уведомлений
```python
# В будущем можно настроить webhook от Stock Tracker → Telegram
# Когда синхронизация завершится, API отправит webhook:
POST https://your-bot.com/webhook/sync_complete
{
  "tenant_id": "uuid",
  "status": "completed",
  "products_synced": 150,
  "timestamp": "2025-11-20T12:00:00Z"
}

# Бот отправит сообщение селлеру:
await bot.send_message(
    chat_id=user_id,
    text=f"✅ Синхронизация завершена!\nОбновлено товаров: {data['products_synced']}"
)
```

## 🚀 Deployment

### Docker Compose для обоих сервисов
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: stock_tracker
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    
  stock_tracker_api:
    build: ./stock-tracker
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@postgres:5432/stock_tracker
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      ENCRYPTION_MASTER_KEY: ${ENCRYPTION_MASTER_KEY}
    depends_on:
      - postgres
      - redis
  
  telegram_bot:
    build: ./telegram-bot
    environment:
      BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      STOCK_TRACKER_API: http://stock_tracker_api:8000
    depends_on:
      - stock_tracker_api

volumes:
  postgres_data:
```

## 📝 Checklist для интеграции

- [ ] Telegram бот регистрирует селлера через `/api/v1/auth/register`
- [ ] Бот сохраняет `access_token` и `refresh_token` в БД
- [ ] Селлер отправляет API ключ боту
- [ ] Бот сохраняет ключ через `/api/v1/tenants/me/credentials`
- [ ] ProductService автоматически использует ключ из БД
- [ ] Настроена логика refresh токенов
- [ ] Добавлена обработка ошибок (401, 403, 500)
- [ ] Реализованы команды: `/status`, `/sync`, `/validate_api_key`
- [ ] (Опционально) Настроены webhooks для уведомлений

## 🎯 Результат

После интеграции:
1. Селлер регистрируется через бот → получает tenant account
2. Селлер отправляет API ключ → ключ шифруется и сохраняется в БД
3. Stock Tracker автоматически берет ключ из БД при каждом запросе
4. Каждый селлер изолирован в своем tenant
5. Поддерживается 20-30 активных селлеров одновременно
