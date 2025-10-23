#!/usr/bin/env python3
"""
Apply improved warehouse logic to fix orders distribution.
This script applies the same logic as the main system - excluding "in transit" warehouses.
"""

import os
import gspread
from pathlib import Path
from google.oauth2.service_account import Credentials

def apply_improved_warehouse_logic():
    """Apply improved warehouse logic that excludes 'in transit' warehouses."""
    
    print("🔧 Applying improved warehouse logic to G3...")
    
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
        row_3_data = worksheet.row_values(3)
        
        if len(row_3_data) < 8:
            print("❌ Row 3 doesn't have enough data")
            return False
        
        # Parse warehouse data
        warehouse_names = row_3_data[5].strip()
        warehouse_stock = row_3_data[7].strip()
        total_orders = int(row_3_data[2]) if row_3_data[2].isdigit() else 0
        
        names_lines = [line.strip() for line in warehouse_names.split('\n') if line.strip()]
        stock_lines = [line.strip() for line in warehouse_stock.split('\n') if line.strip()]
        
        print(f"\n📊 Analyzing warehouses with improved logic:")
        print(f"   Total orders to distribute: {total_orders}")
        print(f"   Total warehouses: {len(names_lines)}")
        
        # Apply the same logic as in the main system
        in_transit_keywords = [
            'в пути', 'в_пути', 'vputi', 'transit', 'pending',
            'до получателей', 'возврат', 'return', 'доставка',
            'delivery', 'shipping', 'отправлен', 'sent'
        ]
        
        real_warehouses = []
        real_stock = []
        all_orders = []
        
        print(f"\n🔍 Warehouse Analysis:")
        for i, (name, stock) in enumerate(zip(names_lines, stock_lines)):
            try:
                stock_num = int(stock)
            except:
                stock_num = 0
            
            # Check if this is an "in transit" warehouse
            is_in_transit = any(keyword in name.lower() for keyword in in_transit_keywords)
            
            if is_in_transit:
                print(f"   {i+1:2d}. {name}: {stock_num} stock - ⚠️  IN TRANSIT (orders = 0)")
                all_orders.append("0")
            else:
                print(f"   {i+1:2d}. {name}: {stock_num} stock - ✅ REAL WAREHOUSE")
                real_warehouses.append(name)
                real_stock.append(stock_num)
                all_orders.append("TBD")  # To be determined
        
        # Calculate orders only for real warehouses
        total_real_stock = sum(real_stock)
        print(f"\n📦 Real warehouse analysis:")
        print(f"   Real warehouses: {len(real_warehouses)}")
        print(f"   Total real stock: {total_real_stock}")
        
        if total_real_stock > 0 and len(real_warehouses) > 0:
            # Distribute orders proportionally among real warehouses
            real_orders = []
            distributed_total = 0
            
            for i, stock in enumerate(real_stock):
                if i == len(real_stock) - 1:
                    # Last warehouse gets the remainder
                    orders = total_orders - distributed_total
                else:
                    orders = int((stock / total_real_stock) * total_orders)
                    distributed_total += orders
                real_orders.append(orders)
            
            # Map back to all warehouses
            real_idx = 0
            for i, name in enumerate(names_lines):
                is_in_transit = any(keyword in name.lower() for keyword in in_transit_keywords)
                if not is_in_transit:
                    all_orders[i] = str(real_orders[real_idx])
                    real_idx += 1
        
        print(f"\n🎯 Final order distribution:")
        total_distributed = 0
        for i, (name, orders, stock) in enumerate(zip(names_lines, all_orders, stock_lines)):
            orders_num = int(orders) if orders.isdigit() else 0
            total_distributed += orders_num
            
            status = "🚚 In Transit" if orders_num == 0 and any(keyword in name.lower() for keyword in in_transit_keywords) else "📦 Real"
            print(f"   {i+1:2d}. {name}: {orders} orders, {stock} stock - {status}")
        
        print(f"\n📊 Distribution Summary:")
        print(f"   Total orders distributed: {total_distributed}")
        print(f"   Target total orders: {total_orders}")
        print(f"   Match: {'✅' if total_distributed == total_orders else '❌'}")
        
        # Ask for confirmation
        print(f"\n❓ Apply this improved distribution? (y/n): ", end="")
        apply_fix = input().strip().lower() == 'y'
        
        if apply_fix:
            # Apply the fix
            orders_text = '\n'.join(all_orders)
            cell_range = f"G3"
            worksheet.update(values=[[orders_text]], range_name=cell_range)
            
            print(f"✅ Applied improved warehouse logic to G3")
            print(f"   In-transit warehouses: excluded from orders")
            print(f"   Real warehouses: {len(real_warehouses)} with {total_distributed} orders")
        else:
            print(f"❌ Fix not applied")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying improved logic: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Apply Improved Warehouse Logic")
    print("=" * 40)
    
    success = apply_improved_warehouse_logic()
    
    if success:
        print(f"\n🎉 Improved warehouse logic applied!")
    else:
        print(f"\n💥 Application failed")