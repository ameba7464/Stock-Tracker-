#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick sync test for problematic articles
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.config import get_config
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations


async def test_sync():
    """Test sync with focus on problematic articles"""
    
    print("\n" + "="*100)
    print("SYNC TEST: Checking if FBS stocks are written to Google Sheets")
    print("="*100)
    
    config = get_config()
    
    # Initialize service
    service = ProductService(config)
    
    print("\nStarting sync...")
    
    # Run sync
    sync_session = await service.sync_from_dual_api_to_sheets(skip_existence_check=True)
    
    print(f"\nSync completed:")
    print(f"  - Total products: {sync_session.products_total}")
    print(f"  - Processed: {sync_session.products_processed}")
    print(f"  - Failed: {sync_session.products_failed}")
    print(f"  - Duration: {sync_session.duration_seconds:.1f} seconds")
    
    # Check specific products in Sheets
    print("\n" + "-"*100)
    print("Checking problematic articles in Google Sheets...")
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
            print(f"  Total orders: {product.total_orders}")
            print(f"  Warehouses: {len(product.warehouses)}")
            
            # Check for Marketpleys warehouse
            marketpleys_found = False
            for wh in product.warehouses:
                if 'маркетплейс' in wh.name.lower() or 'marketplace' in wh.name.lower():
                    print(f"  [OK] Found FBS warehouse: {wh.name} - stock: {wh.stock}, orders: {wh.orders}")
                    marketpleys_found = True
            
            if not marketpleys_found:
                print(f"  [FAIL] Marketpleys warehouse NOT FOUND!")
                print(f"  Available warehouses:")
                for wh in product.warehouses:
                    print(f"    - {wh.name}: {wh.stock}")
        else:
            print(f"\n{article}: NOT FOUND in Sheets")
    
    print("\n" + "="*100)
    print("TEST COMPLETED")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(test_sync())
