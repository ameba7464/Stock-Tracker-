#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug FBS details structure
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from stock_tracker.utils.config import get_config
import json


def debug_fbs_details():
    """Debug FBS details structure"""
    
    config = get_config()
    fetcher = DualAPIStockFetcher(config.wildberries_api_key)
    
    print("\n" + "="*100)
    print("DEBUG: FBS Details Structure")
    print("="*100)
    
    # Get combined stocks
    stocks = fetcher.get_combined_stocks_by_article('Its2/50g')
    
    if 'Its2/50g' in stocks:
        data = stocks['Its2/50g']
        
        print(f"\nIts2/50g FBS Details:")
        print(f"  Total FBS details: {len(data['fbs_details'])}")
        
        for i, detail in enumerate(data['fbs_details'], 1):
            print(f"\n  Detail #{i}:")
            print(f"    warehouse_name: {repr(detail.get('warehouse_name'))}")
            print(f"    warehouse_id: {detail.get('warehouse_id')}")
            print(f"    barcode: {detail.get('barcode')}")
            print(f"    amount: {detail.get('amount')}")
        
        print(f"\n  Full FBS details JSON:")
        print(json.dumps(data['fbs_details'], indent=2, ensure_ascii=False))
    else:
        print("\nIts2/50g NOT FOUND")
    
    print("\n" + "="*100)


if __name__ == "__main__":
    debug_fbs_details()
