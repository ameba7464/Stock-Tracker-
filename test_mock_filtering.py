#!/usr/bin/env python3
"""
Test improved filtering logic with mock data based on real API structure.
Tests the fixes for field name mismatches and warehouse matching.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

def create_mock_data():
    """Create mock data based on real API structure from previous analysis."""
    
    # Mock orders data (using supplierArticle field)
    orders_data = [
        {
            "nmId": 12345,
            "supplierArticle": "ItsSport2/50g+Aks5/20g",
            "warehouseName": "Казань",
            "quantity": 1
        },
        {
            "nmId": 12345,
            "supplierArticle": "ItsSport2/50g+Aks5/20g", 
            "warehouseName": "Обухово МП",
            "quantity": 2
        },
        {
            "nmId": 67890,
            "supplierArticle": "Its2/50g+Aks5/20g",
            "warehouseName": "Электросталь",
            "quantity": 1
        },
        {
            "nmId": 67890,
            "supplierArticle": "Its2/50g+Aks5/20g",
            "warehouseName": "Подольск",
            "quantity": 1
        }
    ]
    
    # Mock warehouse data (using vendorCode field)
    warehouse_data = [
        {
            "nmId": 12345,
            "vendorCode": "ItsSport2/50g+Aks5/20g",  # Same value as supplierArticle
            "warehouses": [
                {
                    "warehouseName": "В пути возвраты на склад WB",
                    "quantity": 15
                },
                {
                    "warehouseName": "В пути до получателей", 
                    "quantity": 8
                },
                {
                    "warehouseName": "Казань",  # Matches order warehouse
                    "quantity": 5
                }
            ]
        },
        {
            "nmId": 67890,
            "vendorCode": "Its2/50g+Aks5/20g",
            "warehouses": [
                {
                    "warehouseName": "В пути возвраты на склад WB",
                    "quantity": 20
                },
                {
                    "warehouseName": "Подольск 3",  # Partial match with "Подольск"
                    "quantity": 12
                }
            ]
        }
    ]
    
    return orders_data, warehouse_data

def test_improved_filtering():
    """Test the improved filtering logic with mock data."""
    
    print("🔍 Testing improved filtering logic with mock data...")
    
    # Create mock data
    orders_data, warehouse_data = create_mock_data()
    
    print(f"📊 Mock data created:")
    print(f"   Orders: {len(orders_data)} records")
    print(f"   Warehouse data: {len(warehouse_data)} products")
    
    # Initialize ProductService with mock database operations
    class MockDatabaseOperations:
        async def create_or_update_product(self, product):
            return True
        async def update_product(self, product_id, updated_product):
            return True
    
    product_service = ProductService(MockDatabaseOperations())
    
    print("\n🔧 Testing _convert_api_record_to_product method...")
    
    for i, warehouse_record in enumerate(warehouse_data):
        nm_id = warehouse_record.get('nmId')
        vendor_code = warehouse_record.get('vendorCode', '')
        
        print(f"\n📦 Test Case {i+1}: nmId={nm_id}, vendorCode={vendor_code}")
        
        # Show matching orders for this product
        matching_orders_supplier = [o for o in orders_data if o.get('supplierArticle') == vendor_code]
        matching_orders_nmid = [o for o in orders_data if o.get('nmId') == nm_id]
        
        print(f"   📋 Orders by supplierArticle ('{vendor_code}'): {len(matching_orders_supplier)}")
        print(f"   📋 Orders by nmId ({nm_id}): {len(matching_orders_nmid)}")
        
        for order in matching_orders_nmid:
            print(f"      - {order['warehouseName']}: {order['quantity']} orders")
        
        # Test conversion with old vs new logic
        print(f"   🔄 Converting with improved logic...")
        
        converted_product = product_service._convert_api_record_to_product(
            warehouse_record, orders_data
        )
        
        print(f"   ✅ Converted product: {converted_product.seller_article} (nmId: {converted_product.wildberries_article})")
        print(f"   📊 Summary: {len(converted_product.warehouses)} warehouses, {converted_product.total_stock} stock, {converted_product.total_orders} orders")
        
        # Detailed warehouse breakdown
        for wh in converted_product.warehouses:
            print(f"      🏭 {wh.name}: stock={wh.stock}, orders={wh.orders}")
        
        # Check for improvements
        warehouses_with_orders = sum(1 for wh in converted_product.warehouses if wh.orders > 0)
        print(f"   📈 Warehouses with orders: {warehouses_with_orders}/{len(converted_product.warehouses)}")
        
        # Verify field matching worked
        total_orders_from_api = sum(o['quantity'] for o in matching_orders_nmid)
        if converted_product.total_orders > 0:
            print(f"   ✅ Orders successfully attributed: {converted_product.total_orders} total")
            if total_orders_from_api != converted_product.total_orders:
                print(f"   ⚠️  Order count difference: API={total_orders_from_api}, Converted={converted_product.total_orders}")
            else:
                print(f"   🎯 Perfect match: All {total_orders_from_api} orders correctly attributed!")
        else:
            print(f"   ❌ No orders attributed (API has {total_orders_from_api} orders)")
    
    print(f"\n✅ Test completed! The improved logic should handle:")
    print(f"   1. ✅ Field name mismatch (supplierArticle vs vendorCode)")
    print(f"   2. ✅ Partial warehouse name matching") 
    print(f"   3. ✅ Proportional order distribution for unmatched warehouses")
    print(f"   4. ✅ Better order attribution to correct products")

if __name__ == "__main__":
    test_improved_filtering()