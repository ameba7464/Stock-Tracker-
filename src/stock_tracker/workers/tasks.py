"""
Celery tasks for background processing.

Tasks:
- sync_tenant_products: Sync products for a specific tenant
- cleanup_old_logs: Clean up old sync logs
- health_check: Periodic health check
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from celery import Task
from sqlalchemy.orm import Session

from .celery_app import celery_app
from ..database.connection import SessionLocal
from ..database.models import Tenant, SyncLog
from ..services.sync_service import SyncService
from ..services.google_sheets_service import GoogleSheetsService
from ..cache.redis_cache import get_cache
from ..services.webhook_dispatcher import dispatch_webhook
from ..utils.exceptions import SheetsAPIError

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """
    Base task class that provides database session management.
    
    Automatically creates and closes database sessions for tasks.
    """
    _db: Optional[Session] = None
    
    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="stock_tracker.workers.tasks.sync_tenant_products",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def sync_tenant_products(self, tenant_id: str) -> dict:
    """
    Sync products for a specific tenant from their marketplace.
    
    Args:
        tenant_id: UUID of the tenant to sync
        
    Returns:
        dict: Sync statistics (products_count, duration, status)
        
    Raises:
        Exception: If sync fails after all retries
    """
    db: Session = self.db
    cache = get_cache()
    
    # Create sync log entry
    sync_log = SyncLog(
        tenant_id=tenant_id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(sync_log)
    db.commit()
    
    try:
        # Load tenant from database
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        if not tenant.is_active:
            logger.warning(f"Skipping sync for inactive tenant {tenant_id}")
            sync_log.status = "skipped"
            sync_log.completed_at = datetime.utcnow()
            sync_log.message = "Tenant is inactive"
            db.commit()
            return {
                "status": "skipped",
                "reason": "inactive_tenant",
                "tenant_id": tenant_id,
            }
        
        logger.info(f"Starting product sync for tenant {tenant_id} ({tenant.name})")
        
        # Dispatch webhook: sync started
        try:
            dispatch_webhook(
                tenant=tenant,
                event_type="sync_started",
                data={
                    "tenant_id": tenant_id,
                    "started_at": sync_log.started_at.isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to dispatch sync_started webhook: {e}")
        
        # Initialize SyncService with tenant context
        sync_service = SyncService(
            tenant=tenant,
            db_session=db,
        )
        
        # Perform synchronization
        start_time = datetime.utcnow()
        result = sync_service.sync_products()
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Update sync log
        sync_log.status = "completed"
        sync_log.completed_at = end_time
        sync_log.products_synced = result.get("products_synced", 0)
        sync_log.duration_ms = int(duration * 1000)  # Convert to milliseconds
        db.commit()
        
        logger.info(
            f"Completed sync for tenant {tenant_id}: "
            f"{sync_log.products_synced} products in {duration:.2f}s"
        )
        
        # Sync to Google Sheets if configured
        sheets_sync_result = None
        if tenant.google_sheet_id and tenant.google_service_account_encrypted:
            try:
                logger.info(f"Syncing {sync_log.products_synced} products to Google Sheets for tenant {tenant_id}")
                
                sheets_service = GoogleSheetsService(tenant)
                
                # Get all synced products
                from ..database.models import Product
                products = db.query(Product).filter(
                    Product.tenant_id == tenant_id
                ).all()
                
                sheets_sync_result = sheets_service.sync_products_to_sheet(products, db)
                
                logger.info(
                    f"✅ Google Sheets sync completed: {sheets_sync_result.get('products_synced')} products "
                    f"in {sheets_sync_result.get('duration_seconds')}s"
                )
                
            except SheetsAPIError as e:
                logger.error(f"❌ Google Sheets sync failed: {e}")
                # Don't fail the entire sync if sheets update fails
                sheets_sync_result = {"success": False, "error": str(e)}
            except Exception as e:
                logger.error(f"❌ Unexpected error during Google Sheets sync: {e}", exc_info=True)
                sheets_sync_result = {"success": False, "error": str(e)}
        else:
            logger.debug(f"Google Sheets not configured for tenant {tenant_id}, skipping sheets sync")
        
        # Dispatch webhook: sync completed
        try:
            webhook_data = {
                "tenant_id": tenant_id,
                "products_count": sync_log.products_synced,
                "duration_seconds": duration,
                "completed_at": end_time.isoformat(),
            }
            
            # Include sheets sync result if available
            if sheets_sync_result:
                webhook_data["google_sheets"] = sheets_sync_result
            
            dispatch_webhook(
                tenant=tenant,
                event_type="sync_completed",
                data=webhook_data
            )
        except Exception as e:
            logger.error(f"Failed to dispatch sync_completed webhook: {e}")
        
        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "products_count": sync_log.products_synced,
            "duration_seconds": duration,
        }
        
    except Exception as exc:
        # Update sync log with error
        sync_log.status = "failed"
        sync_log.completed_at = datetime.utcnow()
        sync_log.message = f"Error: {str(exc)}"
        db.commit()
        
        logger.error(f"Sync failed for tenant {tenant_id}: {exc}", exc_info=True)
        
        # Dispatch webhook: sync failed
        try:
            tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                dispatch_webhook(
                    tenant=tenant,
                    event_type="sync_failed",
                    data={
                        "tenant_id": tenant_id,
                        "error": str(exc),
                        "failed_at": sync_log.completed_at.isoformat(),
                    }
                )
        except Exception as e:
            logger.error(f"Failed to dispatch sync_failed webhook: {e}")
        
        # Retry task if retries remaining
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying sync for tenant {tenant_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=exc)
        
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="stock_tracker.workers.tasks.cleanup_old_logs",
)
def cleanup_old_logs(self, days: int = 30) -> dict:
    """
    Clean up sync logs older than specified days.
    
    Args:
        days: Number of days to keep logs (default: 30)
        
    Returns:
        dict: Cleanup statistics (deleted_count)
    """
    db: Session = self.db
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete old logs
    deleted_count = db.query(SyncLog).filter(
        SyncLog.started_at < cutoff_date
    ).delete()
    
    db.commit()
    
    logger.info(f"Cleaned up {deleted_count} sync logs older than {days} days")
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date.isoformat(),
    }


@celery_app.task(
    bind=True,
    name="stock_tracker.workers.tasks.health_check",
)
def health_check(self) -> dict:
    """
    Periodic health check task.
    
    Verifies:
    - Database connectivity
    - Redis connectivity
    
    Returns:
        dict: Health status
    """
    from ..cache.redis_cache import get_cache
    
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": "unknown",
        "redis": "unknown",
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        status["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        status["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        cache = get_cache()
        if cache.ping():
            status["redis"] = "healthy"
        else:
            status["redis"] = "unhealthy: ping failed"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        status["redis"] = f"unhealthy: {str(e)}"
    
    logger.info(f"Health check: {status}")
    
    return status


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="stock_tracker.workers.tasks.schedule_tenant_syncs",
)
def schedule_tenant_syncs(self) -> dict:
    """
    Schedule sync tasks for all active tenants based on their sync_schedule.
    
    This task should be called periodically (e.g., every minute) to check
    if any tenant is due for synchronization.
    
    Returns:
        dict: Scheduling statistics (scheduled_count, tenants)
    """
    db: Session = self.db
    
    # Get all active tenants with sync enabled
    tenants = db.query(Tenant).filter(
        Tenant.is_active == True,
        Tenant.sync_schedule.isnot(None),
    ).all()
    
    scheduled_count = 0
    scheduled_tenants = []
    
    for tenant in tenants:
        # Check if tenant is due for sync
        # This is a simplified check - in production, you'd parse sync_schedule
        # and compare with last sync time from SyncLog
        
        # Get last sync log
        last_sync = db.query(SyncLog).filter(
            SyncLog.tenant_id == tenant.id,
            SyncLog.status == "completed",
        ).order_by(SyncLog.completed_at.desc()).first()
        
        # Simple logic: sync if no previous sync or last sync was >1 hour ago
        should_sync = False
        if not last_sync:
            should_sync = True
        else:
            time_since_sync = datetime.utcnow() - last_sync.completed_at
            if time_since_sync > timedelta(hours=1):
                should_sync = True
        
        if should_sync:
            # Schedule sync task
            sync_tenant_products.delay(str(tenant.id))
            scheduled_count += 1
            scheduled_tenants.append(str(tenant.id))
            logger.info(f"Scheduled sync for tenant {tenant.id} ({tenant.company_name})")
    
    return {
        "scheduled_count": scheduled_count,
        "tenants": scheduled_tenants,
        "timestamp": datetime.utcnow().isoformat(),
    }
