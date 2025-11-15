#!/usr/bin/env python3
"""
Improved warehouse data cleaner - keeps "Всего находится на складах" but removes "В пути" entries.
This script will filter out transit-related warehouse entries while preserving summary data.
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

def improved_clean_warehouse_data(warehouse_names, warehouse_orders, warehouse_stock):
    """
    Improved warehouse data cleaning - keeps summary data but removes transit entries.
    
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
    
    # Filter logic: keep summary and actual warehouses, remove only transit entries
    cleaned_names = []
    cleaned_orders = []
    cleaned_stock = []
    
    for i in range(len(names_list)):
        name = names_list[i].strip()
        order = orders_list[i].strip() if i < len(orders_list) else ''
        stock = stock_list[i].strip() if i < len(stock_list) else ''
        
        # Skip only specific "В пути" entries, but keep "Всего находится на складах"
        should_keep = True
        
        if 'В пути до получателей' in name:
            should_keep = False
        elif 'В пути возвраты на склад' in name:
            should_keep = False
        elif 'В пути' in name and 'Всего' not in name:
            # Remove other "В пути" entries but keep "Всего находится на складах"
            should_keep = False
        
        # Keep entry if it has a name and should be kept
        if should_keep and name:
            cleaned_names.append(name)
            cleaned_orders.append(order)
            cleaned_stock.append(stock)
    
    # Join back with newlines
    cleaned_names_str = '\n'.join(cleaned_names)
    cleaned_orders_str = '\n'.join(cleaned_orders)
    cleaned_stock_str = '\n'.join(cleaned_stock)
    
    return cleaned_names_str, cleaned_orders_str, cleaned_stock_str

async def restore_and_clean_warehouse_data():
    """Restore original data and apply improved cleaning."""
    
    print("🔄 Restoring and cleaning warehouse data...")
    print("This will restore original data and apply improved cleaning")
    print("Keeping 'Всего находится на складах' but removing 'В пути' entries")
    
    # We need to restore from backup or re-fetch the original data
    # For now, let's suggest manual restoration
    print("\n❗ Important:")
    print("To properly fix this, we need the original data before cleaning.")
    print("Options:")
    print("1. Restore from backup if available")
    print("2. Re-run the sync process to get fresh data")
    print("3. Manually check Google Sheets revision history")
    
    print(f"\n❓ Do you want to proceed with option 2 (re-sync data)? (y/N): ", end="")
    
    # For demonstration, let's show what the improved logic would do
    print("n")
    print("\nShowing improved cleaning logic on sample data:")
    
    # Sample data
    sample_warehouse_names = """В пути до получателей
В пути возвраты на склад WB
Всего находится на складах
Подольск 3
Электросталь
Краснодар"""
    
    sample_orders = """0
0
49
1
6
21"""
    
    sample_stock = """60
10
448
16
60
197"""
    
    print(f"\n📊 Sample BEFORE cleaning:")
    print(f"Names: {sample_warehouse_names.replace(chr(10), ' | ')}")
    print(f"Orders: {sample_orders.replace(chr(10), ' | ')}")
    print(f"Stock: {sample_stock.replace(chr(10), ' | ')}")
    
    # Apply improved cleaning
    cleaned_names, cleaned_orders, cleaned_stock = improved_clean_warehouse_data(
        sample_warehouse_names, sample_orders, sample_stock
    )
    
    print(f"\n📊 Sample AFTER improved cleaning:")
    print(f"Names: {cleaned_names.replace(chr(10), ' | ')}")
    print(f"Orders: {cleaned_orders.replace(chr(10), ' | ')}")
    print(f"Stock: {cleaned_stock.replace(chr(10), ' | ')}")
    
    print(f"\n✅ As you can see, 'Всего находится на складах' is preserved!")
    
    return True

async def suggest_restoration_options():
    """Suggest options for restoring the data."""
    
    print("\n🔧 Restoration Options:")
    print("=" * 50)
    
    print("\n1. 📋 Google Sheets Version History:")
    print("   - Open your Google Sheet")
    print("   - Go to File > Version History > See version history")
    print("   - Find a version before the cleaning")
    print("   - Restore that version")
    
    print("\n2. 🔄 Re-sync from Wildberries API:")
    print("   - Run the main sync script to fetch fresh data")
    print("   - This will overwrite current data with API data")
    print("   - Then apply improved cleaning")
    
    print("\n3. 🛠️ Manual Fix:")
    print("   - Add 'Всего находится на складах' entries manually")
    print("   - Use total orders/stock values for these entries")
    
    print("\n4. 🚀 Quick Fix Script:")
    print("   - Create entries based on total values for empty rows")
    print("   - This is an approximation but better than empty data")
    
    print(f"\n❓ Which option would you like to try? (1-4): ", end="")
    
    return True

if __name__ == "__main__":
    print("🔄 Improved Warehouse Data Cleaner")
    print("=" * 50)
    
    # First, analyze the current situation
    success = asyncio.run(restore_and_clean_warehouse_data())
    
    if success:
        asyncio.run(suggest_restoration_options())
        
        print("\n💡 Recommendation:")
        print("Use Google Sheets version history (Option 1) to restore")
        print("original data, then re-run cleaning with improved logic")
    else:
        print(f"\n💥 Failed to analyze restoration options")