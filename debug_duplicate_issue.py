"""
Debug script to investigate duplicate creation issue
Simplified version using existing infrastructure
"""
import asyncio
from src.stock_tracker.database.sheets import GoogleSheetsClient
from src.stock_tracker.database.operations import SheetsOperations

SPREADSHEET_ID = "1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho"
WORKSHEET_NAME = "Stock Tracker"

async def debug_product_lookup():
    """Debug why Its1_2_3/50g is not found"""
    
    # Initialize services
    sheets_client = GoogleSheetsClient()
    operations = SheetsOperations(sheets_client)
    
    print("=== Debugging Product Lookup ===\n")
    
    # Test case: Its1_2_3/50g should exist at row 2
    test_article = "Its1_2_3/50g"
    
    # Get worksheet
    print(f"1. Getting worksheet '{WORKSHEET_NAME}'...")
    worksheet = operations.get_or_create_worksheet(SPREADSHEET_ID, WORKSHEET_NAME)
    print(f"   Worksheet found: {worksheet.title}")
    
    # Get all seller articles from column A
    print(f"\n2. Getting all seller articles from column A...")
    seller_articles = worksheet.col_values(1)
    print(f"   Found {len(seller_articles)} rows")
    print(f"   First 15 articles:")
    for i, article in enumerate(seller_articles[:15]):
        print(f"   Row {i+1}: '{article}' (length: {len(article)})")
    
    # Check if test_article is in the list
    print(f"\n3. Looking for '{test_article}' (length: {len(test_article)})...")
    found = False
    for i, article in enumerate(seller_articles):
        if test_article.lower() in article.lower():
            print(f"   POTENTIAL MATCH at index {i}, row {i+1}:")
            print(f"   - Article from sheet: '{article}'")
            print(f"   - Search term:        '{test_article}'")
            print(f"   - Are they equal? {article.strip().lower() == test_article.strip().lower()}")
            print(f"   - Repr comparison: {repr(article.strip())} vs {repr(test_article.strip())}")
            found = True
    
    if not found:
        print(f"   NOT FOUND in column A!")
    
    # Try _find_product_row method
    print(f"\n4. Using _find_product_row method...")
    row_num = operations._find_product_row(worksheet, test_article)
    print(f"   Result: {row_num}")
    
    # Try read_product method
    print(f"\n5. Using read_product method...")
    try:
        product = operations.read_product(SPREADSHEET_ID, test_article, WORKSHEET_NAME)
        if product:
            print(f"   SUCCESS - Found product:")
            print(f"   - Seller article: '{product.seller_article}'")
            print(f"   - WB article: {product.wildberries_article}")
        else:
            print(f"   FAILED - Product not found (returned None)")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Get row 2 data directly
    print(f"\n6. Reading row 2 directly...")
    try:
        row_2_data = worksheet.row_values(2)
        print(f"   Row 2 data: {row_2_data}")
        print(f"   Number of columns: {len(row_2_data)}")
    except Exception as e:
        print(f"   ERROR reading row 2: {e}")
    
    # Try to parse row 2
    print(f"\n7. Trying to parse row 2...")
    try:
        if len(row_2_data) > 0:
            parsed_product = operations.formatter.parse_product_from_sheets_row(row_2_data, 2)
            if parsed_product:
                print(f"   SUCCESS - Parsed product:")
                print(f"   - Seller article: '{parsed_product.seller_article}'")
                print(f"   - WB article: {parsed_product.wildberries_article}")
            else:
                print(f"   FAILED - parse_product_from_sheets_row returned None")
    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Check all products with insufficient columns
    print(f"\n8. Checking products with insufficient columns...")
    all_data = worksheet.get_all_values()
    problem_rows = []
    for i, row in enumerate(all_data[1:], start=2):  # Skip header
        if len(row) < 8:
            problem_rows.append((i, len(row), row[0] if row else 'EMPTY'))
            print(f"   Row {i}: {len(row)} columns - '{row[0] if row else 'EMPTY'}'")
    
    if not problem_rows:
        print("   No rows with insufficient columns found!")
    
    # Check for duplicate Its1_2_3/50g entries
    print(f"\n9. Looking for all '{test_article}' entries...")
    duplicate_rows = []
    for i, row in enumerate(all_data[1:], start=2):
        if row and len(row) > 0:
            if row[0].strip().lower() == test_article.strip().lower():
                duplicate_rows.append((i, row))
                print(f"   Found at row {i}: {row[:3]}... ({len(row)} columns)")
    
    if len(duplicate_rows) > 1:
        print(f"\n   WARNING: Found {len(duplicate_rows)} entries for '{test_article}'!")
    elif len(duplicate_rows) == 0:
        print(f"\n   WARNING: No entries found for '{test_article}'!")

if __name__ == "__main__":
    asyncio.run(debug_product_lookup())
