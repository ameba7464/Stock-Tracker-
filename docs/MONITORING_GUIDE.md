# 📊 Руководство по мониторингу Stock Tracker

## Оглавление
- [Архитектура мониторинга](#архитектура-мониторинга)
- [Быстрый старт](#быстрый-старт)
- [Компоненты системы](#компоненты-системы)
- [Настройка уведомлений в Telegram](#настройка-уведомлений-в-telegram)
- [Дашборды Grafana](#дашборды-grafana)
- [Alert Rules](#alert-rules)
- [Метрики приложения](#метрики-приложения)
- [Устранение неполадок](#устранение-неполадок)
- [Best Practices](#best-practices)

---

## 🏗️ Архитектура мониторинга

```
┌──────────────────────────────────────────────────────────────┐
│                     Stock Tracker                             │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐     │
│  │   API   │  │  Worker │  │   Beat   │  │  Postgres │     │
│  └────┬────┘  └────┬────┘  └────┬─────┘  └─────┬─────┘     │
│       │            │             │              │            │
│       └────────────┴─────────────┴──────────────┘            │
│                          │                                    │
└──────────────────────────┼────────────────────────────────────┘
                           │ /metrics endpoint
                           ↓
                    ┌──────────────┐
                    │  Prometheus  │ ← scrapes metrics
                    │  (Port 9090) │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                ↓
   ┌─────────────┐  ┌──────────┐   ┌──────────────┐
   │  Grafana    │  │ Postgres │   │    Redis     │
   │ (Port 3000) │  │ Exporter │   │   Exporter   │
   └─────────────┘  └──────────┘   └──────────────┘
          │
          │ alerts
          ↓
   ┌──────────────┐
   │ Alertmanager │
   │  (Port 9093) │
   └──────┬───────┘
          │
          ↓
   ┌──────────────┐
   │   Telegram   │ → @Enotiz
   └──────────────┘
```

---

## 🚀 Быстрый старт

### 1. Настройте переменные окружения

Добавьте в ваш `.env` файл:

```bash
# Telegram Bot для алертов
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALERT_CHAT_ID=your_telegram_user_id  # ⚠️ ТОЛЬКО ваш личный ID (админа), НЕ broadcast всем пользователям

# Grafana Admin
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password

# Sentry (опционально)
SENTRY_DSN=your_sentry_dsn
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 2. Получите Telegram Bot Token

1. Откройте Telegram и найдите [@BotFather](https://t.me/botfather)
2. Создайте нового бота: `/newbot`
3. Следуйте инструкциям и скопируйте токен
4. Получите ваш Chat ID:
   - Найдите [@userinfobot](https://t.me/userinfobot)
   - Отправьте `/start`
   - Скопируйте ваш ID

### 3. Запустите систему мониторинга

```bash
# Запуск всех сервисов включая мониторинг
docker-compose up -d

# Проверьте статус
docker-compose ps

# Посмотрите логи
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager
```

### 4. Доступ к интерфейсам

- **Grafana**: http://localhost:3000
  - Логин: `admin` (или из GRAFANA_USER)
  - Пароль: из GRAFANA_PASSWORD
  
- **Prometheus**: http://localhost:9090
  - Query: `up{job="stock-tracker-api"}`
  
- **Alertmanager**: http://localhost:9093
  - Просмотр активных алертов

- **Flower (Celery)**: http://localhost:5555
  - Мониторинг Celery tasks

---

## 🔧 Компоненты системы

### 1. **Prometheus** (Port 9090)
Система сбора и хранения метрик.

**Основные функции:**
- Собирает метрики каждые 15 секунд
- Хранит данные 30 дней
- Оценивает alert rules

**Конфигурация:** `monitoring/prometheus.yml`

**Полезные запросы:**
```promql
# API Request Rate
rate(http_requests_total[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Celery queue length
sum(celery_queue_length) by (queue_name)
```

### 2. **Grafana** (Port 3000)
Визуализация метрик и создание дашбордов.

**Доступные дашборды:**
1. **Stock Tracker - Overview** (UID: `stock-tracker-overview`)
   - Общее состояние системы
   - HTTP метрики
   - Latency percentiles
   - CPU/Memory usage
   - Celery tasks

2. **Stock Tracker - Business Metrics** (UID: `stock-tracker-business`)
   - Количество отслеживаемых продуктов
   - Sync operations (Wildberries/Ozon)
   - API errors
   - Google Sheets operations

**Автоматическая настройка:**
- Prometheus источник данных настроен автоматически
- Дашборды загружаются при старте

### 3. **Alertmanager** (Port 9093)
Управление и маршрутизация алертов.

**Уровни важности:**
- 🚨 **Critical** - немедленное уведомление (5 сек группировка)
- ⚠️ **Warning** - менее срочные (30 сек группировка)
- ℹ️ **Info** - ежедневный digest (5 мин группировка)

**Конфигурация:** `monitoring/alertmanager.yml`

### 4. **Exporters**

#### PostgreSQL Exporter (Port 9187)
Метрики базы данных:
- Количество соединений
- Размер базы данных
- Query performance
- Transaction statistics

#### Redis Exporter (Port 9121)
Метрики кэша:
- Memory usage
- Connected clients
- Command statistics
- Keyspace info

#### Node Exporter (Port 9100)
Системные метрики:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

#### cAdvisor (Port 8080)
Метрики контейнеров:
- Container CPU/Memory
- Network I/O
- Disk I/O
- Container lifecycle

---

## 📱 Настройка уведомлений в Telegram

### Создание и настройка бота

**💡 Можно использовать существующий бот!**

Если у вас уже есть Telegram бот (например, в `main.py`), используйте его токен:
```bash
TELEGRAM_BOT_TOKEN=7535946244:AAH1EfK5cbUs6tIq3jf3XZDBhgZeq4qHTwE
```

Один бот может:
- ✅ Отправлять алерты мониторинга
- ✅ Быть интерактивным ботом для пользователей
- ✅ Отправлять backup уведомления
- ✅ Любые другие уведомления

**Или создайте новый бот (опционально):**

1. **Создайте отдельный бот для алертов:**
   ```
   Telegram → @BotFather → /newbot
   ```

2. **Получите Chat ID:**
   ```
   Telegram → @userinfobot → /start
   ```

3. **Добавьте в .env:**
   ```bash
   TELEGRAM_BOT_TOKEN=7535946244:AAH1EfK5cbUs6tIq3jf3XZDBhgZeq4qHTwE
   TELEGRAM_ALERT_CHAT_ID=your_chat_id  # ⚠️ Это должен быть ВАШ личный ID (админа)
   ```

   **❗ Важно:** Алерты приходят ТОЛЬКО на указанный `TELEGRAM_ALERT_CHAT_ID`, это НЕ broadcast всем пользователям бота!

4. **Перезапустите Alertmanager:**
   ```bash
   docker-compose restart alertmanager
   ```

### Формат уведомлений

#### Critical Alert 🚨
```
🚨 CRITICAL ALERT 🚨

⚠️ APIDown
Service: api
Status: FIRING

Summary: Stock Tracker API is down
Description: API instance api:8000 has been down for more than 1 minute.
🔧 Runbook: Check docker logs: docker logs stock-tracker-api
⏰ Started: 2025-12-11 15:30:45

🔗 Dashboard: http://localhost:3000
```

#### Warning Alert ⚠️
```
⚠️ WARNING

HighLatency
Service: api

Summary: High API latency detected
Description: 95th percentile latency is 2.5s (threshold: 2s)
Started: 2025-12-11 15:35:22
```

### Тестирование алертов

```bash
# Остановите API для теста
docker-compose stop api

# Через 1 минуту придет алерт в Telegram

# Запустите обратно
docker-compose start api

# Придет уведомление о resolved
```

---

## 📊 Дашборды Grafana

### Overview Dashboard

**Панели:**
1. **API Status** - текущий статус API (up/down)
2. **Request Rate by Status** - количество запросов по статусам (200, 400, 500)
3. **API Latency Percentiles** - p50, p95, p99 задержки
4. **CPU Usage** - загрузка CPU (gauge)
5. **Memory Usage** - использование памяти (gauge)
6. **Celery Task Rate** - скорость обработки задач
7. **Celery Queue Length** - длина очередей

### Business Metrics Dashboard

**Панели:**
1. **Total Products Tracked** - общее количество товаров
2. **Sync Operations Rate** - частота синхронизаций
3. **Sync Operation Duration** - длительность синхронизаций (p95)
4. **External API Errors** - ошибки WB/Ozon API
5. **Sync Failure Rate** - процент неудачных синхронизаций
6. **Google Sheets Operations** - операции с таблицами

### Создание собственных дашбордов

```bash
# В Grafana UI:
1. Dashboard → New → Add visualization
2. Выберите Prometheus data source
3. Введите PromQL запрос
4. Настройте визуализацию
5. Save dashboard
```

**Примеры запросов:**
```promql
# Топ-5 медленных endpoints
topk(5, histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
))

# Частота ошибок по tenant
sum(rate(http_requests_total{status=~"5.."}[5m])) by (tenant_id)

# Database connections по времени
pg_stat_database_numbackends{datname="stock_tracker"}
```

---

## 🚨 Alert Rules

### Critical Alerts

#### APIDown
**Условие:** API недоступен более 1 минуты
```promql
up{job="stock-tracker-api"} == 0
```
**Действия:**
1. Проверьте логи: `docker logs stock-tracker-api`
2. Проверьте health: `curl http://localhost:8000/api/v1/health/`
3. Перезапустите: `docker-compose restart api`

#### PostgreSQLDown
**Условие:** База данных недоступна более 1 минуты
```promql
up{job="postgresql"} == 0
```
**Действия:**
1. Проверьте контейнер: `docker ps | grep postgres`
2. Проверьте логи: `docker logs stock-tracker-postgres`
3. Проверьте диск: `df -h`

#### HighErrorRate
**Условие:** >5% запросов возвращают 5xx ошибки
```promql
sum(rate(http_requests_total{status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total[5m])) > 0.05
```
**Действия:**
1. Проверьте логи приложения
2. Проверьте Sentry dashboard
3. Проверьте database connections
4. Проверьте external API status

### Warning Alerts

#### HighLatency
**Условие:** p95 latency > 2 секунд
```promql
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
) > 2
```
**Действия:**
1. Проверьте slow queries в PostgreSQL
2. Проверьте Redis connection
3. Проверьте CPU/Memory usage
4. Масштабируйте API workers

#### HighCPUUsage
**Условие:** CPU > 80% более 5 минут
```promql
system_cpu_usage_percent > 80
```
**Действия:**
1. Проверьте top processes
2. Проверьте Celery tasks
3. Рассмотрите horizontal scaling

#### CeleryQueueBacklog
**Условие:** >100 задач в очереди более 10 минут
```promql
sum(celery_queue_length) > 100
```
**Действия:**
1. Увеличьте количество workers
2. Проверьте медленные задачи
3. Проверьте database performance

---

## 📈 Метрики приложения

### HTTP Metrics

```python
from stock_tracker.monitoring import get_metrics

metrics = get_metrics()

# Record HTTP request
metrics.http_requests_total.labels(
    method="GET",
    endpoint="/api/v1/products",
    status=200
).inc()

# Record latency
metrics.http_request_duration_seconds.labels(
    method="GET",
    endpoint="/api/v1/products"
).observe(0.235)
```

### Database Metrics

```python
# Track DB query
with metrics.db_query_duration_seconds.labels(
    operation="select"
).time():
    # Your database query
    result = db.execute(query)

# Record error
metrics.db_errors_total.labels(
    error_type="connection_timeout"
).inc()
```

### Celery Metrics

```python
from celery import Task
from stock_tracker.monitoring import get_metrics

class MonitoredTask(Task):
    def __call__(self, *args, **kwargs):
        metrics = get_metrics()
        
        # Track task execution
        with metrics.celery_task_duration_seconds.labels(
            task_name=self.name
        ).time():
            try:
                result = self.run(*args, **kwargs)
                
                metrics.celery_tasks_total.labels(
                    task_name=self.name,
                    status="success"
                ).inc()
                
                return result
            except Exception as e:
                metrics.celery_tasks_total.labels(
                    task_name=self.name,
                    status="failure"
                ).inc()
                raise
```

### Business Metrics

```python
# Track products
metrics.products_total.labels(
    tenant_id=tenant.id
).set(product_count)

# Track sync operations
metrics.sync_operations_total.labels(
    platform="wildberries",
    status="success",
    tenant_id=tenant.id
).inc()

# Track sync duration
with metrics.sync_duration_seconds.labels(
    platform="wildberries",
    tenant_id=tenant.id
).time():
    # Sync operation
    sync_wildberries_data()
```

---

## 🔍 Устранение неполадок

### Prometheus не собирает метрики

**Симптомы:**
- Grafana показывает "No data"
- Prometheus targets показывают "Down"

**Решение:**
```bash
# 1. Проверьте targets в Prometheus
# http://localhost:9090/targets

# 2. Проверьте метрики API
curl http://localhost:8000/metrics

# 3. Проверьте сеть
docker network inspect stock-tracker-network

# 4. Проверьте логи
docker-compose logs prometheus
docker-compose logs api

# 5. Перезапустите
docker-compose restart prometheus api
```

### Alertmanager не отправляет уведомления

**Симптомы:**
- Алерты firing в Prometheus
- Нет уведомлений в Telegram

**Решение:**
```bash
# 1. Проверьте конфигурацию
docker-compose exec alertmanager \
  amtool config show

# 2. Проверьте статус алертов
# http://localhost:9093

# 3. Тест Telegram bot
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_ALERT_CHAT_ID}" \
  -d "text=Test message"

# 4. Проверьте переменные окружения
docker-compose exec alertmanager env | grep TELEGRAM

# 5. Проверьте логи
docker-compose logs alertmanager
```

### Grafana не показывает данные

**Симптомы:**
- Дашборды пустые
- "No data" на всех панелях

**Решение:**
```bash
# 1. Проверьте Prometheus data source
# Grafana → Configuration → Data Sources

# 2. Проверьте PromQL запросы
# Grafana → Explore → выберите Prometheus

# 3. Проверьте time range
# Убедитесь что выбран правильный временной диапазон

# 4. Проверьте Prometheus
curl http://localhost:9090/api/v1/query?query=up

# 5. Перезапустите
docker-compose restart grafana prometheus
```

### High Memory Usage

**Решение:**
```bash
# 1. Проверьте Prometheus retention
# Уменьшите в docker-compose.yml:
# --storage.tsdb.retention.time=15d

# 2. Очистите старые данные
docker-compose exec prometheus \
  rm -rf /prometheus/*

# 3. Ограничьте memory
# В docker-compose.yml добавьте:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

---

## 🏆 Best Practices

### 1. Метрики

✅ **DO:**
- Используйте низкую cardinality для labels
- Группируйте похожие метрики
- Документируйте кастомные метрики
- Используйте правильные типы (Counter, Gauge, Histogram)

❌ **DON'T:**
- Не используйте user_id как label (высокая cardinality)
- Не создавайте слишком много метрик
- Не используйте динамические label values

### 2. Алерты

✅ **DO:**
- Алертите на symptoms, не на causes
- Устанавливайте разумные thresholds
- Добавляйте runbooks в annotations
- Группируйте похожие алерты

❌ **DON'T:**
- Не создавайте алерты на флуктуации
- Не алертите на каждую метрику
- Не игнорируйте алерты

### 3. Дашборды

✅ **DO:**
- Создавайте роль-специфичные дашборды
- Используйте переменные для фильтрации
- Добавляйте описания к панелям
- Используйте подходящие визуализации

❌ **DON'T:**
- Не перегружайте дашборды
- Не дублируйте информацию
- Не используйте слишком короткие time ranges

### 4. Retention

- **Prometheus**: 30 дней (для детальных метрик)
- **Grafana**: бесконечно (только дашборды)
- **Logs**: 7 дней (для troubleshooting)

### 5. Security

```bash
# 1. Используйте strong passwords
GRAFANA_PASSWORD=$(openssl rand -base64 32)

# 2. Ограничьте доступ к портам
# Только localhost в production
ports:
  - "127.0.0.1:9090:9090"  # Prometheus
  - "127.0.0.1:3000:3000"  # Grafana

# 3. Используйте HTTPS в production
# Настройте reverse proxy (nginx)

# 4. Ограничьте Grafana permissions
GF_USERS_ALLOW_SIGN_UP=false
GF_AUTH_ANONYMOUS_ENABLED=false
```

### 6. Backup

```bash
# Backup Prometheus data
docker run --rm \
  -v stock-tracker_prometheus_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data

# Backup Grafana dashboards
curl -u admin:password \
  http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[].uid' | while read uid; do
    curl -u admin:password \
      "http://localhost:3000/api/dashboards/uid/$uid" > \
      "grafana-dashboard-$uid.json"
  done
```

---

## 📚 Дополнительные ресурсы

### Документация
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)

### Полезные ссылки
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)

### Community Dashboards
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- FastAPI: https://grafana.com/grafana/dashboards/19304
- PostgreSQL: https://grafana.com/grafana/dashboards/9628
- Redis: https://grafana.com/grafana/dashboards/11835

---

## 🎯 Следующие шаги

1. **Настройте Telegram бота** и протестируйте алерты
2. **Изучите дашборды** в Grafana
3. **Создайте кастомные метрики** для вашего бизнеса
4. **Настройте дополнительные алерты** под ваши SLA
5. **Интегрируйте Sentry** для error tracking
6. **Настройте log aggregation** (ELK Stack)

---

**Вопросы?** Telegram: @Enotiz
