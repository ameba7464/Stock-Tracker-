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
import traceback
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

print(f"[STARTUP] Python version: {sys.version}")
print(f"[STARTUP] Working directory: {os.getcwd()}")
print(f"[STARTUP] Python path: {sys.path[:3]}")

try:
    from stock_tracker.database.sheets import GoogleSheetsClient
    from stock_tracker.database.operations import SheetsOperations
    from stock_tracker.services.product_service import ProductService
    from stock_tracker.core.models import SyncStatus
    from stock_tracker.utils.logger import get_logger
    from stock_tracker.utils.config import get_config
    print("[STARTUP] ✅ All modules imported successfully")
except ImportError as e:
    print(f"[STARTUP] ❌ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

logger = get_logger(__name__)
logger.info("=" * 70)
logger.info("📦 Scheduler Service Starting...")
logger.info(f"Python: {sys.version}")
logger.info(f"Working Directory: {os.getcwd()}")
logger.info("=" * 70)


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
        logger.info("📝 Загрузка конфигурации...")
        config = get_config()
        logger.info("✅ Конфигурация загружена успешно")
        
        # Инициализация клиентов
        logger.info("📊 Подключение к Google Sheets...")
        try:
            sheets_client = GoogleSheetsClient(
                service_account_path=config.google_sheets.service_account_key_path,
                sheet_id=config.google_sheets.sheet_id
            )
            logger.info("✅ Google Sheets client инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Google Sheets: {e}")
            raise
        
        logger.info("🔧 Инициализация ProductService...")
        try:
            product_service = ProductService(config=config)
            logger.info("✅ ProductService инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ProductService: {e}")
            raise
        
        logger.info("✅ Подключение к Google Sheets установлено")
        
        # Синхронизация данных из Wildberries API в Google Sheets
        logger.info("🔄 Синхронизация данных из Wildberries API (Dual API: FBO + FBS)...")
        result = await product_service.sync_from_dual_api_to_sheets()
        
        logger.info("=" * 70)
        logger.info("✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!")
        logger.info(f"📊 Статус: {result.status.value if hasattr(result.status, 'value') else result.status}")
        logger.info(f"📦 Всего товаров: {result.products_total}")
        logger.info(f"✅ Обработано: {result.products_processed}")
        if result.products_failed > 0:
            logger.warning(f"⚠️  Ошибок: {result.products_failed}")
        if result.errors:
            logger.warning(f"❌ Первые ошибки:")
            for error in result.errors[:3]:
                logger.warning(f"   - {error}")
        logger.info(f"🕐 Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
        if hasattr(result, 'completed_at') and hasattr(result, 'started_at') and result.completed_at and result.started_at:
            duration = (result.completed_at - result.started_at).total_seconds()
            logger.info(f"⏱️  Длительность: {duration:.2f} сек")
        elif hasattr(result, 'duration') and result.duration:
            # duration может быть строкой или числом
            if isinstance(result.duration, (int, float)):
                logger.info(f"⏱️  Длительность: {result.duration:.2f} сек")
            else:
                logger.info(f"⏱️  Длительность: {result.duration}")
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
    
    # Запуск при старте сервиса (опционально, если установлена переменная)
    run_on_start = os.getenv('RUN_ON_START', 'false').lower() == 'true'
    
    if run_on_start:
        logger.info("🔄 Выполнение первоначального обновления при запуске сервиса...")
        try:
            await run_update()
        except Exception as e:
            logger.error(f"❌ Ошибка при первоначальном обновлении: {e}")
            logger.exception("Детали:")
    else:
        logger.info("⏭️  Пропуск первоначального обновления (RUN_ON_START=false)")
    
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


def main():
    """Main entry point with comprehensive error handling"""
    print("[MAIN] ========================================")
    print("[MAIN] Stock Tracker Scheduler Service v2.0")
    print("[MAIN] ========================================")
    print(f"[MAIN] Python: {sys.version}")
    print(f"[MAIN] Platform: {sys.platform}")
    print(f"[MAIN] CWD: {os.getcwd()}")
    print("[MAIN] ========================================")
    
    try:
        # Проверка переменных окружения
        print("[MAIN] Checking environment variables...")
        required_vars = ['WILDBERRIES_API_KEY', 'GOOGLE_SHEETS_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print(f"[MAIN] ❌ Missing environment variables: {', '.join(missing_vars)}")
            print(f"[MAIN] Available vars: {list(os.environ.keys())[:10]}...")
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
        
        print(f"[MAIN] ✅ Environment variables OK")
        logger.info("✅ Environment variables validated")
        
        # Запуск основного цикла
        print("[MAIN] Starting scheduler loop...")
        logger.info("🚀 Starting scheduler loop...")
        
        # Try asyncio.run (Python 3.7+)
        try:
            asyncio.run(scheduler_loop())
        except AttributeError:
            # Fallback for older Python versions
            print("[MAIN] Using fallback asyncio.get_event_loop()")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(scheduler_loop())
        
    except KeyboardInterrupt:
        print("\n[MAIN] Keyboard interrupt received")
        logger.info("⏹️  Scheduler остановлен пользователем")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[MAIN] ❌ CRITICAL ERROR: {e}")
        print("[MAIN] Traceback:")
        traceback.print_exc()
        
        try:
            logger.error(f"❌ Критическая ошибка при запуске: {e}")
            logger.exception("Детали:")
        except:
            pass  # Logger может не работать
        
        sys.exit(1)


if __name__ == "__main__":
    main()
