"""
Prometheus metrics and monitoring for Stock Tracker.

Provides comprehensive metrics collection for:
- HTTP requests (latency, status codes, paths)
- Database operations
- Celery tasks
- Business metrics (products, sync operations)
- System resources
"""

from typing import Optional
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    REGISTRY,  # Use default registry
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import os
import psutil

from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


class PrometheusMetrics:
    """Centralized Prometheus metrics collector."""
    
    def __init__(self):
        # Use default REGISTRY instead of creating custom one
        self.registry = REGISTRY
        
        # ========== HTTP Metrics ==========
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'Number of HTTP requests in progress',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # ========== Database Metrics ==========
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query execution time in seconds',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )
        
        self.db_errors_total = Counter(
            'db_errors_total',
            'Total database errors',
            ['error_type'],
            registry=self.registry
        )
        
        # ========== Celery Metrics ==========
        self.celery_tasks_total = Counter(
            'celery_tasks_total',
            'Total Celery tasks processed',
            ['task_name', 'status'],
            registry=self.registry
        )
        
        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Celery task execution time in seconds',
            ['task_name'],
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0),
            registry=self.registry
        )
        
        self.celery_tasks_in_progress = Gauge(
            'celery_tasks_in_progress',
            'Number of Celery tasks currently running',
            ['task_name'],
            registry=self.registry
        )
        
        self.celery_queue_length = Gauge(
            'celery_queue_length',
            'Number of tasks in Celery queue',
            ['queue_name'],
            registry=self.registry
        )
        
        # ========== Redis Metrics ==========
        self.redis_operations_total = Counter(
            'redis_operations_total',
            'Total Redis operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        self.redis_operation_duration_seconds = Histogram(
            'redis_operation_duration_seconds',
            'Redis operation duration in seconds',
            ['operation'],
            buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1),
            registry=self.registry
        )
        
        # ========== Business Metrics ==========
        self.products_total = Gauge(
            'products_total',
            'Total number of products being tracked',
            ['tenant_id'],
            registry=self.registry
        )
        
        self.sync_operations_total = Counter(
            'sync_operations_total',
            'Total sync operations with Wildberries/Ozon',
            ['platform', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        self.sync_duration_seconds = Histogram(
            'sync_duration_seconds',
            'Sync operation duration in seconds',
            ['platform', 'tenant_id'],
            buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
            registry=self.registry
        )
        
        self.api_errors_total = Counter(
            'api_errors_total',
            'Total API errors from external services',
            ['platform', 'error_type'],
            registry=self.registry
        )
        
        self.sheets_operations_total = Counter(
            'sheets_operations_total',
            'Total Google Sheets operations',
            ['operation', 'status', 'tenant_id'],
            registry=self.registry
        )
        
        # ========== System Metrics ==========
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )
        
        self.system_memory_available = Gauge(
            'system_memory_available_bytes',
            'System available memory in bytes',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )
        
        # ========== Application Info ==========
        self.app_info = Info(
            'stock_tracker_app',
            'Stock Tracker application information',
            registry=self.registry
        )
        self.app_info.info({
            'version': '2.0.0',
            'python_version': os.sys.version,
            'environment': os.getenv('ENVIRONMENT', 'development')
        })
        
        logger.info("✅ Prometheus metrics initialized")
    
    def update_system_metrics(self):
        """Update system-level metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.system_memory_usage.set(memory.used)
            self.system_memory_available.set(memory.available)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.system_disk_usage.set(disk.percent)
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")


# Global metrics instance
_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic metrics collection."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics."""
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        metrics = get_metrics()
        
        # Normalize endpoint (remove IDs)
        endpoint = self._normalize_path(request.url.path)
        method = request.method
        
        # Track in-progress requests
        metrics.http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()
        
        # Measure request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record metrics
            duration = time.time() - start_time
            
            metrics.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            metrics.http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error
            metrics.http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            
            duration = time.time() - start_time
            metrics.http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            raise
            
        finally:
            # Decrement in-progress counter
            metrics.http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()
    
    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize URL path to reduce cardinality."""
        # Remove UUIDs and numeric IDs
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/:id',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/:id', path)
        
        return path


def setup_sentry(environment: str = "production", traces_sample_rate: float = 0.1):
    """Setup Sentry error tracking."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    
    if not sentry_dsn:
        logger.warning("⚠️ SENTRY_DSN not set, skipping Sentry initialization")
        return
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
            ],
            # Performance monitoring
            enable_tracing=True,
            # Send default PII (IP address, user id)
            send_default_pii=True,
            # Capture 100% of errors
            sample_rate=1.0,
        )
        
        logger.info(f"✅ Sentry initialized for {environment} environment")
        
    except ImportError:
        logger.warning("⚠️ Sentry SDK not installed, skipping initialization")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
