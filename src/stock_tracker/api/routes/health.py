"""
Health check endpoints for monitoring application status.

Provides:
- Basic health check
- Detailed readiness check
- Liveness check
- Component status (database, Redis, etc.)
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status, Response
from sqlalchemy import text

from stock_tracker.database.connection import SessionLocal
from stock_tracker.cache.redis_cache import get_cache
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns 200 if application is running.
    Used by load balancers for basic liveness check.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "stock-tracker",
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness check endpoint.
    
    Checks if application is ready to accept traffic.
    Verifies connectivity to all critical dependencies.
    """
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
    }
    
    # Determine overall status
    all_healthy = all(check["status"] == "healthy" for check in checks.values())
    overall_status = "healthy" if all_healthy else "unhealthy"
    
    # Set appropriate status code
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check endpoint.
    
    Indicates whether application is alive and should not be restarted.
    Returns 200 if process is running, even if dependencies are down.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


def _check_database() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    start_time = time.time()
    
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        duration = time.time() - start_time
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration * 1000, 2),
        }
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Database health check failed: {e}")
        
        return {
            "status": "unhealthy",
            "error": str(e)[:100],
            "response_time_ms": round(duration * 1000, 2),
        }


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    start_time = time.time()
    
    try:
        cache = get_cache()
        if cache.ping():
            duration = time.time() - start_time
            return {
                "status": "healthy",
                "response_time_ms": round(duration * 1000, 2),
            }
        else:
            duration = time.time() - start_time
            return {
                "status": "unhealthy",
                "error": "PING failed",
                "response_time_ms": round(duration * 1000, 2),
            }
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Redis health check failed: {e}")
        
        return {
            "status": "unhealthy",
            "error": str(e)[:100],
            "response_time_ms": round(duration * 1000, 2),
        }
