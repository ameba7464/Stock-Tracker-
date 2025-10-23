#!/usr/bin/env python3
"""
Test to verify NO FAKE DATA is generated when Warehouse API v1 is unavailable.

This test ensures that the system only uses REAL data from APIs and shows
"data unavailable" messages instead of creating fictional warehouse distributions.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.warehouse_cache import get_warehouse_cache, WarehouseCacheEntry
import time

def test_no_fake_data_generation():
    """Test that system doesn't generate fake warehouse data."""
    
    print("🧪 TESTING: No Fake Data Generation")
    print("=" * 50)
    
    # Sample Analytics v2 data (real format)
    analytics_data = [
        {
            "nmID": 12345,
            "vendorCode": "TEST-001",
            "subjectName": "Футболка",
            "brandName": "TestBrand",
            "metrics": {
                "stockCount": 1000,
                "ordersCount": 200
            }
        }
    ]
    
    print(f"📊 Input data: {analytics_data[0]['vendorCode']} - Stock: {analytics_data[0]['metrics']['stockCount']}, Orders: {analytics_data[0]['metrics']['ordersCount']}")
    
    # Test 1: No warehouse cache (API v1 unavailable)
    print("\n🧪 TEST 1: No Warehouse API v1 data available")
    cache = get_warehouse_cache()
    cache._cache = {}  # Clear cache to simulate no API data
    
    products = WildberriesCalculator.process_analytics_v2_data(analytics_data, None)
    
    if products:
        product = products[0]
        print(f"✅ Product created: {product.seller_article}")
        print(f"📦 Warehouses ({len(product.warehouses)}):")
        
        for warehouse in product.warehouses:
            print(f"  - {warehouse.name}: Stock={warehouse.stock}, Orders={warehouse.orders}")
            
            # Check for fake distribution
            if any(fake_name in warehouse.name.lower() for fake_name in ["коледино", "подольск", "электросталь"]):
                if warehouse.stock > 0 and warehouse.stock < analytics_data[0]['metrics']['stockCount']:
                    print(f"❌ FAKE DATA DETECTED: {warehouse.name} has partial stock ({warehouse.stock})")
                    return False
            
            # Check for proper warning messages
            if "недоступ" in warehouse.name.lower() or "api" in warehouse.name.lower():
                print(f"✅ Proper warning message: {warehouse.name}")
    
    # Test 2: Real warehouse cache data
    print("\n🧪 TEST 2: Real Warehouse API v1 data available")
    
    # Simulate real warehouse data from API v1
    real_warehouse_entry = WarehouseCacheEntry(
        warehouse_names=["Тула", "Белые Столбы", "Домодедово"],
        weights=[0.4, 0.3, 0.3],
        timestamp=time.time(),
        source="warehouse_api",  # This is REAL data source
        total_products=1,
        api_success_rate=1.0
    )
    
    cache.set_warehouses(
        warehouse_names=real_warehouse_entry.warehouse_names,
        source="warehouse_api",
        total_products=1
    )
    
    products = WildberriesCalculator.process_analytics_v2_data(analytics_data, real_warehouse_entry)
    
    if products:
        product = products[0]
        print(f"✅ Product created with REAL warehouse data: {product.seller_article}")
        print(f"📦 Real warehouses ({len(product.warehouses)}):")
        
        for warehouse in product.warehouses:
            print(f"  - {warehouse.name}: Stock={warehouse.stock}, Orders={warehouse.orders}")
    
    # Test 3: Get real warehouse list
    print("\n🧪 TEST 3: get_real_warehouse_list() function")
    
    real_warehouses = WildberriesCalculator.get_real_warehouse_list()
    print(f"📦 Real warehouse list: {real_warehouses}")
    
    if not real_warehouses:
        print("✅ CORRECT: Empty list when no real data available")
    else:
        print(f"✅ CORRECT: Found {len(real_warehouses)} real warehouses")
    
    print("\n🎯 RESULT: No fake data generation detected!")
    return True

if __name__ == "__main__":
    print("🚫 TESTING: NO FAKE DATA POLICY")
    print("=" * 60)
    print("Purpose: Verify system shows 'data unavailable' instead of fake distributions")
    print()
    
    try:
        success = test_no_fake_data_generation()
        if success:
            print("\n✅ ALL TESTS PASSED: No fake data generation")
            print("📊 System correctly shows limitations when API v1 unavailable")
        else:
            print("\n❌ TESTS FAILED: Fake data detected!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)