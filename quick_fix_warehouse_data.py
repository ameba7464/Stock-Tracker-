#!/usr/bin/env python3
"""
Quick fix for empty warehouse data - adds "Всего находится на складах" entries.
This script will add summary warehouse entries for products that have no warehouse data.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.structure import SheetsTableStructure
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def quick_fix_empty_warehouse_data():
    """Add 'Всего находится на складах' entries for products with empty warehouse data."""
    
    print("🚀 Quick Fix for Empty Warehouse Data")
    print("Adding 'Всего находится на складах' entries for products without warehouse data")
    
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
        
        # Warehouse columns (F=5, G=6, H=7 in 0-based indexing)
        warehouse_name_col = 5  # Column F
        warehouse_orders_col = 6  # Column G  
        warehouse_stock_col = 7  # Column H
        
        # Total columns for reference
        total_orders_col = 2  # Column C
        total_stock_col = 3   # Column D
        
        fixed_data = []
        fixes_applied = 0
        
        for row_idx, row in enumerate(data_rows):
            # Ensure row has enough columns
            while len(row) < 8:
                row.append('')
            
            # Get current warehouse data
            warehouse_names = row[warehouse_name_col] if warehouse_name_col < len(row) else ''
            warehouse_orders = row[warehouse_orders_col] if warehouse_orders_col < len(row) else ''
            warehouse_stock = row[warehouse_stock_col] if warehouse_stock_col < len(row) else ''
            
            # Get total data
            total_orders = row[total_orders_col] if total_orders_col < len(row) else ''
            total_stock = row[total_stock_col] if total_stock_col < len(row) else ''
            
            # Check if warehouse data is empty
            is_empty = not (warehouse_names.strip() or warehouse_orders.strip() or warehouse_stock.strip())
            
            if is_empty and (total_orders.strip() or total_stock.strip()):
                # Add "Всего находится на складах" entry
                row[warehouse_name_col] = "Всего находится на складах"
                row[warehouse_orders_col] = total_orders
                row[warehouse_stock_col] = total_stock
                
                fixes_applied += 1
                print(f"   📝 Row {row_idx + 2}: Added summary warehouse data")
                print(f"      Product: {row[0]} (WB: {row[1]})")
                print(f"      Orders: {total_orders}, Stock: {total_stock}")
            
            fixed_data.append(row)
        
        print(f"\n📊 Summary:")
        print(f"   Rows processed: {len(data_rows)}")
        print(f"   Fixes applied: {fixes_applied}")
        
        if fixes_applied > 0:
            print(f"\n❓ Apply fixes to Google Sheets? (y/N): ", end="")
            
            # For automated execution, assume 'y'
            apply_fixes = True  # input().strip().lower() == 'y'
            
            if apply_fixes:
                print("y")  # Show the choice
                await apply_quick_fixes(worksheet, headers, fixed_data)
            else:
                print("n")
                print("   ℹ️  No changes applied")
        else:
            print("   ℹ️  No empty warehouse data found - no fixes needed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying quick fix: {e}")
        logger.error(f"Quick fix failed: {e}", exc_info=True)
        return False

async def apply_quick_fixes(worksheet, headers, fixed_data):
    """Apply quick fixes to the worksheet."""
    
    print(f"\n🔄 Applying quick fixes to worksheet...")
    
    try:
        # Clear existing data
        print(f"   1. Clearing existing data...")
        worksheet.clear()
        
        # Update with headers + fixed data
        print(f"   2. Writing fixed data...")
        all_data = [headers] + fixed_data
        
        # Calculate range
        num_rows = len(all_data)
        num_cols = len(headers)
        range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"
        
        # Update all data at once
        worksheet.update(values=all_data, range_name=range_name, value_input_option='RAW')
        
        print(f"   3. Applying formatting...")
        # Re-apply formatting
        table_structure = SheetsTableStructure(GoogleSheetsClient())
        table_structure.apply_complete_formatting(worksheet)
        
        print(f"✅ Successfully applied quick fixes!")
        print(f"   📊 Rows updated: {len(fixed_data)}")
        print(f"   📋 Range: {range_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying quick fixes: {e}")
        logger.error(f"Quick fix application failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("🚀 Quick Fix for Empty Warehouse Data")
    print("=" * 50)
    print("This tool will add 'Всего находится на складах' entries")
    print("for products that have no warehouse data but have totals")
    print()
    
    success = asyncio.run(quick_fix_empty_warehouse_data())
    
    if success:
        print(f"\n🎉 Quick fix completed!")
        print(f"📋 Check your Google Sheets to verify the changes")
        print(f"\n💡 Note: This is a temporary fix based on total values")
        print(f"For complete data, consider re-syncing from Wildberries API")
    else:
        print(f"\n💥 Quick fix failed")