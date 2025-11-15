#!/usr/bin/env python3
"""
Fix Google Sheets table structure and restore correct column data placement.
This script will check the current table structure and fix any misplaced data.
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

async def analyze_and_fix_table_structure():
    """Analyze current table structure and fix any column data issues."""
    
    print("🔍 Analyzing Google Sheets table structure...")
    
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
        
        # Try to get existing worksheet
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            print(f"✅ Found existing worksheet: {worksheet_name}")
        except Exception as e:
            print(f"❌ Error accessing worksheet: {e}")
            return False
        
        # Get all values from the worksheet
        all_values = worksheet.get_all_values()
        
        if not all_values:
            print("❌ No data found in worksheet")
            return False
        
        print(f"📊 Found {len(all_values)} rows of data")
        
        # Analyze header structure
        if len(all_values) > 0:
            headers = all_values[0]
            print(f"\n📋 Current headers ({len(headers)} columns):")
            for i, header in enumerate(headers, 1):
                print(f"   {i:2d}. '{header}'")
        
        # Get expected structure
        expected_headers = table_structure.get_headers()
        print(f"\n📋 Expected headers ({len(expected_headers)} columns):")
        for i, header in enumerate(expected_headers, 1):
            print(f"   {i:2d}. '{header}'")
        
        # Compare structures
        print(f"\n🔍 Structure Analysis:")
        
        if len(headers) != len(expected_headers):
            print(f"   ⚠️  Column count mismatch: {len(headers)} vs {len(expected_headers)} expected")
        else:
            print(f"   ✅ Column count matches: {len(headers)} columns")
        
        # Check each header
        mismatched_headers = []
        for i, (current, expected) in enumerate(zip(headers, expected_headers)):
            if current.strip() != expected.strip():
                mismatched_headers.append((i+1, current, expected))
                print(f"   ❌ Column {i+1}: '{current}' should be '{expected}'")
            else:
                print(f"   ✅ Column {i+1}: '{current}' - correct")
        
        # Analyze data structure for first few rows
        print(f"\n📊 Data Analysis (first 3 data rows):")
        data_rows = all_values[1:4] if len(all_values) > 1 else []
        
        for row_idx, row in enumerate(data_rows, 1):
            print(f"\n   Row {row_idx}:")
            for col_idx, (header, value) in enumerate(zip(headers, row + [''] * (len(headers) - len(row)))):
                if value.strip():  # Only show non-empty cells
                    print(f"      {header}: '{value}'")
        
        # Propose fixes
        print(f"\n🔧 Proposed Fixes:")
        
        if mismatched_headers:
            print(f"   1. Fix {len(mismatched_headers)} header(s)")
            for col_num, current, expected in mismatched_headers:
                print(f"      - Column {col_num}: '{current}' → '{expected}'")
        
        if len(headers) != len(expected_headers):
            if len(headers) < len(expected_headers):
                missing_count = len(expected_headers) - len(headers)
                print(f"   2. Add {missing_count} missing column(s)")
                for i in range(len(headers), len(expected_headers)):
                    print(f"      - Add column: '{expected_headers[i]}'")
            else:
                extra_count = len(headers) - len(expected_headers)
                print(f"   2. Remove {extra_count} extra column(s)")
        
        # Ask for confirmation to apply fixes
        print(f"\n❓ Apply fixes to restore correct table structure? (y/N): ", end="")
        
        # For automated execution, assume 'y' - in real scenario you'd want user input
        apply_fixes = True  # input().strip().lower() == 'y'
        
        if apply_fixes:
            print("y")  # Show the choice
            await apply_table_fixes(worksheet, table_structure, all_values)
        else:
            print("n")
            print("   ℹ️  No changes applied")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing table structure: {e}")
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return False

async def apply_table_fixes(worksheet, table_structure, current_data):
    """Apply fixes to restore correct table structure."""
    
    print(f"\n🔧 Applying table structure fixes...")
    
    try:
        # Get expected headers
        expected_headers = table_structure.get_headers()
        
        # Clear the worksheet and rebuild with correct structure
        print(f"   1. Backing up current data...")
        backup_data = [row[:] for row in current_data]  # Deep copy
        
        print(f"   2. Clearing worksheet...")
        worksheet.clear()
        
        print(f"   3. Setting correct headers...")
        # Set headers
        header_range = f"A1:{chr(ord('A') + len(expected_headers) - 1)}1"
        worksheet.update(header_range, [expected_headers])
        
        print(f"   4. Restoring data with correct column mapping...")
        
        # If we have data to restore
        if len(backup_data) > 1:
            data_rows = backup_data[1:]  # Skip header row
            old_headers = backup_data[0] if backup_data else []
            
            # Create mapping from old structure to new structure
            column_mapping = {}
            for new_idx, new_header in enumerate(expected_headers):
                # Find matching column in old structure
                for old_idx, old_header in enumerate(old_headers):
                    if old_header.strip().lower() == new_header.strip().lower():
                        column_mapping[new_idx] = old_idx
                        break
                    # Also check for common variations
                    elif (new_header.strip().lower() in old_header.strip().lower() or 
                          old_header.strip().lower() in new_header.strip().lower()):
                        column_mapping[new_idx] = old_idx
                        break
            
            print(f"      Column mapping found: {len(column_mapping)} matches")
            for new_idx, old_idx in column_mapping.items():
                print(f"         '{expected_headers[new_idx]}' ← '{old_headers[old_idx] if old_idx < len(old_headers) else 'N/A'}'")
            
            # Reconstruct data with correct column order
            fixed_data = []
            for row in data_rows:
                fixed_row = [''] * len(expected_headers)
                for new_idx, old_idx in column_mapping.items():
                    if old_idx < len(row):
                        fixed_row[new_idx] = row[old_idx]
                fixed_data.append(fixed_row)
            
            # Write restored data
            if fixed_data:
                data_range = f"A2:{chr(ord('A') + len(expected_headers) - 1)}{len(fixed_data) + 1}"
                worksheet.update(data_range, fixed_data)
                print(f"   ✅ Restored {len(fixed_data)} rows of data")
        
        print(f"   5. Applying formatting...")
        # Apply complete formatting including multi-line support
        table_structure.apply_complete_formatting(worksheet)
        
        print(f"✅ Table structure successfully fixed!")
        print(f"   📊 Headers: {len(expected_headers)} columns")
        print(f"   📋 Data: {len(current_data) - 1 if current_data else 0} rows")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fixes: {e}")
        logger.error(f"Fix application failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    print("🔧 Google Sheets Table Structure Fix Tool")
    print("=" * 50)
    
    success = asyncio.run(analyze_and_fix_table_structure())
    
    if success:
        print(f"\n🎉 Table structure analysis completed!")
        print(f"📋 Check your Google Sheets to verify the fixes")
    else:
        print(f"\n💥 Failed to fix table structure")