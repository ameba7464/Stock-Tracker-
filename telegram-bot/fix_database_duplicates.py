"""
Скрипт для проверки и исправления дубликатов в базе данных.
Запускайте этот скрипт если в логах видны ошибки UniqueViolationError.
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям приложения
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import async_session_maker, init_db
from app.database.models import User
from app.utils.logger import logger


async def check_duplicates():
    """Проверка наличия дубликатов по telegram_id."""
    async with async_session_maker() as session:
        # Ищем telegram_id которые встречаются больше одного раза
        stmt = (
            select(User.telegram_id, func.count(User.id).label('count'))
            .group_by(User.telegram_id)
            .having(func.count(User.id) > 1)
        )
        
        result = await session.execute(stmt)
        duplicates = result.all()
        
        if duplicates:
            print(f"\n⚠️  Найдено {len(duplicates)} дубликатов:")
            for telegram_id, count in duplicates:
                print(f"   - telegram_id={telegram_id}: {count} записей")
            return True
        else:
            print("\n✅ Дубликаты не найдены")
            return False


async def fix_duplicates():
    """Исправление дубликатов - оставляем только самую новую запись для каждого telegram_id."""
    async with async_session_maker() as session:
        # Находим все telegram_id с дубликатами
        stmt = (
            select(User.telegram_id, func.count(User.id).label('count'))
            .group_by(User.telegram_id)
            .having(func.count(User.id) > 1)
        )
        
        result = await session.execute(stmt)
        duplicates = result.all()
        
        if not duplicates:
            print("\n✅ Дубликаты не найдены, исправление не требуется")
            return
        
        print(f"\n🔧 Начинаем исправление {len(duplicates)} дубликатов...")
        
        for telegram_id, count in duplicates:
            # Получаем все записи для этого telegram_id, отсортированные по дате создания
            stmt = (
                select(User)
                .where(User.telegram_id == telegram_id)
                .order_by(User.created_at.desc())
            )
            result = await session.execute(stmt)
            users = result.scalars().all()
            
            # Оставляем первую (самую новую) запись
            keep_user = users[0]
            delete_users = users[1:]
            
            print(f"\n   📌 telegram_id={telegram_id}:")
            print(f"      Оставляем: id={keep_user.id}, создан={keep_user.created_at}, имя={keep_user.full_name}")
            
            # Удаляем остальные записи
            for user in delete_users:
                print(f"      Удаляем: id={user.id}, создан={user.created_at}, имя={user.full_name}")
                await session.delete(user)
            
        # Сохраняем изменения
        await session.commit()
        print(f"\n✅ Дубликаты успешно исправлены!")


async def show_user_stats():
    """Показать статистику пользователей."""
    async with async_session_maker() as session:
        # Общее количество записей
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        total_records = result.scalar()
        
        # Количество уникальных telegram_id
        stmt = select(func.count(func.distinct(User.telegram_id)))
        result = await session.execute(stmt)
        unique_users = result.scalar()
        
        print("\n📊 Статистика базы данных:")
        print(f"   - Всего записей: {total_records}")
        print(f"   - Уникальных пользователей: {unique_users}")
        print(f"   - Дубликатов: {total_records - unique_users}")


async def main():
    """Главная функция."""
    print("=" * 70)
    print("🔍 ПРОВЕРКА И ИСПРАВЛЕНИЕ ДУБЛИКАТОВ В БАЗЕ ДАННЫХ")
    print("=" * 70)
    
    try:
        # Инициализируем подключение к БД
        await init_db()
        
        # Показываем статистику
        await show_user_stats()
        
        # Проверяем дубликаты
        has_duplicates = await check_duplicates()
        
        if has_duplicates:
            print("\n" + "=" * 70)
            response = input("\n❓ Хотите исправить дубликаты? (yes/no): ").strip().lower()
            
            if response in ['yes', 'y', 'да', 'д']:
                await fix_duplicates()
                
                # Проверяем еще раз после исправления
                print("\n" + "=" * 70)
                print("🔍 ПОВТОРНАЯ ПРОВЕРКА ПОСЛЕ ИСПРАВЛЕНИЯ")
                print("=" * 70)
                await show_user_stats()
                await check_duplicates()
            else:
                print("\n⏭️  Исправление пропущено")
        
        print("\n" + "=" * 70)
        print("✅ ПРОВЕРКА ЗАВЕРШЕНА")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Ошибка при работе скрипта: {e}", exc_info=True)
        print(f"\n❌ ОШИБКА: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
