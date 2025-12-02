"""CRUD операции для работы с БД."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.utils.logger import logger


async def get_user_by_telegram_id(
    session: AsyncSession, 
    telegram_id: int
) -> Optional[User]:
    """
    Получить пользователя по Telegram ID.
    
    Args:
        session: Сессия БД
        telegram_id: Telegram ID пользователя
        
    Returns:
        User или None если не найден
    """
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    name: str,
    email: str,
    phone: str
) -> User:
    """
    Создать нового пользователя.
    
    Args:
        session: Сессия БД
        telegram_id: Telegram ID
        name: Имя пользователя
        email: Email
        phone: Телефон
        
    Returns:
        Созданный пользователь
    """
    user = User(
        telegram_id=telegram_id,
        name=name,
        email=email,
        phone=phone,
        payment_status='pending',
        google_sheet_sent=False
    )
    
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User created: telegram_id={telegram_id}, name={name}")
    return user


async def update_user_payment_status(
    session: AsyncSession,
    user: User,
    status: str
) -> User:
    """
    Обновить статус оплаты пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        status: Новый статус ('pending', 'completed', 'failed')
        
    Returns:
        Обновленный пользователь
    """
    user.payment_status = status
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User payment status updated: telegram_id={user.telegram_id}, status={status}")
    return user


async def mark_google_sheet_sent(
    session: AsyncSession,
    user: User
) -> User:
    """
    Отметить что таблица была отправлена пользователю.
    
    Args:
        session: Сессия БД
        user: Пользователь
        
    Returns:
        Обновленный пользователь
    """
    user.google_sheet_sent = True
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"Google sheet marked as sent: telegram_id={user.telegram_id}")
    return user


async def update_user_api_key(
    session: AsyncSession,
    user: User,
    api_key: str
) -> User:
    """
    Обновить WB API ключ пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        api_key: Новый API ключ
        
    Returns:
        Обновленный пользователь
    """
    user.wb_api_key = api_key
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User API key updated: telegram_id={user.telegram_id}")
    return user


async def update_user_name(
    session: AsyncSession,
    user: User,
    name: str
) -> User:
    """
    Обновить имя пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        name: Новое имя
        
    Returns:
        Обновленный пользователь
    """
    user.name = name
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User name updated: telegram_id={user.telegram_id}, name={name}")
    return user


async def update_user_email(
    session: AsyncSession,
    user: User,
    email: str
) -> User:
    """
    Обновить email пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        email: Новый email
        
    Returns:
        Обновленный пользователь
    """
    user.email = email
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User email updated: telegram_id={user.telegram_id}, email={email}")
    return user


async def update_user_phone(
    session: AsyncSession,
    user: User,
    phone: str
) -> User:
    """
    Обновить телефон пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        phone: Новый телефон
        
    Returns:
        Обновленный пользователь
    """
    user.phone = phone
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User phone updated: telegram_id={user.telegram_id}, phone={phone}")
    return user


async def delete_user_api_key(
    session: AsyncSession,
    user: User
) -> User:
    """
    Удалить API ключ пользователя.
    
    Args:
        session: Сессия БД
        user: Пользователь
        
    Returns:
        Обновленный пользователь
    """
    user.wb_api_key = None
    await session.commit()
    await session.refresh(user)
    
    logger.info(f"User API key deleted: telegram_id={user.telegram_id}")
    return user
