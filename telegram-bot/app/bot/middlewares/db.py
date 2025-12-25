"""Middleware для работы с базой данных."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError

from app.database.database import async_session_maker
from app.utils.logger import logger


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
            try:
                return await handler(event, data)
            except IntegrityError as e:
                await session.rollback()
                logger.error(f"Database integrity error (duplicate key or constraint violation): {e}")
                
                # Отправляем пользователю понятное сообщение
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Произошла ошибка при сохранении данных. "
                            "Возможно, вы уже зарегистрированы. "
                            "Попробуйте использовать /start для входа."
                        )
                    except Exception:
                        pass
                
            except (OperationalError, SQLTimeoutError) as e:
                await session.rollback()
                logger.error(f"Database connection error: {e}")
                
                # Отправляем пользователю сообщение об ошибке подключения
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Временные проблемы с подключением к базе данных. "
                            "Пожалуйста, попробуйте снова через несколько секунд."
                        )
                    except Exception:
                        pass
                        
            except Exception as e:
                await session.rollback()
                logger.error(f"Unexpected database error, transaction rolled back: {e}", exc_info=True)
                
                # Отправляем пользователю общее сообщение об ошибке
                if isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Произошла непредвиденная ошибка. "
                            "Пожалуйста, попробуйте снова или обратитесь в поддержку."
                        )
                    except Exception:
                        pass

