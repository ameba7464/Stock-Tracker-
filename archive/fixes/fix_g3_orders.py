#!/usr/bin/env python3
"""
Fix warehouse orders data in row 3 (G3) that was incorrectly set to zeros.
This script will analyze the data and restore correct warehouse orders.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials

def fix_warehouse_orders_g3():
    """Fix the warehouse orders in G3 that were incorrectly set to zeros."""
    
    print("🔧 Fixing warehouse orders in G3...")
    
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
        
        # Get current data for row 3
        row_3_data = worksheet.row_values(3)  # Row 3 (0-based index 2)
        
        if len(row_3_data) < 8:
            print("❌ Row 3 doesn't have enough data")
            return False
        
        print(f"\n🔍 Current Row 3 Data:")
        print(f"   A: Артикул продавца = '{row_3_data[0]}'")
        print(f"   B: Артикул товара = '{row_3_data[1]}'") 
        print(f"   C: Заказы (всего) = '{row_3_data[2]}'")
        print(f"   D: Остатки (всего) = '{row_3_data[3]}'")
        print(f"   E: Оборачиваемость = '{row_3_data[4]}'")
        print(f"   F: Название склада = '{row_3_data[5][:100]}{'...' if len(row_3_data[5]) > 100 else ''}'")
        print(f"   G: Заказы со склада = '{row_3_data[6][:100]}{'...' if len(row_3_data[6]) > 100 else ''}'")
        print(f"   H: Остатки на складе = '{row_3_data[7][:100]}{'...' if len(row_3_data[7]) > 100 else ''}'")
        
        # Analyze warehouse data
        warehouse_names = row_3_data[5].strip()
        warehouse_orders = row_3_data[6].strip()
        warehouse_stock = row_3_data[7].strip()
        
        # Split by lines
        names_lines = [line.strip() for line in warehouse_names.split('\n') if line.strip()]
        orders_lines = [line.strip() for line in warehouse_orders.split('\n') if line.strip()]
        stock_lines = [line.strip() for line in warehouse_stock.split('\n') if line.strip()]
        
        print(f"\n📊 Analysis:")
        print(f"   Warehouse names: {len(names_lines)} lines")
        print(f"   Warehouse orders: {len(orders_lines)} lines")
        print(f"   Warehouse stock: {len(stock_lines)} lines")
        
        print(f"\n📋 Warehouse Names:")
        for i, name in enumerate(names_lines, 1):
            print(f"   {i:2d}. {name}")
        
        print(f"\n📦 Current Orders (G3):")
        for i, orders in enumerate(orders_lines, 1):
            print(f"   {i:2d}. {orders}")
        
        print(f"\n🏪 Current Stock (H3):")
        for i, stock in enumerate(stock_lines, 1):
            print(f"   {i:2d}. {stock}")
        
        # Check if G3 has all zeros
        all_zeros = all(orders == '0' for orders in orders_lines if orders.isdigit())
        
        if all_zeros and len(orders_lines) == len(names_lines):
            print(f"\n⚠️  Detected all zeros in warehouse orders - this needs fixing!")
            
            # Let's look at the total orders to understand the distribution
            total_orders = int(row_3_data[2]) if row_3_data[2].isdigit() else 0
            total_stock = int(row_3_data[3]) if row_3_data[3].replace(',', '').replace('.', '').isdigit() else 0
            
            print(f"\n📊 Summary:")
            print(f"   Total orders: {total_orders}")
            print(f"   Total stock: {total_stock}")
            print(f"   Warehouses: {len(names_lines)}")
            
            # Propose solutions
            print(f"\n💡 Possible fixes:")
            print(f"   1. Distribute total orders proportionally to stock")
            print(f"   2. Set specific orders per warehouse manually")
            print(f"   3. Copy pattern from similar product (row 4)")
            print(f"   4. Leave as zeros (no orders from any warehouse)")
            
            # Get data from row 4 for pattern
            row_4_data = worksheet.row_values(4)
            if len(row_4_data) >= 8:
                row_4_names = [line.strip() for line in row_4_data[5].split('\n') if line.strip()]
                row_4_orders = [line.strip() for line in row_4_data[6].split('\n') if line.strip()]
                row_4_stock = [line.strip() for line in row_4_data[7].split('\n') if line.strip()]
                
                print(f"\n📋 Row 4 Pattern (for reference):")
                print(f"   Total orders: {row_4_data[2]}")
                print(f"   Warehouses: {len(row_4_names)}")
                for i, (name, orders, stock) in enumerate(zip(row_4_names[:5], row_4_orders[:5], row_4_stock[:5])):
                    print(f"   {i+1:2d}. {name}: {orders} orders, {stock} stock")
            
            # Ask user what to do
            print(f"\n❓ How should we fix the warehouse orders for row 3?")
            choice = input(f"Choose (1-4): ").strip()
            
            if choice == "1":
                # Proportional distribution
                new_orders = distribute_orders_proportionally(total_orders, stock_lines, names_lines)
                apply_orders_fix(worksheet, 3, new_orders)
                
            elif choice == "2":
                # Manual entry
                new_orders = manual_orders_entry(names_lines)
                apply_orders_fix(worksheet, 3, new_orders)
                
            elif choice == "3":
                # Copy pattern from row 4
                if len(row_4_data) >= 8:
                    pattern_orders = adapt_pattern_to_row(row_4_orders, row_4_names, names_lines, total_orders)
                    apply_orders_fix(worksheet, 3, pattern_orders)
                else:
                    print("❌ Row 4 data not available for pattern")
                    
            elif choice == "4":
                print("✅ Keeping orders as zeros")
            else:
                print("❌ Invalid choice")
                
        else:
            print(f"\n✅ Warehouse orders look correct (not all zeros)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing warehouse orders: {e}")
        return False

def distribute_orders_proportionally(total_orders, stock_lines, names_lines):
    """Distribute total orders proportionally to stock amounts."""
    try:
        print(f"\n🔄 Distributing {total_orders} orders proportionally...")
        
        # Convert stock to numbers
        stock_numbers = []
        for stock in stock_lines:
            try:
                stock_numbers.append(int(stock))
            except:
                stock_numbers.append(0)
        
        total_stock = sum(stock_numbers)
        
        if total_stock == 0:
            # Equal distribution
            orders_per_warehouse = total_orders // len(names_lines)
            remainder = total_orders % len(names_lines)
            new_orders = [str(orders_per_warehouse)] * len(names_lines)
            for i in range(remainder):
                new_orders[i] = str(int(new_orders[i]) + 1)
        else:
            # Proportional distribution
            new_orders = []
            distributed_total = 0
            
            for i, stock in enumerate(stock_numbers):
                if i == len(stock_numbers) - 1:
                    # Last warehouse gets the remainder
                    orders = total_orders - distributed_total
                else:
                    orders = int((stock / total_stock) * total_orders)
                    distributed_total += orders
                new_orders.append(str(orders))
        
        print(f"   Proposed distribution:")
        for i, (name, orders, stock) in enumerate(zip(names_lines, new_orders, stock_lines)):
            print(f"   {i+1:2d}. {name}: {orders} orders (was 0, stock: {stock})")
        
        return new_orders
        
    except Exception as e:
        print(f"❌ Error in proportional distribution: {e}")
        return None

def manual_orders_entry(names_lines):
    """Allow manual entry of orders for each warehouse."""
    print(f"\n✏️  Manual entry mode:")
    new_orders = []
    
    for i, name in enumerate(names_lines):
        while True:
            try:
                orders = input(f"   Enter orders for '{name}': ").strip()
                int(orders)  # Validate it's a number
                new_orders.append(orders)
                break
            except ValueError:
                print(f"   Please enter a valid number")
    
    return new_orders

def adapt_pattern_to_row(pattern_orders, pattern_names, target_names, target_total):
    """Adapt order pattern from another row to current row."""
    print(f"\n🔄 Adapting pattern to target total of {target_total}...")
    
    try:
        # Calculate scaling factor
        pattern_total = sum(int(orders) for orders in pattern_orders if orders.isdigit())
        if pattern_total == 0:
            return [str(0)] * len(target_names)
        
        scale_factor = target_total / pattern_total
        print(f"   Scale factor: {scale_factor:.3f}")
        
        # Try to match warehouses by name
        new_orders = []
        for target_name in target_names:
            matched_orders = 0
            
            # Look for exact or partial match
            for i, pattern_name in enumerate(pattern_names):
                if (target_name.lower() in pattern_name.lower() or 
                    pattern_name.lower() in target_name.lower()):
                    if i < len(pattern_orders) and pattern_orders[i].isdigit():
                        matched_orders = int(int(pattern_orders[i]) * scale_factor)
                        break
            
            new_orders.append(str(matched_orders))
        
        # Adjust to match exact total
        current_total = sum(int(orders) for orders in new_orders)
        if current_total != target_total:
            diff = target_total - current_total
            # Add difference to the first non-zero warehouse
            for i, orders in enumerate(new_orders):
                if int(orders) > 0:
                    new_orders[i] = str(int(orders) + diff)
                    break
        
        print(f"   Adapted orders:")
        for i, (name, orders) in enumerate(zip(target_names, new_orders)):
            print(f"   {i+1:2d}. {name}: {orders} orders")
        
        return new_orders
        
    except Exception as e:
        print(f"❌ Error adapting pattern: {e}")
        return [str(0)] * len(target_names)

def apply_orders_fix(worksheet, row_number, new_orders):
    """Apply the new orders to the specified row."""
    try:
        print(f"\n🔧 Applying fix to row {row_number}...")
        
        # Join orders with newlines
        orders_text = '\n'.join(new_orders)
        
        # Update cell G for the specified row
        cell_range = f"G{row_number}"
        worksheet.update(values=[[orders_text]], range_name=cell_range)
        
        print(f"✅ Updated {cell_range} with new warehouse orders")
        print(f"   New value: {orders_text.replace(chr(10), ' | ')}")
        
    except Exception as e:
        print(f"❌ Error applying fix: {e}")

if __name__ == "__main__":
    print("🔧 Fix Warehouse Orders in G3")
    print("=" * 40)
    
    success = fix_warehouse_orders_g3()
    
    if success:
        print(f"\n🎉 Warehouse orders analysis completed!")
    else:
        print(f"\n💥 Fix failed")