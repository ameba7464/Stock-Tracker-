"""
Check what's actually in Google Sheets right now
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.config import get_config
from stock_tracker.database.sheets import GoogleSheetsClient

def check_sheets():
    """Check Google Sheets data"""
    config = get_config()
    
    client = GoogleSheetsClient(
        spreadsheet_id=config.google_sheet_id,
        credentials_file=config.google_credentials_file
    )
    
    print(f"\n📊 Checking Google Sheets data")
    print(f"Sheet ID: {config.google_sheet_id}")
    print("="*80)
    
    # Open sheet
    sheet = client.open_sheet()
    worksheet = sheet.worksheet('Stock Tracker')
    
    # Get all data
    data = worksheet.get_all_values()
    
    print(f"\n✅ Retrieved {len(data)} rows")
    
    # Show first 5 rows
    print(f"\n📋 First 5 rows:")
    for i, row in enumerate(data[:5]):
        print(f"Row {i+1}: {row}")
    
    # Check specific product
    print(f"\n🔍 Checking Its1_2_3/50g:")
    for i, row in enumerate(data):
        if len(row) > 0 and 'Its1_2_3/50g' in row[0]:
            print(f"Row {i+1}: {row}")
            break

if __name__ == "__main__":
    check_sheets()
