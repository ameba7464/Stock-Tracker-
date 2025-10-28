#!/usr/bin/env python3
"""Debug warehouse remains data for Its1_2_3/50g"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.config import get_config
import json

def main():
    config = get_config()
    client = WildberriesAPIClient(config)
    
    print("\n" + "="*100)
    print("🔍 DEBUG: Wildberries Warehouse Remains API для Its1_2_3/50g")
    print("="*100)
    
    # Create task
    print("\n1️⃣ Создаём задачу...")
    task_id = client.create_warehouse_remains_task()
    print(f"✅ Task ID: {task_id}")
    
    # Wait
    print("\n2️⃣ Ждём 60 секунд обработки...")
    import time
    time.sleep(60)
    
    # Download data
    print("\n3️⃣ Скачиваем данные...")
    data = client.download_warehouse_remains(task_id)
    print(f"✅ Получено записей: {len(data)}")
    
    # Find Its1_2_3/50g
    print("\n4️⃣ Ищем Its1_2_3/50g...")
    target_product = None
    for record in data:
        if record.get('vendorCode') == 'Its1_2_3/50g':
            target_product = record
            break
    
    if not target_product:
        print("❌ Товар Its1_2_3/50g не найден!")
        return
    
    print("\n✅ Товар найден!")
    print("\n" + "-"*100)
    print("📦 ПОЛНАЯ ИНФОРМАЦИЯ О ТОВАРЕ:")
    print("-"*100)
    print(json.dumps(target_product, indent=2, ensure_ascii=False))
    
    # Analyze warehouses
    print("\n" + "-"*100)
    print("📊 АНАЛИЗ СКЛАДОВ:")
    print("-"*100)
    
    warehouses = target_product.get('warehouses', [])
    print(f"\nВсего складов: {len(warehouses)}")
    
    total_quantity = 0
    for i, wh in enumerate(warehouses, 1):
        name = wh.get('warehouseName', 'Unknown')
        qty = wh.get('quantityNotInOrders', 0)
        in_orders = wh.get('quantityInOrders', 0)
        total = qty + in_orders
        
        total_quantity += qty
        
        print(f"\n{i}. {name}")
        print(f"   - Свободные остатки (quantityNotInOrders): {qty}")
        print(f"   - В заказах (quantityInOrders): {in_orders}")
        print(f"   - ИТОГО: {total}")
    
    print("\n" + "="*100)
    print(f"📈 ИТОГО свободных остатков: {total_quantity}")
    print("="*100)
    
    # Check if this matches the 475 we see
    if total_quantity == 475:
        print("\n✅ Подтверждено: API возвращает ровно 475 свободных остатков")
        print("\n⚠️ ПРОБЛЕМА:")
        print("   API Wildberries действительно возвращает 475, а не 3,459")
        print("   Возможные причины:")
        print("   1. Большая часть товара находится 'в заказах' (quantityInOrders)")
        print("   2. Используется неправильный endpoint")
        print("   3. Требуется другой API для получения полных данных")
    else:
        print(f"\n⚠️ API вернул {total_quantity}, но в таблице показано 475")
        print("   Возможно, проблема в логике фильтрации")

if __name__ == "__main__":
    main()
