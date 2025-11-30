"""
Billing API routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel

from stock_tracker.db.session import get_db
from stock_tracker.api.middleware.auth import get_current_user, get_current_tenant
from stock_tracker.db.models import User, Tenant, Subscription
from stock_tracker.services.billing import StripeClient, SubscriptionManager, get_stripe_client


router = APIRouter(prefix="/billing", tags=["billing"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SubscriptionPlanResponse(BaseModel):
    """Subscription plan details"""
    name: str
    price_monthly: int
    api_calls_limit: int
    sync_frequency_minutes: int
    max_products: int
    features: list[str]


class CreateSubscriptionRequest(BaseModel):
    """Create subscription request"""
    plan_name: str
    stripe_price_id: str
    trial_days: int = 14


class CheckoutSessionRequest(BaseModel):
    """Create checkout session request"""
    plan_name: str
    price_id: str
    success_url: str
    cancel_url: str


class SubscriptionResponse(BaseModel):
    """Subscription response"""
    id: str
    plan_name: str
    status: str
    start_date: str
    end_date: Optional[str]
    trial_end_date: Optional[str]
    api_calls_used: int
    api_calls_limit: int
    sync_frequency_minutes: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/plans", response_model=dict[str, SubscriptionPlanResponse])
def get_subscription_plans():
    """
    Get available subscription plans
    
    Returns all available subscription tiers with features and pricing
    """
    from stock_tracker.services.billing.subscription_manager import SUBSCRIPTION_PLANS
    return SUBSCRIPTION_PLANS


@router.get("/subscription", response_model=Optional[SubscriptionResponse])
def get_current_subscription(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get current subscription for authenticated tenant
    """
    manager = SubscriptionManager(db)
    subscription = manager.get_active_subscription(str(tenant.id))
    
    if not subscription:
        return None
    
    return SubscriptionResponse(
        id=str(subscription.id),
        plan_name=subscription.plan_name,
        status=subscription.status,
        start_date=subscription.start_date.isoformat(),
        end_date=subscription.end_date.isoformat() if subscription.end_date else None,
        trial_end_date=subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
        api_calls_used=subscription.api_calls_used,
        api_calls_limit=subscription.api_calls_limit,
        sync_frequency_minutes=subscription.sync_frequency_minutes
    )


@router.post("/checkout-session")
def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create Stripe Checkout session
    
    Returns URL to redirect user to Stripe Checkout page
    """
    stripe_client = get_stripe_client()
    
    # Create Stripe customer if not exists
    if not tenant.stripe_customer_id:
        customer = stripe_client.create_customer(
            email=current_user.email,
            name=tenant.company_name,
            metadata={"tenant_id": str(tenant.id)}
        )
        tenant.stripe_customer_id = customer.id
        db.commit()
    
    # Create checkout session
    session = stripe_client.create_checkout_session(
        customer_id=tenant.stripe_customer_id,
        price_id=request.price_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        trial_days=14,
        metadata={
            "tenant_id": str(tenant.id),
            "plan_name": request.plan_name
        }
    )
    
    return {
        "checkout_url": session.url,
        "session_id": session.id
    }


@router.post("/portal-session")
def create_portal_session(
    return_url: str,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    """
    Create Stripe Customer Portal session
    
    Returns URL to redirect user to manage their subscription
    """
    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    stripe_client = get_stripe_client()
    session = stripe_client.create_portal_session(
        customer_id=tenant.stripe_customer_id,
        return_url=return_url
    )
    
    return {
        "portal_url": session.url
    }


@router.post("/cancel")
def cancel_subscription(
    immediately: bool = False,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Cancel subscription
    
    Args:
        immediately: Cancel now or at period end
    """
    manager = SubscriptionManager(db)
    subscription = manager.get_active_subscription(str(tenant.id))
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    updated_subscription = manager.cancel_subscription(subscription, immediately)
    
    return {
        "message": "Subscription canceled successfully",
        "status": updated_subscription.status,
        "end_date": updated_subscription.end_date.isoformat() if updated_subscription.end_date else None
    }


@router.get("/usage")
def get_usage_stats(
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Get current billing period usage statistics
    """
    manager = SubscriptionManager(db)
    subscription = manager.get_active_subscription(str(tenant.id))
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    return {
        "api_calls_used": subscription.api_calls_used,
        "api_calls_limit": subscription.api_calls_limit,
        "usage_percentage": (subscription.api_calls_used / subscription.api_calls_limit) * 100,
        "remaining": subscription.api_calls_limit - subscription.api_calls_used
    }


# =============================================================================
# Webhooks
# =============================================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events
    
    Events:
    - customer.subscription.created
    - customer.subscription.updated
    - customer.subscription.deleted
    - invoice.payment_succeeded
    - invoice.payment_failed
    """
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    stripe_client = get_stripe_client()
    
    try:
        event = stripe_client.construct_webhook_event(payload, signature)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    manager = SubscriptionManager(db, stripe_client)
    
    # Handle different event types
    if event["type"] == "invoice.payment_succeeded":
        manager.handle_payment_succeeded(event["data"]["object"])
    
    elif event["type"] == "invoice.payment_failed":
        manager.handle_payment_failed(event["data"]["object"])
    
    elif event["type"] == "customer.subscription.deleted":
        manager.handle_subscription_canceled(event["data"]["object"])
    
    elif event["type"] == "customer.subscription.trial_will_end":
        manager.handle_trial_ending(event["data"]["object"])
    
    return {"status": "success"}
