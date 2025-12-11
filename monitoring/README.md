# 📊 Monitoring Configuration

Эта папка содержит конфигурационные файлы для системы мониторинга Stock Tracker.

## 📁 Структура

```
monitoring/
├── prometheus.yml              # Конфигурация Prometheus (сбор метрик)
├── alertmanager.yml           # Конфигурация Alertmanager (уведомления)
├── alerts/                    # Правила алертов
│   └── stock_tracker_alerts.yml
├── alertmanager/
│   └── templates/            # Шаблоны уведомлений
│       └── telegram.tmpl
└── grafana/
    ├── provisioning/
    │   ├── datasources/      # Автонастройка источников данных
    │   │   └── prometheus.yml
    │   └── dashboards/       # Автонастройка дашбордов
    │       └── dashboards.yml
    └── dashboards/           # JSON дашборды
        ├── overview.json
        └── business_metrics.json
```

## 🚀 Использование

### Prometheus
- **URL**: http://localhost:9090
- **Конфиг**: `prometheus.yml`
- **Alerts**: `alerts/stock_tracker_alerts.yml`

Сбор метрик с:
- Stock Tracker API (`:8000/metrics`)
- PostgreSQL Exporter (`:9187`)
- Redis Exporter (`:9121`)
- Node Exporter (`:9100`)
- cAdvisor (`:8080`)

### Alertmanager
- **URL**: http://localhost:9093
- **Конфиг**: `alertmanager.yml`
- **Шаблоны**: `alertmanager/templates/`

Отправка уведомлений в Telegram: @Enotiz

### Grafana
- **URL**: http://localhost:3000
- **Provisioning**: автоматически при старте
- **Дашборды**:
  - Stock Tracker - Overview
  - Stock Tracker - Business Metrics

## ⚙️ Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните переменные:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_ALERT_CHAT_ID=your_chat_id
   GRAFANA_PASSWORD=secure_password
   ```
3. Запустите: `docker-compose up -d`

## 📝 Добавление новых алертов

Отредактируйте `alerts/stock_tracker_alerts.yml`:

```yaml
- alert: MyNewAlert
  expr: my_metric > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Alert summary"
    description: "Alert description"
```

Перезагрузите конфигурацию:
```bash
docker-compose exec prometheus kill -HUP 1
```

## 📚 Документация

См. [../docs/MONITORING_GUIDE.md](../docs/MONITORING_GUIDE.md) для полной документации.
