"""Middleware для работы с базой данных."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import async_session_maker


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для добавления сессии БД в контекст обработчика."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с добавлением сессии БД.
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные контекста
            
        Returns:
            Результат обработчика
        """
        async with async_session_maker() as session:
            data['session'] = session
            return await handler(event, data)
