# Quickstart Guide: Wildberries Stock Tracker

**Date**: 21 октября 2025 г.  
**Feature**: Wildberries Stock Tracker  

## Overview

Wildberries Stock Tracker - это профессиональное решение для автоматизации учета остатков и заказов товаров Wildberries в Google Sheets. Система предоставляет высокопроизводительную синхронизацию данных через API с продвинутыми функциями мониторинга, безопасности и оптимизации производительности.

## Prerequisites

### Required Accounts & Access
- **Wildberries API**: API ключ для доступа к данным о товарах и складах
- **Google Cloud Project**: Проект с активированным Google Sheets API
- **Service Account**: JSON ключ для доступа к Google Sheets
- **Google Sheet**: Подготовленная таблица с правильной структурой заголовков

### Development Environment
- **Python**: версия 3.11+ 
- **pip**: для управления зависимостями
- **Git**: для version control

## Quick Setup (5 minutes)

### 1. Clone & Install
```bash
git clone <repository-url>
cd Stock-Tracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Secure Credential Setup (Recommended)
Use the built-in secure credential storage:

```bash
# Setup secure credentials with encryption
python -m stock_tracker.cli security setup

# This will prompt for:
# - Master password for encryption
# - Wildberries API key
# - Path to Google service account JSON
# - Google Sheets ID
```

### 3. Alternative: Environment Configuration
Create `.env` file (less secure):
```env
# Wildberries API
WILDBERRIES_API_KEY=your_api_key_here
WILDBERRIES_BASE_URL=https://suppliers-api.wildberries.ru

# Google Sheets API  
GOOGLE_SERVICE_ACCOUNT_KEY_PATH=./config/service-account.json
GOOGLE_SHEET_ID=your_sheet_id_here

# Application
LOG_LEVEL=INFO
SYNC_SCHEDULE=0 0 * * *  # Daily at 00:00
AUTO_SYNC_ENABLED=true
MAX_PRODUCTS_PER_SYNC=100
```

### 4. Google Service Account Setup
1. Download service account JSON from Google Cloud Console
2. Save as `./config/service-account.json`  
3. Share your Google Sheet with service account email (with edit permissions)

### 5. Google Sheet Structure
Ensure your sheet has these headers in row 1:

| A | B | C | D | E | F | G | H |
|---|---|---|---|---|---|---|---|
| Артикул продавца | Артикул товара | Заказы (всего) | Остатки (всего) | Оборачиваемость | Название склада | Заказы со склада | Остатки на складе |

### 6. Validation & Health Check
```bash
# Validate configuration and security
python -m stock_tracker.cli config validate

# Check system health
python -m stock_tracker.cli health check

# Test API connections
python -m stock_tracker.cli api test
```

### 7. First Run
```bash
# Start the application
python -m stock_tracker.main

# Or trigger manual sync with CLI
python -m stock_tracker.cli sync run --manual

# Monitor sync status
python -m stock_tracker.cli sync status
```

## Advanced CLI Usage

### Configuration Management
```bash
# Show current configuration
python -m stock_tracker.cli config show

# Validate configuration and security
python -m stock_tracker.cli config validate

# Reset to defaults
python -m stock_tracker.cli config reset
```

### Synchronization Control
```bash
# Manual sync with verbose output
python -m stock_tracker.cli sync run --manual --verbose

# Check sync status and schedule
python -m stock_tracker.cli sync status

# View sync history and statistics
python -m stock_tracker.cli monitor summary
```

### Health Monitoring
```bash
# Comprehensive health check
python -m stock_tracker.cli health check --verbose

# System resource monitoring
python -m stock_tracker.cli health resources

# API connectivity test
python -m stock_tracker.cli api test --verbose
```

### Security & Credentials
```bash
# List stored credentials
python -m stock_tracker.cli security list

# Validate security configuration
python -m stock_tracker.cli security validate

# Change master password
python -m stock_tracker.cli security change-password

# Delete credential
python -m stock_tracker.cli security delete credential_name
```

### Performance Monitoring
```bash
# Real-time performance monitoring
python -m stock_tracker.cli monitor live

# Performance summary
python -m stock_tracker.cli monitor summary

# Export metrics
python -m stock_tracker.cli monitor export --format json
```

### Log Management
```bash
# View recent logs
python -m stock_tracker.cli logs show --tail 100

# Follow logs in real-time
python -m stock_tracker.cli logs follow

# Search logs
python -m stock_tracker.cli logs search "error" --last-hours 24
```

## Expected Results

After successful synchronization, your Google Sheet will contain:

**Example Data:**
```
| WB001 | 12345678 | 92   | 1107 | 0.083 | СЦ Волгоград     | 32  | 654 |
|       |          |      |      |       | СЦ Москва        | 60  | 453 |
| WB002 | 87654321 | 156  | 890  | 0.175 | СЦ Екатеринбург  | 78  | 445 |
|       |          |      |      |       | СЦ Новосибирск   | 78  | 445 |
```

**Advanced Features:**
- ✅ Автоматическое ежедневное обновление в 00:00 по московскому времени
- ✅ Высокопроизводительная батчевая обработка данных
- ✅ Адаптивная оптимизация производительности
- ✅ Экспоненциальный backoff для retry логики
- ✅ Rate limiting для соблюдения лимитов API
- ✅ Комплексный мониторинг здоровья системы
- ✅ Безопасное хранение учетных данных с шифрованием
- ✅ Полнофункциональный CLI интерфейс
- ✅ Детальная система логирования и мониторинга
- ✅ Автоматическая валидация безопасности

## Performance & Optimization

### Batch Processing
Система автоматически оптимизирует батчевые операции:
- Адаптивный размер батча на основе производительности
- Параллельная обработка множественных батчей
- Интеллектуальное кеширование API ответов
- Оптимизированные Google Sheets API вызовы

### Monitoring Metrics
```bash
# View performance metrics
python -m stock_tracker.cli monitor summary

# Export detailed metrics
python -m stock_tracker.cli monitor export --format csv --output metrics.csv
```

**Key Performance Indicators:**
- Throughput: количество элементов в секунду
- Latency: среднее время обработки элемента
- Success rate: процент успешных операций
- API utilization: использование лимитов API

## Troubleshooting

### Common Issues

**❌ "Authentication failed"**
```bash
# Check secure credentials
python -m stock_tracker.cli security list

# Validate configuration
python -m stock_tracker.cli config validate

# Test API connectivity
python -m stock_tracker.cli api test
```

**❌ "Wildberries API timeout"**  
```bash
# Check health status
python -m stock_tracker.cli health check

# View recent errors
python -m stock_tracker.cli logs search "error" --last-hours 1

# Test API with verbose output
python -m stock_tracker.cli api test --verbose
```

**❌ "Sync performance issues"**
```bash
# Check performance metrics
python -m stock_tracker.cli monitor summary

# View system resources
python -m stock_tracker.cli health resources

# Check batch processing efficiency
python -m stock_tracker.cli logs search "batch" --last-hours 2
```

**❌ "Security warnings"**
```bash
# Validate security configuration
python -m stock_tracker.cli security validate

# Check file permissions
ls -la config/ credentials.enc

# Setup secure storage
python -m stock_tracker.cli security setup
```

### Debug Mode
```bash
# Start with debug logging and verbose output
LOG_LEVEL=DEBUG python -m stock_tracker.main --verbose

# Debug specific sync issues
python -m stock_tracker.cli sync run --manual --verbose --log-level DEBUG

# Monitor real-time performance
python -m stock_tracker.cli monitor live --debug
```

### Performance Diagnostics
```bash
# Performance summary with recommendations
python -m stock_tracker.cli monitor summary --verbose

# Check batch processing efficiency
python -m stock_tracker.cli logs search "batch_processing" --last-hours 24

# System resource usage
python -m stock_tracker.cli health resources --detailed
```

## Production Configuration

### Security Best Practices
```bash
# Use secure credential storage
python -m stock_tracker.cli security setup

# Validate security configuration
python -m stock_tracker.cli security validate

# Strong master password (>12 chars, mixed case, numbers, symbols)
# Regular credential rotation
# Restrict file permissions (600 for credential files)
```

### Performance Optimization
```env
# Optimal configuration for production
SHEETS_BATCH_SIZE=100
API_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=3
MAX_PRODUCTS_PER_SYNC=500

# Enable performance monitoring
MONITORING_ENABLED=true
PERFORMANCE_METRICS_RETENTION_DAYS=30

# Rate limiting configuration
RATE_LIMIT_REQUESTS_PER_MINUTE=55  # Conservative for WB API
RATE_LIMIT_BURST_SIZE=10
```

### Monitoring & Alerting
```bash
# Setup health monitoring
python -m stock_tracker.cli health check --enable-alerts

# Monitor system continuously
python -m stock_tracker.cli monitor live --alert-threshold 0.8

# Export metrics for external monitoring
python -m stock_tracker.cli monitor export --format prometheus
```

## Deployment & Operations

### Systemd Service (Linux)
Create `/etc/systemd/system/stock-tracker.service`:
```ini
[Unit]
Description=Wildberries Stock Tracker
After=network.target

[Service]
Type=simple
User=stocktracker
WorkingDirectory=/opt/stock-tracker
ExecStart=/opt/stock-tracker/venv/bin/python -m stock_tracker.main
Restart=always
RestartSec=10
Environment=PYTHONPATH=/opt/stock-tracker

[Install]
WantedBy=multi-user.target
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

CMD ["python", "-m", "stock_tracker.main"]
```

### Monitoring Dashboard
```bash
# Start monitoring dashboard
python -m stock_tracker.cli monitor dashboard --port 8080

# Access at http://localhost:8080
# Real-time metrics, health status, performance charts
```

## Next Steps

1. **Production Setup**: Configure secure credentials and monitoring
2. **Performance Tuning**: Optimize batch sizes based on your data volume
3. **Monitoring**: Set up alerts and dashboards for operational visibility
4. **Security**: Regular credential rotation and security audits
5. **Scaling**: Add multiple Google Sheets or data sources
6. **Integration**: Connect with external monitoring systems (Prometheus, Grafana)

## Documentation Reference

For detailed technical information:
- [Data Model](data-model.md) - Entity relationships and validation rules
- [API Contracts](contracts/api-contracts.md) - Complete API documentation  
- [Research](research.md) - Technology decisions and alternatives
- [Tasks](tasks.md) - Implementation checklist and progress tracking