#!/usr/bin/env python3
"""
Тест фильтрации статусов доставки в данных складов.

Проверяет что исправления из WAREHOUSE_FILTERING_PROMPT.md работают корректно.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.core.calculator import (
    is_real_warehouse, 
    validate_warehouse_name, 
    debug_warehouse_data,
    WildberriesCalculator
)


def test_delivery_status_filtering():
    """Тест 1: Фильтрация статусов"""
    print("🧪 Test 1: Delivery status filtering")
    
    test_data = [
        ("Тула", True),
        ("Белые Столбы", True), 
        ("В пути до получателей", False),
        ("В пути возврата на склад WB", False),
        ("Всего находится на складах", False),
        ("Подольск 3", True),
        ("Краснодар", True),
        ("В пути возврата с ПВЗ", False),
        ("Общий итог", False),
        ("", False),
        (None, False)
    ]
    
    passed = 0
    total = len(test_data)
    
    for name, expected in test_data:
        result = is_real_warehouse(name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{name}': expected {expected}, got {result}")
        if result == expected:
            passed += 1
    
    print(f"📊 Result: {passed}/{total} tests passed")
    return passed == total


def test_warehouse_name_validation():
    """Тест 2: Валидация названий складов"""
    print("\n🧪 Test 2: Warehouse name validation")
    
    test_data = [
        ("Тула", True),
        ("Белые Столбы", True),
        ("Подольск 3", True),
        ("Москва (Север)", True),
        ("Краснодар", True),
        ("", False),
        ("123", False),
        ("English Name", False)  # Нет русских букв
    ]
    
    passed = 0
    total = len(test_data)
    
    for name, expected in test_data:
        result = validate_warehouse_name(name)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{name}': expected {expected}, got {result}")
        if result == expected:
            passed += 1
    
    print(f"📊 Result: {passed}/{total} tests passed")
    return passed == total


def test_group_data_filtering():
    """Тест 3: Проверка что в продуктах нет статусов доставки"""
    print("\n🧪 Test 3: Product data filtering")
    
    # Создаем тестовые данные с доставочными статусами
    warehouse_test_data = [
        {
            "nmId": 12345,
            "vendorCode": "TEST-001",
            "warehouses": [
                {"warehouseName": "Тула", "quantity": 100},
                {"warehouseName": "В пути до получателей", "quantity": 50},  # Должно быть отфильтровано
                {"warehouseName": "Белые Столбы", "quantity": 75},
                {"warehouseName": "Всего находится на складах", "quantity": 200},  # Должно быть отфильтровано
            ]
        }
    ]
    
    orders_test_data = [
        {
            "nmId": 12345,
            "supplierArticle": "TEST-001",
            "warehouseName": "Тула"
        },
        {
            "nmId": 12345,
            "supplierArticle": "TEST-001", 
            "warehouseName": "В пути до получателей"  # Должно быть отфильтровано
        },
        {
            "nmId": 12345,
            "supplierArticle": "TEST-001",
            "warehouseName": "Белые Столбы"
        }
    ]
    
    # Обрабатываем через новую логику
    grouped_data = WildberriesCalculator.group_data_by_product(
        warehouse_test_data, orders_test_data
    )
    
    # Проверяем результат
    print(f"  📊 Grouped data keys: {list(grouped_data.keys())}")
    
    if grouped_data:
        # Берем первый доступный ключ
        first_key = list(grouped_data.keys())[0]
        warehouses = grouped_data[first_key]["warehouses"]
        warehouse_names = list(warehouses.keys())
        
        print(f"  📦 Found warehouses: {warehouse_names}")
        
        # Проверяем что нет статусов доставки
        delivery_statuses_found = []
        for name in warehouse_names:
            if not is_real_warehouse(name):
                delivery_statuses_found.append(name)
        
        if delivery_statuses_found:
            print(f"  ❌ Found delivery statuses in results: {delivery_statuses_found}")
            return False
        else:
            print("  ✅ No delivery statuses found in warehouse data")
            
            # Проверяем что есть реальные склады
            real_warehouses = [name for name in warehouse_names if is_real_warehouse(name)]
            if real_warehouses:
                print(f"  ✅ Real warehouses preserved: {real_warehouses}")
                return True
            else:
                print("  ❌ No real warehouses found")
                return False
    else:
        print("  ❌ Product not found in grouped data")
        return False


def test_debug_warehouse_data():
    """Тест 4: Диагностика входящих данных"""
    print("\n🧪 Test 4: Warehouse data debugging")
    
    test_data = [
        {
            "warehouses": [
                {"warehouseName": "Тула"},
                {"warehouseName": "В пути до получателей"},
                {"warehouseName": "Белые Столбы"},
                {"warehouseName": "Всего находится на складах"}
            ]
        }
    ]
    
    results = debug_warehouse_data(test_data, "Test Data")
    
    expected_real = ["Тула", "Белые Столбы"]
    expected_statuses = ["В пути до получателей", "Всего находится на складах"]
    
    real_match = set(results["real_warehouses"]) == set(expected_real)
    status_match = set(results["delivery_statuses"]) == set(expected_statuses)
    
    print(f"  Real warehouses match: {'✅' if real_match else '❌'}")
    print(f"  Delivery statuses match: {'✅' if status_match else '❌'}")
    
    return real_match and status_match


def run_all_tests():
    """Запустить все тесты фильтрации"""
    print("🚀 WAREHOUSE FILTERING TESTS")
    print("=" * 50)
    
    tests = [
        test_delivery_status_filtering,
        test_warehouse_name_validation,
        test_group_data_filtering,
        test_debug_warehouse_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print(f"\n🏁 FINAL RESULT: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Warehouse filtering works correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    run_all_tests()