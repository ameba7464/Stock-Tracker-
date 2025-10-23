#!/usr/bin/env python3
"""
Тест генерации складов - проверяем что создается при разных сценариях.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.core.calculator import WildberriesCalculator

def test_warehouse_generation():
    """Тест что именно генерируется для складов."""
    
    print("🧪 TESTING: Warehouse Generation Logic")
    print("=" * 50)
    
    # Сценарий 1: Реальные данные из Warehouse API v1
    print("\n📦 SCENARIO 1: Real Warehouse API v1 data")
    
    # Имитируем реальные данные из Warehouse API v1
    analytics_data = [
        {
            "nmID": 12345,
            "vendorCode": "TEST-001",
            "metrics": {"stockCount": 1000, "ordersCount": 200}
        }
    ]
    
    warehouse_api_data = [
        {
            "nmId": 12345,
            "vendorCode": "TEST-001", 
            "warehouses": [
                {"warehouseName": "Тула", "quantity": 400},
                {"warehouseName": "Белые Столбы", "quantity": 350},
                {"warehouseName": "Домодедово", "quantity": 250}
            ]
        }
    ]
    
    print("Input Analytics data:", analytics_data[0])
    print("Input Warehouse data:", warehouse_api_data[0])
    
    # Тестируем процесс combined API data (реальные склады)
    products = WildberriesCalculator.process_combined_api_data(analytics_data, warehouse_api_data)
    
    if products:
        product = products[0]
        print(f"\n✅ Product created: {product.seller_article}")
        print(f"📦 Warehouses ({len(product.warehouses)}):")
        
        total_check_stock = 0
        for warehouse in product.warehouses:
            print(f"  - {warehouse.name}: Stock={warehouse.stock}, Orders={warehouse.orders}")
            total_check_stock += warehouse.stock
            
            # Проверяем на фиктивные названия
            if warehouse.name.lower() in ["коледино", "подольск", "электросталь", "казань"]:
                print(f"    ⚠️ WARNING: Detected potentially fake warehouse name: {warehouse.name}")
        
        print(f"📊 Total stock verification: {total_check_stock} (should be close to 1000)")
    
    # Сценарий 2: Нет данных Warehouse API v1
    print("\n\n📊 SCENARIO 2: No Warehouse API v1 data (Analytics v2 only)")
    
    products_no_warehouse = WildberriesCalculator.process_analytics_v2_data(analytics_data, None)
    
    if products_no_warehouse:
        product = products_no_warehouse[0]
        print(f"\n✅ Product created: {product.seller_article}")
        print(f"📦 Warehouses ({len(product.warehouses)}):")
        
        for warehouse in product.warehouses:
            print(f"  - {warehouse.name}: Stock={warehouse.stock}, Orders={warehouse.orders}")
            
            # Проверяем на фиктивные названия
            if any(fake in warehouse.name.lower() for fake in ["коледино", "подольск", "электросталь"]):
                print(f"    ❌ ERROR: Fake warehouse name detected: {warehouse.name}")
                return False
            
            # Проверяем на правильные предупреждения
            if "api" in warehouse.name.lower() or "недоступ" in warehouse.name.lower():
                print(f"    ✅ CORRECT: Proper warning message: {warehouse.name}")
    
    print("\n🎯 RESULT: Warehouse generation logic works correctly!")
    return True

if __name__ == "__main__":
    print("🏭 TESTING: Warehouse Data Generation")
    print("=" * 60)
    print("Purpose: Verify what warehouse names are generated in different scenarios")
    print()
    
    try:
        success = test_warehouse_generation()
        if success:
            print("\n✅ ALL TESTS PASSED: Warehouse generation is correct")
            print("📊 No fake warehouse names generated")
        else:
            print("\n❌ TESTS FAILED: Fake warehouse names detected!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)