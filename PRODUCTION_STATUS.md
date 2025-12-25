# 🌐 Production Status - Статус работы системы 24/7

> **Последнее обновление:** 25 декабря 2025 г.
> 
> **Статус:** ✅ Система работает в production режиме 24/7

---

## 📊 Текущее состояние

### ✅ Развернутые сервисы

#### 1. **Telegram Bot** (Stock Tracker Bot)
- 🟢 **Статус:** Работает 24/7 в Yandex Cloud
- 📍 **Платформа:** Yandex Cloud VM
- 🐳 **Контейнер:** Docker с `--restart unless-stopped`
- 📦 **Реестр образов:** Yandex Container Registry
- 🔄 **Автодеплой:** GitHub Actions при push в `main`
- 📅 **Планировщик:** Автообновление таблиц ежедневно в 00:01 MSK
- 💾 **База данных:** SQLite (локальная) / PostgreSQL (опционально)
- 🔑 **Credentials:** Смонтированы из `/home/yc-user/credentials.json`

**Workflow:** [.github/workflows/deploy-bot.yml](.github/workflows/deploy-bot.yml)

#### 2. **FastAPI Application** (Stock Tracker API)
- 🟢 **Статус:** Готово к запуску через Docker Compose
- 🐳 **Сервисы:**
  - `api` - FastAPI app (uvicorn с 4 workers)
  - `worker` - Celery worker (4 concurrency)
  - `beat` - Celery beat scheduler
  - `flower` - Celery monitoring UI
  - `postgres` - PostgreSQL 15
  - `redis` - Redis 7
- 🔄 **Auto-restart:** Все сервисы с `restart: unless-stopped`
- 🏥 **Health checks:** Настроены для всех критических сервисов

---

## 🔧 Конфигурация автоперезапуска

### Docker Compose Services

Все сервисы настроены на автоматический перезапуск:

```yaml
restart: unless-stopped  # ✅ Применено ко всем 15 сервисам
```

**Список сервисов с auto-restart:**
1. ✅ `postgres` - База данных
2. ✅ `redis` - Кеш и брокер сообщений
3. ✅ `api` - FastAPI приложение
4. ✅ `worker` - Celery worker (sync, default queues)
5. ✅ `beat` - Celery beat scheduler
6. ✅ `flower` - Celery monitoring
7. ✅ `celery-exporter` - Prometheus metrics
8. ✅ `prometheus` - Metrics collection
9. ✅ `alertmanager` - Alert notifications
10. ✅ `grafana` - Dashboards
11. ✅ `postgres-exporter` - PostgreSQL metrics
12. ✅ `redis-exporter` - Redis metrics
13. ✅ `node-exporter` - System metrics
14. ✅ `cadvisor` - Container metrics
15. ✅ `nginx` - Reverse proxy

---

## 🚀 CI/CD Pipeline

### GitHub Actions Workflows

#### ✅ Активные workflows (Production)

1. **Deploy Telegram Bot** ([deploy-bot.yml](.github/workflows/deploy-bot.yml))
   - ✅ Триггер: Push в `main` или изменения в `telegram-bot/**`
   - ✅ Билд Docker образа → Push в Yandex Container Registry
   - ✅ SSH деплой на VM с автоперезапуском контейнера
   - ✅ Проверка логов после деплоя

#### ⚠️ Отключенные workflows (Не используются)

2. **Monitoring Health Check** ([monitoring-health-check.yml](.github/workflows/monitoring-health-check.yml))
   - ⚠️ **Статус:** Отключен (закомментирован `schedule`)
   - 📝 **Причина:** Локальные сервисы мониторинга недоступны из GitHub Actions
   - 🔄 **Запуск:** Только вручную через `workflow_dispatch`
   - 📌 **Изменено:** 25 декабря 2025 г.

3. **Validate Monitoring Config** ([validate-monitoring.yml](.github/workflows/validate-monitoring.yml))
   - ✅ **Статус:** Активен (проверка конфигурации)
   - 🎯 **Назначение:** Валидация файлов мониторинга при изменениях

---

## 🛡️ Мониторинг системы 24/7

### Production Monitoring (Docker)

Если мониторинг развернут, работают следующие компоненты:

- **Prometheus** (порт 9090) - Сбор метрик каждые 15 секунд
- **Grafana** (порт 3000) - 2 дашборда (Overview, Business Metrics)
- **Alertmanager** (порт 9093) - Уведомления в Telegram
- **Flower** (порт 5555) - Мониторинг Celery задач

**Документация:**
- 📚 [Быстрый старт мониторинга](MONITORING_QUICKSTART.md)
- 🔐 [Настройка Docker Secrets](monitoring/DOCKER_SECRETS_SETUP.md)
- 📖 [Полное руководство](docs/MONITORING_GUIDE.md)

### Health Checks

```yaml
# API Health Check
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s

# PostgreSQL Health Check
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U stock_tracker"]
  interval: 10s
  timeout: 5s
  retries: 5

# Redis Health Check
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## 📋 Checklist для production

### ✅ Telegram Bot

- [x] Docker контейнер развернут в Yandex Cloud
- [x] Автоперезапуск настроен (`--restart unless-stopped`)
- [x] GitHub Actions автодеплой работает
- [x] Credentials смонтированы из VM
- [x] База данных инициализирована
- [x] Планировщик автообновления настроен (00:01 MSK)
- [x] Логи доступны через `docker logs`

### ✅ FastAPI Application (готово к запуску)

- [x] docker-compose.yml настроен
- [x] Все сервисы с `restart: unless-stopped`
- [x] Health checks настроены
- [x] Environment variables подготовлены
- [x] Volumes для персистентности данных
- [x] Networking между сервисами

### ⚠️ Мониторинг (опционально)

- [x] Конфигурационные файлы готовы
- [x] Docker Compose сервисы описаны
- [ ] Мониторинг запущен (по необходимости)
- [x] GitHub Actions health check отключен

---

## 🔄 Процедура обновления

### Автоматическое обновление (GitHub Actions)

1. **Telegram Bot:**
   ```bash
   git add .
   git commit -m "Update telegram bot"
   git push origin main
   # GitHub Actions автоматически задеплоит
   ```

2. **FastAPI App:**
   ```bash
   # На сервере
   cd /path/to/Stock-Tracker
   git pull origin main
   docker-compose pull
   docker-compose up -d --build
   ```

### Ручное обновление

```bash
# Остановка сервисов
docker-compose down

# Обновление кода
git pull origin main

# Пересборка и запуск
docker-compose up -d --build

# Проверка статуса
docker-compose ps
docker-compose logs -f api worker
```

---

## 📊 Метрики и логи

### Просмотр логов

```bash
# Telegram Bot (Yandex Cloud)
sudo docker logs -f stock-tracker-bot
sudo docker logs --tail 100 stock-tracker-bot

# FastAPI (Docker Compose)
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs --tail 100 api worker beat

# Конкретный сервис
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Проверка статуса

```bash
# Все сервисы
docker-compose ps

# Health check API
curl http://localhost:8000/api/v1/health/

# Prometheus metrics
curl http://localhost:8000/metrics
curl http://localhost:9090/-/healthy

# Grafana
curl http://localhost:3000/api/health
```

---

## 🆘 Troubleshooting

### Проблемы с автоперезапуском

```bash
# Проверить политику restart
docker inspect <container_name> | grep -A 3 RestartPolicy

# Принудительный рестарт
docker restart <container_name>

# Если контейнер постоянно падает
docker-compose logs --tail 50 <service_name>
```

### Telegram Bot не отвечает на команды

**Проблема:** Бот присылает алерты, но не отвечает на /start и другие команды.

**Причина:** Два экземпляра бота работают одновременно (conflict).

**Решение:**
1. Убедитесь, что локально бот НЕ запущен
2. Проверьте статус: `python telegram-bot/check_bot_status.py`
3. Остановите лишние процессы

📚 **Подробнее:** [telegram-bot/TROUBLESHOOTING_BOT_NOT_RESPONDING.md](telegram-bot/TROUBLESHOOTING_BOT_NOT_RESPONDING.md)

**Правило:** Никогда не запускайте локально бота с production токеном!

### Telegram Bot не отвечает

```bash
# Проверить статус на VM
sudo docker ps | grep stock-tracker-bot

# Перезапустить
sudo docker restart stock-tracker-bot

# Проверить логи
sudo docker logs --tail 100 stock-tracker-bot

# Редеплой через GitHub Actions
# 1. Зайти в GitHub Actions
# 2. Выбрать "Deploy Telegram Bot"
# 3. Нажать "Run workflow"
```

### FastAPI не запускается

```bash
# Проверить зависимости
docker-compose ps

# Проверить логи
docker-compose logs api worker

# Пересоздать контейнеры
docker-compose down -v
docker-compose up -d
```

---

## 📚 Документация

- 📖 [Production Deployment Guide](PRODUCTION_DEPLOYMENT_GUIDE.md)
- 🚀 [Быстрый старт (Docker)](DOCKER_INSTALLATION_GUIDE.md)
- 📊 [Мониторинг - Быстрый старт](MONITORING_QUICKSTART.md)
- 🤖 [Telegram Bot - Yandex Cloud](telegram-bot/YANDEX_CLOUD_DEPLOY.md)
- 🔄 [CI/CD Deployment](docs/CI_CD_DEPLOYMENT_GUIDE.md)
- 📝 [Полная документация](docs/FULL_PROJECT_DOCUMENTATION.md)

---

## 📞 Контакты и поддержка

**Статус системы:** ✅ Production-ready, работает 24/7

**Последняя проверка:** 25 декабря 2025 г. 16:37 MSK

---

*Этот документ автоматически обновляется при изменении конфигурации production системы.*
