#!/usr/bin/env python3
"""
Test improved filtering logic with real API data.
Tests the fixes for field name mismatches and warehouse matching.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def test_improved_filtering():
    """Test the improved filtering logic."""
    
    print("🔍 Testing improved filtering logic...")
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize API client
        client = WildberriesAPIClient(config)
        products_api = WildberriesProductDataFetcher(client)
        
        print("📊 Fetching fresh API data...")
        
        # Fetch orders data with required date parameter
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S')
        
        orders_data = await products_api.fetch_supplier_orders(date_from)
        print(f"✅ Orders fetched: {len(orders_data)}")
        
        # Sample orders structure
        if orders_data:
            sample_order = orders_data[0]
            print(f"📋 Sample order structure: {list(sample_order.keys())}")
            print(f"   - nmId: {sample_order.get('nmId')}")
            print(f"   - supplierArticle: {sample_order.get('supplierArticle')}")
            print(f"   - warehouseName: {sample_order.get('warehouseName')}")
        
        # Fetch warehouse data
        task_id = await products_api.create_warehouse_remains_task()
        await asyncio.sleep(30)  # Wait for task processing
        
        warehouse_data = await products_api.download_warehouse_remains(task_id)
        print(f"✅ Warehouse data fetched: {len(warehouse_data)} records")
        
        # Sample warehouse structure
        if warehouse_data:
            sample_warehouse = warehouse_data[0]
            print(f"📦 Sample warehouse structure: {list(sample_warehouse.keys())}")
            print(f"   - nmId: {sample_warehouse.get('nmId')}")
            print(f"   - vendorCode: {sample_warehouse.get('vendorCode')}")
            if 'warehouses' in sample_warehouse:
                wh_list = sample_warehouse['warehouses']
                if wh_list:
                    print(f"   - warehouse example: {wh_list[0].get('warehouseName')}")
        
        # Initialize ProductService with mock database operations
        class MockDatabaseOperations:
            async def create_or_update_product(self, product):
                return True
            async def update_product(self, product_id, updated_product):
                return True
        
        product_service = ProductService(MockDatabaseOperations())
        
        print("\n🔧 Testing improved _convert_api_record_to_product method...")
        
        # Test conversion with problematic records
        test_cases = []
        
        # Find records that had matching issues
        for warehouse_record in warehouse_data[:5]:  # Test first 5 records
            nm_id = warehouse_record.get('nmId')
            vendor_code = warehouse_record.get('vendorCode', '')
            
            # Count matching orders for this product
            matching_orders_supplier = [o for o in orders_data if o.get('supplierArticle') == vendor_code]
            matching_orders_nmid = [o for o in orders_data if o.get('nmId') == nm_id]
            
            print(f"\n📊 Product nmId={nm_id}, vendorCode={vendor_code}")
            print(f"   Orders by supplierArticle: {len(matching_orders_supplier)}")
            print(f"   Orders by nmId: {len(matching_orders_nmid)}")
            
            # Test conversion
            converted_product = product_service._convert_api_record_to_product(
                warehouse_record, orders_data
            )
            
            print(f"   ✅ Converted product: {converted_product.name}")
            print(f"   📦 Total warehouses: {len(converted_product.warehouses)}")
            print(f"   📈 Total stock: {converted_product.total_quantity}")
            print(f"   🛒 Total orders: {converted_product.total_orders}")
            
            # Check warehouse distribution
            for wh in converted_product.warehouses:
                print(f"      {wh.name}: stock={wh.stock}, orders={wh.orders}")
            
            test_cases.append({
                'product': converted_product,
                'original_record': warehouse_record,
                'orders_count': len(matching_orders_nmid)
            })
        
        print(f"\n✅ Successfully tested {len(test_cases)} products with improved filtering logic")
        
        # Summary statistics
        total_stock = sum(case['product'].total_quantity for case in test_cases)
        total_orders = sum(case['product'].total_orders for case in test_cases)
        products_with_orders = sum(1 for case in test_cases if case['product'].total_orders > 0)
        
        print(f"\n📊 Test Summary:")
        print(f"   Total products tested: {len(test_cases)}")
        print(f"   Products with orders: {products_with_orders}")
        print(f"   Total stock across all products: {total_stock}")
        print(f"   Total orders across all products: {total_orders}")
        print(f"   Average orders per product: {total_orders / len(test_cases) if test_cases else 0:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing improved filtering: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_improved_filtering())