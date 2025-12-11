# 🎉 Stock Tracker - Система мониторинга успешно установлена!

## ✅ Что было создано

### 1. Модули и код
- ✅ `src/stock_tracker/monitoring.py` - Prometheus метрики для FastAPI
- ✅ Интеграция метрик в существующее приложение
- ✅ Middleware для автоматического сбора HTTP метрик

### 2. Конфигурация мониторинга
- ✅ `monitoring/prometheus.yml` - конфигурация Prometheus
- ✅ `monitoring/alertmanager.yml` - уведомления в Telegram
- ✅ `monitoring/alerts/` - 20+ готовых alert rules
- ✅ `monitoring/grafana/` - provisioning и дашборды

### 3. Docker-compose
- ✅ Prometheus (сбор метрик)
- ✅ Alertmanager (алерты в Telegram)
- ✅ Grafana (визуализация)
- ✅ PostgreSQL Exporter
- ✅ Redis Exporter
- ✅ Node Exporter (системные метрики)
- ✅ cAdvisor (метрики контейнеров)

### 4. Дашборды Grafana
- ✅ Overview Dashboard - общее состояние системы
- ✅ Business Metrics Dashboard - бизнес-метрики

### 5. Документация
- ✅ `MONITORING_QUICKSTART.md` - быстрый старт (5 минут)
- ✅ `docs/MONITORING_GUIDE.md` - полное руководство (50+ страниц)
- ✅ `.env.example` - обновлен с переменными мониторинга

---

## 🚀 Следующие шаги для запуска

### Шаг 1: Настройте переменные окружения

```bash
cd Stock-Tracker

# Создайте .env если его нет
cp .env.example .env

# Отредактируйте .env и добавьте:
nano .env
```

Добавьте в `.env`:
```bash
# Telegram Bot для алертов
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ALERT_CHAT_ID=your_chat_id_here

# Grafana Admin
GRAFANA_USER=admin
GRAFANA_PASSWORD=your_secure_password
```

### Шаг 2: Получите Telegram настройки

#### Получить Bot Token:

**✅ РЕКОМЕНДУЕТСЯ: Используйте существующий бот!**
```bash
TELEGRAM_BOT_TOKEN=7535946244:AAH1EfK5cbUs6tIq3jf3XZDBhgZeq4qHTwE
```
Это ваш бот из `main.py` - он может отправлять и алерты, и работать как интерактивный бот одновременно.

**Или создайте новый бот (если нужен отдельный):**
1. Откройте Telegram
2. Найдите [@BotFather](https://t.me/botfather)
3. Отправьте `/newbot`
4. Следуйте инструкциям
5. Скопируйте токен в формате: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

#### Получить Chat ID (ВАШ личный ID администратора):
1. Откройте Telegram
2. Найдите [@userinfobot](https://t.me/userinfobot)
3. Отправьте `/start`
4. Скопируйте **ваш личный ID** (например: `123456789`)

⚠️ **ВАЖНО:** Это ваш **личный ID как администратора**.

**Кто получает алерты:**
- ✅ **ВЫ** (администратор) - на указанный `TELEGRAM_ALERT_CHAT_ID`
- ❌ **НЕ** обычные пользователи бота
- ❌ **НЕ** все подписчики бота

**Разделение функций:**
- 📊 **Алерты мониторинга** → Только админ (вы)
- 💬 **Интерактивный бот** → Все пользователи (отдельно)
- 💾 **Backup notifications** → Только админ (вы)

### Шаг 3: Запустите систему

```bash
# Запуск всех сервисов
docker-compose up -d

# Проверьте что все запустилось
docker-compose ps

# Должны увидеть:
# ✅ stock-tracker-api
# ✅ stock-tracker-postgres
# ✅ stock-tracker-redis
# ✅ stock-tracker-prometheus
# ✅ stock-tracker-grafana
# ✅ stock-tracker-alertmanager
# ✅ postgres-exporter
# ✅ redis-exporter
# ✅ node-exporter
# ✅ cadvisor
```

### Шаг 4: Проверьте доступность

Откройте в браузере:

1. **Grafana**: http://localhost:3000
   - Логин: `admin`
   - Пароль: из `.env`
   
2. **Prometheus**: http://localhost:9090
   - Проверьте targets: http://localhost:9090/targets
   - Все должны быть "UP"

3. **Alertmanager**: http://localhost:9093
   - Проверьте статус

4. **API Metrics**: http://localhost:8000/metrics
   - Должны увидеть метрики в формате Prometheus

### Шаг 5: Протестируйте алерты

```bash
# Остановите API для теста
docker-compose stop api

# Подождите 1-2 минуты
# Вы должны получить критический алерт в Telegram:
# 🚨 CRITICAL ALERT 🚨
# ⚠️ APIDown
# Service: api
# Status: FIRING

# Запустите обратно
docker-compose start api

# Получите уведомление о resolved
```

---

## 📊 Что можно посмотреть прямо сейчас

### В Grafana (http://localhost:3000):

1. **Dashboards → Stock Tracker - Overview**
   - API Status (UP/DOWN)
   - Request Rate по статусам
   - API Latency (p50, p95, p99)
   - CPU & Memory Usage
   - Celery Tasks

2. **Dashboards → Stock Tracker - Business Metrics**
   - Количество отслеживаемых товаров
   - Sync операции (Wildberries/Ozon)
   - Ошибки внешних API
   - Google Sheets операции

### В Prometheus (http://localhost:9090):

Попробуйте запросы:
```promql
# API is up?
up{job="stock-tracker-api"}

# Request rate
rate(http_requests_total[5m])

# CPU usage
system_cpu_usage_percent

# Celery queue length
sum(celery_queue_length)
```

---

## 📈 Метрики которые собираются

### HTTP Метрики
- ✅ Количество запросов (по методам, endpoints, статусам)
- ✅ Latency (histogram с перцентилями)
- ✅ Активные запросы

### Database Метрики
- ✅ Активные подключения
- ✅ Время выполнения запросов
- ✅ Ошибки БД

### Celery Метрики
- ✅ Количество задач (success/failure)
- ✅ Длительность выполнения
- ✅ Длина очередей
- ✅ Активные задачи

### Business Метрики
- ✅ Количество товаров
- ✅ Sync операции (WB/Ozon)
- ✅ Ошибки внешних API
- ✅ Google Sheets операции

### System Метрики
- ✅ CPU Usage
- ✅ Memory Usage
- ✅ Disk Usage
- ✅ Network I/O

---

## 🚨 Настроенные алерты (отправляются в Telegram)

### Critical (немедленно)
- 🚨 **APIDown** - API недоступен >1 мин
- 🚨 **PostgreSQLDown** - БД недоступна >1 мин
- 🚨 **RedisDown** - Redis недоступен >1 мин
- 🚨 **HighErrorRate** - >5% ошибок 5xx
- 🚨 **CriticalCPUUsage** - CPU >95%
- 🚨 **CriticalMemoryUsage** - Memory >95%
- 🚨 **CriticalDiskUsage** - Disk >95%

### Warning (менее срочно)
- ⚠️ **HighLatency** - p95 latency >2 сек
- ⚠️ **HighCPUUsage** - CPU >80%
- ⚠️ **HighMemoryUsage** - Memory >85%
- ⚠️ **HighDiskUsage** - Disk >85%
- ⚠️ **CeleryQueueBacklog** - >100 задач в очереди
- ⚠️ **SlowDatabaseQueries** - медленные запросы
- ⚠️ **SyncOperationFailures** - много неудачных синхронизаций

---

## 🔧 Команды для управления

```bash
# Просмотр логов
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager

# Перезапуск сервисов
docker-compose restart prometheus grafana alertmanager

# Остановка мониторинга
docker-compose stop prometheus grafana alertmanager postgres-exporter redis-exporter

# Полная остановка
docker-compose down

# Удаление данных (будьте осторожны!)
docker-compose down -v
```

---

## 📚 Документация

### Для быстрого старта (5 минут)
📄 [MONITORING_QUICKSTART.md](./MONITORING_QUICKSTART.md)

### Полное руководство (все детали)
📄 [docs/MONITORING_GUIDE.md](./docs/MONITORING_GUIDE.md)

Включает:
- Детальная архитектура
- Все alert rules с объяснениями
- Создание кастомных метрик
- PromQL примеры
- Best practices
- Troubleshooting

---

## 🎯 Best Practices

### 1. Security
```bash
# Используйте сильные пароли
GRAFANA_PASSWORD=$(openssl rand -base64 32)

# В production ограничьте доступ к портам
# Используйте reverse proxy (nginx)
```

### 2. Backups
```bash
# Backup Prometheus data
docker run --rm \
  -v stock-tracker_prometheus_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/prometheus-$(date +%Y%m%d).tar.gz /data
```

### 3. Alerts
- Настройте thresholds под вашу нагрузку
- Не игнорируйте warning alerts
- Регулярно проверяйте alert rules

### 4. Retention
- По умолчанию: 30 дней
- Для production: рассмотрите long-term storage (Thanos, Cortex)

---

## ❓ Troubleshooting

### Grafana не показывает данные
```bash
# 1. Проверьте Prometheus
curl http://localhost:9090/-/healthy

# 2. Проверьте targets
open http://localhost:9090/targets

# 3. Проверьте data source в Grafana
# Configuration → Data Sources → Prometheus → Test

# 4. Перезапустите
docker-compose restart grafana prometheus
```

### Нет алертов в Telegram
```bash
# 1. Проверьте переменные
docker-compose exec alertmanager env | grep TELEGRAM

# 2. Тест бота
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_ALERT_CHAT_ID}" \
  -d "text=Test from Stock Tracker Monitoring"

# 3. Логи
docker-compose logs alertmanager
```

### API не экспортирует метрики
```bash
# 1. Проверьте endpoint
curl http://localhost:8000/metrics

# 2. Проверьте что модуль загружен
docker-compose logs api | grep "Prometheus metrics"

# 3. Перезапустите API
docker-compose restart api
```

---

## 🌟 Следующие шаги

1. ✅ Запустите систему и убедитесь что все работает
2. ✅ Протестируйте алерты (остановите API)
3. ✅ Изучите дашборды в Grafana
4. ✅ Настройте пароль Grafana
5. ⏭️ Создайте кастомные метрики для вашего бизнеса
6. ⏭️ Настройте дополнительные алерты
7. ⏭️ Интегрируйте Sentry для error tracking
8. ⏭️ Рассмотрите ELK Stack для логов

---

## 💬 Контакты

Вопросы по мониторингу: **Telegram @Enotiz**

---

**Готово! Ваша система мониторинга полностью настроена и готова к работе! 🎉**

**Следуйте шагам выше для первого запуска.**
