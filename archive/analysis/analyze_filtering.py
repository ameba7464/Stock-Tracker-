#!/usr/bin/env python3
"""
Diagnostic script to analyze real data filtering issues.

This script will examine the actual data from API and show 
how orders are being matched to products and warehouses.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient, create_wildberries_client
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_data_filtering():
    """Analyze real data filtering and matching logic."""
    
    print("🔍 Analyzing Data Filtering Issues")
    print("=" * 60)
    
    try:
        # 1. Get fresh data from API
        print("\n📡 1. Fetching Fresh Data from API...")
        client = create_wildberries_client()
        fetcher = WildberriesProductDataFetcher(client)
        
        # Get recent orders (last 7 days)
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
        orders_data = await fetcher.fetch_supplier_orders(date_from, flag=0)
        print(f"   ✅ Orders fetched: {len(orders_data)}")
        
        # Get warehouse data
        warehouse_task_id = await fetcher.create_warehouse_remains_task()
        print(f"   ✅ Warehouse task created: {warehouse_task_id}")
        
        await asyncio.sleep(30)  # Wait for task processing
        warehouse_data = await fetcher.download_warehouse_remains(warehouse_task_id)
        print(f"   ✅ Warehouse data fetched: {len(warehouse_data)}")
        
        # 2. Analyze Orders Data Structure
        print("\n📋 2. Orders Data Analysis:")
        print("-" * 40)
        
        if orders_data:
            sample_order = orders_data[0]
            print("   Sample order structure:")
            for key, value in sample_order.items():
                print(f"      {key}: {value}")
            
            # Group orders by product
            orders_by_product = defaultdict(list)
            orders_by_warehouse = defaultdict(list)
            
            for order in orders_data:
                supplier_article = order.get('supplierArticle', 'Unknown')
                nm_id = order.get('nmId', 0)
                warehouse_name = order.get('warehouseName', 'Unknown')
                
                product_key = f"{supplier_article}|{nm_id}"
                orders_by_product[product_key].append(order)
                orders_by_warehouse[warehouse_name].append(order)
            
            print(f"\n   📊 Orders grouped by product: {len(orders_by_product)} unique products")
            print("   Top products by order count:")
            
            sorted_products = sorted(orders_by_product.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (product_key, product_orders) in enumerate(sorted_products[:5]):
                supplier_article, nm_id = product_key.split('|')
                print(f"      {i+1}. {supplier_article} (nmId: {nm_id}): {len(product_orders)} orders")
            
            print(f"\n   📦 Orders grouped by warehouse: {len(orders_by_warehouse)} warehouses")
            print("   Top warehouses by order count:")
            
            sorted_warehouses = sorted(orders_by_warehouse.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (warehouse_name, warehouse_orders) in enumerate(sorted_warehouses[:5]):
                print(f"      {i+1}. {warehouse_name}: {len(warehouse_orders)} orders")
        
        # 3. Analyze Warehouse Data Structure  
        print("\n📦 3. Warehouse Data Analysis:")
        print("-" * 40)
        
        if warehouse_data:
            sample_warehouse = warehouse_data[0]
            print("   Sample warehouse structure:")
            for key, value in sample_warehouse.items():
                if key == 'warehouses' and isinstance(value, list):
                    print(f"      {key}: {len(value)} warehouses")
                    if value:
                        print(f"         Sample warehouse: {value[0]}")
                else:
                    print(f"      {key}: {value}")
            
            # Analyze warehouse distribution
            warehouse_products = defaultdict(list)
            
            for wh_record in warehouse_data:
                supplier_article = wh_record.get('vendorCode', 'Unknown')
                nm_id = wh_record.get('nmId', 0)
                warehouses = wh_record.get('warehouses', [])
                
                product_key = f"{supplier_article}|{nm_id}"
                warehouse_products[product_key] = warehouses
            
            print(f"\n   📊 Warehouse products: {len(warehouse_products)} unique products")
            print("   Top products by warehouse count:")
            
            sorted_wh_products = sorted(warehouse_products.items(), key=lambda x: len(x[1]), reverse=True)
            for i, (product_key, warehouses) in enumerate(sorted_wh_products[:5]):
                supplier_article, nm_id = product_key.split('|')
                total_stock = sum(wh.get('quantity', 0) for wh in warehouses)
                print(f"      {i+1}. {supplier_article} (nmId: {nm_id}): {len(warehouses)} warehouses, {total_stock} total stock")
        
        # 4. Cross-Analysis: Orders vs Warehouse Data
        print("\n🔄 4. Cross-Analysis: Orders vs Warehouse Matching:")
        print("-" * 50)
        
        if orders_data and warehouse_data:
            # Check product matching
            order_products = set()
            warehouse_products_set = set()
            
            for order in orders_data:
                supplier_article = order.get('supplierArticle', '')
                nm_id = order.get('nmId', 0)
                if supplier_article and nm_id:
                    order_products.add(f"{supplier_article}|{nm_id}")
            
            for wh_record in warehouse_data:
                supplier_article = wh_record.get('vendorCode', '')
                nm_id = wh_record.get('nmId', 0)
                if supplier_article and nm_id:
                    warehouse_products_set.add(f"{supplier_article}|{nm_id}")
            
            print(f"   📋 Products with orders: {len(order_products)}")
            print(f"   📦 Products with warehouse data: {len(warehouse_products_set)}")
            
            matching_products = order_products.intersection(warehouse_products_set)
            print(f"   🎯 Matching products: {len(matching_products)}")
            
            if matching_products:
                print("\n   ✅ Matching products found:")
                for i, product_key in enumerate(list(matching_products)[:5]):
                    supplier_article, nm_id = product_key.split('|')
                    
                    # Count orders for this product
                    product_orders = [o for o in orders_data if o.get('supplierArticle') == supplier_article and o.get('nmId') == int(nm_id)]
                    
                    # Get warehouse data for this product
                    product_warehouse = next((w for w in warehouse_data if w.get('vendorCode') == supplier_article and w.get('nmId') == int(nm_id)), None)
                    
                    total_stock = 0
                    warehouse_count = 0
                    if product_warehouse and 'warehouses' in product_warehouse:
                        warehouses = product_warehouse['warehouses']
                        warehouse_count = len(warehouses)
                        total_stock = sum(wh.get('quantity', 0) for wh in warehouses)
                    
                    print(f"      {i+1}. {supplier_article} (nmId: {nm_id})")
                    print(f"         Orders: {len(product_orders)}")
                    print(f"         Stock: {total_stock} across {warehouse_count} warehouses")
                    
                    # Check warehouse name matching
                    if product_orders:
                        order_warehouses = set(o.get('warehouseName', '') for o in product_orders)
                        if product_warehouse and 'warehouses' in product_warehouse:
                            stock_warehouses = set(wh.get('warehouseName', '') for wh in product_warehouse['warehouses'])
                            common_warehouses = order_warehouses.intersection(stock_warehouses)
                            print(f"         Order warehouses: {len(order_warehouses)}")
                            print(f"         Stock warehouses: {len(stock_warehouses)}")
                            print(f"         Common warehouses: {len(common_warehouses)}")
                            
                            if len(common_warehouses) == 0:
                                print(f"         🚨 WARNING: No common warehouses!")
                                print(f"            Order WH: {list(order_warehouses)[:3]}")
                                print(f"            Stock WH: {list(stock_warehouses)[:3]}")
            
            # Check for unmatched products
            orders_only = order_products - warehouse_products_set
            warehouse_only = warehouse_products_set - order_products
            
            if orders_only:
                print(f"\n   ⚠️  Products with orders but no warehouse data: {len(orders_only)}")
                for product_key in list(orders_only)[:3]:
                    print(f"      - {product_key}")
            
            if warehouse_only:
                print(f"\n   ⚠️  Products with warehouse data but no orders: {len(warehouse_only)}")
                for product_key in list(warehouse_only)[:3]:
                    print(f"      - {product_key}")
        
        # 5. Identify Filtering Issues
        print("\n🔍 5. Potential Filtering Issues:")
        print("-" * 40)
        
        issues_found = []
        
        # Check for field name mismatches
        if orders_data and warehouse_data:
            order_sample = orders_data[0]
            warehouse_sample = warehouse_data[0]
            
            # Check supplier article field names
            order_supplier_field = 'supplierArticle' if 'supplierArticle' in order_sample else None
            warehouse_supplier_field = 'vendorCode' if 'vendorCode' in warehouse_sample else None
            
            if order_supplier_field != warehouse_supplier_field:
                issues_found.append(f"Field name mismatch: orders use '{order_supplier_field}', warehouse uses '{warehouse_supplier_field}'")
            
            # Check nmId consistency
            if 'nmId' not in order_sample:
                issues_found.append("nmId field missing in orders data")
            if 'nmId' not in warehouse_sample:
                issues_found.append("nmId field missing in warehouse data")
        
        # Check date range issues
        if orders_data:
            order_dates = []
            for order in orders_data[:10]:  # Sample first 10
                if 'date' in order:
                    order_dates.append(order['date'])
                elif 'lastChangeDate' in order:
                    order_dates.append(order['lastChangeDate'])
            
            if order_dates:
                print(f"   📅 Sample order dates: {order_dates[:3]}")
                
                # Check if dates are too old or too new
                now = datetime.now()
                recent_threshold = now - timedelta(days=30)
                
                old_orders = sum(1 for date_str in order_dates if datetime.fromisoformat(date_str.replace('Z', '+00:00')).replace(tzinfo=None) < recent_threshold)
                if old_orders > len(order_dates) * 0.8:  # More than 80% are old
                    issues_found.append(f"Most orders are older than 30 days - may need different date range")
        
        if issues_found:
            print("   🚨 Issues found:")
            for issue in issues_found:
                print(f"      - {issue}")
        else:
            print("   ✅ No obvious filtering issues detected")
        
        print("\n💡 6. Recommendations:")
        print("-" * 30)
        
        if len(matching_products) == 0:
            print("   🔧 CRITICAL: No matching products found!")
            print("      1. Check field name mapping (supplierArticle vs vendorCode)")
            print("      2. Verify nmId data types (string vs int)")
            print("      3. Check data freshness and date ranges")
        elif len(matching_products) < len(order_products) * 0.5:
            print("   ⚠️  Low product matching rate")
            print("      1. Review product filtering logic")
            print("      2. Check for data inconsistencies")
        else:
            print("   ✅ Good product matching rate")
            print("      1. Focus on warehouse name matching")
            print("      2. Review order counting logic")
        
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(analyze_data_filtering())