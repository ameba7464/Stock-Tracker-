#!/usr/bin/env python3
"""
Test warehouse stock calculation with proper exclusion of "in transit" warehouses.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

def create_test_data_with_in_transit():
    """Create test data with various warehouse types including in-transit."""
    
    # Mock orders data
    orders_data = [
        {"nmId": 12345, "supplierArticle": "TestProduct1", "warehouseName": "Казань", "quantity": 2},
        {"nmId": 12345, "supplierArticle": "TestProduct1", "warehouseName": "Подольск", "quantity": 1},
    ]
    
    # Mock warehouse data with mixed warehouse types
    warehouse_data = [
        {
            "nmId": 12345,
            "vendorCode": "TestProduct1",
            "warehouses": [
                # Real WB warehouses
                {"warehouseName": "Казань", "quantity": 10},
                {"warehouseName": "Подольск", "quantity": 15},
                {"warehouseName": "Электросталь", "quantity": 8},
                
                # In-transit warehouses (should be excluded from real stock)
                {"warehouseName": "В пути возвраты на склад WB", "quantity": 25},
                {"warehouseName": "В пути до получателей", "quantity": 12},
                {"warehouseName": "В дороге транзит", "quantity": 5},
                
                # MP warehouses (should be included in real stock)
                {"warehouseName": "Склад МП Москва", "quantity": 7},
            ]
        }
    ]
    
    return orders_data, warehouse_data

def test_warehouse_categorization():
    """Test the _is_in_transit_warehouse method."""
    
    print("🧪 Testing warehouse categorization...")
    
    # Mock database operations
    class MockDatabaseOperations:
        async def create_or_update_product(self, product):
            return True
        async def update_product(self, product_id, updated_product):
            return True
    
    product_service = ProductService(MockDatabaseOperations())
    
    # Test cases for warehouse categorization
    test_cases = [
        # In-transit warehouses (should return True)
        ("В пути возвраты на склад WB", True),
        ("В пути до получателей", True),
        ("В дороге транзит", True),
        ("Возврат товаров", True),
        ("Доставка до получателей", True),
        ("Перемещение товаров", True),
        
        # Real warehouses (should return False)
        ("Казань", False),
        ("Подольск", False),
        ("Электросталь", False),
        ("Склад МП Москва", False),
        ("Обухово МП", False),
        ("Коледино", False),
        ("", False),  # Empty string
    ]
    
    print("   🔍 Testing warehouse categorization:")
    all_correct = True
    
    for warehouse_name, expected_in_transit in test_cases:
        result = product_service._is_in_transit_warehouse(warehouse_name)
        status = "✅" if result == expected_in_transit else "❌"
        warehouse_type = "In-Transit" if result else "Real Warehouse"
        expected_type = "In-Transit" if expected_in_transit else "Real Warehouse"
        
        print(f"      {status} '{warehouse_name}' → {warehouse_type} (expected: {expected_type})")
        
        if result != expected_in_transit:
            all_correct = False
    
    print(f"   📊 Categorization test: {'✅ PASSED' if all_correct else '❌ FAILED'}")
    return all_correct

def test_stock_calculation():
    """Test stock calculation with in-transit exclusion."""
    
    print("\n📊 Testing stock calculation with in-transit exclusion...")
    
    # Create test data
    orders_data, warehouse_data = create_test_data_with_in_transit()
    
    # Mock database operations
    class MockDatabaseOperations:
        async def create_or_update_product(self, product):
            return True
        async def update_product(self, product_id, updated_product):
            return True
    
    product_service = ProductService(MockDatabaseOperations())
    
    # Test conversion
    warehouse_record = warehouse_data[0]
    converted_product = product_service._convert_api_record_to_product(
        warehouse_record, orders_data
    )
    
    # Calculate expected values
    all_warehouses = warehouse_record['warehouses']
    total_all_stock = sum(wh['quantity'] for wh in all_warehouses)
    
    real_warehouses = []
    in_transit_warehouses = []
    
    for wh in all_warehouses:
        if product_service._is_in_transit_warehouse(wh['warehouseName']):
            in_transit_warehouses.append(wh)
        else:
            real_warehouses.append(wh)
    
    expected_real_stock = sum(wh['quantity'] for wh in real_warehouses)
    expected_in_transit_stock = sum(wh['quantity'] for wh in in_transit_warehouses)
    
    print(f"   📦 Warehouse breakdown:")
    print(f"      Total warehouses: {len(all_warehouses)}")
    print(f"      Real warehouses: {len(real_warehouses)} (stock: {expected_real_stock})")
    for wh in real_warehouses:
        print(f"         - {wh['warehouseName']}: {wh['quantity']}")
    
    print(f"      In-transit warehouses: {len(in_transit_warehouses)} (stock: {expected_in_transit_stock})")
    for wh in in_transit_warehouses:
        print(f"         - {wh['warehouseName']}: {wh['quantity']}")
    
    print(f"\n   🎯 Stock calculation results:")
    print(f"      Expected real stock: {expected_real_stock}")
    print(f"      Actual product.total_stock: {converted_product.total_stock}")
    print(f"      Expected total all stock: {total_all_stock}")
    print(f"      Orders: {converted_product.total_orders}")
    
    # Debug: Check all Product attributes
    print(f"\n   🔍 Debug Product attributes:")
    for attr_name in dir(converted_product):
        if not attr_name.startswith('_'):
            attr_value = getattr(converted_product, attr_name, 'N/A')
            if not callable(attr_value):
                print(f"      {attr_name}: {attr_value}")
    
    # Verify calculation
    stock_calculation_correct = (converted_product.total_stock == expected_real_stock)
    
    print(f"   📊 Stock calculation: {'✅ CORRECT' if stock_calculation_correct else '❌ INCORRECT'}")
    
    if stock_calculation_correct:
        savings = expected_in_transit_stock
        print(f"   💡 Improvement: Excluded {savings} in-transit items from stock count")
        print(f"   📈 More accurate turnover calculation based on real warehouse stock")
    
    return stock_calculation_correct

def test_improved_warehouse_logic():
    """Run all tests for improved warehouse logic."""
    
    print("🔧 Testing Improved Warehouse Stock Logic")
    print("=" * 60)
    
    # Test 1: Warehouse categorization
    categorization_passed = test_warehouse_categorization()
    
    # Test 2: Stock calculation
    calculation_passed = test_stock_calculation()
    
    print(f"\n{'=' * 60}")
    print(f"📊 TEST SUMMARY:")
    print(f"   Warehouse Categorization: {'✅ PASSED' if categorization_passed else '❌ FAILED'}")
    print(f"   Stock Calculation: {'✅ PASSED' if calculation_passed else '❌ FAILED'}")
    
    overall_passed = categorization_passed and calculation_passed
    print(f"   Overall Result: {'✅ ALL TESTS PASSED' if overall_passed else '❌ SOME TESTS FAILED'}")
    
    if overall_passed:
        print(f"\n🎉 Improvement Summary:")
        print(f"   ✅ In-transit warehouses correctly excluded from stock count")
        print(f"   ✅ Real warehouse stock calculation accurate")
        print(f"   ✅ More precise turnover calculations")
        print(f"   ✅ Better inventory management metrics")
    
    return overall_passed

if __name__ == "__main__":
    test_improved_warehouse_logic()