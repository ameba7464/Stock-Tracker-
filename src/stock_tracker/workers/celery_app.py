"""
Celery application configuration for Stock Tracker.

This module configures Celery for:
- Multi-tenant product synchronization
- Background task processing
- Scheduled periodic tasks (Celery Beat)
"""

import os
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery application
celery_app = Celery(
    "stock_tracker",
    broker=REDIS_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["stock_tracker.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "stock_tracker.workers.tasks.sync_tenant_products": {"queue": "sync"},
        "stock_tracker.workers.tasks.cleanup_old_logs": {"queue": "maintenance"},
    },
    
    # Task queues
    task_queues=(
        Queue("sync", routing_key="sync"),
        Queue("maintenance", routing_key="maintenance"),
        Queue("default", routing_key="default"),
    ),
    task_default_queue="default",
    task_default_routing_key="default",
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=1,  # Fair task distribution
    
    # Result settings
    result_expires=3600,  # Keep results for 1 hour
    result_persistent=True,  # Store results in Redis
    
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Cleanup old sync logs every day at 3 AM
        "cleanup-old-logs": {
            "task": "stock_tracker.workers.tasks.cleanup_old_logs",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "maintenance"},
        },
        # Health check every 5 minutes
        "health-check": {
            "task": "stock_tracker.workers.tasks.health_check",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "maintenance"},
        },
    },
    
    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,
    
    # Logging
    worker_hijack_root_logger=False,
)


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery configuration."""
    print(f"Request: {self.request!r}")
