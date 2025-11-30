"""Интеграция с Wildberries API и Google Sheets."""
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

# Добавляем путь к основному проекту (корень "Stock Tracker")
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from wildberries_complete_data_collector import WildberriesDataCollector
from app.services.google_sheets import google_sheets_service
from app.database.crud import update_user_api_key
from app.database.models import User
from app.utils.logger import logger


class WBIntegrationService:
    """Сервис для интеграции с Wildberries API и генерации таблиц."""
    
    async def validate_api_key(self, api_key: str) -> bool:
        """
        Валидация WB API ключа через реальный запрос.
        
        Args:
            api_key: API ключ для проверки
            
        Returns:
            True если ключ валидный
        """
        try:
            # Создаем коллектор
            collector = WildberriesDataCollector(api_key=api_key)
            
            # Пробуем запросить данные за последний день
            period_end = datetime.now()
            period_start = period_end - timedelta(days=1)
            
            # Делаем тестовый запрос
            funnel_data = collector.get_sales_funnel_data(
                period_start=period_start.strftime("%Y-%m-%d"),
                period_end=period_end.strftime("%Y-%m-%d")
            )
            
            # Если данные получены (даже пустые) - ключ валидный
            if funnel_data and 'data' in funnel_data:
                logger.info("API key validated successfully")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False
    
    async def setup_user_table(
        self,
        user: User,
        sheet_id: str,
        session: AsyncSession
    ) -> Optional[str]:
        """
        Настройка таблицы пользователя и первое заполнение данными.
        
        Args:
            user: Объект пользователя
            sheet_id: ID Google Таблицы
            session: Сессия БД
            
        Returns:
            URL таблицы или None
        """
        try:
            logger.info(f"Setting up table for user {user.telegram_id}, sheet_id: {sheet_id}")
            
            # 1. Получаем данные из WB API
            wb_data = await self._fetch_wb_data(user.wb_api_key)
            
            if not wb_data:
                logger.warning(f"No data fetched for user {user.telegram_id}")
                return None
            
            # 2. Обновляем таблицу
            success = await google_sheets_service.update_sheet(
                sheet_id=sheet_id,
                data=wb_data
            )
            
            if not success:
                logger.error(f"Failed to update sheet {sheet_id}")
                return None
            
            # 3. Сохраняем ID таблицы в БД
            user.google_sheet_id = sheet_id
            await session.commit()
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            logger.info(f"Table set up successfully: {sheet_url}")
            
            return sheet_url
            
        except Exception as e:
            logger.error(f"Error in setup_user_table: {e}", exc_info=True)
            return None
    
    async def update_existing_table(
        self,
        user: User,
        session: AsyncSession
    ) -> Optional[str]:
        """
        Обновление существующей таблицы пользователя.
        
        Args:
            user: Объект пользователя
            session: Сессия БД
            
        Returns:
            URL таблицы или None
        """
        try:
            if not user.google_sheet_id:
                logger.error(f"No sheet_id for user {user.telegram_id}")
                return None
            
            logger.info(f"Updating table for user {user.telegram_id}")
            
            # 1. Получаем данные из WB API
            wb_data = await self._fetch_wb_data(user.wb_api_key)
            
            if not wb_data:
                logger.warning(f"No data fetched for user {user.telegram_id}")
                return None
            
            # 2. Обновляем таблицу
            success = await google_sheets_service.update_sheet(
                sheet_id=user.google_sheet_id,
                data=wb_data
            )
            
            if not success:
                logger.error(f"Failed to update sheet {user.google_sheet_id}")
                return None
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{user.google_sheet_id}"
            logger.info(f"Table updated successfully: {sheet_url}")
            
            return sheet_url
            
        except Exception as e:
            logger.error(f"Error in update_existing_table: {e}", exc_info=True)
            return None

    async def generate_or_get_table(
        self,
        user: User,
        session: AsyncSession
    ) -> Optional[str]:
        """
        Генерация или получение существующей таблицы для пользователя.
        
        Args:
            user: Объект пользователя
            session: Сессия БД
            
        Returns:
            URL таблицы или None
        """
        try:
            logger.info(f"Starting table generation for user {user.telegram_id}")
            
            # 1. Получаем данные из WB API
            wb_data = await self._fetch_wb_data(user.wb_api_key)
            
            if not wb_data:
                logger.warning(f"No data fetched for user {user.telegram_id}")
                return None
            
            # 2. Создаем или обновляем Google Таблицу
            if user.google_sheet_id:
                # Обновляем существующую таблицу
                logger.info(f"Updating existing sheet: {user.google_sheet_id}")
                success = await google_sheets_service.update_sheet(
                    sheet_id=user.google_sheet_id,
                    data=wb_data
                )
                
                if success:
                    sheet_url = f"https://docs.google.com/spreadsheets/d/{user.google_sheet_id}"
                    logger.info(f"Sheet updated successfully: {sheet_url}")
                    return sheet_url
                else:
                    # Если не удалось обновить - создаем новую
                    logger.warning("Failed to update sheet, creating new one")
                    user.google_sheet_id = None
            
            # Создаем новую таблицу
            logger.info("Creating new Google Sheet")
            sheet_id = await google_sheets_service.create_sheet(
                user_name=user.name,
                telegram_id=user.telegram_id,
                data=wb_data
            )
            
            if not sheet_id:
                logger.error("Failed to create Google Sheet")
                return None
            
            # Сохраняем ID таблицы в БД
            user.google_sheet_id = sheet_id
            await session.commit()
            
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            logger.info(f"New sheet created: {sheet_url}")
            
            return sheet_url
            
        except Exception as e:
            logger.error(f"Error in generate_or_get_table: {e}", exc_info=True)
            return None
    
    async def _fetch_wb_data(self, api_key: str) -> Optional[list]:
        """
        Получение данных из Wildberries API.
        
        Args:
            api_key: WB API ключ
            
        Returns:
            Список ProductMetrics
        """
        try:
            logger.info("Fetching data from Wildberries API")
            
            # Создаем коллектор
            collector = WildberriesDataCollector(api_key=api_key)
            
            # Период - последние 7 дней
            period_end = datetime.now()
            period_start = period_end - timedelta(days=7)
            
            # Собираем полные данные
            products = collector.collect_complete_data(
                period_start=period_start.strftime("%Y-%m-%d"),
                period_end=period_end.strftime("%Y-%m-%d")
            )
            
            logger.info(f"Fetched {len(products)} products from WB API")
            return products
            
        except Exception as e:
            logger.error(f"Error fetching WB data: {e}", exc_info=True)
            return None


# Глобальный экземпляр сервиса
wb_integration = WBIntegrationService()
