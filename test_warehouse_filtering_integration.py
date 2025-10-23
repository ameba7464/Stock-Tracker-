#!/usr/bin/env python3
"""
Интеграционный тест для проверки фильтрации складов в реальной системе.

Проверяет что все модули корректно применяют фильтрацию статусов доставки.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.core.calculator import WildberriesCalculator, debug_warehouse_data
from stock_tracker.api.products import extract_warehouse_data_from_response
from stock_tracker.api.warehouses import WarehouseDataProcessor


def test_complete_warehouse_filtering_pipeline():
    """Полный тест пайплайна обработки данных складов"""
    print("🧪 Integration Test: Complete Warehouse Filtering Pipeline")
    print("=" * 60)
    
    # Создаем реалистичные тестовые данные с проблемными статусами
    raw_warehouse_data = [
        {
            "nmId": 123456,
            "supplierArticle": "TEST-PRODUCT-001",
            "vendorCode": "TEST-PRODUCT-001", 
            "brand": "Test Brand",
            "subjectName": "Тестовый товар",
            "warehouses": [
                {"warehouseName": "Тула", "quantity": 150},
                {"warehouseName": "Белые Столбы", "quantity": 200},
                {"warehouseName": "В пути до получателей", "quantity": 50},      # ФИЛЬТРУЕМ
                {"warehouseName": "Всего находится на складах", "quantity": 400}, # ФИЛЬТРУЕМ
                {"warehouseName": "Подольск 3", "quantity": 75},
                {"warehouseName": "В пути возврата на склад WB", "quantity": 25}, # ФИЛЬТРУЕМ
                {"warehouseName": "Краснодар", "quantity": 100}
            ]
        },
        {
            "nmId": 789012,
            "supplierArticle": "TEST-PRODUCT-002",
            "vendorCode": "TEST-PRODUCT-002",
            "brand": "Another Brand", 
            "warehouses": [
                {"warehouseName": "Электросталь", "quantity": 80},
                {"warehouseName": "К доплате", "quantity": 10},                  # ФИЛЬТРУЕМ
                {"warehouseName": "Общий итог", "quantity": 300},                # ФИЛЬТРУЕМ
                {"warehouseName": "Домодедово", "quantity": 120}
            ]
        }
    ]
    
    raw_orders_data = [
        {"nmId": 123456, "supplierArticle": "TEST-PRODUCT-001", "warehouseName": "Тула"},
        {"nmId": 123456, "supplierArticle": "TEST-PRODUCT-001", "warehouseName": "В пути до получателей"},  # ФИЛЬТРУЕМ
        {"nmId": 123456, "supplierArticle": "TEST-PRODUCT-001", "warehouseName": "Белые Столбы"},
        {"nmId": 123456, "supplierArticle": "TEST-PRODUCT-001", "warehouseName": "Подольск 3"},
        {"nmId": 789012, "supplierArticle": "TEST-PRODUCT-002", "warehouseName": "Электросталь"},
        {"nmId": 789012, "supplierArticle": "TEST-PRODUCT-002", "warehouseName": "К доплате"},            # ФИЛЬТРУЕМ
        {"nmId": 789012, "supplierArticle": "TEST-PRODUCT-002", "warehouseName": "Домодедово"}
    ]
    
    print("🔍 Step 1: Debugging raw warehouse data...")
    debug_results = debug_warehouse_data(raw_warehouse_data, "Raw API Data")
    
    expected_real_warehouses = {"Тула", "Белые Столбы", "Подольск 3", "Краснодар", "Электросталь", "Домодедово"}
    expected_delivery_statuses = {"В пути до получателей", "Всего находится на складах", "В пути возврата на склад WB", "К доплате", "Общий итог"}
    
    print(f"\n📊 Expected real warehouses: {len(expected_real_warehouses)}")
    print(f"📊 Found real warehouses: {len(debug_results['real_warehouses'])}")
    print(f"📊 Expected delivery statuses: {len(expected_delivery_statuses)}")
    print(f"📊 Found delivery statuses: {len(debug_results['delivery_statuses'])}")
    
    # Проверка диагностики
    real_match = set(debug_results["real_warehouses"]) == expected_real_warehouses
    status_match = set(debug_results["delivery_statuses"]) == expected_delivery_statuses
    
    print(f"✅ Real warehouses detection: {'PASS' if real_match else 'FAIL'}")
    print(f"✅ Delivery statuses detection: {'PASS' if status_match else 'FAIL'}")
    
    if not (real_match and status_match):
        print("❌ Debugging failed!")
        return False
    
    print("\n🔍 Step 2: Testing extract_warehouse_data_from_response...")
    flat_warehouse_data = extract_warehouse_data_from_response(raw_warehouse_data)
    
    # Проверяем что статусы доставки отфильтрованы
    flat_warehouse_names = {item["warehouseName"] for item in flat_warehouse_data}
    
    print(f"📦 Warehouses in flat data: {flat_warehouse_names}")
    
    delivery_statuses_in_flat = flat_warehouse_names & expected_delivery_statuses
    if delivery_statuses_in_flat:
        print(f"❌ Found delivery statuses in flat data: {delivery_statuses_in_flat}")
        return False
    else:
        print("✅ No delivery statuses in flat warehouse data")
    
    print("\n🔍 Step 3: Testing WildberriesCalculator.group_data_by_product...")
    grouped_data = WildberriesCalculator.group_data_by_product(raw_warehouse_data, raw_orders_data)
    
    # Собираем все склады из сгруппированных данных
    all_grouped_warehouses = set()
    for product_data in grouped_data.values():
        all_grouped_warehouses.update(product_data["warehouses"].keys())
    
    print(f"📦 Warehouses in grouped data: {all_grouped_warehouses}")
    
    delivery_statuses_in_grouped = all_grouped_warehouses & expected_delivery_statuses
    if delivery_statuses_in_grouped:
        print(f"❌ Found delivery statuses in grouped data: {delivery_statuses_in_grouped}")
        return False
    else:
        print("✅ No delivery statuses in grouped data")
    
    print("\n🔍 Step 4: Testing WildberriesCalculator.process_combined_api_data...")
    
    # Создаем mock данные v2 для combined API
    analytics_v2_data = [
        {
            "nmID": 123456,
            "brandName": "Test Brand",
            "subjectID": 1001,
            "metrics": {
                "ordersCount": 4  # 4 заказа (исключая фильтрованные)
            }
        },
        {
            "nmID": 789012,
            "brandName": "Another Brand", 
            "subjectID": 1002,
            "metrics": {
                "ordersCount": 2  # 2 заказа (исключая фильтрованные)
            }
        }
    ]
    
    products = WildberriesCalculator.process_combined_api_data(analytics_v2_data, raw_warehouse_data)
    
    # Собираем все склады из продуктов
    all_product_warehouses = set()
    for product in products:
        for warehouse in product.warehouses:
            all_product_warehouses.add(warehouse.name)
    
    print(f"📦 Warehouses in products: {all_product_warehouses}")
    
    delivery_statuses_in_products = all_product_warehouses & expected_delivery_statuses
    if delivery_statuses_in_products:
        print(f"❌ Found delivery statuses in products: {delivery_statuses_in_products}")
        return False
    else:
        print("✅ No delivery statuses in final products")
    
    print("\n🔍 Step 5: Testing WarehouseDataProcessor...")
    processor = WarehouseDataProcessor()
    
    # Тестируем процессор складов для первого продукта
    processed_warehouses = processor.process_warehouse_remains(
        [item for item in raw_warehouse_data if item["supplierArticle"] == "TEST-PRODUCT-001"],
        "TEST-PRODUCT-001"
    )
    
    processed_warehouse_names = {wh.name for wh in processed_warehouses}
    print(f"📦 Warehouses from processor: {processed_warehouse_names}")
    
    delivery_statuses_in_processor = processed_warehouse_names & expected_delivery_statuses
    if delivery_statuses_in_processor:
        print(f"❌ Found delivery statuses in processor output: {delivery_statuses_in_processor}")
        return False
    else:
        print("✅ No delivery statuses in processor output")
    
    print("\n🎉 All filtering tests passed!")
    print("=" * 60)
    
    # Финальная статистика
    print("📊 FILTERING SUMMARY:")
    print(f"   Real warehouses preserved: {len(all_product_warehouses)}")
    print(f"   Delivery statuses filtered: {len(expected_delivery_statuses)}")
    print(f"   Products created: {len(products)}")
    print(f"   Total stock in products: {sum(p.total_stock for p in products)}")
    print(f"   Total orders in products: {sum(p.total_orders for p in products)}")
    
    return True


def test_edge_cases():
    """Тест крайних случаев"""
    print("\n🧪 Edge Cases Test")
    print("=" * 30)
    
    # Тест с пустыми данными
    empty_result = WildberriesCalculator.group_data_by_product([], [])
    if empty_result != {}:
        print("❌ Empty data test failed")
        return False
    print("✅ Empty data handling")
    
    # Тест с None значениями
    bad_data = [
        {
            "nmId": 12345,
            "vendorCode": "TEST",
            "warehouses": [
                {"warehouseName": None, "quantity": 100},
                {"warehouseName": "", "quantity": 50},
                {"warehouseName": "Тула", "quantity": 200}
            ]
        }
    ]
    
    result = WildberriesCalculator.group_data_by_product(bad_data, [])
    if ("TEST", 12345) in result:
        warehouses = result[("TEST", 12345)]["warehouses"]
        if None in warehouses or "" in warehouses:
            print("❌ None/empty handling failed")
            return False
        if "Тула" not in warehouses:
            print("❌ Valid warehouse not preserved")
            return False
    
    print("✅ None/empty values handling")
    
    return True


if __name__ == "__main__":
    print("🚀 WAREHOUSE FILTERING INTEGRATION TESTS")
    print("=" * 70)
    
    success = True
    
    try:
        success &= test_complete_warehouse_filtering_pipeline()
        success &= test_edge_cases()
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Warehouse filtering is working correctly across all modules")
    else:
        print("❌ SOME TESTS FAILED!")
        print("⚠️ Check the warehouse filtering implementation")
    
    print("=" * 70)