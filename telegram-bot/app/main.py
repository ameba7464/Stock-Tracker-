"""Главная точка входа в приложение."""
import asyncio
import os
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import settings
from app.database.database import init_db, close_db
from app.bot.middlewares.db import DatabaseMiddleware
from app.bot.middlewares.payment import PaymentMiddleware
from app.bot.handlers import start, registration, menu, api_key, profile
from app.services.scheduler import auto_update_scheduler
from app.utils.logger import logger

# Webhook settings
WEBHOOK_PATH = f"/webhook/{settings.bot_token}"
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else ""
USE_WEBHOOK = bool(WEBHOOK_HOST)


async def on_startup(bot: Bot):
    """Действия при запуске бота."""
    logger.info("Bot is starting...")
    
    # Устанавливаем команды бота для кнопки "Меню"
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    logger.info("Bot commands and menu button configured")
    
    # Логируем информацию о подключении к БД
    db_url = settings.get_database_url()
    db_type = "PostgreSQL" if "postgresql" in db_url else "SQLite"
    logger.info(f"Database type: {db_type}")
    if "postgresql" in db_url:
        # Скрываем пароль в логах
        safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
        logger.info(f"Database host: {safe_url}")
    
    await init_db()
    
    # Запускаем планировщик автообновления таблиц
    auto_update_scheduler.start()
    
    # Устанавливаем webhook если указан хост
    if USE_WEBHOOK:
        await bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    
    logger.info("Bot started successfully!")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    logger.info("Bot is shutting down...")
    
    # Останавливаем планировщик
    auto_update_scheduler.stop()
    
    # Удаляем webhook
    if USE_WEBHOOK:
        await bot.delete_webhook()
    
    await close_db()
    logger.info("Bot stopped successfully!")


async def main_polling():
    """Запуск бота в режиме polling (для разработки)."""
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(PaymentMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(profile.router)
    dp.include_router(menu.router)
    dp.include_router(api_key.router)
    
    try:
        await on_startup(bot)
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
        await on_shutdown(bot)
        await bot.session.close()


def main_webhook():
    """Запуск бота в режиме webhook (для production)."""
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация middleware
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(PaymentMiddleware())
    
    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(registration.router)
    dp.include_router(profile.router)
    dp.include_router(menu.router)
    dp.include_router(api_key.router)
    
    # Создаём aiohttp приложение
    app = web.Application()
    
    # Health check endpoint
    async def health_check(request):
        return web.json_response({"status": "ok"})
    
    app.router.add_get("/health", health_check)
    app.router.add_get("/", health_check)
    
    # Настраиваем webhook handler
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Startup/shutdown hooks
    async def on_startup_wrapper(app):
        await on_startup(bot)
    
    async def on_shutdown_wrapper(app):
        await on_shutdown(bot)
        await bot.session.close()
    
    app.on_startup.append(on_startup_wrapper)
    app.on_shutdown.append(on_shutdown_wrapper)
    
    # Запускаем сервер
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting webhook server on port {port}")
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    try:
        if USE_WEBHOOK:
            main_webhook()
        else:
            asyncio.run(main_polling())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
