#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Симуляция запуска update_table_fixed.py для проверки инициализации
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

# ИСПРАВЛЕНИЕ: Меняем рабочую директорию на директорию скрипта
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


async def test_initialization():
    """Тест инициализации всех компонентов"""
    try:
        print("🚀 Симуляция запуска update_table_fixed.py")
        print(f"📅 Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Загружаем конфигурацию
        print("📋 Загружаем конфигурацию...")
        config = get_config()
        
        # Используем ID из конфига
        spreadsheet_id = config.google_sheet_id
        worksheet_name = "Stock Tracker"
        
        print(f"📊 Документ: {spreadsheet_id[:20]}...")
        print(f"📝 Лист: {worksheet_name}")
        
        # Инициализируем клиент Google Sheets
        print("🔐 Подключаемся к Google Sheets...")
        
        service_account_path = config.google_service_account_key_path
        print(f"   Используем: {service_account_path}")
        
        if not os.path.exists(service_account_path):
            print(f"❌ Ошибка: Файл сервисного аккаунта не найден: {service_account_path}")
            return False
            
        sheets_client = GoogleSheetsClient(service_account_path)
        operations = SheetsOperations(sheets_client)
        
        print("✅ Google Sheets клиент инициализирован")
        
        # Инициализируем ProductService
        print("📦 Инициализируем ProductService...")
        product_service = ProductService(config)
        
        print("✅ ProductService инициализирован")
        
        # Проверяем метод sync_from_dual_api_to_sheets
        print("🔍 Проверяем метод sync_from_dual_api_to_sheets...")
        assert hasattr(product_service, 'sync_from_dual_api_to_sheets'), "Метод не найден!"
        print("✅ Метод существует")
        
        print("\n" + "="*70)
        print("✅ ВСЕ КОМПОНЕНТЫ ИНИЦИАЛИЗИРОВАНЫ УСПЕШНО!")
        print("="*70)
        print("\n📝 Скрипт update_table_fixed.py готов к запуску")
        print("   ⚠️  Для реального обновления запустите:")
        print("   python update_table_fixed.py\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Critical error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_initialization())
    exit(0 if success else 1)
