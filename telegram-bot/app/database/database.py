"""Подключение к базе данных."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database.models import Base
from app.utils.logger import logger


# Создаем асинхронный движок
# Для SQLite не используем pool_size и max_overflow
engine = create_async_engine(
    settings.database_url,
    echo=False,  # Установить True для отладки SQL запросов
)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор асинхронных сессий БД.
    
    Yields:
        AsyncSession: Сессия для работы с БД
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Инициализация базы данных (создание таблиц)."""
    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Закрытие подключения к БД."""
    await engine.dispose()
    logger.info("Database connection closed")
