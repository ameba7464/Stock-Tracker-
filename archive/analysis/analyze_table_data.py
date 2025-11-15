#!/usr/bin/env python3
"""
Analyze current table data and identify rows with missing warehouse information.
This script will help understand what happened after cleaning and suggest fixes.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def analyze_current_data():
    """Analyze current table data to see what's missing."""
    
    print("🔍 Analyzing current table data...")
    print("Checking for empty warehouse columns")
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize Google Sheets client
        sheets_client = GoogleSheetsClient()
        
        # Get spreadsheet
        spreadsheet_id = config.google_sheets.sheet_id
        worksheet_name = "Stock Tracker"
        
        print(f"📊 Connecting to spreadsheet: {spreadsheet_id}")
        print(f"📄 Worksheet: {worksheet_name}")
        
        # Get spreadsheet and worksheet
        spreadsheet = sheets_client.get_spreadsheet(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"✅ Found existing worksheet: {worksheet_name}")
        except Exception as e:
            print(f"❌ Error accessing worksheet: {e}")
            return False
        
        # Get all values from the worksheet
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) <= 1:
            print("❌ No data found in worksheet")
            return False
        
        print(f"📊 Found {len(all_values)} rows (including header)")
        
        # Process data rows (skip header)
        headers = all_values[0]
        data_rows = all_values[1:]
        
        print(f"\n📋 Headers: {headers}")
        print(f"📊 Analyzing {len(data_rows)} data rows...\n")
        
        # Warehouse columns (F=5, G=6, H=7 in 0-based indexing)
        warehouse_name_col = 5  # Column F
        warehouse_orders_col = 6  # Column G
        warehouse_stock_col = 7  # Column H
        
        empty_rows = []
        non_empty_rows = []
        
        for row_idx, row in enumerate(data_rows):
            row_num = row_idx + 2  # +2 because we skip header and use 1-based indexing
            
            # Get basic product info
            seller_article = row[0] if len(row) > 0 else ''
            wb_article = row[1] if len(row) > 1 else ''
            total_orders = row[2] if len(row) > 2 else ''
            total_stock = row[3] if len(row) > 3 else ''
            
            # Get warehouse data
            warehouse_names = row[warehouse_name_col] if len(row) > warehouse_name_col else ''
            warehouse_orders = row[warehouse_orders_col] if len(row) > warehouse_orders_col else ''
            warehouse_stock = row[warehouse_stock_col] if len(row) > warehouse_stock_col else ''
            
            # Check if warehouse data is empty
            is_empty = not (warehouse_names.strip() or warehouse_orders.strip() or warehouse_stock.strip())
            
            if is_empty:
                empty_rows.append({
                    'row': row_num,
                    'seller_article': seller_article,
                    'wb_article': wb_article,
                    'total_orders': total_orders,
                    'total_stock': total_stock
                })
            else:
                warehouse_count = len([name for name in warehouse_names.split('\n') if name.strip()])
                non_empty_rows.append({
                    'row': row_num,
                    'seller_article': seller_article,
                    'wb_article': wb_article,
                    'total_orders': total_orders,
                    'total_stock': total_stock,
                    'warehouse_count': warehouse_count,
                    'warehouse_names': warehouse_names
                })
        
        print(f"📊 Analysis Results:")
        print(f"   Total rows: {len(data_rows)}")
        print(f"   Rows with warehouse data: {len(non_empty_rows)}")
        print(f"   Rows with empty warehouse data: {len(empty_rows)}")
        print()
        
        if empty_rows:
            print(f"❌ Rows with empty warehouse data:")
            for row_info in empty_rows:
                print(f"   Row {row_info['row']}: {row_info['seller_article']} (WB: {row_info['wb_article']})")
                print(f"      Total orders: {row_info['total_orders']}, Total stock: {row_info['total_stock']}")
            print()
        
        if non_empty_rows:
            print(f"✅ Rows with warehouse data:")
            for row_info in non_empty_rows:
                print(f"   Row {row_info['row']}: {row_info['seller_article']} (WB: {row_info['wb_article']})")
                print(f"      Warehouses: {row_info['warehouse_count']}")
                # Show first few warehouse names
                names_preview = row_info['warehouse_names'].replace('\n', ', ')[:60]
                if len(names_preview) < len(row_info['warehouse_names']):
                    names_preview += "..."
                print(f"      Names: {names_preview}")
            print()
        
        # Analysis summary
        print(f"🎯 Summary:")
        print(f"   • {len(empty_rows)} products have NO warehouse data")
        print(f"   • {len(non_empty_rows)} products have warehouse data")
        
        if empty_rows:
            print(f"\n❗ Issue detected:")
            print(f"   The cleaning process removed ALL warehouse data for some products")
            print(f"   This likely means these products only had 'В пути' entries")
            print(f"   You may want to:")
            print(f"   1. Check if these products should have warehouse data")
            print(f"   2. Consider keeping 'Всего находится на складах' data")
            print(f"   3. Or accept that some products are only in transit")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing data: {e}")
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("🔍 Table Data Analyzer")
    print("=" * 50)
    print("This tool will analyze current table data")
    print("and identify rows with missing warehouse information")
    print()
    
    success = asyncio.run(analyze_current_data())
    
    if success:
        print(f"\n🎉 Analysis completed!")
    else:
        print(f"\n💥 Analysis failed")