#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway.app Scheduler Service
Постоянно работает и запускает обновления по расписанию.
Полностью автономное решение для автоматического обновления таблицы.

Работает 24/7 на Railway.app без зависимости от локального ПК.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Установка кодировки UTF-8
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Установка рабочей директории
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir / 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.services.product_service import ProductService
from stock_tracker.core.models import SyncStatus
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config

logger = get_logger(__name__)


async def run_update():
    """
    Запускает обновление таблицы Google Sheets.
    
    Returns:
        bool: True если обновление успешно, False в случае ошибки
    """
    logger.info("=" * 70)
    logger.info(f"🚀 Начало автоматического обновления")
    logger.info(f"🕐 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info("=" * 70)
    
    try:
        # Загрузка конфигурации
        config = get_config()
        logger.info("✅ Конфигурация загружена успешно")
        
        # Инициализация клиентов
        logger.info("📊 Подключение к Google Sheets...")
        sheets_client = GoogleSheetsClient(
            credentials_path=config.google_sheets.service_account_key_path,
            sheet_id=config.google_sheets.sheet_id
        )
        
        operations = SheetsOperations(sheets_client)
        product_service = ProductService(api_key=config.wildberries.api_key)
        
        logger.info("✅ Подключение к Google Sheets установлено")
        
        # Получение данных из Wildberries API
        logger.info("🔄 Получение данных из Wildberries API...")
        logger.info("   📦 Получение остатков (Dual API: FBO + FBS)...")
        stocks_data = await product_service.get_all_stocks_dual_api()
        
        logger.info("   📋 Получение заказов...")
        orders_data = await product_service.get_orders()
        
        logger.info(f"✅ Данные получены:")
        logger.info(f"   📦 Товаров: {len(stocks_data)}")
        logger.info(f"   📋 Заказов: {len(orders_data)}")
        
        # Обновление таблицы
        logger.info("📝 Обновление Google Sheets...")
        result = await operations.update_table_data(stocks_data, orders_data)
        
        logger.info("=" * 70)
        logger.info("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        logger.info(f"📊 Статус: {result.status}")
        logger.info(f"📦 Обработано товаров: {result.products_processed}")
        if result.errors:
            logger.warning(f"⚠️  Ошибки: {len(result.errors)}")
            for error in result.errors[:5]:  # Показываем первые 5 ошибок
                logger.warning(f"   - {error}")
        logger.info(f"🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error("=" * 70)
        logger.error("❌ ОШИБКА ПРИ ОБНОВЛЕНИИ!")
        logger.error(f"💥 {type(e).__name__}: {e}")
        logger.error("=" * 70)
        logger.exception("Детальная информация об ошибке:")
        return False


async def scheduler_loop():
    """
    Основной цикл scheduler.
    Работает постоянно и запускает обновления по расписанию.
    """
    logger.info("=" * 70)
    logger.info("🚀 STOCK TRACKER SCHEDULER SERVICE")
    logger.info("=" * 70)
    logger.info("🌐 Работает на Railway.app")
    logger.info("⏰ Расписание: каждый день в 00:01 МСК (21:01 UTC)")
    logger.info("🔄 Режим: непрерывная работа 24/7")
    logger.info("=" * 70)
    
    # Запуск при старте сервиса
    logger.info("🔄 Выполнение первоначального обновления при запуске сервиса...")
    await run_update()
    
    # Основной цикл
    while True:
        try:
            # Текущее время UTC
            now = datetime.now(timezone.utc)
            
            # Целевое время: 21:01 UTC (00:01 МСК)
            target_hour = 21
            target_minute = 1
            
            # Вычисляем секунды с начала дня
            current_seconds = now.hour * 3600 + now.minute * 60 + now.second
            target_seconds = target_hour * 3600 + target_minute * 60
            
            # Вычисляем время до следующего запуска
            if current_seconds < target_seconds:
                # Сегодня еще не было запуска в целевое время
                seconds_until_next = target_seconds - current_seconds
            else:
                # Запуск уже был сегодня, ждем завтра
                seconds_until_next = (24 * 3600) - current_seconds + target_seconds
            
            hours = seconds_until_next // 3600
            minutes = (seconds_until_next % 3600) // 60
            
            next_run_time = datetime.fromtimestamp(now.timestamp() + seconds_until_next)
            
            logger.info("=" * 70)
            logger.info("⏳ ОЖИДАНИЕ СЛЕДУЮЩЕГО ЗАПУСКА")
            logger.info(f"⏰ Текущее время UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"🎯 Следующий запуск через: {hours}ч {minutes}м")
            logger.info(f"📅 Время следующего запуска: {next_run_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            logger.info("=" * 70)
            
            # Периодически показываем, что сервис жив
            # Разбиваем ожидание на интервалы по 1 часу
            remaining_seconds = seconds_until_next
            while remaining_seconds > 0:
                sleep_time = min(3600, remaining_seconds)  # Максимум 1 час
                await asyncio.sleep(sleep_time)
                remaining_seconds -= sleep_time
                
                if remaining_seconds > 0:
                    hours_left = remaining_seconds // 3600
                    minutes_left = (remaining_seconds % 3600) // 60
                    logger.info(f"💓 Сервис активен. До следующего запуска: {hours_left}ч {minutes_left}м")
            
            # Запускаем обновление
            logger.info("🎯 Время запланированного обновления наступило!")
            await run_update()
            
        except KeyboardInterrupt:
            logger.info("⏹️  Получен сигнал остановки (Ctrl+C)")
            break
            
        except Exception as e:
            logger.error("=" * 70)
            logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА В SCHEDULER!")
            logger.error(f"💥 {type(e).__name__}: {e}")
            logger.error("=" * 70)
            logger.exception("Детальная информация об ошибке:")
            
            # Ждем 1 час перед повторной попыткой
            logger.info("⏳ Ожидание 1 час перед повторной попыткой...")
            await asyncio.sleep(3600)
    
    logger.info("=" * 70)
    logger.info("⏹️  Scheduler Service остановлен")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        # Запуск основного цикла
        asyncio.run(scheduler_loop())
        
    except KeyboardInterrupt:
        logger.info("⏹️  Scheduler остановлен пользователем")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        logger.exception("Детали:")
        sys.exit(1)
