"""
Проверка текущего состояния Google Sheets после полной синхронизации.
Показывает актуальные данные по заказам со складов.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.database.sheets import GoogleSheetsClient

def check_sheets_status():
    """Проверка текущего состояния таблицы"""
    
    print("=" * 70)
    print("CHECKING GOOGLE SHEETS STATUS")
    print("=" * 70)
    print()
    
    try:
        # Initialize
        config = StockTrackerConfig()
        sheets_client = GoogleSheetsClient(config.google_sheets.service_account_key_path,
                                          config.google_sheets.sheet_id,
                                          config.google_sheets.sheet_name)
        
        # Open sheet
        print("Opening Google Sheets...")
        spreadsheet = sheets_client._get_spreadsheet()
        
        # List all worksheets
        print(f"\nAvailable worksheets:")
        for ws in spreadsheet.worksheets():
            print(f"  - {ws.title} ({ws.row_count} rows, {ws.col_count} cols)")
        
        # Try to find the right worksheet
        worksheet = None
        for ws_name in ["Stock Tracker", "Sheet1", spreadsheet.worksheets()[0].title]:
            try:
                worksheet = spreadsheet.worksheet(ws_name)
                print(f"\nUsing worksheet: '{ws_name}'")
                break
            except:
                continue
        
        if worksheet is None:
            print("ERROR: Could not find worksheet!")
            return
        
        # Get all data
        print("Reading data...")
        all_values = worksheet.get_all_values()
        
        if len(all_values) < 2:
            print("No data in sheet!")
            return
        
        # Parse header
        header = all_values[0]
        print(f"\nColumns found: {len(header)}")
        print(f"Header: {header[:10]}...")  # First 10 columns
        
        # Find orders column
        orders_col_idx = None
        for idx, col_name in enumerate(header):
            if "заказ" in col_name.lower():
                orders_col_idx = idx
                print(f"\nOrders column found at index {idx}: '{col_name}'")
                break
        
        if orders_col_idx is None:
            print("\nWARNING: Orders column not found!")
            return
        
        # Parse data
        print(f"\nTotal rows: {len(all_values)}")
        print(f"Data rows: {len(all_values) - 1}")
        
        products_with_orders = 0
        total_orders = 0
        max_orders_product = ("", 0)
        
        print("\n" + "=" * 70)
        print("PRODUCTS WITH ORDERS:")
        print("=" * 70)
        print(f"{'Product':<40} {'Orders':>10}")
        print("-" * 70)
        
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) <= orders_col_idx:
                continue
            
            product_name = row[0] if len(row) > 0 else f"Row {row_idx}"
            orders_value = row[orders_col_idx]
            
            try:
                orders = int(orders_value) if orders_value else 0
            except ValueError:
                continue
            
            if orders > 0:
                products_with_orders += 1
                total_orders += orders
                print(f"{product_name:<40} {orders:>10}")
                
                if orders > max_orders_product[1]:
                    max_orders_product = (product_name, orders)
        
        print("-" * 70)
        print(f"{'TOTAL:':<40} {total_orders:>10}")
        print("=" * 70)
        
        # Summary
        print("\nSUMMARY:")
        print(f"  Products with orders > 0: {products_with_orders}")
        print(f"  Total orders: {total_orders}")
        print(f"  Top product: {max_orders_product[0]} ({max_orders_product[1]} orders)")
        
        # Check for zero orders
        products_with_zero = len(all_values) - 1 - products_with_orders
        if products_with_zero > 0:
            print(f"\n  WARNING: {products_with_zero} products have 0 orders")
        else:
            print(f"\n  SUCCESS: All products have orders data!")
        
        print("\n" + "=" * 70)
        print("CHECK COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_sheets_status()
