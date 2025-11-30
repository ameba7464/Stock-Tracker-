"""
Webhook dispatcher for sending notifications to external services.

Supports:
- Telegram bot notifications
- Custom webhook endpoints
- Retry logic for failed deliveries
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
import requests
from sqlalchemy.orm import Session

from ..database.models import Tenant, WebhookConfig

logger = logging.getLogger(__name__)

# Webhook timeout in seconds
WEBHOOK_TIMEOUT = 10
MAX_RETRIES = 3


def dispatch_webhook(
    tenant: Tenant,
    event_type: str,
    data: Dict[str, Any],
    db_session: Optional[Session] = None,
) -> bool:
    """
    Dispatch webhook notification to tenant's configured endpoints.
    
    Args:
        tenant: Tenant to send webhook for
        event_type: Type of event (sync_started, sync_completed, sync_failed, low_stock_alert)
        data: Event data payload
        db_session: Optional database session for updating webhook config
        
    Returns:
        bool: True if webhook delivered successfully, False otherwise
    """
    if not tenant.webhook_configs:
        logger.debug(f"No webhooks configured for tenant {tenant.id}")
        return False
    
    # Get active webhook configs for this event type
    active_webhooks = [
        wh for wh in tenant.webhook_configs
        if wh.is_active and event_type in wh.event_types
    ]
    
    if not active_webhooks:
        logger.debug(f"No active webhooks for event {event_type} on tenant {tenant.id}")
        return False
    
    success_count = 0
    
    for webhook in active_webhooks:
        try:
            delivered = _send_webhook(webhook, event_type, data)
            if delivered:
                success_count += 1
                # Reset failure count on success
                if db_session and webhook.failure_count > 0:
                    webhook.failure_count = 0
                    webhook.last_success_at = datetime.utcnow()
                    db_session.commit()
            else:
                # Increment failure count
                if db_session:
                    webhook.failure_count += 1
                    if webhook.failure_count >= MAX_RETRIES:
                        logger.warning(
                            f"Webhook {webhook.id} exceeded max failures, deactivating"
                        )
                        webhook.is_active = False
                    db_session.commit()
                    
        except Exception as e:
            logger.error(f"Error dispatching webhook {webhook.id}: {e}", exc_info=True)
            if db_session:
                webhook.failure_count += 1
                db_session.commit()
    
    return success_count > 0


def _send_webhook(
    webhook_config: WebhookConfig,
    event_type: str,
    data: Dict[str, Any],
) -> bool:
    """
    Send webhook HTTP request.
    
    Args:
        webhook_config: Webhook configuration
        event_type: Event type
        data: Event payload
        
    Returns:
        bool: True if delivered successfully
    """
    payload = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "StockTracker/1.0",
    }
    
    # Add custom headers if configured
    if webhook_config.headers:
        headers.update(webhook_config.headers)
    
    try:
        logger.info(f"Sending webhook to {webhook_config.url} for event {event_type}")
        
        response = requests.post(
            webhook_config.url,
            json=payload,
            headers=headers,
            timeout=WEBHOOK_TIMEOUT,
        )
        
        # Consider 2xx responses as success
        if 200 <= response.status_code < 300:
            logger.info(
                f"Webhook delivered successfully: {webhook_config.url} "
                f"(status: {response.status_code})"
            )
            return True
        else:
            logger.warning(
                f"Webhook delivery failed: {webhook_config.url} "
                f"(status: {response.status_code}, body: {response.text[:200]})"
            )
            return False
            
    except requests.exceptions.Timeout:
        logger.warning(f"Webhook timeout: {webhook_config.url}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook request failed: {webhook_config.url} - {e}")
        return False


def send_telegram_notification(
    chat_id: str,
    message: str,
    bot_token: str,
    parse_mode: str = "HTML",
) -> bool:
    """
    Send notification via Telegram Bot API.
    
    Args:
        chat_id: Telegram chat ID
        message: Message text
        bot_token: Bot token
        parse_mode: Message parse mode (HTML, Markdown, or None)
        
    Returns:
        bool: True if sent successfully
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=WEBHOOK_TIMEOUT)
        
        if response.status_code == 200:
            logger.info(f"Telegram notification sent to chat {chat_id}")
            return True
        else:
            logger.warning(
                f"Telegram notification failed: status {response.status_code}, "
                f"body: {response.text[:200]}"
            )
            return False
            
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


def format_sync_notification(event_type: str, data: Dict[str, Any]) -> str:
    """
    Format sync event into human-readable notification message.
    
    Args:
        event_type: Event type
        data: Event data
        
    Returns:
        str: Formatted message (HTML)
    """
    if event_type == "sync_started":
        return (
            f"🔄 <b>Синхронизация началась</b>\n"
            f"Время: {data.get('started_at', 'N/A')}"
        )
    
    elif event_type == "sync_completed":
        products_count = data.get('products_count', 0)
        duration = data.get('duration_seconds', 0)
        return (
            f"✅ <b>Синхронизация завершена</b>\n"
            f"Товаров: {products_count}\n"
            f"Время выполнения: {duration:.1f}с"
        )
    
    elif event_type == "sync_failed":
        error = data.get('error', 'Unknown error')
        return (
            f"❌ <b>Ошибка синхронизации</b>\n"
            f"Причина: {error}"
        )
    
    elif event_type == "low_stock_alert":
        product_name = data.get('product_name', 'N/A')
        quantity = data.get('quantity', 0)
        threshold = data.get('threshold', 0)
        return (
            f"⚠️ <b>Низкий остаток товара</b>\n"
            f"Товар: {product_name}\n"
            f"Остаток: {quantity} (порог: {threshold})"
        )
    
    else:
        return f"📢 <b>Событие: {event_type}</b>\n{json.dumps(data, indent=2)}"
