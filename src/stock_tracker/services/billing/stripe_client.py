"""
Stripe API client for billing integration
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import stripe
from stripe.error import StripeError

from stock_tracker.core.config import get_settings


class StripeClient:
    """
    Stripe API client for handling subscriptions and payments
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Stripe client"""
        settings = get_settings()
        self.api_key = api_key or settings.STRIPE_API_KEY
        stripe.api_key = self.api_key
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    # =========================================================================
    # Customer Management
    # =========================================================================
    
    def create_customer(
        self,
        email: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.Customer:
        """
        Create a new Stripe customer
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata (tenant_id, etc.)
        
        Returns:
            stripe.Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            return customer
        except StripeError as e:
            raise Exception(f"Failed to create Stripe customer: {str(e)}")
    
    def get_customer(self, customer_id: str) -> stripe.Customer:
        """Get customer by ID"""
        try:
            return stripe.Customer.retrieve(customer_id)
        except StripeError as e:
            raise Exception(f"Failed to retrieve customer: {str(e)}")
    
    def update_customer(
        self,
        customer_id: str,
        **kwargs
    ) -> stripe.Customer:
        """Update customer information"""
        try:
            return stripe.Customer.modify(customer_id, **kwargs)
        except StripeError as e:
            raise Exception(f"Failed to update customer: {str(e)}")
    
    def delete_customer(self, customer_id: str) -> Dict[str, Any]:
        """Delete customer"""
        try:
            return stripe.Customer.delete(customer_id)
        except StripeError as e:
            raise Exception(f"Failed to delete customer: {str(e)}")
    
    # =========================================================================
    # Subscription Management
    # =========================================================================
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.Subscription:
        """
        Create a new subscription
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID (from dashboard)
            trial_days: Number of trial days (optional)
            metadata: Additional metadata
        
        Returns:
            stripe.Subscription object
        """
        try:
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {}
            }
            
            if trial_days:
                params["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**params)
            return subscription
        except StripeError as e:
            raise Exception(f"Failed to create subscription: {str(e)}")
    
    def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Get subscription by ID"""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except StripeError as e:
            raise Exception(f"Failed to retrieve subscription: {str(e)}")
    
    def update_subscription(
        self,
        subscription_id: str,
        **kwargs
    ) -> stripe.Subscription:
        """Update subscription (change plan, quantity, etc.)"""
        try:
            return stripe.Subscription.modify(subscription_id, **kwargs)
        except StripeError as e:
            raise Exception(f"Failed to update subscription: {str(e)}")
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> stripe.Subscription:
        """
        Cancel subscription
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: If True, cancel immediately; otherwise, at period end
        """
        try:
            if immediately:
                return stripe.Subscription.cancel(subscription_id)
            else:
                return stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
        except StripeError as e:
            raise Exception(f"Failed to cancel subscription: {str(e)}")
    
    def list_subscriptions(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[stripe.Subscription]:
        """
        List subscriptions
        
        Args:
            customer_id: Filter by customer
            status: Filter by status (active, past_due, canceled, etc.)
            limit: Maximum number to return
        """
        try:
            params = {"limit": limit}
            if customer_id:
                params["customer"] = customer_id
            if status:
                params["status"] = status
            
            subscriptions = stripe.Subscription.list(**params)
            return subscriptions.data
        except StripeError as e:
            raise Exception(f"Failed to list subscriptions: {str(e)}")
    
    # =========================================================================
    # Checkout Session
    # =========================================================================
    
    def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.checkout.Session:
        """
        Create Stripe Checkout session
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            trial_days: Number of trial days
            metadata: Additional metadata
        
        Returns:
            stripe.checkout.Session with URL to redirect user
        """
        try:
            params = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{
                    "price": price_id,
                    "quantity": 1,
                }],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {}
            }
            
            if trial_days:
                params["subscription_data"] = {
                    "trial_period_days": trial_days
                }
            
            session = stripe.checkout.Session.create(**params)
            return session
        except StripeError as e:
            raise Exception(f"Failed to create checkout session: {str(e)}")
    
    # =========================================================================
    # Customer Portal
    # =========================================================================
    
    def create_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> stripe.billing_portal.Session:
        """
        Create Customer Portal session for managing subscription
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session
        
        Returns:
            stripe.billing_portal.Session with URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session
        except StripeError as e:
            raise Exception(f"Failed to create portal session: {str(e)}")
    
    # =========================================================================
    # Webhooks
    # =========================================================================
    
    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str
    ) -> stripe.Event:
        """
        Verify and construct webhook event
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
        
        Returns:
            stripe.Event object
        
        Raises:
            ValueError: If signature verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError as e:
            raise ValueError(f"Invalid webhook payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid webhook signature: {str(e)}")
    
    # =========================================================================
    # Prices & Products
    # =========================================================================
    
    def list_prices(
        self,
        product_id: Optional[str] = None,
        active: bool = True
    ) -> List[stripe.Price]:
        """List available prices"""
        try:
            params = {"active": active, "limit": 100}
            if product_id:
                params["product"] = product_id
            
            prices = stripe.Price.list(**params)
            return prices.data
        except StripeError as e:
            raise Exception(f"Failed to list prices: {str(e)}")
    
    def list_products(self, active: bool = True) -> List[stripe.Product]:
        """List available products"""
        try:
            products = stripe.Product.list(active=active, limit=100)
            return products.data
        except StripeError as e:
            raise Exception(f"Failed to list products: {str(e)}")
    
    # =========================================================================
    # Usage-based Billing
    # =========================================================================
    
    def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[datetime] = None,
        action: str = "increment"
    ) -> stripe.UsageRecord:
        """
        Report usage for metered billing
        
        Args:
            subscription_item_id: Subscription item ID
            quantity: Usage quantity
            timestamp: Usage timestamp (defaults to now)
            action: 'increment' or 'set'
        """
        try:
            params = {
                "quantity": quantity,
                "action": action,
            }
            if timestamp:
                params["timestamp"] = int(timestamp.timestamp())
            
            usage_record = stripe.SubscriptionItem.create_usage_record(
                subscription_item_id,
                **params
            )
            return usage_record
        except StripeError as e:
            raise Exception(f"Failed to report usage: {str(e)}")


# =============================================================================
# Singleton instance
# =============================================================================

_stripe_client: Optional[StripeClient] = None


def get_stripe_client() -> StripeClient:
    """Get or create Stripe client singleton"""
    global _stripe_client
    if _stripe_client is None:
        _stripe_client = StripeClient()
    return _stripe_client
