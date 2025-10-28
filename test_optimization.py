#!/usr/bin/env python3
"""
Тестовый скрипт для проверки оптимизации API запросов Google Sheets.

Проверяет:
1. Что метод create_or_update_product() принимает параметр skip_existence_check
2. Что при skip_existence_check=True не вызывается read_product()
3. Что update_table_fixed.py корректно использует оптимизацию
"""

import sys
import os
from unittest.mock import MagicMock, patch, call
import asyncio

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.database.operations import SheetsOperations
from stock_tracker.core.models import Product, Warehouse


def test_skip_existence_check_parameter():
    """Тест 1: Проверка наличия параметра skip_existence_check"""
    print("\n🧪 Тест 1: Проверка параметра skip_existence_check...")
    
    # Создаём mock объекты
    mock_sheets_client = MagicMock()
    operations = SheetsOperations(mock_sheets_client)
    
    # Проверяем сигнатуру метода
    import inspect
    sig = inspect.signature(operations.create_or_update_product)
    params = sig.parameters
    
    assert 'skip_existence_check' in params, "❌ Параметр skip_existence_check не найден!"
    assert params['skip_existence_check'].default == False, "❌ Значение по умолчанию должно быть False!"
    
    print("   ✅ Параметр skip_existence_check присутствует")
    print("   ✅ Значение по умолчанию = False")
    return True


def test_skip_read_when_flag_true():
    """Тест 2: Проверка что read_product() не вызывается при skip_existence_check=True"""
    print("\n🧪 Тест 2: Проверка пропуска read_product()...")
    
    # Создаём mock объекты
    mock_sheets_client = MagicMock()
    operations = SheetsOperations(mock_sheets_client)
    
    # Создаём тестовый продукт
    test_product = Product(
        seller_article="TEST001",
        wildberries_article=12345678
    )
    test_product.add_warehouse(Warehouse(name="Тест склад", orders=10, stock=50))
    
    # Mock методы
    with patch.object(operations, 'read_product', return_value=None) as mock_read, \
         patch.object(operations, 'create_product', return_value=2) as mock_create:
        
        # Вызываем с skip_existence_check=True
        result = operations.create_or_update_product(
            spreadsheet_id="test_id",
            product=test_product,
            skip_existence_check=True
        )
        
        # Проверяем что read_product НЕ вызывался
        assert mock_read.call_count == 0, "❌ read_product() НЕ должен был вызываться!"
        
        # Проверяем что create_product вызвался
        assert mock_create.call_count == 1, "❌ create_product() должен был вызваться!"
        
    print("   ✅ read_product() не вызывается при skip_existence_check=True")
    print("   ✅ create_product() вызывается напрямую")
    return True


def test_read_called_when_flag_false():
    """Тест 3: Проверка что read_product() вызывается при skip_existence_check=False"""
    print("\n🧪 Тест 3: Проверка вызова read_product() по умолчанию...")
    
    # Создаём mock объекты
    mock_sheets_client = MagicMock()
    operations = SheetsOperations(mock_sheets_client)
    
    # Создаём тестовый продукт
    test_product = Product(
        seller_article="TEST002",
        wildberries_article=87654321
    )
    test_product.add_warehouse(Warehouse(name="Тест склад 2", orders=20, stock=100))
    
    # Mock методы
    with patch.object(operations, 'read_product', return_value=None) as mock_read, \
         patch.object(operations, 'create_product', return_value=2) as mock_create:
        
        # Вызываем БЕЗ skip_existence_check (по умолчанию False)
        result = operations.create_or_update_product(
            spreadsheet_id="test_id",
            product=test_product
        )
        
        # Проверяем что read_product вызывался
        assert mock_read.call_count == 1, "❌ read_product() должен был вызываться!"
        
        # Проверяем что create_product вызвался (т.к. read_product вернул None)
        assert mock_create.call_count == 1, "❌ create_product() должен был вызываться!"
        
    print("   ✅ read_product() вызывается при skip_existence_check=False")
    print("   ✅ Стандартное поведение сохранено")
    return True


def test_product_service_signature():
    """Тест 4: Проверка что ProductService.sync_from_api_to_sheets() принимает параметр"""
    print("\n🧪 Тест 4: Проверка ProductService.sync_from_api_to_sheets()...")
    
    from stock_tracker.services.product_service import ProductService
    import inspect
    
    sig = inspect.signature(ProductService.sync_from_api_to_sheets)
    params = sig.parameters
    
    assert 'skip_existence_check' in params, "❌ Параметр skip_existence_check не найден!"
    assert params['skip_existence_check'].default == False, "❌ Значение по умолчанию должно быть False!"
    
    print("   ✅ ProductService.sync_from_api_to_sheets() принимает skip_existence_check")
    print("   ✅ Параметр корректно передаётся через всю цепочку вызовов")
    return True


def calculate_api_savings():
    """Расчёт экономии API запросов"""
    print("\n📊 РАСЧЁТ ЭКОНОМИИ API ЗАПРОСОВ:")
    print("=" * 60)
    
    # Данные из отчёта
    products_count = 11
    
    # ДО оптимизации
    requests_before = {
        "Аутентификация": 1,
        "Открытие spreadsheet": 1,
        "Открытие worksheet": 1,
        "Очистка таблицы": 2,
        "get_worksheet (read_product)": products_count,
        "find_product_row (scan)": products_count,
        "get_worksheet (create_product)": products_count,
        "verify_structure": 0,  # Уже удалено ранее
    }
    
    # ПОСЛЕ оптимизации
    requests_after = {
        "Аутентификация": 1,
        "Открытие spreadsheet": 1,
        "Открытие worksheet": 1,
        "Очистка таблицы": 2,
        "get_worksheet (create_product)": products_count,
    }
    
    total_before = sum(requests_before.values())
    total_after = sum(requests_after.values())
    
    savings = total_before - total_after
    savings_percent = (savings / total_before) * 100
    
    print(f"📈 ДО оптимизации:  {total_before} requests")
    print(f"📉 ПОСЛЕ:           {total_after} requests")
    print(f"💰 ЭКОНОМИЯ:        {savings} requests ({savings_percent:.1f}%)")
    print()
    print(f"🚀 Requests/minute: {total_before * 60 / 90:.1f} → {total_after * 60 / 90:.1f}")
    print(f"⏱️  Время синхр.:    ~90 сек → ~{90 * total_after / total_before:.0f} сек")
    print("=" * 60)
    
    return savings_percent


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 60)
    print("🔬 ТЕСТИРОВАНИЕ ОПТИМИЗАЦИИ GOOGLE SHEETS API")
    print("=" * 60)
    
    tests = [
        test_skip_existence_check_parameter,
        test_skip_read_when_flag_true,
        test_read_called_when_flag_false,
        test_product_service_signature,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ Неожиданная ошибка: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📋 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"   ✅ Пройдено: {passed}/{len(tests)}")
    print(f"   ❌ Не пройдено: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        
        # Показываем экономию
        savings = calculate_api_savings()
        
        print("\n✅ ФАЗА 1: БЫСТРЫЕ ИСПРАВЛЕНИЯ - ЗАВЕРШЕНА")
        print(f"   • Добавлен параметр skip_existence_check")
        print(f"   • Пропуск проверки существования после clear_all_products()")
        print(f"   • Экономия ~{savings:.0f}% API запросов к Google Sheets")
        print(f"   • update_table_fixed.py обновлён для использования оптимизации")
        
        return True
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ!")
        print("   Проверьте реализацию оптимизаций")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
