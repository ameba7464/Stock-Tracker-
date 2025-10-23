#!/usr/bin/env python3
"""
Update existing products in Google Sheets with corrected warehouse stock calculations.
This script fixes the "in transit" warehouse issue by recalculating totals for existing products.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.database.operations import SheetsOperations
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger
from stock_tracker.core.models import Product, Warehouse

logger = get_logger(__name__)

async def update_existing_products():
    """Update existing products with corrected warehouse stock calculations."""
    
    print("🔄 Updating existing products with corrected warehouse logic...")
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize Google Sheets client
        sheets_client = GoogleSheetsClient(config)
        
        # Initialize database operations
        operations = SheetsOperations(sheets_client)
        
        print("📊 Reading existing products from Google Sheets...")
        
        # Read all products from sheets
        spreadsheet_id = config.google_sheets.sheet_id
        products = await operations.read_all_products(spreadsheet_id)
        print(f"✅ Found {len(products)} products in Google Sheets")
        
        if not products:
            print("❌ No products found in Google Sheets")
            return False
        
        # Update each product
        updated_count = 0
        for i, product in enumerate(products, 1):
            print(f"\n📦 Product {i}/{len(products)}: {product.seller_article}")
            
            # Check if product has warehouses
            if not product.warehouses:
                print(f"   ⚠️  No warehouses data, skipping...")
                continue
            
            # Calculate current totals (with in-transit)
            current_total_stock = sum(wh.stock for wh in product.warehouses)
            current_total_orders = sum(wh.orders for wh in product.warehouses)
            
            # Calculate corrected totals (excluding in-transit)
            real_warehouses = []
            in_transit_warehouses = []
            
            for wh in product.warehouses:
                if product._is_in_transit_warehouse(wh.name):
                    in_transit_warehouses.append(wh)
                else:
                    real_warehouses.append(wh)
            
            corrected_stock = sum(wh.stock for wh in real_warehouses)
            corrected_orders = sum(wh.orders for wh in product.warehouses)  # Keep all orders
            
            # Check if correction is needed
            if current_total_stock != corrected_stock:
                in_transit_stock = sum(wh.stock for wh in in_transit_warehouses)
                
                print(f"   🔧 Correction needed:")
                print(f"      Current total stock: {current_total_stock}")
                print(f"      Real warehouse stock: {corrected_stock}")
                print(f"      In-transit stock (excluded): {in_transit_stock}")
                print(f"      In-transit warehouses: {[wh.name for wh in in_transit_warehouses]}")
                
                # Update product with corrected values
                product.total_stock = corrected_stock
                product.total_orders = corrected_orders
                
                # Recalculate turnover
                if corrected_stock > 0:
                    product.turnover = corrected_orders / corrected_stock
                else:
                    product.turnover = 0.0
                
                # Update in Google Sheets
                try:
                    success = await operations.update_product(
                        product.wildberries_article, 
                        product
                    )
                    
                    if success:
                        print(f"   ✅ Updated in Google Sheets")
                        updated_count += 1
                    else:
                        print(f"   ❌ Failed to update in Google Sheets")
                        
                except Exception as e:
                    print(f"   ❌ Error updating product: {e}")
                    
            else:
                print(f"   ✅ Already correct (no in-transit warehouses)")
        
        print(f"\n{'='*60}")
        print(f"📊 UPDATE SUMMARY:")
        print(f"   Total products processed: {len(products)}")
        print(f"   Products updated: {updated_count}")
        print(f"   Products already correct: {len(products) - updated_count}")
        
        if updated_count > 0:
            print(f"\n🎉 Successfully updated {updated_count} products!")
            print(f"   ✅ Corrected warehouse stock calculations")
            print(f"   ✅ Excluded 'in transit' warehouses from totals")
            print(f"   ✅ Recalculated accurate turnover rates")
        else:
            print(f"\n✅ All products already have correct calculations")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating products: {e}")
        logger.error(f"Update failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(update_existing_products())
    if success:
        print(f"\n🚀 Products updated successfully!")
    else:
        print(f"\n💥 Update failed!")