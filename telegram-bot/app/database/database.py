"""Подключение к базе данных."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool

from app.config import settings
from app.database.models import Base
from app.utils.logger import logger


# Получаем URL базы данных
db_url = settings.get_database_url()
logger.info(f"Database URL type: {'PostgreSQL' if 'postgresql' in db_url else 'SQLite'}")

# Настройки пула соединений для стабильной работы
engine_kwargs = {
    "echo": False,  # Установить True для отладки SQL запросов
}

# Для PostgreSQL используем пул соединений с оптимальными настройками
if "postgresql" in db_url:
    engine_kwargs.update({
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": 10,  # Количество постоянных соединений в пуле
        "max_overflow": 20,  # Дополнительные соединения при пиковой нагрузке
        "pool_timeout": 30,  # Тайм-аут ожидания свободного соединения
        "pool_recycle": 3600,  # Переподключение каждый час (защита от idle timeout)
        "pool_pre_ping": True,  # Проверка соединения перед использованием
    })
else:
    # Для SQLite используем NullPool (без пула)
    engine_kwargs["poolclass"] = NullPool

# Создаем асинхронный движок
engine = create_async_engine(db_url, **engine_kwargs)

# Фабрика сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Отключаем автоматический flush для лучшего контроля
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
    try:
        async with engine.begin() as conn:
            # Создаем все таблицы
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """Закрытие подключения к БД."""
    try:
        await engine.dispose()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
