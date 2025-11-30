"""Сервис автоматического обновления таблиц по расписанию."""
import asyncio
from datetime import datetime
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import async_session_maker
from app.database.models import User
from app.services.wb_integration import wb_integration
from app.utils.logger import logger


class AutoUpdateScheduler:
    """Планировщик автоматического обновления таблиц пользователей."""
    
    def __init__(self):
        """Инициализация планировщика."""
        self.scheduler = AsyncIOScheduler(timezone='Europe/Moscow')
        self.is_running = False
    
    def start(self):
        """Запуск планировщика."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        try:
            # Добавляем задачу обновления в 00:01 МСК каждый день
            self.scheduler.add_job(
                self.update_all_user_tables,
                trigger=CronTrigger(hour=0, minute=1, timezone='Europe/Moscow'),
                id='daily_update',
                name='Daily table update at 00:01 MSK',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info("✅ Scheduler started successfully")
            logger.info("⏰ Next update scheduled for: 00:01 MSK daily")
            
            # Логируем время следующего запуска
            next_run = self.scheduler.get_job('daily_update').next_run_time
            logger.info(f"📅 Next run time: {next_run}")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    
    def stop(self):
        """Остановка планировщика."""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)
    
    async def update_all_user_tables(self):
        """
        Обновление таблиц всех пользователей.
        Вызывается автоматически по расписанию.
        """
        logger.info("=" * 70)
        logger.info("🔄 AUTOMATIC TABLE UPDATE STARTED")
        logger.info(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        updated_count = 0
        error_count = 0
        
        try:
            async with async_session_maker() as session:
                # Получаем всех пользователей с API ключами и таблицами
                result = await session.execute(
                    select(User).where(
                        User.wb_api_key.isnot(None),
                        User.google_sheet_id.isnot(None)
                    )
                )
                users = result.scalars().all()
                
                total_users = len(users)
                logger.info(f"📊 Found {total_users} users with configured tables")
                
                if total_users == 0:
                    logger.info("ℹ️ No users to update")
                    return
                
                # Обновляем таблицы каждого пользователя
                for i, user in enumerate(users, 1):
                    try:
                        logger.info(f"[{i}/{total_users}] Updating table for user {user.telegram_id} ({user.name})")
                        
                        # Обновляем таблицу
                        result = await wb_integration.update_existing_table(user, session)
                        
                        if result:
                            updated_count += 1
                            logger.info(f"✅ [{i}/{total_users}] User {user.telegram_id} updated successfully")
                        else:
                            error_count += 1
                            logger.warning(f"⚠️ [{i}/{total_users}] Failed to update user {user.telegram_id}")
                        
                        # Небольшая пауза между обновлениями для снижения нагрузки
                        if i < total_users:
                            await asyncio.sleep(2)
                        
                    except Exception as e:
                        error_count += 1
                        logger.error(f"❌ Error updating user {user.telegram_id}: {e}", exc_info=True)
                        continue
                
                # Итоговая статистика
                logger.info("=" * 70)
                logger.info("📊 UPDATE SUMMARY")
                logger.info(f"✅ Successfully updated: {updated_count}/{total_users}")
                logger.info(f"❌ Failed: {error_count}/{total_users}")
                logger.info(f"⏱️ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 70)
                
        except Exception as e:
            logger.error(f"Critical error in update_all_user_tables: {e}", exc_info=True)
    
    async def run_manual_update(self):
        """
        Ручной запуск обновления всех таблиц.
        Используется для тестирования или внеплановых обновлений.
        """
        logger.info("🔧 Manual update triggered")
        await self.update_all_user_tables()
    
    def get_next_run_time(self) -> datetime:
        """
        Получить время следующего запланированного обновления.
        
        Returns:
            Datetime следующего запуска
        """
        if not self.is_running:
            return None
        
        job = self.scheduler.get_job('daily_update')
        return job.next_run_time if job else None


# Глобальный экземпляр планировщика
auto_update_scheduler = AutoUpdateScheduler()
