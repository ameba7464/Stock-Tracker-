# 📊 Мониторинг Stock Tracker - Быстрый старт

## ⚡ Запуск за 5 минут

### 1. Настройте .env файл

```bash
# Добавьте в Stock-Tracker/.env:

# Telegram Bot для алертов
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALERT_CHAT_ID=your_chat_id

# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_password
```

### 2. Получите Telegram настройки

**Можно использовать СУЩЕСТВУЮЩИЙ бот!** (из main.py)

```bash
# Вариант 1: Используйте существующий бот (РЕКОМЕНДУЕТСЯ)
TELEGRAM_BOT_TOKEN=7535946244:AAH1EfK5cbUs6tIq3jf3XZDBhgZeq4qHTwE

# Вариант 2: Создайте новый бот (если нужен отдельный)
# 1. Telegram → @BotFather → /newbot
# 2. Скопируйте токен

# Chat ID (ваш личный ID для получения алертов):
# 1. Telegram → @userinfobot → /start
# 2. Скопируйте ваш ID
TELEGRAM_ALERT_CHAT_ID=123456789  # ← ТОЛЬКО для вас (админа)
```

💡 **Один бот может:**
- ✅ Отправлять алерты мониторинга **ТОЛЬКО вам** (на ваш CHAT_ID)
- ✅ Работать как интерактивный бот для всех пользователей
- ✅ Отправлять backup notifications

⚠️ **Важно:** Алерты идут **ТОЛЬКО на указанный CHAT_ID** (ваш личный), НЕ всем пользователям бота!

### 3. Запустите мониторинг

```bash
cd Stock-Tracker

# Запуск всех сервисов
docker-compose up -d

# Проверка статусов
docker-compose ps

# Просмотр логов
docker-compose logs -f prometheus grafana alertmanager
```

### 4. Откройте интерфейсы

| Сервис | URL | Credentials |
|--------|-----|-------------|
| Grafana | http://localhost:3000 | admin / ваш пароль |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| API Metrics | http://localhost:8000/metrics | - |
| Flower (Celery) | http://localhost:5555 | - |

---

## 🎯 Доступные дашборды

### Overview Dashboard
- API Status & Health
- Request Rate & Latency
- CPU & Memory Usage
- Celery Tasks
- Error Rates

### Business Metrics Dashboard
- Products Tracked
- Sync Operations (WB/Ozon)
- API Errors
- Google Sheets Operations
- Sync Performance

---

## 🚨 Основные алерты

| Alert | Порог | Критичность |
|-------|-------|-------------|
| APIDown | API недоступен >1 мин | 🚨 Critical |
| PostgreSQLDown | БД недоступна >1 мин | 🚨 Critical |
| HighErrorRate | >5% ошибок 5xx | 🚨 Critical |
| HighLatency | p95 >2 сек | ⚠️ Warning |
| HighCPUUsage | >80% >5 мин | ⚠️ Warning |
| HighMemoryUsage | >85% >5 мин | ⚠️ Warning |
| CeleryQueueBacklog | >100 задач | ⚠️ Warning |

---

## 📊 Полезные PromQL запросы

### Производительность API
```promql
# Request rate
rate(http_requests_total[5m])

# Latency (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

### Celery
```promql
# Tasks per second
rate(celery_tasks_total[5m])

# Queue length
sum(celery_queue_length) by (queue_name)

# Task duration (p95)
histogram_quantile(0.95, rate(celery_task_duration_seconds_bucket[5m]))
```

### Система
```promql
# CPU usage
system_cpu_usage_percent

# Memory usage %
(system_memory_usage_bytes / (system_memory_usage_bytes + system_memory_available_bytes)) * 100

# Disk usage
system_disk_usage_percent
```

---

## 🔧 Быстрые команды

### Управление сервисами
```bash
# Остановить мониторинг
docker-compose stop prometheus grafana alertmanager

# Перезапустить
docker-compose restart prometheus grafana alertmanager

# Логи
docker-compose logs -f [service_name]

# Статус
docker-compose ps
```

### Тестирование алертов
```bash
# Остановить API для теста
docker-compose stop api
# Через 1 минуту придет алерт

# Запустить обратно
docker-compose start api
# Придет resolved notification
```

### Проверка метрик
```bash
# API metrics
curl http://localhost:8000/metrics

# Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=up'
```

---

## 🐛 Устранение проблем

### Grafana не показывает данные
```bash
# 1. Проверьте Prometheus
curl http://localhost:9090/-/healthy

# 2. Проверьте data source в Grafana
# Configuration → Data Sources → Prometheus

# 3. Перезапустите
docker-compose restart grafana prometheus
```

### Нет алертов в Telegram
```bash
# 1. Проверьте переменные
docker-compose exec alertmanager env | grep TELEGRAM

# 2. Тест бота
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_ALERT_CHAT_ID}" \
  -d "text=Test"

# 3. Проверьте логи
docker-compose logs alertmanager

# 4. Перезапустите
docker-compose restart alertmanager
```

### Высокое использование памяти
```bash
# Уменьшите retention в docker-compose.yml
--storage.tsdb.retention.time=15d  # было 30d

# Перезапустите Prometheus
docker-compose restart prometheus
```

---

## 📚 Полная документация

См. [MONITORING_GUIDE.md](MONITORING_GUIDE.md) для:
- Детальное описание архитектуры
- Все alert rules с объяснениями
- Создание кастомных метрик
- Best practices
- Troubleshooting guide

---

## ✅ Checklist первого запуска

- [ ] Настроены переменные окружения (TELEGRAM_BOT_TOKEN, TELEGRAM_ALERT_CHAT_ID)
- [ ] Запущены все сервисы (`docker-compose up -d`)
- [ ] Grafana доступна (http://localhost:3000)
- [ ] Prometheus собирает метрики (проверить /targets)
- [ ] Дашборды отображают данные
- [ ] Протестированы алерты (остановить API)
- [ ] Получено тестовое уведомление в Telegram
- [ ] Настроен пароль Grafana

---

**Готово! Ваша система мониторинга настроена.**

Telegram для вопросов: @Enotiz
