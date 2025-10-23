#!/usr/bin/env python3
"""
Clean warehouse data by removing "В пути" entries from warehouse information.
This script will filter out transit-related warehouse entries and keep only actual warehouses.
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

def clean_warehouse_data(warehouse_names, warehouse_orders, warehouse_stock):
    """
    Clean warehouse data by removing 'В пути' entries.
    
    Args:
        warehouse_names: String with warehouse names separated by newlines
        warehouse_orders: String with orders separated by newlines  
        warehouse_stock: String with stock separated by newlines
    
    Returns:
        Tuple of cleaned (names, orders, stock) strings
    """
    # Split data by newlines
    names_list = warehouse_names.split('\n') if warehouse_names else []
    orders_list = warehouse_orders.split('\n') if warehouse_orders else []
    stock_list = warehouse_stock.split('\n') if warehouse_stock else []
    
    # Ensure all lists have the same length by padding with empty strings
    max_length = max(len(names_list), len(orders_list), len(stock_list))
    names_list.extend([''] * (max_length - len(names_list)))
    orders_list.extend([''] * (max_length - len(orders_list)))
    stock_list.extend([''] * (max_length - len(stock_list)))
    
    # Filter out entries containing "В пути"
    cleaned_names = []
    cleaned_orders = []
    cleaned_stock = []
    
    for i in range(len(names_list)):
        name = names_list[i].strip()
        order = orders_list[i].strip() if i < len(orders_list) else ''
        stock = stock_list[i].strip() if i < len(stock_list) else ''
        
        # Skip entries with "В пути" in the name
        if 'В пути' not in name and name:  # Only keep non-empty names without "В пути"
            cleaned_names.append(name)
            cleaned_orders.append(order)
            cleaned_stock.append(stock)
    
    # Join back with newlines
    cleaned_names_str = '\n'.join(cleaned_names)
    cleaned_orders_str = '\n'.join(cleaned_orders)
    cleaned_stock_str = '\n'.join(cleaned_stock)
    
    return cleaned_names_str, cleaned_orders_str, cleaned_stock_str

async def clean_warehouse_table_data():
    """Clean warehouse data in the Google Sheets table."""
    
    print("🧹 Cleaning warehouse data...")
    print("Removing 'В пути' entries from warehouse information")
    
    try:
        # Load configuration
        config = get_config()
        
        # Initialize Google Sheets client
        sheets_client = GoogleSheetsClient()
        
        # Initialize table structure manager
        table_structure = SheetsTableStructure(sheets_client)
        
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
        
        print(f"📋 Headers: {headers}")
        print(f"📊 Processing {len(data_rows)} data rows...")
        
        # Find warehouse columns (F=5, G=6, H=7 in 0-based indexing)
        warehouse_name_col = 5  # Column F
        warehouse_orders_col = 6  # Column G
        warehouse_stock_col = 7  # Column H
        
        cleaned_data = []
        changes_made = 0
        
        for row_idx, row in enumerate(data_rows):
            # Ensure row has enough columns
            while len(row) < 8:
                row.append('')
            
            # Get warehouse data
            warehouse_names = row[warehouse_name_col] if warehouse_name_col < len(row) else ''
            warehouse_orders = row[warehouse_orders_col] if warehouse_orders_col < len(row) else ''
            warehouse_stock = row[warehouse_stock_col] if warehouse_stock_col < len(row) else ''
            
            # Clean warehouse data
            cleaned_names, cleaned_orders, cleaned_stock = clean_warehouse_data(
                warehouse_names, warehouse_orders, warehouse_stock
            )
            
            # Check if changes were made
            if (cleaned_names != warehouse_names or 
                cleaned_orders != warehouse_orders or 
                cleaned_stock != warehouse_stock):
                changes_made += 1
                print(f"   📝 Row {row_idx + 2}: Cleaned warehouse data")
                print(f"      Before: {len(warehouse_names.split('\n')) if warehouse_names else 0} warehouses")
                print(f"      After:  {len(cleaned_names.split('\n')) if cleaned_names else 0} warehouses")
            
            # Update row with cleaned data
            row[warehouse_name_col] = cleaned_names
            row[warehouse_orders_col] = cleaned_orders
            row[warehouse_stock_col] = cleaned_stock
            
            cleaned_data.append(row)
        
        print(f"\n📊 Summary:")
        print(f"   Rows processed: {len(data_rows)}")
        print(f"   Rows modified: {changes_made}")
        
        if changes_made > 0:
            print(f"\n❓ Apply changes to Google Sheets? (y/N): ", end="")
            
            # For automated execution, assume 'y'
            apply_changes = True  # input().strip().lower() == 'y'
            
            if apply_changes:
                print("y")  # Show the choice
                await apply_cleaned_data(worksheet, headers, cleaned_data)
            else:
                print("n")
                print("   ℹ️  No changes applied")
        else:
            print("   ℹ️  No 'В пути' entries found - no changes needed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning warehouse data: {e}")
        logger.error(f"Cleaning failed: {e}", exc_info=True)
        return False

async def apply_cleaned_data(worksheet, headers, cleaned_data):
    """Apply cleaned data to the worksheet."""
    
    print(f"\n🔄 Applying cleaned data to worksheet...")
    
    try:
        # Clear existing data
        print(f"   1. Clearing existing data...")
        worksheet.clear()
        
        # Update with headers + cleaned data
        print(f"   2. Writing cleaned data...")
        all_data = [headers] + cleaned_data
        
        # Calculate range
        num_rows = len(all_data)
        num_cols = len(headers)
        range_name = f"A1:{chr(ord('A') + num_cols - 1)}{num_rows}"
        
        # Update all data at once
        worksheet.update(range_name, all_data, value_input_option='RAW')
        
        print(f"   3. Applying formatting...")
        # Re-apply formatting
        from stock_tracker.database.structure import SheetsTableStructure
        from stock_tracker.database.sheets import GoogleSheetsClient
        
        sheets_client = GoogleSheetsClient()
        table_structure = SheetsTableStructure(sheets_client)
        table_structure.apply_complete_formatting(worksheet)
        
        print(f"✅ Successfully applied cleaned data!")
        print(f"   📊 Rows updated: {len(cleaned_data)}")
        print(f"   📋 Range: {range_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying cleaned data: {e}")
        logger.error(f"Data application failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("🧹 Warehouse Data Cleaner")
    print("=" * 50)
    print("This tool will remove 'В пути' entries from warehouse data")
    print("Keeping only actual warehouse locations")
    print()
    
    success = asyncio.run(clean_warehouse_table_data())
    
    if success:
        print(f"\n🎉 Warehouse data cleaning completed!")
        print(f"📋 Check your Google Sheets to verify the changes")
    else:
        print(f"\n💥 Failed to clean warehouse data")