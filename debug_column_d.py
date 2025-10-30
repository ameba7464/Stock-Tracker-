"""
Debug: Check column D (Total Stock) values
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.database.sheets import GoogleSheetsClient

def check_column_d():
    """Check what's in column D"""
    
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
    
    headers = all_values[0]
    print("Headers:", headers)
    print()
    
    target_articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']
    
    for article in target_articles:
        for i, row in enumerate(all_values[1:], start=2):
            if len(row) > 0 and row[0] == article:
                print(f"\n{article} (Row {i}):")
                print(f"  Column A (Article): '{row[0]}'")
                print(f"  Column B (NM ID): '{row[1] if len(row) > 1 else ''}'")
                print(f"  Column C (Orders Total): '{row[2] if len(row) > 2 else ''}'")
                print(f"  Column D (Stock Total): '{row[3] if len(row) > 3 else ''}'")
                print(f"  Column E (Turnover): '{row[4] if len(row) > 4 else ''}'")
                print(f"  Column F (Warehouse Names): '{row[5] if len(row) > 5 else ''}'")
                print(f"  Column G (Warehouse Orders): '{row[6] if len(row) > 6 else ''}'")
                print(f"  Column H (Warehouse Stocks): '{row[7] if len(row) > 7 else ''}'")
                break

if __name__ == '__main__':
    check_column_d()
