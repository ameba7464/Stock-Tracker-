"""
Subscription manager for handling billing logic
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from stock_tracker.db.models import Tenant, Subscription
from stock_tracker.services.billing.stripe_client import StripeClient, get_stripe_client


# =============================================================================
# Subscription Plans
# =============================================================================

SUBSCRIPTION_PLANS = {
    "starter": {
        "name": "Starter",
        "price_monthly": 990,  # $9.90
        "api_calls_limit": 1000,
        "sync_frequency_minutes": 120,
        "max_products": 100,
        "features": [
            "1 marketplace connection",
            "Daily sync",
            "Basic analytics",
            "Email support"
        ]
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 2990,  # $29.90
        "api_calls_limit": 10000,
        "sync_frequency_minutes": 30,
        "max_products": 1000,
        "features": [
            "2 marketplace connections",
            "Every 30 min sync",
            "Advanced analytics",
            "Priority email support",
            "Webhook notifications"
        ]
    },
    "enterprise": {
        "name": "Enterprise",
        "price_monthly": 9990,  # $99.90
        "api_calls_limit": 100000,
        "sync_frequency_minutes": 10,
        "max_products": 10000,
        "features": [
            "Unlimited marketplace connections",
            "Every 10 min sync",
            "Custom analytics",
            "24/7 phone support",
            "Webhook notifications",
            "Dedicated account manager",
            "Custom integrations"
        ]
    }
}


class SubscriptionManager:
    """
    Manager for subscription lifecycle and enforcement
    """
    
    def __init__(self, db_session: Session, stripe_client: Optional[StripeClient] = None):
        self.db = db_session
        self.stripe = stripe_client or get_stripe_client()
    
    # =========================================================================
    # Subscription Creation
    # =========================================================================
    
    def create_subscription(
        self,
        tenant: Tenant,
        plan_name: str,
        stripe_price_id: str,
        trial_days: int = 14
    ) -> Subscription:
        """
        Create new subscription for tenant
        
        Args:
            tenant: Tenant object
            plan_name: Plan name (starter, pro, enterprise)
            stripe_price_id: Stripe price ID from dashboard
            trial_days: Trial period in days
        
        Returns:
            Subscription object
        """
        if plan_name not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {plan_name}")
        
        plan = SUBSCRIPTION_PLANS[plan_name]
        
        # Create Stripe customer if not exists
        if not tenant.stripe_customer_id:
            customer = self.stripe.create_customer(
                email=tenant.company_name + "@stock-tracker.com",  # Use proper email
                name=tenant.company_name,
                metadata={"tenant_id": str(tenant.id)}
            )
            tenant.stripe_customer_id = customer.id
            self.db.commit()
        
        # Create Stripe subscription
        stripe_subscription = self.stripe.create_subscription(
            customer_id=tenant.stripe_customer_id,
            price_id=stripe_price_id,
            trial_days=trial_days,
            metadata={
                "tenant_id": str(tenant.id),
                "plan_name": plan_name
            }
        )
        
        # Create local subscription record
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_name=plan_name,
            status="trialing" if trial_days > 0 else "active",
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=tenant.stripe_customer_id,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            trial_end_date=datetime.utcnow() + timedelta(days=trial_days) if trial_days else None,
            api_calls_limit=plan["api_calls_limit"],
            sync_frequency_minutes=plan["sync_frequency_minutes"]
        )
        
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    # =========================================================================
    # Subscription Updates
    # =========================================================================
    
    def upgrade_subscription(
        self,
        subscription: Subscription,
        new_plan_name: str,
        new_price_id: str
    ) -> Subscription:
        """
        Upgrade subscription to higher plan
        
        Args:
            subscription: Current subscription
            new_plan_name: New plan name
            new_price_id: New Stripe price ID
        
        Returns:
            Updated subscription
        """
        if new_plan_name not in SUBSCRIPTION_PLANS:
            raise ValueError(f"Invalid plan: {new_plan_name}")
        
        plan = SUBSCRIPTION_PLANS[new_plan_name]
        
        # Update Stripe subscription
        stripe_subscription = self.stripe.get_subscription(subscription.stripe_subscription_id)
        self.stripe.update_subscription(
            subscription.stripe_subscription_id,
            items=[{
                "id": stripe_subscription["items"]["data"][0].id,
                "price": new_price_id,
            }],
            proration_behavior="always_invoice"
        )
        
        # Update local subscription
        subscription.plan_name = new_plan_name
        subscription.api_calls_limit = plan["api_calls_limit"]
        subscription.sync_frequency_minutes = plan["sync_frequency_minutes"]
        subscription.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    def cancel_subscription(
        self,
        subscription: Subscription,
        immediately: bool = False
    ) -> Subscription:
        """
        Cancel subscription
        
        Args:
            subscription: Subscription to cancel
            immediately: Cancel now or at period end
        """
        # Cancel in Stripe
        self.stripe.cancel_subscription(
            subscription.stripe_subscription_id,
            immediately=immediately
        )
        
        # Update local subscription
        if immediately:
            subscription.status = "canceled"
            subscription.end_date = datetime.utcnow()
        else:
            subscription.status = "canceling"
            # end_date remains at period end
        
        subscription.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(subscription)
        
        return subscription
    
    # =========================================================================
    # Subscription Status
    # =========================================================================
    
    def get_active_subscription(self, tenant_id: str) -> Optional[Subscription]:
        """Get active subscription for tenant"""
        return self.db.query(Subscription).filter(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_(["active", "trialing"])
        ).first()
    
    def is_subscription_active(self, tenant_id: str) -> bool:
        """Check if tenant has active subscription"""
        subscription = self.get_active_subscription(tenant_id)
        return subscription is not None and subscription.status in ["active", "trialing"]
    
    def can_sync(self, tenant_id: str) -> bool:
        """Check if tenant can perform sync based on subscription"""
        subscription = self.get_active_subscription(tenant_id)
        if not subscription:
            return False
        
        return subscription.status in ["active", "trialing"]
    
    def get_sync_frequency(self, tenant_id: str) -> int:
        """Get allowed sync frequency in minutes"""
        subscription = self.get_active_subscription(tenant_id)
        if not subscription:
            return 1440  # Default: once per day
        
        return subscription.sync_frequency_minutes
    
    # =========================================================================
    # Usage Tracking
    # =========================================================================
    
    def track_api_call(self, tenant_id: str) -> bool:
        """
        Track API call and check if within limits
        
        Returns:
            True if within limits, False if exceeded
        """
        subscription = self.get_active_subscription(tenant_id)
        if not subscription:
            return False
        
        subscription.api_calls_used += 1
        
        # Check if exceeded limit
        if subscription.api_calls_used > subscription.api_calls_limit:
            self.db.commit()
            return False
        
        self.db.commit()
        return True
    
    def reset_api_calls(self, tenant_id: str):
        """Reset API calls counter (call monthly)"""
        subscription = self.get_active_subscription(tenant_id)
        if subscription:
            subscription.api_calls_used = 0
            self.db.commit()
    
    # =========================================================================
    # Webhook Handlers
    # =========================================================================
    
    def handle_payment_succeeded(self, event_data: Dict[str, Any]):
        """Handle successful payment webhook"""
        subscription_id = event_data.get("subscription")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "active"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
    
    def handle_payment_failed(self, event_data: Dict[str, Any]):
        """Handle failed payment webhook"""
        subscription_id = event_data.get("subscription")
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "past_due"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
    
    def handle_subscription_canceled(self, event_data: Dict[str, Any]):
        """Handle subscription canceled webhook"""
        subscription_id = event_data["id"]
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            subscription.status = "canceled"
            subscription.end_date = datetime.utcnow()
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
    
    def handle_trial_ending(self, event_data: Dict[str, Any]):
        """Handle trial ending webhook"""
        subscription_id = event_data["id"]
        
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == subscription_id
        ).first()
        
        if subscription:
            # Send notification to tenant
            # TODO: Implement notification logic
            pass
