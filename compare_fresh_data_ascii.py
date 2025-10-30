#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
[*] [*] [*] [*] WB [*] [*] Stock-Tracker
[*] [*] [*] [*] [*] Google Sheets API
[*] [*]: 30-10-2025
"""

import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.database.sheets import GoogleSheetsClient

def get_fresh_tracker_data():
    """Get fresh data directly from Google Sheets"""
    config = get_config()
    
    client = GoogleSheetsClient(
        service_account_path=config.google_service_account_key_path,
        sheet_id=config.google_sheet_id,
        sheet_name=config.google_sheet_name
    )
    
    sheet = client.get_spreadsheet()
    worksheet = sheet.worksheet(config.google_sheet_name)
    
    # Get all data
    data = worksheet.get_all_values()
    
    # Convert to DataFrame
    if len(data) > 1:
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    else:
        return pd.DataFrame()

# [*] [*]
wb_file = r"c:\Users\miros\Downloads\30-10-2025 [*] [*] [*] 24-10-2025 [*] 30-10-2025_export.csv_export (1).tsv"

print("=" * 100)
print("[*] [*]: [*] [*] WB vs Stock-Tracker ([*] [*])")
print("=" * 100)

# [*] [*]
wb_df = pd.read_csv(wb_file, sep='\t', encoding='utf-8')
print(f"\n[*] [*] [*] [*] [*] Google Sheets API...")
tracker_df = get_fresh_tracker_data()

print(f"\n[+] [*] [*]:")
print(f"  - WB [*]: {len(wb_df)} [*]")
print(f"  - Stock-Tracker (LIVE): {len(tracker_df)} [*]")

# Print tracker columns
print(f"\n[i] [*] [*]: {list(tracker_df.columns)}")

# Print first row
if len(tracker_df) > 0:
    print(f"\n[*] [*] [*] [*]:")
    print(tracker_df.iloc[0].to_dict())

# [*] [*] [*] [*]
# WB [*]
wb_grouped = defaultdict(lambda: {
    'nm_id': None,
    'total_orders': 0,
    'total_stock': 0,
    'warehouses': []
})

for _, row in wb_df.iterrows():
    article = row.get('[*] [*]', '')
    nm_id = row.get('[*] WB', None)
    warehouse = row.get('[*]', '')
    orders = float(row.get('[*]', 0) or 0)
    stock = float(row.get('[*]', 0) or 0)
    
    if article:
        wb_grouped[article]['nm_id'] = nm_id
        wb_grouped[article]['total_orders'] += orders
        wb_grouped[article]['total_stock'] += stock
        wb_grouped[article]['warehouses'].append({
            'name': warehouse,
            'orders': orders,
            'stock': stock
        })

# Tracker [*]
tracker_grouped = {}
for _, row in tracker_df.iterrows():
    article = row.get('[*] [*]', '')
    
    if article:
        # Try to parse numeric values
        try:
            total_stock = int(row.get('[*] [*]', '0').replace(' ', ''))
        except:
            total_stock = 0
            
        try:
            total_orders = int(row.get('[*] [*] [*]', '0').replace(' ', ''))
        except:
            total_orders = 0
            
        try:
            nm_id = int(row.get('[*] WB', '0'))
        except:
            nm_id = 0
        
        tracker_grouped[article] = {
            'nm_id': nm_id,
            'total_orders': total_orders,
            'total_stock': total_stock,
            'turnover': row.get('[*] ([*])', '0')
        }

# [*]
print("\n" + "="*100)
print("[*] [*] [*] [*]")
print("="*100)

# Get common articles
wb_articles = set(wb_grouped.keys())
tracker_articles = set(tracker_grouped.keys())
common_articles = wb_articles & tracker_articles

print(f"\n[*] [*]:")
print(f"  - [*] WB [*]: {len(wb_articles)} [*]")
print(f"  - [*] Stock-Tracker: {len(tracker_articles)} [*]")
print(f"  - [*] [*]: {len(common_articles)}")
if wb_articles - tracker_articles:
    print(f"  - [*] [*] WB: {wb_articles - tracker_articles}")
if tracker_articles - wb_articles:
    print(f"  - [*] [*] Tracker: {tracker_articles - wb_articles}")

# Compare each common article
total_wb_orders = 0
total_tracker_orders = 0
total_wb_stock = 0
total_tracker_stock = 0

orders_match_count = 0
stock_match_count = 0

for article in sorted(common_articles):
    wb_data = wb_grouped[article]
    tracker_data = tracker_grouped[article]
    
    wb_orders = wb_data['total_orders']
    tracker_orders = tracker_data['total_orders']
    wb_stock = wb_data['total_stock']
    tracker_stock = tracker_data['total_stock']
    
    total_wb_orders += wb_orders
    total_tracker_orders += tracker_orders
    total_wb_stock += wb_stock
    total_tracker_stock += tracker_stock
    
    orders_match = wb_orders == tracker_orders
    stock_match = wb_stock == tracker_stock
    
    if orders_match:
        orders_match_count += 1
    if stock_match:
        stock_match_count += 1
    
    print(f"\n\n{'[*]'*100}")
    print(f"[*]  [*]: {article}")
    print(f"{'[*]'*100}")
    
    print(f"\n[*] [*] WB:")
    print(f"  WB:      {wb_data['nm_id']}")
    print(f"  Tracker: {tracker_data['nm_id']}")
    
    print(f"\n[*] [*] ([*] [*] [*] 24-30 [*]):")
    print(f"  WB:        {wb_orders} [*]")
    print(f"  Tracker:    {tracker_orders} [*]")
    if orders_match:
        print(f"  [*] [*]")
    else:
        diff = tracker_orders - wb_orders
        diff_pct = (diff / wb_orders * 100) if wb_orders > 0 else 0
        print(f"  [*] [*]: {diff:+.1f} [*] ({diff_pct:+.1f}%)")
    
    print(f"\n[*] [*] ([*] [*] [*]):")
    print(f"  WB:       {wb_stock} [*]")
    print(f"  Tracker:    {tracker_stock} [*]")
    if stock_match:
        print(f"  [*] [*]")
    else:
        diff = tracker_stock - wb_stock
        diff_pct = (diff / wb_stock * 100) if wb_stock > 0 else 0
        print(f"  [*] [*]: {diff:+.1f} [*] ({diff_pct:+.1f}%)")
    
    # Show WB warehouses
    print(f"\n[*] [*] ([*] WB):")
    active_warehouses = [w for w in wb_data['warehouses'] if w['orders'] > 0 or w['stock'] > 0]
    if active_warehouses:
        print(f"  [*] [*]: {len(active_warehouses)}")
        for wh in active_warehouses:
            print(f"    [*] {wh['name']:40} | [*]: {wh['orders']:>4} | [*]: {wh['stock']:>6}")
    
    print(f"\n[*]  [*] (Tracker): {tracker_data['turnover']} [*]")

# Summary
print("\n" + "="*100)
print("[*] [*]")
print("="*100)

print(f"\n[*] [*] [*] [*] [*]:")
print(f"\n  [*]:")
print(f"    WB:         {total_wb_orders} [*]")
print(f"    Tracker:      {total_tracker_orders} [*]")
print(f"    [*]:    {total_tracker_orders - total_wb_orders:+.1f} [*]")

print(f"\n  [*]:")
print(f"    WB:        {total_wb_stock} [*]")
print(f"    Tracker:     {total_tracker_stock} [*]")
print(f"    [*]:   {total_tracker_stock - total_wb_stock:+.1f} [*]")

print(f"\n[*] [*] [*]:")
print(f"    [*] [*] [*] [*] [*]:  {len(common_articles) - orders_match_count}/{len(common_articles)} ({(len(common_articles) - orders_match_count)/len(common_articles)*100:.1f}%)")
print(f"    [*] [*] [*] [*] [*]: {len(common_articles) - stock_match_count}/{len(common_articles)} ({(len(common_articles) - stock_match_count)/len(common_articles)*100:.1f}%)")

print("\n" + "="*100)
print("[*] [*] [*]")
print("="*100)

print(f"\n[*] [*] [*]:")
print(f"   - [*] [*] [*] [*] [*] [*] [*] [*] WB")
print(f"   - [*] [*] [*] [*] [*] Google Sheets API")
print(f"   - [*] [*] [*] [*] [*] [*]")

if orders_match_count == len(common_articles) and stock_match_count == len(common_articles):
    print(f"\n[*] [*]! [*] [*] [*] [*] [*] [*] [*] WB!")
else:
    print(f"\n[*]  [*] [*]:")
    print(f"   - [*] [*] [*] [*] ([*] [*] [*]-[*] [*] [*] [*])")
    print(f"   - [*] [*] [*] ([*] [*] [*]-[*] [*] [*] [*])")
    
    print(f"\n[*] [*]:")
    print(f"   1. [*], [*] [*] [*] [*] [*]")
    print(f"   2. [*] [*] [*] [*] (WB [*] [*] 24-30 [*])")
    print(f"   3. [*] [*] [*] [*] [*] [*]")
    print(f"   4. [*], [*] [*] [*] [*]")

print("\n" + "="*100)
