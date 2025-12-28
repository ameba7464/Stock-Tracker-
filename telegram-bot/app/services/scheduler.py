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
            
            logger.info("[OK] Scheduler started successfully")
            logger.info("[SCHEDULE] Next update scheduled for: 00:01 MSK daily")
            
            # Логируем время следующего запуска
            next_run = self.scheduler.get_job('daily_update').next_run_time
            logger.info(f"[SCHEDULE] Next run time: {next_run}")
            
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
        Параллельное обновление таблиц всех пользователей.
        
        Ключевое отличие: каждый пользователь имеет СВОЙ API ключ WB,
        поэтому rate limit 3 req/min применяется ОТДЕЛЬНО к каждому.
        Это позволяет обновлять всех пользователей ОДНОВРЕМЕННО!
        """
        logger.info("=" * 70)
        logger.info("[UPDATE] PARALLEL TABLE UPDATE STARTED")
        logger.info(f"[TIME] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)
        
        start_time = datetime.now()
        
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
                logger.info(f"[STATS] Found {total_users} users with configured tables")
                
                if total_users == 0:
                    logger.info("[INFO] No users to update")
                    return
                
                # Определяем максимальное количество одновременных обновлений
                # Ограничиваем для защиты от перегрузки сервера и Google Sheets API
                max_concurrent = min(20, total_users)  # До 20 параллельных обновлений
                semaphore = asyncio.Semaphore(max_concurrent)
                
                logger.info(f"[PARALLEL] Will process {total_users} users with max {max_concurrent} concurrent tasks")
                
                async def update_single_user(user: User, index: int) -> tuple[bool, str]:
                    """
                    Обновление одного пользователя с контролем параллелизма.
                    
                    Args:
                        user: Объект пользователя
                        index: Номер в списке (для логирования)
                    
                    Returns:
                        (success: bool, message: str)
                    """
                    async with semaphore:
                        try:
                            logger.info(
                                f"[{index}/{total_users}] Starting update for user {user.telegram_id} "
                                f"({user.full_name})"
                            )
                            
                            # Создаем отдельную сессию для каждого пользователя
                            # Это критично для параллельной работы!
                            async with async_session_maker() as user_session:
                                result = await wb_integration.update_existing_table(user, user_session)
                                
                                if result:
                                    logger.info(
                                        f"[OK] [{index}/{total_users}] User {user.telegram_id} "
                                        f"updated successfully"
                                    )
                                    return True, "success"
                                else:
                                    logger.warning(
                                        f"[WARNING] [{index}/{total_users}] Failed to update "
                                        f"user {user.telegram_id}"
                                    )
                                    return False, "update_failed"
                        
                        except Exception as e:
                            logger.error(
                                f"[ERROR] Error updating user {user.telegram_id}: {e}",
                                exc_info=True
                            )
                            return False, f"exception: {type(e).__name__}"
                
                # Запускаем ВСЕ задачи параллельно с asyncio.gather
                # gather автоматически управляет параллелизмом через semaphore
                tasks = [
                    update_single_user(user, i+1) 
                    for i, user in enumerate(users)
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Подсчет статистики
                updated_count = sum(1 for r in results if isinstance(r, tuple) and r[0] is True)
                error_count = sum(1 for r in results if isinstance(r, tuple) and r[0] is False)
                exception_count = sum(1 for r in results if isinstance(r, Exception))
                
                duration = (datetime.now() - start_time).total_seconds()
                avg_time = duration / total_users if total_users > 0 else 0
                
                # Итоговая статистика
                logger.info("=" * 70)
                logger.info("[SUMMARY] PARALLEL UPDATE SUMMARY")
                logger.info(f"[OK] Successfully updated: {updated_count}/{total_users}")
                logger.info(f"[ERROR] Failed: {error_count}/{total_users}")
                logger.info(f"[EXCEPTION] Exceptions: {exception_count}/{total_users}")
                logger.info(f"[TIME] Total duration: {duration:.1f}s")
                logger.info(f"[TIME] Average per user: {avg_time:.1f}s")
                logger.info(f"[TIME] Speedup vs sequential: ~{total_users * 60 / duration:.1f}x")
                logger.info(f"[TIME] Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 70)
                
        except Exception as e:
            logger.error(f"Critical error in update_all_user_tables: {e}", exc_info=True)
    
    async def run_manual_update(self):
        """
        Ручной запуск обновления всех таблиц.
        Используется для тестирования или внеплановых обновлений.
        """
        logger.info("[MANUAL] Manual update triggered")
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
