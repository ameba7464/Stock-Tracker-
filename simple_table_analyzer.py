#!/usr/bin/env python3
"""
Simple script to analyze and fix Google Sheets table structure.
This script reads the current table and shows its structure.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials
import json

def analyze_table_structure():
    """Analyze and display current table structure."""
    
    print("🔍 Analyzing Google Sheets table structure...")
    
    try:
        # Configuration
        SHEET_ID = "1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho"
        WORKSHEET_NAME = "Stock Tracker"
        SERVICE_ACCOUNT_PATH = "config/service-account.json"
        
        print(f"📊 Sheet ID: {SHEET_ID}")
        print(f"📄 Worksheet: {WORKSHEET_NAME}")
        print(f"🔑 Service Account: {SERVICE_ACCOUNT_PATH}")
        
        # Check if service account file exists
        if not Path(SERVICE_ACCOUNT_PATH).exists():
            print(f"❌ Service account file not found: {SERVICE_ACCOUNT_PATH}")
            return False
        
        # Initialize Google Sheets client
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scope)
        client = gspread.authorize(credentials)
        
        # Open spreadsheet
        spreadsheet = client.open_by_key(SHEET_ID)
        
        # Get worksheet
        try:
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            print(f"✅ Connected to worksheet: {WORKSHEET_NAME}")
        except gspread.WorksheetNotFound:
            print(f"❌ Worksheet not found: {WORKSHEET_NAME}")
            print(f"📋 Available worksheets:")
            for ws in spreadsheet.worksheets():
                print(f"   - {ws.title}")
            return False
        
        # Get all data
        all_values = worksheet.get_all_values()
        
        if not all_values:
            print("❌ No data found in worksheet")
            return False
        
        print(f"📊 Found {len(all_values)} rows of data")
        
        # Analyze headers
        headers = all_values[0] if all_values else []
        print(f"\n📋 Current Structure ({len(headers)} columns):")
        for i, header in enumerate(headers, 1):
            print(f"   {i:2d}. Column {chr(ord('A') + i - 1)}: '{header}'")
        
        # Expected structure from the system
        expected_headers = [
            "Артикул продавца",
            "Артикул товара", 
            "Заказы (всего)",
            "Остатки (всего)",
            "Оборачиваемость",
            "Название склада",
            "Заказы со склада",
            "Остатки на складе"
        ]
        
        print(f"\n📋 Expected Structure ({len(expected_headers)} columns):")
        for i, header in enumerate(expected_headers, 1):
            print(f"   {i:2d}. Column {chr(ord('A') + i - 1)}: '{header}'")
        
        # Compare structures
        print(f"\n🔍 Structure Analysis:")
        
        if len(headers) != len(expected_headers):
            print(f"   ⚠️  Column count mismatch: {len(headers)} current vs {len(expected_headers)} expected")
        else:
            print(f"   ✅ Column count matches: {len(headers)} columns")
        
        # Check each header
        mismatches = []
        for i, (current, expected) in enumerate(zip(headers, expected_headers)):
            if current.strip() != expected.strip():
                mismatches.append((i+1, chr(ord('A') + i), current, expected))
                print(f"   ❌ Column {chr(ord('A') + i)}: '{current}' should be '{expected}'")
            else:
                print(f"   ✅ Column {chr(ord('A') + i)}: '{current}' - correct")
        
        # Show sample data
        print(f"\n📊 Sample Data (first 3 rows):")
        data_rows = all_values[1:4] if len(all_values) > 1 else []
        
        for row_idx, row in enumerate(data_rows, 1):
            print(f"\n   Row {row_idx}:")
            for col_idx, (header, value) in enumerate(zip(headers, row + [''] * len(headers))):
                if value.strip():  # Only show non-empty cells
                    print(f"      {chr(ord('A') + col_idx)}: {header} = '{value}'")
        
        # Detect possible data movement issues
        print(f"\n🔧 Potential Issues Analysis:")
        
        if mismatches:
            print(f"   1. Header mismatches detected ({len(mismatches)} columns)")
            for col_num, col_letter, current, expected in mismatches:
                print(f"      - Column {col_letter}: '{current}' → '{expected}'")
        
        # Check for data that might be in wrong columns
        if len(all_values) > 1:
            sample_row = all_values[1]
            print(f"   2. Data analysis for row 1:")
            
            for i, value in enumerate(sample_row):
                if value.strip():
                    col_letter = chr(ord('A') + i)
                    header = headers[i] if i < len(headers) else "Unknown"
                    print(f"      - Column {col_letter} ({header}): '{value}'")
                    
                    # Check if data looks like it's in the wrong column
                    if header == "Артикул продавца" and value.isdigit():
                        print(f"        ⚠️  Seller article looks like WB article (numbers only)")
                    elif header == "Артикул товара" and not value.isdigit():
                        print(f"        ⚠️  WB article should be numeric")
                    elif "Заказы" in header and not value.replace('.', '').isdigit():
                        print(f"        ⚠️  Orders should be numeric")
                    elif "Остатки" in header and not value.replace('.', '').isdigit():
                        print(f"        ⚠️  Stock should be numeric")
        
        # Ask what to do
        print(f"\n❓ What would you like to do?")
        print(f"   1. Fix header names only")
        print(f"   2. Fix headers and reorganize data")
        print(f"   3. Show detailed column analysis")
        print(f"   4. Exit without changes")
        
        choice = input(f"\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            fix_headers_only(worksheet, expected_headers)
        elif choice == "2":
            fix_headers_and_data(worksheet, headers, expected_headers, all_values)
        elif choice == "3":
            show_detailed_analysis(worksheet, headers, all_values)
        else:
            print(f"   ℹ️  No changes made")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing table: {e}")
        return False

def fix_headers_only(worksheet, expected_headers):
    """Fix only the header row."""
    try:
        print(f"\n🔧 Fixing header row...")
        
        # Update headers
        header_range = f"A1:{chr(ord('A') + len(expected_headers) - 1)}1"
        worksheet.update(header_range, [expected_headers])
        
        print(f"✅ Headers updated successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing headers: {e}")

def fix_headers_and_data(worksheet, current_headers, expected_headers, all_data):
    """Fix headers and reorganize data columns."""
    try:
        print(f"\n🔧 Fixing headers and reorganizing data...")
        
        # Create column mapping
        mapping = {}
        for new_idx, new_header in enumerate(expected_headers):
            for old_idx, old_header in enumerate(current_headers):
                if old_header.strip().lower() == new_header.strip().lower():
                    mapping[new_idx] = old_idx
                    break
                # Check for partial matches
                elif (new_header.strip().lower() in old_header.strip().lower() or 
                      old_header.strip().lower() in new_header.strip().lower()):
                    mapping[new_idx] = old_idx
                    break
        
        print(f"   Column mapping: {len(mapping)} matches found")
        for new_idx, old_idx in mapping.items():
            print(f"      '{expected_headers[new_idx]}' ← '{current_headers[old_idx] if old_idx < len(current_headers) else 'N/A'}'")
        
        # Clear worksheet
        worksheet.clear()
        
        # Set new headers
        header_range = f"A1:{chr(ord('A') + len(expected_headers) - 1)}1"
        worksheet.update(header_range, [expected_headers])
        
        # Reorganize data
        if len(all_data) > 1:
            data_rows = all_data[1:]
            reorganized_data = []
            
            for row in data_rows:
                new_row = [''] * len(expected_headers)
                for new_idx, old_idx in mapping.items():
                    if old_idx < len(row):
                        new_row[new_idx] = row[old_idx]
                reorganized_data.append(new_row)
            
            # Write reorganized data
            if reorganized_data:
                data_range = f"A2:{chr(ord('A') + len(expected_headers) - 1)}{len(reorganized_data) + 1}"
                worksheet.update(data_range, reorganized_data)
                print(f"   ✅ Reorganized {len(reorganized_data)} rows of data")
        
        print(f"✅ Table structure fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error fixing table structure: {e}")

def show_detailed_analysis(worksheet, headers, all_data):
    """Show detailed column-by-column analysis."""
    try:
        print(f"\n🔍 Detailed Column Analysis:")
        
        for col_idx, header in enumerate(headers):
            col_letter = chr(ord('A') + col_idx)
            print(f"\n   Column {col_letter}: '{header}'")
            
            # Analyze data in this column
            values = []
            for row in all_data[1:6]:  # Check first 5 rows
                if col_idx < len(row) and row[col_idx].strip():
                    values.append(row[col_idx].strip())
            
            if values:
                print(f"      Sample values: {values[:3]}")
                
                # Data type analysis
                numeric_count = sum(1 for v in values if v.replace('.', '').replace(',', '').isdigit())
                text_count = len(values) - numeric_count
                
                print(f"      Data types: {numeric_count} numeric, {text_count} text")
                
                # Suggest data type
                if numeric_count > text_count:
                    print(f"      → Appears to be numeric data")
                else:
                    print(f"      → Appears to be text data")
            else:
                print(f"      No data found")
        
    except Exception as e:
        print(f"❌ Error in detailed analysis: {e}")

if __name__ == "__main__":
    print("🔧 Google Sheets Table Structure Analyzer")
    print("=" * 50)
    
    success = analyze_table_structure()
    
    if success:
        print(f"\n🎉 Analysis completed!")
    else:
        print(f"\n💥 Analysis failed")