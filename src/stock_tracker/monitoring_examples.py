"""
Примеры использования Prometheus метрик в Stock Tracker.

Этот файл содержит готовые примеры кода для интеграции
мониторинга в различные части приложения.
"""

from stock_tracker.monitoring import get_metrics
from contextlib import contextmanager
import time

# ============================================================================
# ПРИМЕР 1: HTTP Endpoints
# ============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()
metrics = get_metrics()


@router.get("/products")
async def get_products(db: Session = Depends(get_db)):
    """Пример endpoint с метриками."""
    
    # Метрики HTTP автоматически собираются middleware
    # Но можно добавить кастомные:
    
    try:
        # Бизнес-логика
        products = db.query(Product).all()
        
        # Обновляем метрику количества товаров
        metrics.products_total.labels(
            tenant_id="tenant_123"
        ).set(len(products))
        
        return products
        
    except Exception as e:
        # Метрика ошибок
        metrics.db_errors_total.labels(
            error_type=type(e).__name__
        ).inc()
        raise


# ============================================================================
# ПРИМЕР 2: Database Operations
# ============================================================================

@contextmanager
def track_db_query(operation: str):
    """Context manager для отслеживания DB запросов."""
    metrics = get_metrics()
    
    start_time = time.time()
    try:
        yield
        
        # Успешный запрос
        duration = time.time() - start_time
        metrics.db_query_duration_seconds.labels(
            operation=operation
        ).observe(duration)
        
    except Exception as e:
        # Ошибка БД
        metrics.db_errors_total.labels(
            error_type=type(e).__name__
        ).inc()
        raise


# Использование:
def get_user_by_id(user_id: int):
    with track_db_query("select_user"):
        return db.query(User).filter(User.id == user_id).first()


# ============================================================================
# ПРИМЕР 3: Celery Tasks
# ============================================================================

from celery import Task
from stock_tracker.workers.celery_app import celery_app


class MonitoredTask(Task):
    """Base task class с автоматическим мониторингом."""
    
    def __call__(self, *args, **kwargs):
        metrics = get_metrics()
        
        # Увеличиваем счетчик активных задач
        metrics.celery_tasks_in_progress.labels(
            task_name=self.name
        ).inc()
        
        start_time = time.time()
        
        try:
            # Выполняем задачу
            result = self.run(*args, **kwargs)
            
            # Успех
            duration = time.time() - start_time
            
            metrics.celery_tasks_total.labels(
                task_name=self.name,
                status="success"
            ).inc()
            
            metrics.celery_task_duration_seconds.labels(
                task_name=self.name
            ).observe(duration)
            
            return result
            
        except Exception as e:
            # Ошибка
            metrics.celery_tasks_total.labels(
                task_name=self.name,
                status="failure"
            ).inc()
            raise
            
        finally:
            # Уменьшаем счетчик активных задач
            metrics.celery_tasks_in_progress.labels(
                task_name=self.name
            ).dec()


@celery_app.task(base=MonitoredTask)
def sync_wildberries_data(tenant_id: str):
    """Пример задачи с мониторингом."""
    
    metrics = get_metrics()
    
    try:
        # Синхронизация
        result = perform_sync()
        
        # Бизнес-метрика: успешная синхронизация
        metrics.sync_operations_total.labels(
            platform="wildberries",
            status="success",
            tenant_id=tenant_id
        ).inc()
        
        return result
        
    except Exception as e:
        # Бизнес-метрика: неудачная синхронизация
        metrics.sync_operations_total.labels(
            platform="wildberries",
            status="failure",
            tenant_id=tenant_id
        ).inc()
        
        metrics.api_errors_total.labels(
            platform="wildberries",
            error_type=type(e).__name__
        ).inc()
        
        raise


# ============================================================================
# ПРИМЕР 4: External API Calls
# ============================================================================

import httpx


async def call_wildberries_api(endpoint: str, tenant_id: str):
    """Пример вызова внешнего API с метриками."""
    
    metrics = get_metrics()
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.wildberries.ru/{endpoint}")
            response.raise_for_status()
            
            # Метрика длительности
            duration = time.time() - start_time
            metrics.sync_duration_seconds.labels(
                platform="wildberries",
                tenant_id=tenant_id
            ).observe(duration)
            
            return response.json()
            
    except httpx.HTTPError as e:
        # Метрика ошибок API
        metrics.api_errors_total.labels(
            platform="wildberries",
            error_type=type(e).__name__
        ).inc()
        raise


# ============================================================================
# ПРИМЕР 5: Google Sheets Operations
# ============================================================================

async def update_google_sheet(tenant_id: str, data: list):
    """Пример операции с Google Sheets."""
    
    metrics = get_metrics()
    
    try:
        # Обновление таблицы
        sheet.update(data)
        
        # Успешная операция
        metrics.sheets_operations_total.labels(
            operation="update",
            status="success",
            tenant_id=tenant_id
        ).inc()
        
    except Exception as e:
        # Ошибка
        metrics.sheets_operations_total.labels(
            operation="update",
            status="error",
            tenant_id=tenant_id
        ).inc()
        raise


# ============================================================================
# ПРИМЕР 6: Redis Operations
# ============================================================================

import redis


def cache_get(key: str):
    """Пример операции с Redis."""
    
    metrics = get_metrics()
    start_time = time.time()
    
    try:
        r = redis.Redis()
        value = r.get(key)
        
        # Метрика операции
        duration = time.time() - start_time
        
        metrics.redis_operations_total.labels(
            operation="get",
            status="success"
        ).inc()
        
        metrics.redis_operation_duration_seconds.labels(
            operation="get"
        ).observe(duration)
        
        return value
        
    except redis.RedisError as e:
        metrics.redis_operations_total.labels(
            operation="get",
            status="error"
        ).inc()
        raise


# ============================================================================
# ПРИМЕР 7: Background Job для системных метрик
# ============================================================================

from apscheduler.schedulers.asyncio import AsyncIOScheduler


def update_system_metrics():
    """Периодическое обновление системных метрик."""
    metrics = get_metrics()
    metrics.update_system_metrics()


# Запуск в lifespan
@asynccontextmanager
async def lifespan(app):
    # Startup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        update_system_metrics,
        'interval',
        seconds=30  # Каждые 30 секунд
    )
    scheduler.start()
    
    yield
    
    # Shutdown
    scheduler.shutdown()


# ============================================================================
# ПРИМЕР 8: Кастомные бизнес-метрики
# ============================================================================

def track_user_action(user_id: str, action: str):
    """Пример кастомной бизнес-метрики."""
    
    metrics = get_metrics()
    
    # Создайте новую метрику в monitoring.py:
    # self.user_actions_total = Counter(
    #     'user_actions_total',
    #     'Total user actions',
    #     ['action', 'user_id'],
    #     registry=self.registry
    # )
    
    metrics.user_actions_total.labels(
        action=action,
        user_id=user_id
    ).inc()


# ============================================================================
# ПРИМЕР 9: Context Manager для таймеров
# ============================================================================

@contextmanager
def track_operation(name: str, **labels):
    """Универсальный context manager для отслеживания операций."""
    
    metrics = get_metrics()
    start_time = time.time()
    
    try:
        yield
        
        # Успех
        duration = time.time() - start_time
        labels['status'] = 'success'
        
        # Record in histogram
        metrics.http_request_duration_seconds.labels(**labels).observe(duration)
        
    except Exception as e:
        # Ошибка
        labels['status'] = 'error'
        labels['error_type'] = type(e).__name__
        raise


# Использование:
def process_data():
    with track_operation('process_data', operation='data_processing'):
        # Your code here
        pass


# ============================================================================
# ПРИМЕР 10: Middleware для дополнительных метрик
# ============================================================================

from starlette.middleware.base import BaseHTTPMiddleware


class CustomMetricsMiddleware(BaseHTTPMiddleware):
    """Кастомный middleware для специфичных метрик."""
    
    async def dispatch(self, request, call_next):
        metrics = get_metrics()
        
        # Метрика перед обработкой
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if tenant_id:
            # Трекинг запросов по tenant
            metrics.http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                tenant_id=tenant_id
            ).inc()
        
        response = await call_next(request)
        
        return response


# Добавьте в main.py:
# app.add_middleware(CustomMetricsMiddleware)


# ============================================================================
# ПРИМЕР 11: Периодический сбор метрик
# ============================================================================

async def collect_queue_metrics():
    """Сбор метрик очередей Celery."""
    
    from celery import current_app
    metrics = get_metrics()
    
    # Получаем длину очередей
    inspect = current_app.control.inspect()
    active = inspect.active()
    
    if active:
        for worker, tasks in active.items():
            queue_name = worker.split('@')[0]
            metrics.celery_queue_length.labels(
                queue_name=queue_name
            ).set(len(tasks))


# Запускайте периодически через scheduler
# scheduler.add_job(collect_queue_metrics, 'interval', seconds=30)


# ============================================================================
# ЗАМЕТКИ ПО BEST PRACTICES
# ============================================================================

"""
1. Labels:
   - Используйте низкую cardinality (не user_id, не timestamps)
   - Хорошие labels: status, operation, platform, error_type
   - Плохие labels: user_id, order_id, product_id

2. Naming:
   - Counter: _total суффикс (http_requests_total)
   - Gauge: описательное имя (system_cpu_usage_percent)
   - Histogram: _seconds/_bytes суффикс (http_request_duration_seconds)

3. Units:
   - Время: seconds (не milliseconds)
   - Размер: bytes (не megabytes)
   - Проценты: 0-100 (не 0-1)

4. Performance:
   - Не создавайте метрики в hot path
   - Используйте .inc() вместо .inc(1)
   - Кэшируйте label combinations

5. Testing:
   - Проверяйте что метрики экспортируются: curl localhost:8000/metrics
   - Используйте Prometheus UI для проверки: localhost:9090
   - Тестируйте алерты перед production
"""
