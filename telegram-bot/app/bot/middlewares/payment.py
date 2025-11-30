"""Middleware для обработки платежей (заглушка)."""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import settings
from app.utils.logger import logger


class PaymentMiddleware(BaseMiddleware):
    """
    Middleware для проверки статуса оплаты (заглушка для будущей интеграции).
    
    В будущем здесь будет логика проверки оплаты перед предоставлением доступа.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка события с проверкой статуса оплаты.
        
        Args:
            handler: Обработчик события
            event: Событие Telegram
            data: Данные контекста
            
        Returns:
            Результат обработчика
        """
        # ============================================
        # [ТОЧКА ИНТЕГРАЦИИ ПЛАТЕЖЕЙ]
        # ============================================
        # В будущем добавить логику:
        # if settings.payment_enabled:
        #     user_id = event.from_user.id
        #     if not await check_payment_status(user_id):
        #         await event.answer("Требуется оплата")
        #         return
        # ============================================
        
        # Пока просто пропускаем дальше
        return await handler(event, data)
