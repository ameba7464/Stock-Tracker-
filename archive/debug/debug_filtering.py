#!/usr/bin/env python3
"""
Debug improved filtering logic with detailed logging.
"""

import sys
from pathlib import Path
from collections import defaultdict

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from stock_tracker.core.models import Product, Warehouse

def debug_convert_api_record_to_product(api_record, orders_data):
    """Debug version of the conversion method with detailed logging."""
    
    # Get product identifiers - FIXED field mapping
    nm_id = api_record.get('nmId', 0)
    vendor_code = api_record.get('vendorCode', '')  # Warehouse uses vendorCode
    
    print(f"🔍 Debug: nmId={nm_id}, vendorCode={vendor_code}")
    print(f"📋 Orders data available: {len(orders_data)} records")
    
    # Calculate total quantity from all warehouses
    total_quantity = 0
    total_orders = 0
    warehouses = []
    
    # FIXED: Improved matching logic for orders
    warehouse_orders_map = {}
    
    if 'warehouses' in api_record and isinstance(api_record['warehouses'], list):
        # Initialize warehouse order counts
        for wh in api_record['warehouses']:
            warehouse_name = wh.get('warehouseName', 'Unknown')
            warehouse_orders_map[warehouse_name] = 0
            
        # Count orders for this product using BOTH nmId and supplierArticle
        product_orders = []
        for order in orders_data:
            order_nm_id = order.get('nmId')
            order_supplier_article = order.get('supplierArticle', '')  # Orders use supplierArticle
            
            # Match by nmId (primary) AND supplierArticle (secondary validation)
            if (order_nm_id == nm_id and 
                (not vendor_code or order_supplier_article == vendor_code)):
                product_orders.append(order)
                print(f"  ✅ Matched order: {order_supplier_article} at {order.get('warehouseName')} (qty: {order.get('quantity', 1)})")
        
        print(f"📊 Found {len(product_orders)} orders for product {vendor_code} (nmId: {nm_id})")
        
        # Group orders by warehouse for this product
        orders_by_warehouse = defaultdict(int)
        for order in product_orders:
            order_warehouse = order.get('warehouseName', '')
            order_quantity = order.get('quantity', 1)  # FIXED: Use actual quantity, not count
            if order_warehouse:
                orders_by_warehouse[order_warehouse] += order_quantity
                print(f"  📦 Order warehouse '{order_warehouse}': +{order_quantity} (total: {orders_by_warehouse[order_warehouse]})")
        
        print(f"🏭 Orders by warehouse: {dict(orders_by_warehouse)}")
        
        # FIXED: More intelligent warehouse matching
        # 1. Direct warehouse name match
        # 2. Fallback: distribute orders proportionally to stock
        remaining_orders = dict(orders_by_warehouse)  # Create copy for safe modification
        
        print(f"🔄 Processing {len(api_record['warehouses'])} warehouses...")
        
        for wh in api_record['warehouses']:
            warehouse_name = wh.get('warehouseName', 'Unknown')
            warehouse_stock = wh.get('quantity', 0)
            
            print(f"  🏭 Processing warehouse: '{warehouse_name}' (stock: {warehouse_stock})")
            
            # Try direct warehouse name match first
            warehouse_orders = remaining_orders.get(warehouse_name, 0)
            if warehouse_orders > 0:
                # Remove from available orders to prevent double counting
                del remaining_orders[warehouse_name]
                print(f"    ✅ Direct match: {warehouse_orders} orders")
            
            # If no direct match, check for partial matches or related warehouses
            if warehouse_orders == 0 and remaining_orders:
                print(f"    🔍 Looking for partial matches in: {list(remaining_orders.keys())}")
                # Look for partial matches (e.g., "Подольск" matches "Подольск 3")
                matched_order_wh = None
                for order_wh_name, order_count in remaining_orders.items():
                    if (warehouse_name.lower() in order_wh_name.lower() or 
                        order_wh_name.lower() in warehouse_name.lower()):
                        warehouse_orders = order_count
                        matched_order_wh = order_wh_name
                        print(f"    ✅ Partial match: '{order_wh_name}' → {order_count} orders")
                        break
                
                # Remove matched warehouse from remaining orders
                if matched_order_wh:
                    del remaining_orders[matched_order_wh]
                else:
                    print(f"    ❌ No matches found")
            
            warehouse = Warehouse(
                name=warehouse_name,
                stock=warehouse_stock,
                orders=warehouse_orders,
                orders_quantity=wh.get('orders_quantity', 0),
                stock_quantity=wh.get('stock_quantity', 0)
            )
            warehouses.append(warehouse)
            total_quantity += warehouse.stock
            total_orders += warehouse_orders
            
            print(f"    📊 Result: {warehouse_name} = stock:{warehouse_stock}, orders:{warehouse_orders}")
        
        # If we still have unmatched orders, distribute them to warehouses with stock
        total_order_quantity_from_api = sum(order.get('quantity', 1) for order in product_orders)
        unmatched_orders = sum(remaining_orders.values())  # Use remaining unmatched orders
        
        print(f"📈 Summary before distribution:")
        print(f"  Total API orders: {total_order_quantity_from_api}")
        print(f"  Attributed orders: {total_orders}")
        print(f"  Unmatched orders: {unmatched_orders}")
        print(f"  Remaining unmatched: {dict(remaining_orders)}")
        
        if unmatched_orders > 0 and warehouses:
            print(f"🔄 Distributing {unmatched_orders} unmatched orders proportionally")
            
            # Get warehouses with stock for proportional distribution
            warehouses_with_stock = [wh for wh in warehouses if wh.stock > 0]
            if warehouses_with_stock:
                total_stock_for_distribution = sum(wh.stock for wh in warehouses_with_stock)
                print(f"  📦 {len(warehouses_with_stock)} warehouses with stock (total: {total_stock_for_distribution})")
                
                for warehouse in warehouses_with_stock:
                    if total_stock_for_distribution > 0:
                        proportion = warehouse.stock / total_stock_for_distribution
                        additional_orders = int(unmatched_orders * proportion)
                        warehouse.orders += additional_orders
                        total_orders += additional_orders
                        print(f"    ✅ Added {additional_orders} proportional orders to {warehouse.name} (proportion: {proportion:.2f})")
            else:
                # Fallback: distribute evenly to all warehouses
                print(f"  📦 No warehouses with stock, distributing evenly")
                orders_per_warehouse = unmatched_orders // len(warehouses)
                remainder = unmatched_orders % len(warehouses)
                for i, warehouse in enumerate(warehouses):
                    additional_orders = orders_per_warehouse + (1 if i < remainder else 0)
                    warehouse.orders += additional_orders
                    total_orders += additional_orders
                    print(f"    ✅ Added {additional_orders} even orders to {warehouse.name}")
    
    # Create Product object
    product = Product(
        wildberries_article=nm_id,
        seller_article=vendor_code,
        total_orders=total_orders,
        total_stock=total_quantity,
        turnover=total_orders / total_quantity if total_quantity > 0 else 0.0,
        warehouses=warehouses
    )
    
    print(f"🎯 Final result: {product.total_orders} orders, {product.total_stock} stock")
    return product

def test_debug_filtering():
    """Test with debug output."""
    
    print("🔍 Debug testing improved filtering logic...")
    
    # Mock data
    orders_data = [
        {"nmId": 12345, "supplierArticle": "ItsSport2/50g+Aks5/20g", "warehouseName": "Казань", "quantity": 1},
        {"nmId": 12345, "supplierArticle": "ItsSport2/50g+Aks5/20g", "warehouseName": "Обухово МП", "quantity": 2},
        {"nmId": 67890, "supplierArticle": "Its2/50g+Aks5/20g", "warehouseName": "Электросталь", "quantity": 1},
        {"nmId": 67890, "supplierArticle": "Its2/50g+Aks5/20g", "warehouseName": "Подольск", "quantity": 1}
    ]
    
    warehouse_data = [
        {
            "nmId": 12345,
            "vendorCode": "ItsSport2/50g+Aks5/20g",
            "warehouses": [
                {"warehouseName": "В пути возвраты на склад WB", "quantity": 15},
                {"warehouseName": "В пути до получателей", "quantity": 8},
                {"warehouseName": "Казань", "quantity": 5}
            ]
        }
    ]
    
    for warehouse_record in warehouse_data:
        print(f"\n{'='*60}")
        result = debug_convert_api_record_to_product(warehouse_record, orders_data)
        print(f"{'='*60}")

if __name__ == "__main__":
    test_debug_filtering()