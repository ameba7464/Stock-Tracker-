#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Dual API for problematic articles
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from stock_tracker.utils.config import get_config


def test_problematic_articles():
    """Test problematic articles that were losing FBS stocks"""
    
    config = get_config()
    fetcher = DualAPIStockFetcher(config.wildberries_api_key)
    
    problematic_articles = ['Its2/50g', 'ItsSport2/50g']
    working_articles = ['Its2/50g+Aks5/20g.FBS']
    
    print("\n" + "="*100)
    print("TEST: Problematic Articles FBS Stock Check")
    print("="*100)
    
    print("\nPROBLEMATIC ARTICLES (were missing FBS stocks):")
    print("-" * 100)
    
    for article in problematic_articles:
        stocks = fetcher.get_combined_stocks_by_article(article)
        
        if article in stocks:
            data = stocks[article]
            print(f"\n{article}:")
            print(f"  NM ID: {data['nm_id']}")
            print(f"  FBO stock: {data['fbo_stock']} pcs")
            print(f"  FBS stock: {data['fbs_stock']} pcs  <- SHOULD BE > 0")
            print(f"  TOTAL: {data['total_stock']} pcs")
            
            if data['fbs_details']:
                print(f"\n  FBS warehouses:")
                for detail in data['fbs_details']:
                    wh = detail.get('warehouse_name')
                    qty = detail.get('amount', 0)
                    print(f"    - {wh}: {qty} pcs")
            else:
                print("  [WARN] NO FBS warehouses found!")
        else:
            print(f"\n{article}: NOT FOUND in API")
    
    print("\n\nWORKING ARTICLES (correct FBS stocks):")
    print("-" * 100)
    
    for article in working_articles:
        stocks = fetcher.get_combined_stocks_by_article(article)
        
        if article in stocks:
            data = stocks[article]
            print(f"\n{article}:")
            print(f"  NM ID: {data['nm_id']}")
            print(f"  FBO stock: {data['fbo_stock']} pcs")
            print(f"  FBS stock: {data['fbs_stock']} pcs")
            print(f"  TOTAL: {data['total_stock']} pcs")
            
            if data['fbs_details']:
                print(f"\n  FBS warehouses:")
                for detail in data['fbs_details']:
                    wh = detail.get('warehouse_name')
                    qty = detail.get('amount', 0)
                    print(f"    - {wh}: {qty} pcs")
        else:
            print(f"\n{article}: NOT FOUND in API")
    
    print("\n" + "="*100)
    print("TEST COMPLETED")
    print("="*100)
    print("\nEXPECTED RESULTS:")
    print("  - Its2/50g should have ~2019 pcs FBS stock (Marketpleys warehouse)")
    print("  - ItsSport2/50g should have ~1016 pcs FBS stock (Marketpleys warehouse)")
    print("  - Both should show warehouse name: 'Marketpleys' (normalized)")
    print("="*100)


if __name__ == "__main__":
    test_problematic_articles()
