# Research: Wildberries Stock Tracker

**Date**: 21 октября 2025 г.  
**Feature**: Wildberries Stock Tracker  
**Phase**: 0 - Research & Technology Decisions

## Research Tasks

### Testing Framework Decision

**Decision**: pytest с дополнительными утилитами для API testing

**Rationale**: 
- pytest - стандарт для Python testing с отличной поддержкой fixtures и async
- requests-mock для мокирования HTTP API вызовов (Wildberries API)
- gspread-mock для тестирования Google Sheets интеграции
- Простая настройка и богатая экосистема плагинов

**Alternatives considered**: 
- unittest - встроенный, но менее функциональный
- nose2 - устаревший и менее популярный
- testify - дополнительная зависимость без значительных преимуществ

### Target Platform Decision

**Decision**: Python script/application с возможностью deployment на cloud platforms

**Rationale**:
- Python обеспечивает отличную работу с REST APIs через requests
- Богатая экосистема для Google APIs (google-api-python-client, gspread)
- Легкий deployment на Heroku, Google Cloud Functions, AWS Lambda
- APScheduler для настройки cron-like scheduling

**Alternatives considered**:
- Desktop application - избыточно для данной задачи
- Web application с Django/Flask - излишняя сложность для API integration
- Jupyter Notebook - не подходит для production automation

### Google Sheets API Integration Patterns

**Decision**: Использовать gspread library для упрощенной работы с Google Sheets API

**Rationale**:
- gspread предоставляет высокоуровневый API поверх google-api-python-client
- Простая аутентификация через service account
- Batch operations для эффективной работы с большими объемами данных
- Активная поддержка и хорошая документация

**Alternatives considered**:
- google-api-python-client напрямую - более сложная настройка
- pygsheets - менее популярный и активный
- xlsxwriter - только для локальных файлов, не для cloud sheets

### Wildberries API Integration Patterns

**Decision**: requests library с retry logic и rate limiting

**Rationale**:
- requests - стандарт для HTTP клиентов в Python
- urllib3.util.retry для automatic retry logic
- ratelimit library для соблюдения API limits
- Comprehensive error handling и timeout management

**Alternatives considered**:
- httpx - современная альтернатива, но requests более стабильный
- aiohttp - async, но избыточен для данной задачи
- urllib - встроенный, но менее удобный в использовании

### Scheduling Strategy

**Decision**: APScheduler для внутреннего scheduling + возможность external triggers

**Rationale**:
- APScheduler поддерживает cron-like expressions для ежедневного запуска в 00:00
- Возможность programmatic triggers для manual sync
- Persistent job store для reliability
- Logging и monitoring capabilities

**Alternatives considered**:
- system cron + separate script - менее гибкий для monitoring
- Celery - избыточно сложный для single-machine task
- external cloud schedulers - зависимость от конкретного provider

### Configuration Management

**Decision**: YAML configuration + environment variables

**Rationale**:
- YAML для structured configuration (API endpoints, sheet structure)
- Environment variables для secrets (API keys, credentials)
- pydantic для configuration validation
- Простое deployment в различных средах

**Alternatives considered**:
- Pure environment variables - менее читаемо для complex config
- JSON config - менее удобно для editing
- Python config files - security risks для secrets