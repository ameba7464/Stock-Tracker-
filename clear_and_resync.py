#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear table and re-sync with fixed FBS names
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.config import get_config


async def clear_and_resync():
    """Clear table and re-sync"""
    
    print("\n" + "="*100)
    print("CLEAR AND RE-SYNC with fixed FBS warehouse names")
    print("="*100)
    
    config = get_config()
    service = ProductService(config)
    
    # Step 1: Clear all products
    print("\nStep 1: Clearing all products from table...")
    cleared = service.operations.clear_all_products(
        config.google_sheets.sheet_id,
        "Stock Tracker"
    )
    print(f"  Cleared: {cleared}")
    
    # Step 2: Re-sync with skip_existence_check=True
    print("\nStep 2: Re-syncing from Dual API...")
    sync_session = await service.sync_from_dual_api_to_sheets(skip_existence_check=True)
    
    print(f"\nSync completed:")
    print(f"  - Total products: {sync_session.products_total}")
    print(f"  - Processed: {sync_session.products_processed}")
    print(f"  - Failed: {sync_session.products_failed}")
    print(f"  - Duration: {sync_session.duration_seconds:.1f} seconds")
    
    # Step 3: Verify specific products
    print("\n" + "-"*100)
    print("Step 3: Verifying problematic articles...")
    print("-"*100)
    
    problematic_articles = ['Its2/50g', 'ItsSport2/50g']
    
    for article in problematic_articles:
        product = service.operations.read_product(
            config.google_sheets.sheet_id,
            article,
            "Stock Tracker"
        )
        
        if product:
            print(f"\n{article}:")
            print(f"  Total stock: {product.total_stock}")
            print(f"  Warehouses: {len(product.warehouses)}")
            
            # Check for Marketpleys warehouse
            marketpleys_found = False
            for wh in product.warehouses:
                if wh.name == 'Маркетплейс' or wh.name == 'Marketpleys':
                    print(f"  [OK] FBS warehouse: '{wh.name}' - stock: {wh.stock}")
                    marketpleys_found = True
                elif 'fulllog' in wh.name.lower() and 'fbs' in wh.name.lower():
                    print(f"  [FAIL] OLD NAME FOUND: '{wh.name}' - stock: {wh.stock}")
            
            if not marketpleys_found:
                print(f"  [WARN] Marketpleys warehouse NOT FOUND")
                print(f"  Warehouses list:")
                for wh in product.warehouses[:10]:
                    print(f"    - {wh.name}: {wh.stock}")
        else:
            print(f"\n{article}: NOT FOUND")
    
    print("\n" + "="*100)
    print("COMPLETED")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(clear_and_resync())
