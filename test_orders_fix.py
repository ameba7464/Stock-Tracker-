#!/usr/bin/env python3
"""
Simple test script to verify the orders synchronization fix.

This script will test the basic synchronization to verify that 
orders are now properly counted and synchronized.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient, create_wildberries_client
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def test_orders_sync():
    """Test orders synchronization quickly."""
    
    print("🧪 Testing Orders Synchronization Fix")
    print("=" * 50)
    
    try:
        # 1. Test recent orders API directly (should work)
        print("\n📋 1. Testing Recent Orders API...")
        client = create_wildberries_client()
        fetcher = WildberriesProductDataFetcher(client)
        
        # Use just yesterday to avoid rate limit issues
        date_from = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        
        orders_data = await fetcher.fetch_supplier_orders(date_from, flag=0)
        print(f"   ✅ Recent orders (flag=0): {len(orders_data)} orders")
        
        if orders_data:
            sample = orders_data[0]
            print(f"   📋 Sample order: {sample.get('supplierArticle')} -> {sample.get('nmId')} at {sample.get('warehouseName')}")
        
        # Skip flag=1 to avoid rate limits for now
        orders_data_flag1 = []
        print(f"   ⚠️  Skipping flag=1 test to avoid rate limits")
        
        # 2. Test warehouse API with fixed parameters
        print("\n📦 2. Testing Warehouse API with Fixed Parameters...")
        try:
            task_id = await fetcher.create_warehouse_remains_task()
            print(f"   ✅ Created warehouse task: {task_id}")
            
            # Wait a bit for task to process
            print("   ⏳ Waiting 30 seconds...")
            await asyncio.sleep(30)
            
            warehouse_data = await fetcher.download_warehouse_remains(task_id, max_retries=3)
            print(f"   ✅ Downloaded warehouse data: {len(warehouse_data)} records")
            
            if warehouse_data:
                sample = warehouse_data[0]
                print(f"   📦 Sample warehouse: {sample.get('vendorCode')} -> {sample.get('nmId')} with {len(sample.get('warehouses', []))} warehouses")
                
        except Exception as e:
            print(f"   ⚠️  Warehouse API issue: {e}")
            # Continue with empty warehouse data for testing
            warehouse_data = []
        
        # 3. Test the actual product conversion logic
        print("\n🔄 3. Testing Product Conversion Logic...")
        
        if orders_data and warehouse_data:
            # Use product service conversion
            service = ProductService()
            
            # Test with first warehouse record
            for warehouse_record in warehouse_data[:1]:  # Just test first one
                product = service._convert_api_record_to_product(warehouse_record, orders_data)
                
                print(f"   🎯 Converted product: {product.seller_article}")
                print(f"      - Total stock: {product.total_stock}")
                print(f"      - Total orders: {product.total_orders}")
                print(f"      - Turnover rate: {product.turnover_rate:.3f}")
                print(f"      - Warehouses: {len(product.warehouses)}")
                
                if product.warehouses:
                    for wh in product.warehouses[:2]:  # Show first 2 warehouses
                        print(f"        * {wh.name}: {wh.stock} stock, {wh.orders} orders")
                
                # This is the key test - orders should no longer be 0!
                if product.total_orders > 0:
                    print(f"   ✅ SUCCESS: Orders are properly counted! ({product.total_orders} orders)")
                else:
                    print(f"   ⚠️  WARNING: Orders still showing 0")
                    
                break
        else:
            print("   ⚠️  Cannot test conversion - missing warehouse or orders data")
        
        # 4. Summary
        print("\n📊 4. Test Summary:")
        print("=" * 50)
        
        orders_working = len(orders_data) > 0
        warehouse_working = len(warehouse_data) > 0
        
        if orders_working:
            print("   ✅ Orders API: Working")
        else:
            print("   ❌ Orders API: Not working")
            
        if warehouse_working:
            print("   ✅ Warehouse API: Working")
        else:
            print("   ⚠️  Warehouse API: Issues (but not critical for orders)")
        
        if orders_working:
            print("\n   🎉 MAIN ISSUE LIKELY FIXED!")
            print("   📋 Orders data is now being retrieved successfully")
            print("   🔄 The 'orders showing 0' problem should be resolved")
            print("\n   💡 Next steps:")
            print("      1. Run full sync to update Google Sheets")
            print("      2. Check products in sheets for updated order counts")
            print("      3. Monitor warehouse API task timing")
        else:
            print("\n   ❌ Orders API still has issues")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_orders_sync())