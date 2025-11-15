# 🚀 Автономное развертывание Stock Tracker

## 🎯 Цель: Полностью автономная работа 24/7 без зависимости от локального ПК

---

## 🏆 Рекомендуемое решение: Railway.app (БЕСПЛАТНО)

### ✅ Преимущества:
- ✨ **$5 бесплатно каждый месяц** (достаточно для вашего случая)
- 🚀 Простое развертывание из GitHub
- ⚡ Автоматические деплои при push
- 🔄 Встроенный cron scheduler
- 📊 Логи и мониторинг
- 🌍 Работает 24/7

### 📋 Пошаговая инструкция для Railway.app

#### Шаг 1: Подготовка проекта

1. Создайте файл `railway.json` в корне проекта:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python scheduler_service.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

2. Создайте файл `Procfile`:

```
worker: python scheduler_service.py
```

3. Создайте файл `runtime.txt`:

```
python-3.11
```

#### Шаг 2: Создание scheduler_service.py

Этот скрипт будет постоянно работать на Railway и запускать обновления по расписанию.

```python
#!/usr/bin/env python3
"""
Railway.app Scheduler Service
Постоянно работает и запускает обновления по расписанию
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Установка кодировки
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

script_dir = Path(__file__).parent
os.chdir(script_dir)
sys.path.insert(0, str(script_dir / 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.services.product_service import ProductService
from stock_tracker.core.models import SyncStatus
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config

logger = get_logger(__name__)


async def run_update():
    """Запускает обновление таблицы"""
    logger.info("=" * 60)
    logger.info(f"🚀 Начало обновления: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        config = get_config()
        
        # Инициализация клиентов
        logger.info("📊 Подключение к Google Sheets...")
        sheets_client = GoogleSheetsClient(
            credentials_path=config.google.service_account_key_path,
            sheet_id=config.google.sheet_id
        )
        
        operations = SheetsOperations(sheets_client)
        product_service = ProductService(api_key=config.wildberries.api_key)
        
        # Получение данных
        logger.info("🔄 Получение данных из Wildberries API...")
        stocks_data = await product_service.get_all_stocks_dual_api()
        orders_data = await product_service.get_orders()
        
        logger.info(f"✅ Получено: {len(stocks_data)} товаров, {len(orders_data)} заказов")
        
        # Обновление таблицы
        logger.info("📝 Обновление Google Sheets...")
        result = await operations.update_table_data(stocks_data, orders_data)
        
        logger.info("=" * 60)
        logger.info(f"✅ Обновление завершено успешно!")
        logger.info(f"📊 Статус: {result.status}")
        logger.info(f"📦 Обработано товаров: {result.products_processed}")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении: {e}", exc_info=True)
        return False


async def scheduler_loop():
    """Основной цикл scheduler"""
    logger.info("🚀 Scheduler Service запущен на Railway.app")
    logger.info("⏰ Расписание: каждый день в 00:01 МСК (21:01 UTC)")
    logger.info("=" * 60)
    
    # Запуск сразу при старте
    logger.info("🔄 Первоначальное обновление при запуске...")
    await run_update()
    
    while True:
        try:
            # Получаем текущее время UTC
            now = datetime.utcnow()
            
            # Целевое время: 21:01 UTC (00:01 МСК)
            target_hour = 21
            target_minute = 1
            
            # Вычисляем секунды до следующего запуска
            current_seconds = now.hour * 3600 + now.minute * 60 + now.second
            target_seconds = target_hour * 3600 + target_minute * 60
            
            if current_seconds < target_seconds:
                # Сегодня еще не было запуска
                seconds_until_next = target_seconds - current_seconds
            else:
                # Запуск был сегодня, ждем завтра
                seconds_until_next = (24 * 3600) - current_seconds + target_seconds
            
            hours = seconds_until_next // 3600
            minutes = (seconds_until_next % 3600) // 60
            
            logger.info(f"⏳ Следующее обновление через {hours}ч {minutes}м")
            
            # Ждем до следующего запуска
            await asyncio.sleep(seconds_until_next)
            
            # Запускаем обновление
            await run_update()
            
        except Exception as e:
            logger.error(f"❌ Ошибка в scheduler: {e}", exc_info=True)
            # Ждем 1 час перед повторной попыткой
            await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        logger.info("⏹️  Scheduler остановлен")
```

#### Шаг 3: Развертывание на Railway

1. **Зарегистрируйтесь на Railway**:
   - Перейдите на https://railway.app
   - Войдите через GitHub

2. **Создайте новый проект**:
   - New Project → Deploy from GitHub repo
   - Выберите репозиторий: `ameba7464/Stock-Tracker-`
   - Railway автоматически обнаружит Python проект

3. **Настройте переменные окружения**:
   
   В Railway Dashboard → Variables добавьте:
   
   ```
   WILDBERRIES_API_KEY=ваш_ключ_тут
   GOOGLE_SHEET_ID=ваш_sheet_id
   GOOGLE_SHEET_NAME=Stock Tracker
   LOG_LEVEL=INFO
   TZ=Europe/Moscow
   ```

4. **Настройте Google Service Account**:
   
   Содержимое `service-account.json` нужно добавить как переменную:
   ```
   GOOGLE_SERVICE_ACCOUNT={"type":"service_account","project_id":"...весь JSON..."}
   ```

5. **Обновите код для Railway**:
   
   В `src/stock_tracker/utils/config.py` добавьте поддержку JSON из переменной:
   
   ```python
   # Если GOOGLE_SERVICE_ACCOUNT передан как JSON строка
   if not self.service_account_key_path and os.getenv('GOOGLE_SERVICE_ACCOUNT'):
       import json
       import tempfile
       
       # Создаем временный файл с credentials
       service_account_json = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT'))
       temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
       json.dump(service_account_json, temp_file)
       temp_file.close()
       self.service_account_key_path = temp_file.name
   ```

6. **Деплой**:
   - Railway автоматически начнет деплой
   - Смотрите логи в реальном времени
   - После успешного деплоя сервис начнет работать 24/7

#### Шаг 4: Мониторинг

- **Логи**: Railway Dashboard → Deployments → View Logs
- **Метрики**: Вкладка Metrics покажет использование ресурсов
- **Алерты**: Настройте в Settings → Notifications

---

## 🥈 Альтернатива 2: Render.com (БЕСПЛАТНО)

### ✅ Преимущества:
- 💰 Полностью бесплатный план
- 🔄 Автоматические деплои из GitHub
- ⏰ Cron Jobs (встроенная поддержка)

### 📋 Инструкция для Render

1. **Создайте `render.yaml`**:

```yaml
services:
  - type: cron
    name: stock-tracker-updater
    env: python
    schedule: "1 21 * * *"  # 21:01 UTC = 00:01 МСК
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python update_table_fixed.py"
    envVars:
      - key: WILDBERRIES_API_KEY
        sync: false
      - key: GOOGLE_SHEET_ID
        sync: false
      - key: GOOGLE_SHEET_NAME
        value: Stock Tracker
      - key: GOOGLE_SERVICE_ACCOUNT
        sync: false
      - key: LOG_LEVEL
        value: INFO
      - key: TZ
        value: Europe/Moscow
```

2. **Зарегистрируйтесь на Render**:
   - https://render.com
   - Войдите через GitHub

3. **Создайте Cron Job**:
   - New → Cron Job
   - Connect repository
   - Render обнаружит `render.yaml`
   - Добавьте переменные окружения

4. **Деплой**:
   - Render автоматически запустит cron job
   - Работает полностью автономно

---

## 🥉 Альтернатива 3: Northflank (Более продвинутый)

### ✅ Преимущества:
- 🆓 $20 бесплатно каждый месяц
- 🚀 Профессиональная платформа
- 📊 Расширенный мониторинг
- ⚙️ Гибкие настройки cron

### 📋 Быстрая настройка:

1. Зарегистрируйтесь на https://northflank.com
2. Создайте новый сервис из GitHub
3. Выберите "Cron Job" тип
4. Установите расписание: `1 21 * * *`
5. Добавьте переменные окружения
6. Деплой!

---

## 🥉 Альтернатива 4: Google Cloud Run + Cloud Scheduler

### ✅ Преимущества:
- 🌐 Инфраструктура Google (высокая надежность)
- 💰 Бесплатный уровень (первые 2М вызовов)
- ⚡ Очень быстрый cold start
- 🔗 Легко интегрируется с Google Sheets

### 📋 Настройка:

```bash
# 1. Установите gcloud CLI
# 2. Аутентификация
gcloud auth login

# 3. Создайте Dockerfile
cat > Dockerfile << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "update_table_fixed.py"]
EOF

# 4. Деплой на Cloud Run
gcloud run deploy stock-tracker \
  --source . \
  --platform managed \
  --region europe-west1 \
  --no-allow-unauthenticated

# 5. Создайте Cloud Scheduler job
gcloud scheduler jobs create http stock-tracker-daily \
  --schedule="1 21 * * *" \
  --uri="https://stock-tracker-xxx.run.app" \
  --http-method=POST \
  --oidc-service-account-email=your-service-account@project.iam.gserviceaccount.com
```

---

## 📊 Сравнение решений

| Платформа | Бесплатный лимит | Сложность | Надежность | Рекомендация |
|-----------|------------------|-----------|------------|--------------|
| **Railway** | $5/месяц | ⭐⭐ Легко | ⭐⭐⭐⭐⭐ | 🏆 **ЛУЧШИЙ** |
| **Render** | Полностью бесплатно | ⭐ Очень легко | ⭐⭐⭐⭐ | 🥈 Отлично |
| **Northflank** | $20/месяц | ⭐⭐⭐ Средне | ⭐⭐⭐⭐⭐ | Для опытных |
| **GCP Cloud Run** | 2М вызовов | ⭐⭐⭐⭐ Сложно | ⭐⭐⭐⭐⭐ | Максимальная надежность |

---

## 🚀 Быстрый старт (Railway - рекомендуется)

### За 5 минут:

1. **Создайте файлы**:
   ```bash
   # В корне вашего репозитория
   touch railway.json Procfile scheduler_service.py
   ```

2. **Скопируйте содержимое из инструкций выше**

3. **Коммит и push**:
   ```bash
   git add railway.json Procfile scheduler_service.py
   git commit -m "feat: add Railway.app deployment config"
   git push origin main
   ```

4. **Зайдите на Railway.app**:
   - Войдите через GitHub
   - New Project → Deploy from GitHub
   - Выберите ваш репозиторий
   - Добавьте переменные окружения
   - Deploy!

5. **Готово!** 🎉
   - Проверьте логи
   - Сервис работает 24/7
   - Обновления каждый день в 00:01 МСК

---

## 🛠️ Подготовка проекта к деплою

### Обновите config.py для работы с переменными окружения:

```python
# В src/stock_tracker/utils/config.py
import os
import json
import tempfile

class GoogleConfig:
    def __init__(self):
        # Поддержка JSON из переменной окружения
        if os.getenv('GOOGLE_SERVICE_ACCOUNT'):
            service_account_json = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT'))
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
            json.dump(service_account_json, temp_file)
            temp_file.close()
            self.service_account_key_path = temp_file.name
        else:
            self.service_account_key_path = os.getenv(
                'GOOGLE_SERVICE_ACCOUNT_KEY_PATH',
                './config/service-account.json'
            )
        
        self.sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
        self.sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Stock Tracker')
```

---

## 🎯 Итоговая рекомендация

**Используйте Railway.app!**

### Почему:
- ✅ Простая настройка (5 минут)
- ✅ $5 бесплатно каждый месяц (хватит с запасом)
- ✅ Автоматический деплой из GitHub
- ✅ Работает 24/7 без вашего ПК
- ✅ Отличные логи и мониторинг
- ✅ Не нужно настраивать инфраструктуру

### Ваш результат:
- 🔄 Таблица обновляется автоматически каждый день в 00:01
- 📊 Полная автономность - не зависит от вашего ПК
- 🚀 Надежно работает даже если GitHub Actions глючит
- 💰 Бесплатно для вашего случая использования

---

**Следующий шаг**: Создайте необходимые файлы и задеплойте на Railway! 🚀
