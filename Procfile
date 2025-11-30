# FastAPI web server
web: uvicorn stock_tracker.api.main:app --host 0.0.0.0 --port $PORT

# Celery worker for background tasks
worker: celery -A stock_tracker.workers.celery_app worker --loglevel=info --concurrency=4 --queues=sync,default

# Celery Beat scheduler for periodic tasks
beat: celery -A stock_tracker.workers.celery_app beat --loglevel=info

# Legacy scheduler (kept for backward compatibility)
legacy_worker: python scheduler_service.py
