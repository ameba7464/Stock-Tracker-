#!/usr/bin/env python3
"""
Diagnostic script for investigating orders synchronization issues.

This script helps diagnose why orders are showing as 0 while warehouse 
remains are properly fetched. It will test each API endpoint separately
and provide detailed diagnostics.
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient, create_wildberries_client
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config

logger = get_logger(__name__)


async def diagnose_orders_issue():
    """Comprehensive diagnosis of orders synchronization issue."""
    
    print("🔍 Starting Orders Synchronization Diagnosis")
    print("=" * 60)
    
    try:
        # Initialize clients
        print("\n📡 1. Initializing API Client...")
        config = get_config()
        client = create_wildberries_client()
        fetcher = WildberriesProductDataFetcher(client)
        
        print(f"   ✅ API Key configured: {'Yes' if config.wildberries.api_key else 'No'}")
        print(f"   ✅ Base URL: {config.wildberries.base_url}")
        print(f"   ✅ Statistics URL: {config.wildberries.statistics_base_url}")
        
        # Test basic connectivity
        print("\n🔌 2. Testing API Connectivity...")
        connectivity = await fetcher.validate_api_connectivity()
        
        print(f"   Overall Status: {connectivity['overall_status']}")
        for endpoint_name, endpoint_data in connectivity.get('endpoints', {}).items():
            status_icon = "✅" if endpoint_data['status'] == 'success' else "❌"
            print(f"   {status_icon} {endpoint_name}: {endpoint_data['status']}")
            if endpoint_data['status'] == 'error':
                print(f"      Error: {endpoint_data.get('error', 'Unknown')}")
        
        # Test warehouse remains (working)
        print("\n📦 3. Testing Warehouse Remains API...")
        try:
            warehouse_task_id = await fetcher.create_warehouse_remains_task()
            print(f"   ✅ Created warehouse task: {warehouse_task_id}")
            
            # Wait a bit and try to download
            print("   ⏳ Waiting 30 seconds for task processing...")
            await asyncio.sleep(30)
            
            warehouse_data = await fetcher.download_warehouse_remains(warehouse_task_id, max_retries=3)
            print(f"   ✅ Downloaded warehouse data: {len(warehouse_data)} records")
            
            # Show sample warehouse data
            if warehouse_data:
                sample = warehouse_data[0]
                print(f"   📋 Sample warehouse record:")
                print(f"      - supplierArticle: {sample.get('vendorCode', 'N/A')}")
                print(f"      - nmId: {sample.get('nmId', 'N/A')}")
                print(f"      - warehouses count: {len(sample.get('warehouses', []))}")
                
                if sample.get('warehouses'):
                    wh = sample['warehouses'][0]
                    print(f"      - warehouse example: {wh.get('warehouseName', 'N/A')} (stock: {wh.get('quantity', 0)})")
            
        except Exception as e:
            print(f"   ❌ Warehouse API failed: {e}")
            warehouse_data = []
        
        # Test orders API (problematic)
        print("\n📋 4. Testing Orders API...")
        
        # Try different date ranges
        date_ranges = [
            ("1 day ago", 1),
            ("7 days ago", 7),
            ("30 days ago", 30),
            ("90 days ago", 90)
        ]
        
        orders_results = {}
        
        for desc, days_back in date_ranges:
            try:
                date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
                print(f"\n   🗓️  Testing {desc} ({date_from})...")
                
                # Test both flag values
                for flag in [0, 1]:
                    try:
                        orders_data = await fetcher.fetch_supplier_orders(date_from, flag=flag)
                        orders_results[f"{desc}_flag_{flag}"] = len(orders_data)
                        print(f"      Flag {flag}: {len(orders_data)} orders")
                        
                        # Show sample order if available
                        if orders_data:
                            sample_order = orders_data[0]
                            print(f"      Sample order structure: {list(sample_order.keys())}")
                            print(f"      - supplierArticle: {sample_order.get('supplierArticle', 'N/A')}")
                            print(f"      - nmId: {sample_order.get('nmId', 'N/A')}")
                            print(f"      - warehouseName: {sample_order.get('warehouseName', 'N/A')}")
                            print(f"      - date: {sample_order.get('date', 'N/A')}")
                            print(f"      - lastChangeDate: {sample_order.get('lastChangeDate', 'N/A')}")
                        
                    except Exception as e:
                        print(f"      ❌ Flag {flag} failed: {e}")
                        orders_results[f"{desc}_flag_{flag}"] = f"Error: {e}"
                        
            except Exception as e:
                print(f"   ❌ {desc} failed: {e}")
        
        # Summary of orders results
        print("\n📊 5. Orders API Results Summary:")
        for test_name, result in orders_results.items():
            if isinstance(result, int):
                icon = "✅" if result > 0 else "⚠️"
                print(f"   {icon} {test_name}: {result} orders")
            else:
                print(f"   ❌ {test_name}: {result}")
        
        # Check if orders are truly empty or just not matching
        print("\n🔍 6. Product Matching Analysis...")
        
        if warehouse_data and any(isinstance(r, int) and r > 0 for r in orders_results.values()):
            print("   📦 Have warehouse data and orders data - checking matching...")
            
            # Get unique products from warehouse
            warehouse_products = set()
            for record in warehouse_data:
                supplier_article = record.get('vendorCode', '')
                nm_id = record.get('nmId', 0)
                if supplier_article and nm_id:
                    warehouse_products.add((supplier_article, nm_id))
            
            print(f"   📦 Warehouse products: {len(warehouse_products)}")
            
            # Get any orders data for comparison
            orders_data = None
            for test_name, result in orders_results.items():
                if isinstance(result, int) and result > 0:
                    # Re-fetch this successful query
                    parts = test_name.split('_')
                    days_back = int(parts[0].split()[0]) if parts[0].split()[0].isdigit() else 30
                    flag = int(parts[-1])
                    
                    date_from = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
                    orders_data = await fetcher.fetch_supplier_orders(date_from, flag=flag)
                    break
            
            if orders_data:
                # Get unique products from orders
                orders_products = set()
                for order in orders_data:
                    supplier_article = order.get('supplierArticle', '')
                    nm_id = order.get('nmId', 0)
                    if supplier_article and nm_id:
                        orders_products.add((supplier_article, nm_id))
                
                print(f"   📋 Orders products: {len(orders_products)}")
                
                # Find matches
                matching_products = warehouse_products.intersection(orders_products)
                print(f"   🎯 Matching products: {len(matching_products)}")
                
                if matching_products:
                    print("   ✅ Products match between warehouse and orders!")
                    # Show some examples
                    for i, (sa, nm) in enumerate(list(matching_products)[:3]):
                        print(f"      Example {i+1}: {sa} (nmId: {nm})")
                else:
                    print("   ⚠️  No matching products between warehouse and orders")
                    print("   📦 Warehouse products (first 3):")
                    for i, (sa, nm) in enumerate(list(warehouse_products)[:3]):
                        print(f"      {i+1}: {sa} (nmId: {nm})")
                    print("   📋 Orders products (first 3):")
                    for i, (sa, nm) in enumerate(list(orders_products)[:3]):
                        print(f"      {i+1}: {sa} (nmId: {nm})")
            
        else:
            print("   ⚠️  Cannot perform matching analysis - insufficient data")
        
        # Test the full synchronization flow
        print("\n🔄 7. Testing Full Synchronization Flow...")
        try:
            product_service = ProductService()
            sync_result = await product_service.sync_from_api_to_sheets()
            
            print(f"   Status: {sync_result.status}")
            print(f"   Products total: {sync_result.products_total}")
            print(f"   Products processed: {sync_result.products_processed}")
            print(f"   Products failed: {sync_result.products_failed}")
            
            if sync_result.errors:
                print("   Errors:")
                for error in sync_result.errors[:3]:  # Show first 3 errors
                    print(f"      - {error}")
                    
        except Exception as e:
            print(f"   ❌ Full sync test failed: {e}")
        
        # Final recommendations
        print("\n💡 8. Diagnosis and Recommendations:")
        print("=" * 60)
        
        # Check if we have warehouse data but no orders
        has_warehouse = len(warehouse_data) > 0
        has_orders = any(isinstance(r, int) and r > 0 for r in orders_results.values())
        
        if has_warehouse and not has_orders:
            print("   🔍 DIAGNOSIS: Warehouse data available but no orders found")
            print("   📋 POSSIBLE CAUSES:")
            print("      1. No orders in the tested date ranges")
            print("      2. Different authentication required for orders API")
            print("      3. Orders API endpoint URL incorrect")
            print("      4. Different API key needed for statistics API")
            print("      5. Account permissions don't include orders access")
            print("\n   🛠️  RECOMMENDATIONS:")
            print("      1. Check API key permissions for statistics endpoints")
            print("      2. Verify orders API base URL configuration")
            print("      3. Try longer date ranges (6+ months)")
            print("      4. Contact Wildberries support about orders API access")
            print("      5. Check if orders require different authentication")
            
        elif has_warehouse and has_orders:
            print("   🎯 DIAGNOSIS: Both APIs working - check product matching logic")
            print("   🛠️  RECOMMENDATIONS:")
            print("      1. Review product matching in _convert_api_record_to_product")
            print("      2. Check field name mapping (vendorCode vs supplierArticle)")
            print("      3. Verify date filtering in orders processing")
            
        elif not has_warehouse and not has_orders:
            print("   ❌ DIAGNOSIS: Both APIs failing - authentication/configuration issue")
            print("   🛠️  RECOMMENDATIONS:")
            print("      1. Verify API key is correct and active")
            print("      2. Check base URLs configuration")
            print("      3. Verify account has required API access")
            
        else:  # has_orders and not has_warehouse
            print("   🔄 DIAGNOSIS: Orders working but warehouse failing")
            print("   🛠️  RECOMMENDATIONS:")
            print("      1. Check warehouse API task creation logic")
            print("      2. Verify task polling and download logic")
            
    except Exception as e:
        print(f"\n❌ Diagnosis failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n✅ Diagnosis completed!")


if __name__ == "__main__":
    asyncio.run(diagnose_orders_issue())