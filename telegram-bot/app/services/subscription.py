"""
Subscription service for unified access control.

This module provides a unified interface for checking user access
across telegram bot and admin panel.

Feature Flag Support:
- payment_enabled = False → Free access for everyone (MVP mode)
- payment_enabled = True → Check subscription.has_access
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User, Subscription
from app.utils.logger import logger


async def check_user_access(user_id: UUID, session: AsyncSession) -> bool:
    """
    Единая проверка доступа пользователя к сервису.
    
    Логика работы:
    1. Если payment_enabled=False (MVP режим) → все имеют доступ
    2. Если payment_enabled=True (продакшн) → проверяем subscription.has_access
    3. Если у пользователя нет записи subscription → создаем с FREE статусом
    
    Args:
        user_id: UUID пользователя
        session: AsyncSession для работы с БД
        
    Returns:
        bool: True если пользователь имеет доступ, False иначе
        
    Example:
        >>> has_access = await check_user_access(user.id, session)
        >>> if not has_access:
        >>>     await message.answer("Для доступа необходима подписка")
        >>>     return
    """
    # MVP режим: все имеют бесплатный доступ
    if not settings.payment_enabled:
        logger.debug(f"Payment disabled - granting free access to user {user_id}")
        return True
    
    # Продакшн режим: проверяем подписку
    try:
        result = await session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        # Если подписки нет → создаем с бесплатным доступом (legacy users)
        if not subscription:
            logger.info(f"Creating FREE subscription for legacy user {user_id}")
            subscription = Subscription(
                user_id=user_id,
                status='FREE',
                has_access=True,
                subscription_starts_at=datetime.utcnow()
            )
            session.add(subscription)
            await session.commit()
            return True
        
        # Проверяем истек ли триал или подписка
        if subscription.status == 'TRIAL' and subscription.trial_ends_at:
            if datetime.utcnow() > subscription.trial_ends_at:
                logger.info(f"Trial expired for user {user_id}")
                subscription.status = 'EXPIRED'
                subscription.has_access = False
                await session.commit()
                return False
        
        if subscription.status == 'PAID' and subscription.subscription_ends_at:
            if datetime.utcnow() > subscription.subscription_ends_at:
                logger.info(f"Subscription expired for user {user_id}")
                subscription.status = 'EXPIRED'
                subscription.has_access = False
                await session.commit()
                return False
        
        return subscription.has_access
        
    except Exception as e:
        logger.error(f"Error checking user access: {e}", exc_info=True)
        # В случае ошибки даем доступ (fail-open для лучшего UX)
        return True


async def get_or_create_subscription(user_id: UUID, session: AsyncSession):
    """
    Получить существующую подписку или создать новую.
    
    Args:
        user_id: UUID пользователя
        session: AsyncSession для работы с БД
        
    Returns:
        Subscription: Объект подписки
    """
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        # Создаем новую подписку
        if settings.payment_enabled:
            # Если платежи включены → даем триал
            subscription = Subscription(
                user_id=user_id,
                status='TRIAL',
                has_access=True,
                trial_ends_at=datetime.utcnow() + timedelta(days=settings.free_trial_days)
            )
            logger.info(f"Created TRIAL subscription for user {user_id}")
        else:
            # Если платежи выключены → даем бесплатный доступ
            subscription = Subscription(
                user_id=user_id,
                status='FREE',
                has_access=True,
                subscription_starts_at=datetime.utcnow()
            )
            logger.info(f"Created FREE subscription for user {user_id}")
        
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
    
    return subscription


async def grant_paid_access(
    user_id: UUID,
    session: AsyncSession,
    payment_provider: str,
    payment_id: str,
    duration_days: int = 30
):
    """
    Выдать платный доступ пользователю после успешной оплаты.
    
    Args:
        user_id: UUID пользователя
        session: AsyncSession для работы с БД
        payment_provider: Провайдер оплаты (yookassa, stripe, etc)
        payment_id: ID транзакции в системе провайдера
        duration_days: Длительность подписки в днях (по умолчанию 30)
    """
    subscription = await get_or_create_subscription(user_id, session)
    
    now = datetime.utcnow()
    
    # Обновляем подписку
    subscription.status = 'PAID'
    subscription.has_access = True
    subscription.payment_provider = payment_provider
    subscription.payment_external_id = payment_id
    subscription.last_payment_at = now
    
    # Продлеваем подписку
    if subscription.subscription_ends_at and subscription.subscription_ends_at > now:
        # Если текущая подписка еще активна → продлеваем от даты окончания
        subscription.subscription_ends_at += timedelta(days=duration_days)
    else:
        # Если подписка истекла или новая → устанавливаем новые даты
        subscription.subscription_starts_at = now
        subscription.subscription_ends_at = now + timedelta(days=duration_days)
    
    await session.commit()
    await session.refresh(subscription)
    
    logger.info(
        f"Granted PAID access to user {user_id} "
        f"until {subscription.subscription_ends_at} "
        f"via {payment_provider} (payment_id: {payment_id})"
    )
    
    return subscription


async def revoke_access(user_id: UUID, session: AsyncSession):
    """
    Отозвать доступ пользователя (например, при возврате платежа).
    
    Args:
        user_id: UUID пользователя
        session: AsyncSession для работы с БД
    """
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    
    if subscription:
        subscription.status = 'EXPIRED'
        subscription.has_access = False
        await session.commit()
        
        logger.warning(f"Revoked access for user {user_id}")


async def get_subscription_info(user_id: UUID, session: AsyncSession) -> dict:
    """
    Получить информацию о подписке пользователя.
    
    Args:
        user_id: UUID пользователя
        session: AsyncSession для работы с БД
        
    Returns:
        dict: Информация о подписке в удобном формате
    """
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return {
            'status': 'NO_SUBSCRIPTION',
            'has_access': not settings.payment_enabled,  # Бесплатный доступ если платежи выключены
            'days_remaining': None,
            'is_trial': False,
            'is_paid': False
        }
    
    days_remaining = None
    if subscription.subscription_ends_at:
        delta = subscription.subscription_ends_at - datetime.utcnow()
        days_remaining = max(0, delta.days)
    elif subscription.trial_ends_at:
        delta = subscription.trial_ends_at - datetime.utcnow()
        days_remaining = max(0, delta.days)
    
    return {
        'status': subscription.status,
        'has_access': subscription.has_access,
        'days_remaining': days_remaining,
        'is_trial': subscription.status == 'TRIAL',
        'is_paid': subscription.status == 'PAID',
        'subscription_ends_at': subscription.subscription_ends_at,
        'trial_ends_at': subscription.trial_ends_at
    }
