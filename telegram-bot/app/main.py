"""Главная точка входа в приложение."""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.database import init_db, close_db
from app.bot.middlewares.db import DatabaseMiddleware
from app.bot.middlewares.payment import PaymentMiddleware
from app.bot.handlers import start, registration, menu, api_key
from app.services.scheduler import auto_update_scheduler
from app.utils.logger import logger


async def on_startup():
    """Действия при запуске бота."""
    logger.info("Bot is starting...")
    await init_db()
    
    # Запускаем планировщик автообновления таблиц
    auto_update_scheduler.start()
    
    logger.info("Bot started successfully!")


async def on_shutdown():
    """Действия при остановке бота."""
    logger.info("Bot is shutting down...")
    
    # Останавливаем планировщик
    auto_update_scheduler.stop()
    
    await close_db()
    logger.info("Bot stopped successfully!")


async def main():
    """Главная функция запуска бота."""
    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(PaymentMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(menu.router)
    dp.include_router(api_key.router)
    
    try:
        await on_startup()
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error during bot execution: {e}", exc_info=True)
    finally:
        await on_shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
