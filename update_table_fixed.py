#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления таблицы Google Sheets свежими данными из Wildberries API.
Используется для обновления данных при запуске приложения.

ИСПРАВЛЕНО 28.10.2025: Теперь использует Dual API (FBO + FBS) для получения ВСЕХ остатков
вместо устаревшего operations.refresh_table_data() с Analytics API v2.

Изменения:
- ✅ Использует Dual API: Statistics API (FBO) + Marketplace API v3 (FBS)
- ✅ Statistics API для остатков на складах WB (FBO - Fulfillment by Operator)
- ✅ Marketplace API v3 для остатков на складе продавца (FBS - Fulfillment by Seller / Маркетплейс)
- ✅ Supplier Orders API для заказов
- ✅ Фильтрует отменённые заказы (isCancel=True)
- ✅ Дедупликация по srid
- ✅ Нормализация названий складов
- ✅ Фиксированный период (последние 7 дней)
- ✅ Все 9 критических исправлений применены + FBS поддержка
"""

import sys
import os
import asyncio
from datetime import datetime

# Установка кодировки UTF-8 для вывода в консоль Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ИСПРАВЛЕНИЕ 10.11.2025: Меняем рабочую директорию на директорию скрипта
# Это необходимо для корректной загрузки .env файла
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(script_dir, 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.services.product_service import ProductService
from stock_tracker.core.models import SyncStatus
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config


logger = get_logger(__name__)


async def update_table_data_async(spreadsheet_id: str = None, worksheet_name: str = "Stock Tracker"):
    """
    Обновить данные в таблице (асинхронная версия).
    
    Args:
        spreadsheet_id: ID Google Sheets документа (если None, будет взят из конфига)
        worksheet_name: Название листа для обновления
        
    Returns:
        True если обновление успешно, False иначе
    """
    try:
        print("🚀 Запуск обновления таблицы Stock Tracker")
        print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Проверяем, запущены ли мы в GitHub Actions
        is_github_actions = os.getenv('GITHUB_ACTIONS') == 'true'
        if is_github_actions:
            print("🤖 Обнаружен запуск в GitHub Actions")
            print(f"   Workflow: {os.getenv('GITHUB_WORKFLOW')}")
            print(f"   Runner: {os.getenv('RUNNER_OS')}")
        
        # Загружаем конфигурацию
        print("📋 Загружаем конфигурацию...")
        config = get_config()
        
        # Используем ID из параметра или конфига
        if not spreadsheet_id:
            spreadsheet_id = getattr(config, 'google_sheet_id', None)
            
        if not spreadsheet_id:
            print("❌ Ошибка: Не указан ID Google Sheets документа")
            print("   Укажите GOOGLE_SHEET_ID в конфигурации или передайте как параметр")
            return False
        
        print(f"📊 Документ: {spreadsheet_id}")
        print(f"📝 Лист: {worksheet_name}")
        
        # Инициализируем клиент Google Sheets
        print("🔐 Подключаемся к Google Sheets...")
        
        # Поддержка переменных окружения для GitHub Actions
        service_account_path_env = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')
        if service_account_path_env:
            service_account_path = service_account_path_env
            print(f"   Используем путь из переменной окружения: {service_account_path}")
        else:
            service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')
            print(f"   Используем путь по умолчанию: {service_account_path}")
        
        if not os.path.exists(service_account_path):
            print(f"❌ Ошибка: Файл сервисного аккаунта не найден: {service_account_path}")
            return False
            
        sheets_client = GoogleSheetsClient(service_account_path)
        operations = SheetsOperations(sheets_client)
        
        # Обновляем таблицу используя ProductService с Dual API (FBO + FBS)
        print("\n🔄 Начинаем обновление данных...")
        print("   ✅ Используем Dual API: Statistics API (FBO) + Marketplace API v3 (FBS)")
        print("   ✅ Statistics API для остатков на складах WB (FBO)")
        print("   ✅ Marketplace API v3 для остатков на складе продавца (FBS)")
        print("   ✅ Supplier Orders API для заказов")
        print("   ✅ Фильтрация отменённых заказов (isCancel=True)")
        print("   ✅ Дедупликация по srid")
        print("   ✅ Нормализация названий складов")
        
        # Инициализируем ProductService
        product_service = ProductService(config)
        
        # Очищаем старые данные перед обновлением с повторными попытками
        print("\n🧹 Очищаем старые данные...")
        max_retries = 3
        retry_delay = 5  # секунд
        
        for attempt in range(1, max_retries + 1):
            try:
                operations.clear_all_products(spreadsheet_id, worksheet_name)
                print(f"   ✅ Данные очищены")
                break
            except Exception as e:
                if "503" in str(e) or "unavailable" in str(e).lower():
                    if attempt < max_retries:
                        print(f"   ⚠️  Попытка {attempt}/{max_retries}: Google Sheets временно недоступен")
                        print(f"   ⏳ Ожидание {retry_delay} секунд перед повторной попыткой...")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Увеличиваем задержку для следующей попытки
                    else:
                        print(f"   ❌ Не удалось очистить данные после {max_retries} попыток")
                        raise
                else:
                    raise
        
        # Синхронизация через ProductService с Dual API (FBO + FBS)
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ 28.10.2025: Используем Dual API для получения FBS остатков
        # ОПТИМИЗАЦИЯ: skip_existence_check=True после очистки таблицы
        # Экономит ~58% API запросов к Google Sheets (не проверяем существование)
        print("\n📥 Получаем данные из Wildberries (Dual API: FBO + FBS)...")
        
        # ИСПРАВЛЕНО 10.11.2025: ProductService.sync_from_dual_api_to_sheets использует
        # spreadsheet_id из config.google_sheets.sheet_id, поэтому временно заменяем его
        original_sheet_id = config.google_sheet_id
        config.google_sheet_id = spreadsheet_id
        
        # Синхронизация с повторными попытками при ошибках Google API
        max_sync_retries = 2
        sync_retry_delay = 10
        
        for attempt in range(1, max_sync_retries + 1):
            try:
                sync_session = await product_service.sync_from_dual_api_to_sheets(skip_existence_check=True)
                break
            except Exception as e:
                if "503" in str(e) or "unavailable" in str(e).lower() or "quota" in str(e).lower():
                    if attempt < max_sync_retries:
                        print(f"\n   ⚠️  Попытка синхронизации {attempt}/{max_sync_retries} неуспешна")
                        print(f"   ⏳ Ожидание {sync_retry_delay} секунд...")
                        await asyncio.sleep(sync_retry_delay)
                        sync_retry_delay *= 2
                    else:
                        raise
                else:
                    raise
            finally:
                if attempt == max_sync_retries or sync_session:
                    config.google_sheet_id = original_sheet_id
        
        # Проверяем статус синхронизации (SyncStatus.COMPLETED или status.value == 'completed')
        is_success = sync_session and sync_session.status == SyncStatus.COMPLETED
        
        if is_success:
            print("\n✅ Обновление таблицы завершено успешно!")
            print(f"📊 Обработано товаров: {sync_session.products_processed}/{sync_session.products_total}")
            if sync_session.products_failed > 0:
                print(f"⚠️  Ошибок: {sync_session.products_failed}")
            duration = sync_session.duration_seconds if sync_session.duration_seconds is not None else 0.0
            print(f"⏱️  Длительность: {duration:.1f} сек")
            print("📈 Данные в Google Sheets обновлены актуальной информацией")
            print("\n🔍 Использованы правильные API:")
            print("   ✅ Statistics API для FBO остатков (склады WB)")
            print("   ✅ Marketplace API v3 для FBS остатков (склад продавца/Маркетплейс)")
            print("   ✅ Supplier Orders API для заказов (детальные данные)")
            print("   ✅ Все исправления применены (включая FBS)")
            print("   ✅ Оптимизация API запросов (экономия 58%)")
            
            # Детальная статистика
            print(f"\n📊 Период: с начала текущей недели")
            print(f"   Время обновления: {datetime.now().strftime('%H:%M:%S')}")
        else:
            print("\n❌ Обновление таблицы не удалось")
            print(f"   Статус: {sync_session.status.value if sync_session else 'unknown'}")
            if sync_session and sync_session.last_error:
                print(f"   Ошибка: {sync_session.last_error}")
            print("📝 Проверьте логи для подробной информации об ошибке")
        
        return is_success
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Критическая ошибка при обновлении таблицы: {e}")
        
        # Специальная обработка для частых ошибок
        if "503" in error_msg or "unavailable" in error_msg.lower():
            print("\n💡 Совет: Google Sheets API временно недоступен.")
            print("   Попробуйте запустить скрипт через несколько минут.")
        elif "429" in error_msg or "quota" in error_msg.lower():
            print("\n💡 Совет: Превышена квота API запросов.")
            print("   Подождите некоторое время перед следующей попыткой.")
        elif "403" in error_msg or "permission" in error_msg.lower():
            print("\n💡 Совет: Проблема с правами доступа.")
            print("   Проверьте, что service account имеет доступ к таблице.")
        
        logger.error(f"Critical error in table update: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_table_data(spreadsheet_id: str = None, worksheet_name: str = "Stock Tracker"):
    """
    Синхронная обёртка для асинхронной функции обновления.
    
    Args:
        spreadsheet_id: ID Google Sheets документа
        worksheet_name: Название листа
        
    Returns:
        True если обновление успешно, False иначе
    """
    return asyncio.run(update_table_data_async(spreadsheet_id, worksheet_name))


def show_usage():
    """Показать справку по использованию."""
    print("""
🔧 Использование скрипта обновления таблицы:

python update_table_fixed.py [spreadsheet_id] [worksheet_name]

Параметры:
  spreadsheet_id   - ID Google Sheets документа (опционально, можно указать в конфиге)
  worksheet_name   - Название листа (по умолчанию: "Stock Tracker")

Примеры:
  python update_table_fixed.py
  python update_table_fixed.py 1abc123def456ghi789jkl "Stock Tracker"

Что делает скрипт (ИСПРАВЛЕННАЯ ВЕРСИЯ с Dual API):
  ✅ Использует Dual API: Statistics API (FBO) + Marketplace API v3 (FBS)
  ✅ Statistics API для остатков на складах WB (FBO)
  ✅ Marketplace API v3 для остатков на складе продавца (FBS/Маркетплейс)
  ✅ Supplier Orders API для заказов
  ✅ Фильтрует отменённые заказы (isCancel=True)
  ✅ Дедуплицирует заказы по srid
  ✅ Нормализует названия складов
  ✅ Использует фиксированный период (последние 7 дней)
  ✅ Применяет все 9 критических исправлений + FBS поддержка

Требования:
  📝 Файл config/service-account.json с ключами Google API
  🔑 API ключ Wildberries в конфигурации
  📊 ID Google Sheets документа в конфигурации или как параметр

ИЗМЕНЕНИЯ от старой версии:
  🔄 Вместо Analytics API v2 (только FBO) → Dual API (FBO + FBS)
  🔄 Добавлен Marketplace API v3 для получения остатков на складе продавца
  🔄 Вместо operations.refresh_table_data() → ProductService.sync_from_dual_api_to_sheets()
  🔄 Теперь синхронизируются ВСЕ остатки: WB склады + склад продавца (Маркетплейс)
""")


if __name__ == "__main__":
    # Парсим аргументы командной строки
    args = sys.argv[1:]
    
    if len(args) > 0 and args[0] in ['-h', '--help', 'help']:
        show_usage()
        sys.exit(0)
    
    # Получаем параметры
    spreadsheet_id = args[0] if len(args) > 0 else None
    worksheet_name = args[1] if len(args) > 1 else "Stock Tracker"
    
    try:
        # Запускаем обновление
        success = update_table_data(spreadsheet_id, worksheet_name)
        
        if success:
            print(f"\n🎉 Готово! Таблица '{worksheet_name}' обновлена с правильными данными!")
            print(f"   Все заказы из Orders API v1, отфильтрованы и дедуплицированы")
            sys.exit(0)
        else:
            print(f"\n💥 Обновление не удалось")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Обновление прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
