# 🚀 Деплой Telegram бота в Yandex Cloud

## 📋 Оглавление
1. [Подготовка](#подготовка)
2. [Создание Container Registry](#создание-container-registry)
3. [Сборка и загрузка Docker образа](#сборка-и-загрузка-docker-образа)
4. [Создание виртуальной машины](#создание-виртуальной-машины)
5. [Запуск бота](#запуск-бота)
6. [Мониторинг и логи](#мониторинг-и-логи)

---

## ✅ Подготовка

### 1. Установите Yandex Cloud CLI

```bash
# Windows (PowerShell)
iex (New-Object System.Net.WebClient).DownloadString('https://storage.yandexcloud.net/yandexcloud-yc/install.ps1')

# Linux/macOS
curl https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash
```

### 2. Инициализируйте CLI

```bash
yc init
```

Следуйте инструкциям для входа и выбора каталога.

### 3. Проверьте конфигурацию

```bash
yc config list
```

---

## 🐳 Создание Container Registry

### 1. Создайте реестр

```bash
yc container registry create --name stock-tracker-registry
```

### 2. Получите ID реестра

```bash
yc container registry list
```

Сохраните `REGISTRY_ID` из вывода.

### 3. Настройте Docker для работы с реестром

```bash
# Получите токен
yc iam create-token

# Авторизуйтесь в Docker
docker login cr.yandex/<REGISTRY_ID> \
  --username json_key \
  --password-stdin < key.json
```

Или используйте более простой способ:

```bash
yc container registry configure-docker
```

---

## 📦 Сборка и загрузка Docker образа

### 1. Перейдите в директорию бота

```bash
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\telegram-bot"
```

### 2. Убедитесь, что все файлы на месте

Проверьте наличие:
- ✅ `credentials.json` (Service Account)
- ✅ `token.json` (OAuth токен)
- ✅ `.env` (переменные окружения)
- ✅ `Dockerfile`
- ✅ `requirements.txt`

### 3. Соберите Docker образ

```bash
docker build -t cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest .
```

Замените `<REGISTRY_ID>` на ваш ID реестра.

### 4. Загрузите образ в реестр

```bash
docker push cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest
```

---

## 🖥️ Создание виртуальной машины

### Вариант 1: Через веб-интерфейс

1. Откройте [Yandex Cloud Console](https://console.cloud.yandex.ru/)
2. Перейдите в **Compute Cloud** → **Виртуальные машины**
3. Нажмите **Создать ВМ**
4. Настройте параметры:
   - **Имя**: `stock-tracker-bot-vm`
   - **Зона доступности**: `ru-central1-a`
   - **Платформа**: Intel Ice Lake
   - **vCPU**: 2
   - **RAM**: 2 ГБ
   - **Прерываемая**: Нет (для 24/7 работы)
   - **Образ**: Container Optimized Image
5. В разделе **Docker container settings**:
   - **Docker image**: `cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest`
   - **Environment variables**: (см. ниже)
6. Создайте ВМ

### Вариант 2: Через CLI

```bash
yc compute instance create-with-container \
  --name stock-tracker-bot-vm \
  --zone ru-central1-a \
  --platform standard-v3 \
  --cores 2 \
  --memory 2GB \
  --create-boot-disk size=30GB \
  --network-interface subnet-name=default-ru-central1-a,nat-ip-version=ipv4 \
  --container-image cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest \
  --container-env-file .env \
  --container-restart-policy always \
  --service-account-name bot-service-account
```

### Environment Variables (.env)

Убедитесь, что в `.env` файле присутствуют:

```env
# Telegram Bot
BOT_TOKEN=8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms

# Database
DATABASE_URL=sqlite+aiosqlite:///./database.db

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA

# Logging
LOG_LEVEL=INFO

# Timezone
TZ=Europe/Moscow
```

---

## ▶️ Запуск бота

### Через веб-интерфейс

Бот запустится автоматически после создания ВМ с Docker контейнером.

### Через CLI - подключение к ВМ

```bash
# Получите IP адрес ВМ
yc compute instance get stock-tracker-bot-vm

# Подключитесь по SSH
ssh yc-user@<EXTERNAL_IP>

# Проверьте статус контейнера
docker ps

# Просмотрите логи
docker logs -f <CONTAINER_ID>
```

---

## 📊 Мониторинг и логи

### Просмотр логов бота

```bash
# Подключитесь к ВМ
ssh yc-user@<EXTERNAL_IP>

# Логи контейнера
docker logs -f $(docker ps -q --filter ancestor=cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest)

# Логи внутри контейнера
docker exec -it <CONTAINER_ID> cat logs/bot.log
docker exec -it <CONTAINER_ID> tail -f logs/bot.log
```

### Проверка автообновления

Автообновление настроено на **00:01 МСК** каждый день.

Проверьте в логах:

```
✅ Scheduler started successfully
⏰ Next update scheduled for: 00:01 MSK daily
📅 Next run time: 2025-11-27 00:01:00+03:00
```

### Ручное обновление всех таблиц

Для тестирования можно запустить обновление вручную через бота или подключившись к контейнеру:

```bash
docker exec -it <CONTAINER_ID> python -c "
from app.services.scheduler import auto_update_scheduler
import asyncio
asyncio.run(auto_update_scheduler.run_manual_update())
"
```

---

## 🔄 Обновление бота

Когда нужно обновить код:

### 1. Пересоберите образ

```bash
cd "c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\telegram-bot"
docker build -t cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest .
docker push cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest
```

### 2. Перезапустите контейнер на ВМ

```bash
ssh yc-user@<EXTERNAL_IP>
docker pull cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest
docker stop <CONTAINER_ID>
docker rm <CONTAINER_ID>
docker run -d --restart always cr.yandex/<REGISTRY_ID>/stock-tracker-bot:latest
```

Или просто перезапустите ВМ через консоль.

---

## 💰 Стоимость

**Примерная стоимость при 24/7 работе:**

- **ВМ** (2 vCPU, 2 GB RAM): ~500 ₽/месяц
- **Диск** (30 GB SSD): ~200 ₽/месяц
- **IP-адрес**: ~150 ₽/месяц
- **Container Registry**: ~100 ₽/месяц (за хранение образа)

**Итого: ~950 ₽/месяц**

💡 **Совет**: Используйте прерываемые ВМ для снижения стоимости на 50-70%

---

## 🛠️ Полезные команды

### Остановка ВМ

```bash
yc compute instance stop stock-tracker-bot-vm
```

### Запуск ВМ

```bash
yc compute instance start stock-tracker-bot-vm
```

### Удаление ВМ

```bash
yc compute instance delete stock-tracker-bot-vm
```

### Проверка статуса

```bash
yc compute instance get stock-tracker-bot-vm
```

---

## ✅ Проверка работы

1. **Отправьте `/start` боту в Telegram**
2. **Добавьте WB API ключ**
3. **Нажмите "📊 Получить мою таблицу"**
4. **Проверьте, что таблица создана и заполнена**
5. **Дождитесь 00:01 следующего дня** - таблица должна автоматически обновиться

Проверить в логах:

```
🔄 AUTOMATIC TABLE UPDATE STARTED
⏰ Time: 2025-11-27 00:01:00
📊 Found X users with configured tables
✅ Successfully updated: X/X
```

---

## ❓ Troubleshooting

### Бот не запускается

Проверьте логи:

```bash
docker logs <CONTAINER_ID>
```

### Таблицы не обновляются автоматически

1. Проверьте, что scheduler запущен в логах
2. Убедитесь, что timezone установлен в `Europe/Moscow`
3. Проверьте, что у пользователей есть `wb_api_key` и `google_sheet_id` в БД

### Ошибки Google Sheets API

Убедитесь, что файлы `credentials.json` и `token.json` скопированы в контейнер.

---

## 🎉 Готово!

Ваш бот теперь работает 24/7 в Yandex Cloud и автоматически обновляет таблицы пользователей каждый день в 00:01 МСК! 🚀
