#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verify final results in Google Sheets after fix
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.services.product_service import ProductService

async def verify_results():
    """Check that problematic articles now show Marketplace warehouse correctly"""
    service = ProductService()
    
    print("\n" + "="*100)
    print("FINAL VERIFICATION - Google Sheets Data")
    print("="*100)
    
    problematic_articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']
    
    for article in problematic_articles:
        print(f"\n{article}:")
        
        # Use read_product from operations instead
        try:
            product = service.operations.read_product(
                service.spreadsheet_id,
                article,
                worksheet_name=service.worksheet_name
            )
        except Exception as e:
            print(f"  [ERROR] Failed to read: {e}")
            continue
        
        if not product:
            print(f"  [ERROR] Not found in table!")
            continue
        print(f"  Total stock: {product.stock}")
        print(f"  Total orders: {product.orders}")
        print(f"  Warehouses: {len(product.warehouse_stocks)}")
        
        # Check for Marketplace warehouse
        marketplace_found = False
        marketplace_stock = 0
        
        print(f"  Warehouse details:")
        for wh_name, wh_stock in product.warehouse_stocks.items():
            print(f"    - {wh_name}: {wh_stock} pcs")
            if wh_name == 'Marketplace' or 'marketplace' in wh_name.lower():
                marketplace_found = True
                marketplace_stock = wh_stock
        
        if marketplace_found:
            print(f"  [SUCCESS] Marketplace warehouse found with {marketplace_stock} units")
        else:
            print(f"  [FAIL] Marketplace warehouse NOT found!")
    
    print("\n" + "="*100)
    print("VERIFICATION COMPLETED")
    print("="*100 + "\n")

if __name__ == '__main__':
    asyncio.run(verify_results())
