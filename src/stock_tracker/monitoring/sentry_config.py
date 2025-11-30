"""
Sentry integration for error tracking and performance monitoring.

Provides:
- Automatic error capture
- User context (tenant, user)
- Request context
- Performance transaction tracking
- Breadcrumb logging
"""

import os
import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)


def setup_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
):
    """
    Initialize Sentry SDK for error tracking and performance monitoring.
    
    Args:
        dsn: Sentry DSN (Data Source Name) - from environment if not provided
        environment: Deployment environment (production, staging, development)
        release: Release version (e.g., "stock-tracker@1.0.0")
        traces_sample_rate: Percentage of transactions to trace (0.0-1.0)
        profiles_sample_rate: Percentage of transactions to profile (0.0-1.0)
    """
    # Get DSN from environment if not provided
    dsn = dsn or os.getenv("SENTRY_DSN")
    
    if not dsn:
        logger.warning("Sentry DSN not configured, skipping Sentry initialization")
        return
    
    # Get environment from env vars if not provided
    environment = environment or os.getenv("SENTRY_ENVIRONMENT", "development")
    
    # Get release from env vars if not provided
    release = release or os.getenv("SENTRY_RELEASE", "unknown")
    
    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        
        # Integrations
        integrations=[
            # FastAPI integration
            FastApiIntegration(
                transaction_style="endpoint",  # Group by endpoint
            ),
            
            # SQLAlchemy integration
            SqlalchemyIntegration(),
            
            # Redis integration
            RedisIntegration(),
            
            # Celery integration
            CeleryIntegration(
                monitor_beat_tasks=True,
                exclude_beat_tasks=[
                    "celery.backend_cleanup",
                ],
            ),
            
            # Logging integration
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above
                event_level=logging.ERROR,  # Create events for errors
            ),
        ],
        
        # Performance monitoring
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        
        # Error filtering
        before_send=before_send_filter,
        
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send personally identifiable info
        max_breadcrumbs=50,
    )
    
    logger.info(
        f"Sentry initialized: environment={environment}, "
        f"release={release}, traces_sample_rate={traces_sample_rate}"
    )


def before_send_filter(event, hint):
    """
    Filter events before sending to Sentry.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context about the event
        
    Returns:
        Modified event or None to drop the event
    """
    # Drop certain error types
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        
        # Drop 404 errors
        if "404" in str(exc_value):
            return None
        
        # Drop rate limit errors (already tracked in metrics)
        if "429" in str(exc_value) or "Too Many Requests" in str(exc_value):
            return None
    
    return event


def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    tenant_id: Optional[str] = None,
    company_name: Optional[str] = None,
):
    """
    Set user context for Sentry events.
    
    Args:
        user_id: User UUID
        email: User email
        tenant_id: Tenant UUID
        company_name: Company name
    """
    context = {}
    
    if user_id:
        context["id"] = user_id
    if email:
        context["email"] = email
    if tenant_id:
        context["tenant_id"] = tenant_id
    if company_name:
        context["company_name"] = company_name
    
    if context:
        sentry_sdk.set_user(context)


def set_tenant_context(tenant_id: str, company_name: str, marketplace: str):
    """
    Set tenant context for Sentry events.
    
    Args:
        tenant_id: Tenant UUID
        company_name: Company name
        marketplace: Marketplace type (wildberries, ozon)
    """
    sentry_sdk.set_context("tenant", {
        "tenant_id": tenant_id,
        "company_name": company_name,
        "marketplace": marketplace,
    })


def capture_exception(
    exception: Exception,
    level: str = "error",
    **kwargs
):
    """
    Manually capture an exception to Sentry.
    
    Args:
        exception: Exception to capture
        level: Severity level (error, warning, info)
        **kwargs: Additional context
    """
    with sentry_sdk.push_scope() as scope:
        # Set level
        scope.level = level
        
        # Add extra context
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        
        # Capture exception
        sentry_sdk.capture_exception(exception)


def capture_message(
    message: str,
    level: str = "info",
    **kwargs
):
    """
    Capture a message to Sentry.
    
    Args:
        message: Message to capture
        level: Severity level (error, warning, info)
        **kwargs: Additional context
    """
    with sentry_sdk.push_scope() as scope:
        # Set level
        scope.level = level
        
        # Add extra context
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        
        # Capture message
        sentry_sdk.capture_message(message)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    **data
):
    """
    Add a breadcrumb for debugging context.
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category (auth, db, api, etc.)
        level: Severity level
        **data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data,
    )


def start_transaction(name: str, op: str = "task") -> sentry_sdk.tracing.Transaction:
    """
    Start a performance transaction.
    
    Usage:
        with start_transaction("sync_products", op="task") as transaction:
            # Do work
            transaction.set_tag("tenant_id", tenant_id)
    
    Args:
        name: Transaction name
        op: Operation type (task, http, db, etc.)
        
    Returns:
        Transaction context manager
    """
    return sentry_sdk.start_transaction(name=name, op=op)
