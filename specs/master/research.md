# Research: Google Sheets Stock Tracker для Wildberries

**Date**: 21 октября 2025 г.  
**Purpose**: Разрешение технических неопределенностей из Technical Context

## Исследовательские задачи

### 1. Wildberries API Endpoints и Authentication

**Decision**: Использовать Wildberries Seller API с токенной аутентификацией  
**Rationale**: 
- Официальные endpoints для получения остатков и заказов
- Токенная аутентификация более безопасна для автоматизации
- Поддержка агрегации данных за период

**Key Endpoints**:
- `/api/v3/stocks` - получение остатков по складам
- `/api/v3/orders` - получение заказов за период  
- Аутентификация через заголовок `Authorization: Bearer {token}`

**Alternatives considered**: 
- Парсинг личного кабинета - отклонено из-за нестабильности
- CSV выгрузки - отклонено из-за отсутствия автоматизации

### 2. Google Apps Script Testing Framework

**Decision**: Встроенная система логирования + QUnit for Google Apps Script  
**Rationale**:
- QUnit адаптирован для Google Apps Script среды
- Поддержка unit и integration тестов
- Встроенное логирование для отладки

**Testing Approach**:
- Unit tests для каждого модуля (API, data processing, sheets operations)
- Integration tests для полного цикла обновления
- Mock данные для тестирования без реальных API вызовов

**Alternatives considered**:
- Clasp + Jest - отклонено из-за сложности настройки
- Только логирование - недостаточно для качественного тестирования

### 3. Performance и Scale Requirements

**Decision**: Оптимизация для средних объемов (до 1000 товаров, до 20 складов)  
**Rationale**:
- Типичный объем для среднего продавца на Wildberries
- Укладывается в лимиты Google Apps Script (6 минут выполнения)
- Batch обработка для больших объемов

**Performance Targets**:
- Полное обновление данных: <2 минут для 1000 товаров
- API вызовы: batch запросы по 100 товаров
- Sheets операции: bulk updates вместо построчной записи

**Scale Considerations**:
- Пагинация API запросов при больших объемах
- Chunking данных для записи в Google Sheets
- Кеширование для минимизации API вызовов

**Alternatives considered**:
- Неограниченный масштаб - отклонено из-за технических лимитов
- Только малые объемы (<100 товаров) - недостаточно для практического применения

### 4. API Rate Limits и Error Handling

**Decision**: Экспоненциальная задержка + circuit breaker pattern  
**Rationale**:
- Wildberries API имеет строгие лимиты (обычно 10 запросов/секунду)
- Graceful degradation при временных сбоях
- Возможность partial updates при частичных ошибках

**Implementation Strategy**:
- Retry logic с экспоненциальной задержкой (1s, 2s, 4s, 8s)
- Circuit breaker после 5 последовательных ошибок
- Partial update support - сохранение успешно полученных данных
- Детальное логирование ошибок для диагностики

**Error Categories**:
- **Network errors**: retry с задержкой
- **Authentication errors**: критическая ошибка, остановка процесса  
- **Rate limit errors**: увеличение интервала запросов
- **Data format errors**: пропуск некорректных записей с логированием

**Alternatives considered**:
- Простой retry без circuit breaker - может привести к бесконечным циклам
- Fail-fast approach - потеря данных при временных сбоях

### 5. Data Processing и Aggregation Logic

**Decision**: In-memory агрегация с промежуточным кешированием  
**Rationale**:
- Эффективная обработка данных за 7-дневный период
- Минимизация операций записи в Google Sheets
- Поддержка сложной логики группировки по складам

**Aggregation Algorithm**:
1. Загрузка всех данных за 7 дней в memory
2. Группировка по артикулам продавца
3. Суммирование заказов и остатков по складам
4. Расчет оборачиваемости (с обработкой division by zero)
5. Форматирование для множественных складов (newline separated)

**Memory Management**:
- Batch processing для больших объемов
- Освобождение памяти после каждого batch
- Streaming approach для экстремально больших наборов данных

**Alternatives considered**:
- Database-style aggregation - избыточно для данного объема
- Real-time streaming - не подходит для ежедневных обновлений

## Архитектурные решения

### Google Apps Script Architecture

**Decision**: Модульная архитектура с четким разделением ответственности  
**Rationale**:
- Улучшенная тестируемость
- Простота поддержки и расширения
- Переиспользование компонентов

**Module Structure**:
- `WildberriesAPI`: HTTP клиент для работы с API
- `DataProcessor`: бизнес-логика агрегации  
- `SheetsManager`: операции с Google Sheets
- `Scheduler`: управление триггерами и расписанием
- `ErrorHandler`: centralized error handling и logging

### Configuration Management

**Decision**: Конфигурация через Google Apps Script Properties Service  
**Rationale**:
- Безопасное хранение API токенов
- Легкая настройка без изменения кода
- Версионирование конфигурации

**Configuration Items**:
- Wildberries API token
- Таблица ID для записи данных
- Настройки расписания (timezone, время запуска)
- Лимиты и timeout значения
- Feature flags для экспериментальных функций

## Технические риски и митигация

### Risk 1: Wildberries API Changes
**Mitigation**: Версионирование API вызовов, graceful fallback, monitoring

### Risk 2: Google Apps Script Execution Limits  
**Mitigation**: Chunking данных, progress tracking, resume capability

### Risk 3: Data Consistency Issues
**Mitigation**: Atomic updates, transaction-like patterns, validation

### Risk 4: Performance Degradation
**Mitigation**: Профилирование, caching, optimized batch sizes

## Заключение

Исследование показало техническую осуществимость проекта с использованием Google Apps Script как основной платформы интеграции. Ключевые технические решения обеспечивают надежность, производительность и масштабируемость в рамках заданных ограничений.

**Next Steps**: Phase 1 - создание data model, API contracts, и quickstart документации.