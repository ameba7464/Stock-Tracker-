"""
Prometheus metrics for monitoring application performance.

Metrics exported:
- stock_tracker_requests_total: Total HTTP requests
- stock_tracker_request_duration_seconds: Request duration histogram
- stock_tracker_sync_duration_seconds: Sync task duration histogram
- stock_tracker_sync_products_total: Total products synced
- stock_tracker_errors_total: Total errors
- stock_tracker_active_tenants: Number of active tenants
"""

import time
import logging
from typing import Optional
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
)
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus metrics collector for Stock Tracker.
    
    Tracks:
    - HTTP request metrics (rate, duration, status codes)
    - Sync task metrics (duration, product counts)
    - Error rates
    - Active tenant count
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus metrics.
        
        Args:
            registry: Prometheus registry (optional, uses default if not provided)
        """
        self.registry = registry
        
        # HTTP request metrics
        self.requests_total = Counter(
            "stock_tracker_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=registry,
        )
        
        self.request_duration = Histogram(
            "stock_tracker_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry,
        )
        
        # Sync task metrics
        self.sync_duration = Histogram(
            "stock_tracker_sync_duration_seconds",
            "Product sync duration in seconds",
            ["tenant_id", "marketplace"],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
            registry=registry,
        )
        
        self.sync_products_total = Counter(
            "stock_tracker_sync_products_total",
            "Total products synced",
            ["tenant_id", "marketplace", "status"],
            registry=registry,
        )
        
        # Error metrics
        self.errors_total = Counter(
            "stock_tracker_errors_total",
            "Total errors",
            ["error_type", "endpoint"],
            registry=registry,
        )
        
        # Tenant metrics
        self.active_tenants = Gauge(
            "stock_tracker_active_tenants",
            "Number of active tenants",
            registry=registry,
        )
        
        # Cache metrics
        self.cache_hits = Counter(
            "stock_tracker_cache_hits_total",
            "Total cache hits",
            ["cache_key"],
            registry=registry,
        )
        
        self.cache_misses = Counter(
            "stock_tracker_cache_misses_total",
            "Total cache misses",
            ["cache_key"],
            registry=registry,
        )
        
        # Celery task metrics
        self.celery_tasks_total = Counter(
            "stock_tracker_celery_tasks_total",
            "Total Celery tasks",
            ["task_name", "status"],
            registry=registry,
        )
        
        logger.info("Prometheus metrics initialized")
    
    def track_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
    ):
        """
        Track HTTP request metrics.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        self.requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)
    
    def track_sync(
        self,
        tenant_id: str,
        marketplace: str,
        duration: float,
        products_count: int,
        status: str,
    ):
        """
        Track product sync metrics.
        
        Args:
            tenant_id: Tenant UUID
            marketplace: Marketplace name (wildberries, ozon)
            duration: Sync duration in seconds
            products_count: Number of products synced
            status: Sync status (success, failed)
        """
        self.sync_duration.labels(
            tenant_id=tenant_id,
            marketplace=marketplace,
        ).observe(duration)
        
        self.sync_products_total.labels(
            tenant_id=tenant_id,
            marketplace=marketplace,
            status=status,
        ).inc(products_count)
    
    def track_error(self, error_type: str, endpoint: str):
        """
        Track error occurrence.
        
        Args:
            error_type: Type of error (ValidationError, APIError, etc.)
            endpoint: Endpoint where error occurred
        """
        self.errors_total.labels(
            error_type=error_type,
            endpoint=endpoint,
        ).inc()
    
    def set_active_tenants(self, count: int):
        """
        Update active tenant count.
        
        Args:
            count: Number of active tenants
        """
        self.active_tenants.set(count)
    
    def track_cache_hit(self, cache_key: str):
        """Track cache hit."""
        self.cache_hits.labels(cache_key=cache_key).inc()
    
    def track_cache_miss(self, cache_key: str):
        """Track cache miss."""
        self.cache_misses.labels(cache_key=cache_key).inc()
    
    def track_celery_task(self, task_name: str, status: str):
        """
        Track Celery task execution.
        
        Args:
            task_name: Name of Celery task
            status: Task status (success, failed, retry)
        """
        self.celery_tasks_total.labels(
            task_name=task_name,
            status=status,
        ).inc()


# Global metrics instance
_metrics: Optional[PrometheusMetrics] = None


def get_metrics() -> PrometheusMetrics:
    """
    Get global metrics instance.
    
    Returns:
        PrometheusMetrics instance
    """
    global _metrics
    if _metrics is None:
        _metrics = PrometheusMetrics()
    return _metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic request metrics collection.
    
    Tracks all HTTP requests and adds metrics to Prometheus.
    """
    
    def __init__(self, app):
        """Initialize metrics middleware."""
        super().__init__(app)
        self.metrics = get_metrics()
        logger.info("Metrics middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and track metrics.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response with metrics tracked
        """
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track request start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Track error
            error_type = type(e).__name__
            self.metrics.track_error(error_type, request.url.path)
            
            # Re-raise to let error handler deal with it
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            self.metrics.track_request(
                method=request.method,
                endpoint=self._normalize_endpoint(request.url.path),
                status_code=status_code if 'status_code' in locals() else 500,
                duration=duration,
            )
        
        return response
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for metrics labels.
        
        Replaces UUIDs and IDs with placeholders to prevent high cardinality.
        
        Args:
            path: Request path
            
        Returns:
            Normalized path
        """
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def track_sync_operation(func):
    """
    Decorator to track sync operation metrics.
    
    Usage:
        @track_sync_operation
        async def sync_products(tenant_id: str):
            # Sync logic
            return {"products_count": 150, "duration": 45.3}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        metrics = get_metrics()
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Extract metrics from result
            tenant_id = result.get("tenant_id", "unknown")
            marketplace = result.get("marketplace", "wildberries")
            products_count = result.get("products_count", 0)
            
            metrics.track_sync(
                tenant_id=tenant_id,
                marketplace=marketplace,
                duration=duration,
                products_count=products_count,
                status="success",
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Try to extract tenant info from args/kwargs
            tenant_id = kwargs.get("tenant_id", "unknown")
            marketplace = kwargs.get("marketplace", "wildberries")
            
            metrics.track_sync(
                tenant_id=tenant_id,
                marketplace=marketplace,
                duration=duration,
                products_count=0,
                status="failed",
            )
            
            raise
    
    return wrapper


async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint handler.
    
    Returns:
        Response with Prometheus metrics in text format
    """
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )
