#!/usr/bin/env python3
"""
Analyze warehouse remains data structure from API to understand
what constitutes real warehouse stock vs "in transit" items.
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
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def analyze_warehouse_data_structure():
    """Analyze the warehouse data structure to understand stock types."""
    
    print("🔍 Analyzing warehouse data structure...")
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize API client
        client = WildberriesAPIClient(config)
        products_api = WildberriesProductDataFetcher(client)
        
        print("📊 Fetching warehouse remains data...")
        
        # Fetch warehouse data
        task_id = await products_api.create_warehouse_remains_task()
        await asyncio.sleep(30)  # Wait for task processing
        
        warehouse_data = await products_api.download_warehouse_remains(task_id)
        print(f"✅ Warehouse data fetched: {len(warehouse_data)} records")
        
        if not warehouse_data:
            print("❌ No warehouse data received")
            return False
        
        # Analyze first few products in detail
        for i, product_data in enumerate(warehouse_data[:3]):
            print(f"\n{'='*60}")
            print(f"📦 PRODUCT {i+1}: {product_data.get('vendorCode', 'Unknown')}")
            print(f"   nmId: {product_data.get('nmId')}")
            print(f"   subject: {product_data.get('subject', 'Unknown')}")
            print(f"   brand: {product_data.get('brand', 'Unknown')}")
            
            # Check all top-level fields
            print(f"\n📋 All product fields:")
            for key, value in product_data.items():
                if key != 'warehouses':
                    print(f"   {key}: {value}")
            
            # Analyze warehouse breakdown
            if 'warehouses' in product_data and isinstance(product_data['warehouses'], list):
                warehouses = product_data['warehouses']
                print(f"\n🏭 WAREHOUSES ({len(warehouses)} total):")
                
                total_all_warehouses = 0
                wb_warehouse_total = 0
                mp_warehouse_total = 0
                in_transit_total = 0
                
                warehouse_categories = {
                    'WB_warehouses': [],
                    'MP_warehouses': [],
                    'in_transit': [],
                    'other': []
                }
                
                for wh in warehouses:
                    wh_name = wh.get('warehouseName', 'Unknown')
                    wh_quantity = wh.get('quantity', 0)
                    total_all_warehouses += wh_quantity
                    
                    print(f"   📦 {wh_name}: {wh_quantity}")
                    
                    # Categorize warehouses
                    wh_name_lower = wh_name.lower()
                    if 'в пути' in wh_name_lower:
                        warehouse_categories['in_transit'].append(wh)
                        in_transit_total += wh_quantity
                    elif any(wb_keyword in wh_name_lower for wb_keyword in ['wb', 'wildberries', 'вайлдберриз']):
                        warehouse_categories['WB_warehouses'].append(wh)
                        wb_warehouse_total += wh_quantity
                    elif 'мп' in wh_name_lower or 'маркетплейс' in wh_name_lower:
                        warehouse_categories['MP_warehouses'].append(wh)
                        mp_warehouse_total += wh_quantity
                    else:
                        # Try to detect by common WB warehouse names
                        wb_cities = ['казань', 'подольск', 'электросталь', 'обухово', 'коледино', 
                                   'санкт-петербург', 'екатеринбург', 'новосибирск', 'краснодар']
                        if any(city in wh_name_lower for city in wb_cities):
                            warehouse_categories['WB_warehouses'].append(wh)
                            wb_warehouse_total += wh_quantity
                        else:
                            warehouse_categories['other'].append(wh)
                
                print(f"\n📊 WAREHOUSE BREAKDOWN:")
                print(f"   🏢 Total all warehouses: {total_all_warehouses}")
                print(f"   🏭 WB warehouses: {wb_warehouse_total} ({len(warehouse_categories['WB_warehouses'])} locations)")
                print(f"   🏪 MP warehouses: {mp_warehouse_total} ({len(warehouse_categories['MP_warehouses'])} locations)")
                print(f"   🚚 In transit: {in_transit_total} ({len(warehouse_categories['in_transit'])} locations)")
                print(f"   ❓ Other: {len(warehouse_categories['other'])} locations")
                
                # Show categorized warehouses
                for category, wh_list in warehouse_categories.items():
                    if wh_list:
                        print(f"\n   📂 {category.replace('_', ' ').title()}:")
                        for wh in wh_list:
                            print(f"      - {wh.get('warehouseName')}: {wh.get('quantity', 0)}")
                
                # Check if there are summary fields at product level
                print(f"\n🔢 PRODUCT-LEVEL TOTALS:")
                if 'quantityFull' in product_data:
                    print(f"   quantityFull: {product_data['quantityFull']}")
                if 'quantityNotInOrders' in product_data:
                    print(f"   quantityNotInOrders: {product_data['quantityNotInOrders']}")
                if 'quantityInTransit' in product_data:
                    print(f"   quantityInTransit: {product_data['quantityInTransit']}")
                
                # Calculate what should be "real stock" 
                real_stock_calculation = wb_warehouse_total + mp_warehouse_total
                print(f"\n💡 SUGGESTED CALCULATIONS:")
                print(f"   Real warehouse stock (WB + MP): {real_stock_calculation}")
                print(f"   In transit (should be excluded): {in_transit_total}")
                print(f"   Total as reported by API: {total_all_warehouses}")
        
        print(f"\n{'='*60}")
        print(f"🎯 ANALYSIS SUMMARY:")
        print(f"   • Current logic counts ALL warehouse quantities including 'В пути'")
        print(f"   • 'В пути' items are not actual warehouse stock")
        print(f"   • Real stock = WB warehouses + MP warehouses (excluding 'В пути')")
        print(f"   • Need to filter out warehouses with 'в пути' in the name")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing warehouse data: {e}")
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(analyze_warehouse_data_structure())