"""
Simple verification of problematic articles in Google Sheets
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.database.sheets import GoogleSheetsClient

def check_articles():
    """Check specific problematic articles"""
    
    print("\n" + "="*100)
    print("FINAL VERIFICATION - Checking Its2/50g and ItsSport2/50g in Google Sheets")
    print("="*100)
    
    config = StockTrackerConfig()
    sheets = GoogleSheetsClient(
        config.google_sheets.service_account_key_path,
        config.google_sheets.sheet_id,
        config.google_sheets.sheet_name
    )
    
    spreadsheet = sheets._get_spreadsheet()
    worksheet = spreadsheet.worksheet("Stock Tracker")
    
    # Get all data
    all_values = worksheet.get_all_values()
    
    if not all_values:
        print("ERROR: No data in worksheet")
        return
    
    # Find column indices
    headers = all_values[0]
    print(f"\nHeaders: {headers}")
    
    article_col = 0  # Column A
    stock_col = 3    # Column D - Total stocks
    warehouse_names_col = 5  # Column F - Warehouse names
    warehouse_stocks_col = 7  # Column H - Warehouse stocks
    
    target_articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']
    
    for article in target_articles:
        print(f"\n{article}:")
        found = False
        
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) > article_col and row[article_col] == article:
                found = True
                total_stock = row[stock_col] if len(row) > stock_col else "N/A"
                warehouse_names = row[warehouse_names_col] if len(row) > warehouse_names_col else ""
                warehouse_stocks = row[warehouse_stocks_col] if len(row) > warehouse_stocks_col else ""
                
                print(f"  Row: {i}")
                print(f"  Total stock: {total_stock}")
                
                # Parse warehouse data (multi-line cells with \n separator)
                wh_names_list = warehouse_names.split('\n') if warehouse_names else []
                wh_stocks_list = warehouse_stocks.split('\n') if warehouse_stocks else []
                
                print(f"  Warehouses ({len(wh_names_list)}):")
                for j, (name, stock) in enumerate(zip(wh_names_list, wh_stocks_list), 1):
                    print(f"    {j}. {name}: {stock} pcs")
                    
                # Check for Marketplace warehouse
                marketplace_variants = ['Маркетплейс', 'маркетплейс', 'Marketplace', 'marketplace', 'FBS']
                marketplace_found = False
                
                for name in wh_names_list:
                    if any(variant.lower() in name.lower() for variant in marketplace_variants):
                        marketplace_found = True
                        idx = wh_names_list.index(name)
                        stock = wh_stocks_list[idx] if idx < len(wh_stocks_list) else "N/A"
                        print(f"\n  [SUCCESS] Marketplace warehouse found: '{name}' with {stock} units")
                        break
                
                if not marketplace_found:
                    print(f"\n  [FAIL] Marketplace warehouse NOT found!")
                    print(f"  Available warehouses: {wh_names_list}")
                
                break
        
        if not found:
            print(f"  [ERROR] Article not found in table!")
    
    print("\n" + "="*100)
    print("VERIFICATION COMPLETED")
    print("="*100 + "\n")

if __name__ == '__main__':
    check_articles()
