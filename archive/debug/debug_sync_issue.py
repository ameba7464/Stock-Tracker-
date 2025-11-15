"""
Debug script to investigate duplicate creation issue
"""
import asyncio
from src.stock_tracker.database.operations import SheetsOperations
from src.stock_tracker.core.formatter import ProductDataFormatter
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1wlbV0_LnAFHPWh2Xwb_RlXVT1Uf2MJOYOOJxOWJNhEI"
WORKSHEET_NAME = "Stock Tracker"

async def debug_product_lookup():
    """Debug why Its1_2_3/50g is not found"""
    
    # Initialize services
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file('config/service-account.json', scopes=scopes)
    gc = gspread.authorize(creds)
    
    formatter = ProductDataFormatter()
    operations = SheetsOperations(gc, formatter)
    
    print("=== Debugging Product Lookup ===\n")
    
    # Test case: Its1_2_3/50g should exist at row 2
    test_article = "Its1_2_3/50g"
    
    # Get worksheet
    worksheet = operations.get_or_create_worksheet(SPREADSHEET_ID, WORKSHEET_NAME)
    
    # Get all seller articles from column A
    print(f"1. Getting all seller articles from column A...")
    seller_articles = worksheet.col_values(1)
    print(f"   Found {len(seller_articles)} rows")
    print(f"   First 10 articles: {seller_articles[:10]}")
    
    # Check if test_article is in the list
    print(f"\n2. Looking for '{test_article}'...")
    for i, article in enumerate(seller_articles):
        if test_article.lower() in article.lower():
            print(f"   FOUND at index {i}, row {i+1}: '{article}'")
            print(f"   Article length: {len(article)}, Test length: {len(test_article)}")
            print(f"   Are they equal? {article.strip().lower() == test_article.strip().lower()}")
    
    # Try _find_product_row method
    print(f"\n3. Using _find_product_row method...")
    row_num = operations._find_product_row(worksheet, test_article)
    print(f"   Result: {row_num}")
    
    # Try read_product method
    print(f"\n4. Using read_product method...")
    product = operations.read_product(SPREADSHEET_ID, test_article, WORKSHEET_NAME)
    print(f"   Result: {product}")
    
    # Get row 2 data directly
    print(f"\n5. Reading row 2 directly...")
    row_2_data = worksheet.row_values(2)
    print(f"   Row 2 data: {row_2_data}")
    print(f"   Number of columns: {len(row_2_data)}")
    
    # Try to parse row 2
    print(f"\n6. Trying to parse row 2...")
    try:
        parsed_product = formatter.parse_product_from_sheets_row(row_2_data, 2)
        print(f"   Parsed product: {parsed_product}")
        if parsed_product:
            print(f"   Seller article: '{parsed_product.seller_article}'")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Check all products with insufficient columns
    print(f"\n7. Checking products with insufficient columns...")
    all_data = worksheet.get_all_values()
    for i, row in enumerate(all_data[1:], start=2):  # Skip header
        if len(row) < 8:
            print(f"   Row {i}: {len(row)} columns - {row[0] if row else 'EMPTY'}")

if __name__ == "__main__":
    asyncio.run(debug_product_lookup())
