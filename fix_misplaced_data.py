#!/usr/bin/env python3
"""
Fix misplaced data in Google Sheets table.
This script identifies and fixes rows where data has shifted between columns.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials
import json

def fix_misplaced_data():
    """Find and fix misplaced data in the table."""
    
    print("🔧 Fixing misplaced data in Google Sheets...")
    
    try:
        # Configuration
        SHEET_ID = "1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho"
        WORKSHEET_NAME = "Stock Tracker"
        SERVICE_ACCOUNT_PATH = "config/service-account.json"
        
        # Initialize Google Sheets client
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Open spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        print(f"✅ Connected to worksheet: {WORKSHEET_NAME}")
        
        # Get all data
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            print("❌ No data rows found")
            return False
        
        headers = all_values[0]
        data_rows = all_values[1:]
        
        print(f"📊 Analyzing {len(data_rows)} data rows...")
        
        # Analyze each row for misplaced data
        fixes_needed = []
        
        for row_idx, row in enumerate(data_rows, 2):  # Start from row 2 (after header)
            print(f"\n🔍 Analyzing row {row_idx}:")
            
            # Check if this row has the missing "Заказы со склада" (column G) issue
            if len(row) >= 8:
                seller_article = row[0].strip()  # A
                wb_article = row[1].strip()      # B  
                total_orders = row[2].strip()    # C
                total_stock = row[3].strip()     # D
                turnover = row[4].strip()        # E
                warehouse_names = row[5].strip() # F
                warehouse_orders = row[6].strip() # G
                warehouse_stock = row[7].strip()  # H
                
                print(f"   A: '{seller_article}'")
                print(f"   B: '{wb_article}'")
                print(f"   C: '{total_orders}'")
                print(f"   D: '{total_stock}'")
                print(f"   E: '{turnover}'")
                print(f"   F: '{warehouse_names[:50]}{'...' if len(warehouse_names) > 50 else ''}'")
                print(f"   G: '{warehouse_orders[:50]}{'...' if len(warehouse_orders) > 50 else ''}'")
                print(f"   H: '{warehouse_stock[:50]}{'...' if len(warehouse_stock) > 50 else ''}'")
                
                # Check for the specific issue: missing warehouse orders (G)
                # Pattern: if G is empty but H has data, data might have shifted
                if not warehouse_orders.strip() and warehouse_stock.strip():
                    print(f"   ⚠️  Column G (Заказы со склада) is empty but H has data - possible shift")
                    
                    # Check if H contains what should be in G
                    h_lines = warehouse_stock.split('\n')
                    if len(h_lines) > 1:
                        print(f"   🔍 Analyzing H content with {len(h_lines)} lines")
                        
                        # Check if this looks like it might contain orders data
                        numeric_lines = [line.strip() for line in h_lines if line.strip().isdigit()]
                        if len(numeric_lines) > 0:
                            print(f"   💡 Found {len(numeric_lines)} numeric lines in H - might be orders")
                            
                            # This could be the issue - ask user to confirm
                            print(f"   ❓ Does this row need fixing? (y/n): ", end="")
                            user_input = input().strip().lower()
                            
                            if user_input == 'y':
                                fixes_needed.append({
                                    'row': row_idx,
                                    'issue': 'missing_warehouse_orders',
                                    'data': row[:]
                                })
                                print(f"   ✅ Marked for fixing")
                            else:
                                print(f"   ➡️  Skipping")
                        else:
                            print(f"   ✅ H data looks correct (non-numeric)")
                    else:
                        print(f"   ✅ H has single line - probably correct")
                
                # Check for other potential issues
                elif warehouse_orders.strip() and not warehouse_stock.strip():
                    print(f"   ⚠️  Column G has data but H is empty - unusual pattern")
                
                elif len(warehouse_names.split('\n')) != len(warehouse_orders.split('\n')) and warehouse_orders.strip():
                    names_count = len([line for line in warehouse_names.split('\n') if line.strip()])
                    orders_count = len([line for line in warehouse_orders.split('\n') if line.strip()])
                    stock_count = len([line for line in warehouse_stock.split('\n') if line.strip()])
                    
                    print(f"   📊 Line counts: Names={names_count}, Orders={orders_count}, Stock={stock_count}")
                    
                    if orders_count != names_count or stock_count != names_count:
                        print(f"   ⚠️  Mismatched line counts - data might be misaligned")
                        print(f"   ❓ Does this row need manual review? (y/n): ", end="")
                        user_input = input().strip().lower()
                        
                        if user_input == 'y':
                            fixes_needed.append({
                                'row': row_idx,
                                'issue': 'misaligned_warehouse_data',
                                'data': row[:]
                            })
                            print(f"   ✅ Marked for manual review")
                        else:
                            print(f"   ➡️  Skipping")
                else:
                    print(f"   ✅ Row looks correct")
        
        # Apply fixes
        if fixes_needed:
            print(f"\n🔧 Found {len(fixes_needed)} rows that need fixing:")
            for fix in fixes_needed:
                print(f"   - Row {fix['row']}: {fix['issue']}")
            
            print(f"\n❓ Apply fixes? (y/n): ", end="")
            apply_fixes = input().strip().lower() == 'y'
            
            if apply_fixes:
                apply_data_fixes(worksheet, fixes_needed)
            else:
                print(f"   ℹ️  No fixes applied")
        else:
            print(f"\n✅ No data issues found!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing data: {e}")
        return False

def apply_data_fixes(worksheet, fixes_needed):
    """Apply the identified fixes to the worksheet."""
    try:
        print(f"\n🔧 Applying {len(fixes_needed)} fixes...")
        
        for fix in fixes_needed:
            row_num = fix['row']
            issue = fix['issue']
            data = fix['data']
            
            print(f"\n   Fixing row {row_num} ({issue})...")
            
            if issue == 'missing_warehouse_orders':
                # Try to fix the missing warehouse orders issue
                warehouse_names = data[5].strip()  # F
                warehouse_stock = data[7].strip()  # H
                
                print(f"     Current warehouse names (F):")
                names_lines = [line.strip() for line in warehouse_names.split('\n') if line.strip()]
                for i, line in enumerate(names_lines[:5]):  # Show first 5
                    print(f"       {i+1}. {line}")
                
                print(f"     Current warehouse stock (H):")
                stock_lines = [line.strip() for line in warehouse_stock.split('\n') if line.strip()]
                for i, line in enumerate(stock_lines[:5]):  # Show first 5
                    print(f"       {i+1}. {line}")
                
                # Ask user how to fix this
                print(f"     ❓ How should we fix this?")
                print(f"       1. Set warehouse orders (G) to zeros matching names count")
                print(f"       2. Move some H data to G (manual split)")
                print(f"       3. Skip this row")
                
                choice = input(f"     Choose (1-3): ").strip()
                
                if choice == '1':
                    # Create zeros for warehouse orders
                    zeros = '\n'.join(['0'] * len(names_lines))
                    
                    # Update the row
                    new_row = data[:]
                    new_row[6] = zeros  # Set warehouse orders to zeros
                    
                    # Update worksheet
                    range_name = f"A{row_num}:H{row_num}"
                    worksheet.update(values=[new_row], range_name=range_name)
                    print(f"     ✅ Set warehouse orders to zeros")
                
                elif choice == '2':
                    print(f"     📝 Manual split needed for row {row_num}")
                    print(f"     Current H data: {warehouse_stock}")
                    print(f"     Please enter warehouse orders (G) data (use \\n for new lines):")
                    new_g = input(f"     G: ").replace('\\n', '\n')
                    print(f"     Please enter corrected warehouse stock (H) data:")
                    new_h = input(f"     H: ").replace('\\n', '\n')
                    
                    # Update the row
                    new_row = data[:]
                    new_row[6] = new_g  # Warehouse orders
                    new_row[7] = new_h  # Warehouse stock
                    
                    # Update worksheet
                    range_name = f"A{row_num}:H{row_num}"
                    worksheet.update(values=[new_row], range_name=range_name)
                    print(f"     ✅ Applied manual corrections")
                
                else:
                    print(f"     ➡️  Skipped row {row_num}")
            
            elif issue == 'misaligned_warehouse_data':
                print(f"     📝 Manual review needed for row {row_num}")
                print(f"     Please check and correct this row manually in Google Sheets")
        
        print(f"\n✅ Fixes applied successfully!")
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")

if __name__ == "__main__":
    print("🔧 Google Sheets Data Fix Tool")
    print("=" * 50)
    
    success = fix_misplaced_data()
    
    if success:
        print(f"\n🎉 Data analysis and fixing completed!")
    else:
        print(f"\n💥 Data fixing failed")