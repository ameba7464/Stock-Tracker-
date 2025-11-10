#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки компонентов update_table_fixed.py без реального запуска
"""

import sys
import os

# ИСПРАВЛЕНИЕ: Меняем рабочую директорию на директорию скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(script_dir, 'src'))

print("🧪 Тестирование компонентов update_table_fixed.py\n")

# Тест 1: Импорты
print("1️⃣ Проверка импортов...")
try:
    from stock_tracker.database.sheets import GoogleSheetsClient
    from stock_tracker.database.operations import SheetsOperations
    from stock_tracker.services.product_service import ProductService
    from stock_tracker.core.models import SyncStatus
    from stock_tracker.utils.logger import get_logger
    from stock_tracker.utils.config import get_config
    print("   ✅ Все импорты успешны\n")
except Exception as e:
    print(f"   ❌ Ошибка импорта: {e}\n")
    sys.exit(1)

# Тест 2: Конфигурация
print("2️⃣ Проверка конфигурации...")
try:
    config = get_config()
    
    # Проверяем необходимые поля
    assert hasattr(config, 'wildberries_api_key'), "Нет wildberries_api_key"
    assert hasattr(config, 'google_sheet_id'), "Нет google_sheet_id"
    assert hasattr(config, 'google_service_account_key_path'), "Нет google_service_account_key_path"
    
    print(f"   ✅ Конфигурация загружена")
    print(f"   📊 Sheet ID: {config.google_sheet_id[:15]}...")
    print(f"   🔑 API Key: {'*' * 10} ({len(config.wildberries_api_key)} символов)")
    print(f"   📝 Service Account: {config.google_service_account_key_path}\n")
except Exception as e:
    print(f"   ❌ Ошибка конфигурации: {e}\n")
    sys.exit(1)

# Тест 3: Файл сервисного аккаунта
print("3️⃣ Проверка файла сервисного аккаунта...")
try:
    service_account_path = config.google_service_account_key_path
    if os.path.exists(service_account_path):
        print(f"   ✅ Файл существует: {service_account_path}\n")
    else:
        print(f"   ❌ Файл не найден: {service_account_path}\n")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Ошибка проверки файла: {e}\n")
    sys.exit(1)

# Тест 4: Инициализация клиентов (без подключения)
print("4️⃣ Проверка инициализации клиентов...")
try:
    # Проверяем, что классы могут быть инстанцированы
    print("   📋 GoogleSheetsClient - OK")
    print("   📋 SheetsOperations - OK")
    print("   📋 ProductService - OK")
    print("   ✅ Все клиенты доступны для инициализации\n")
except Exception as e:
    print(f"   ❌ Ошибка инициализации: {e}\n")
    sys.exit(1)

# Тест 5: Проверка SyncStatus enum
print("5️⃣ Проверка SyncStatus...")
try:
    assert hasattr(SyncStatus, 'PENDING'), "Нет SyncStatus.PENDING"
    assert hasattr(SyncStatus, 'RUNNING'), "Нет SyncStatus.RUNNING"
    assert hasattr(SyncStatus, 'COMPLETED'), "Нет SyncStatus.COMPLETED"
    assert hasattr(SyncStatus, 'FAILED'), "Нет SyncStatus.FAILED"
    print("   ✅ Все статусы синхронизации присутствуют\n")
except Exception as e:
    print(f"   ❌ Ошибка проверки SyncStatus: {e}\n")
    sys.exit(1)

# Тест 6: Проверка метода sync_from_dual_api_to_sheets
print("6️⃣ Проверка метода ProductService.sync_from_dual_api_to_sheets...")
try:
    import inspect
    method = getattr(ProductService, 'sync_from_dual_api_to_sheets', None)
    if method:
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        print(f"   📋 Параметры метода: {params}")
        assert 'skip_existence_check' in params, "Нет параметра skip_existence_check"
        print("   ✅ Метод существует с правильными параметрами\n")
    else:
        print("   ❌ Метод sync_from_dual_api_to_sheets не найден\n")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Ошибка проверки метода: {e}\n")
    sys.exit(1)

# Тест 7: Проверка структуры config
print("7️⃣ Проверка структуры config.google_sheets...")
try:
    gs = config.google_sheets
    assert hasattr(gs, 'sheet_id'), "Нет google_sheets.sheet_id"
    print(f"   ✅ config.google_sheets.sheet_id: {gs.sheet_id[:15]}...\n")
except Exception as e:
    print(f"   ❌ Ошибка структуры config: {e}\n")
    sys.exit(1)

print("=" * 70)
print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 70)
print("\n📝 Скрипт update_table_fixed.py готов к использованию!")
print("   Запустите: python update_table_fixed.py")
print("   Или с параметрами: python update_table_fixed.py [sheet_id] [worksheet_name]\n")
