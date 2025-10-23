#!/usr/bin/env python3
"""
Скрипт для обновления таблицы Google Sheets свежими данными из Wildberries API.
Используется для обновления данных при запуске приложения.
"""

import sys
import os
import asyncio
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config


logger = get_logger(__name__)


def update_table_data(spreadsheet_id: str = None, worksheet_name: str = "Stock Tracker"):
    """
    Обновить данные в таблице.
    
    Args:
        spreadsheet_id: ID Google Sheets документа (если None, будет взят из конфига)
        worksheet_name: Название листа для обновления
    """
    try:
        print("🚀 Запуск обновления таблицы Stock Tracker")
        print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
        service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')
        
        if not os.path.exists(service_account_path):
            print(f"❌ Ошибка: Файл сервисного аккаунта не найден: {service_account_path}")
            return False
            
        sheets_client = GoogleSheetsClient(service_account_path)
        operations = SheetsOperations(sheets_client)
        
        # Обновляем таблицу
        print("\n🔄 Начинаем обновление данных...")
        print("   - Получение данных из Wildberries API")
        print("   - Обработка и расчет показателей")
        print("   - Запись в Google Sheets")
        
        result = operations.update_table_on_startup(
            spreadsheet_id=spreadsheet_id,
            worksheet_name=worksheet_name
        )
        
        if result:
            print("\n✅ Обновление таблицы завершено успешно!")
            print("📈 Данные в Google Sheets обновлены актуальной информацией")
        else:
            print("\n❌ Обновление таблицы не удалось")
            print("📝 Проверьте логи для подробной информации об ошибке")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка при обновлении таблицы: {e}")
        logger.error(f"Critical error in table update: {e}")
        return False


def show_usage():
    """Показать справку по использованию."""
    print("""
🔧 Использование скрипта обновления таблицы:

python update_table.py [spreadsheet_id] [worksheet_name]

Параметры:
  spreadsheet_id   - ID Google Sheets документа (опционально, можно указать в конфиге)
  worksheet_name   - Название листа (по умолчанию: "Stock Tracker")

Примеры:
  python update_table.py
  python update_table.py 1abc123def456ghi789jkl "Stock Tracker"

Что делает скрипт:
  ✅ Подключается к Wildberries API
  ✅ Получает актуальные данные об остатках и заказах
  ✅ Рассчитывает показатели (оборачиваемость и др.)
  ✅ Обновляет Google Sheets таблицу
  ✅ Очищает старые данные перед обновлением

Требования:
  📝 Файл config/service-account.json с ключами Google API
  🔑 API ключ Wildberries в конфигурации
  📊 ID Google Sheets документа в конфигурации или как параметр
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
            print(f"\n🎉 Готово! Таблица '{worksheet_name}' обновлена")
            sys.exit(0)
        else:
            print(f"\n💥 Обновление не удалось")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Обновление прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
        sys.exit(1)