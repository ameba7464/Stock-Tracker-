#!/usr/bin/env python3
"""
Исправление логики подсчета заказов в group_data_by_product().
Устраняет дублирование заказов и добавляет валидацию.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("="*80)
print("🔧 ИСПРАВЛЕНИЕ ДУБЛИРОВАНИЯ ЗАКАЗОВ")
print("="*80)

print("\n📋 План исправления:")
print("   1. Добавить отслеживание уникальных заказов по gNumber/odid")
print("   2. Удалить неиспользуемое поле group['total_orders']")
print("   3. Добавить валидацию соответствия заказов по складам")
print("   4. Улучшить логирование для отладки")

print("\n🔧 Создание патча для src/stock_tracker/core/calculator.py...")

patch_content = '''
# PATCH for src/stock_tracker/core/calculator.py
# Добавить в начало метода group_data_by_product():

    # Track unique orders to prevent duplication
    processed_order_ids = set()
    duplicate_orders_count = 0
    
    logger.info("Starting order processing with deduplication...")

# В цикле обработки заказов (около строки 580), ЗАМЕНИТЬ:
# for order in orders_data:
# НА:

    for order in orders_data:
        # Get unique order identifier
        order_id = order.get("gNumber") or order.get("odid") or order.get("srid")
        
        # Skip if we've already processed this order
        if order_id and order_id in processed_order_ids:
            duplicate_orders_count += 1
            logger.debug(f"Skipping duplicate order: {order_id}")
            continue
        
        # Mark order as processed
        if order_id:
            processed_order_ids.add(order_id)
        
        nm_id = order.get("nmId")
        supplier_article = order.get("supplierArticle", "")
        # ... rest of the logic

# УДАЛИТЬ строку (около 644):
# group["total_orders"] += 1  # ❌ Это поле не используется!

# ДОБАВИТЬ в конец метода, ПЕРЕД return:

    # Validate orders calculation
    logger.info(f"\\n📊 ORDERS VALIDATION:")
    logger.info(f"   Total orders processed: {orders_processed}")
    logger.info(f"   Duplicate orders skipped: {duplicate_orders_count}")
    logger.info(f"   Unique order IDs tracked: {len(processed_order_ids)}")
    
    # Validate that sum of warehouse orders matches expectations
    validation_errors = 0
    for (article, nm_id), group in grouped_data.items():
        warehouse_orders_sum = sum(wh["orders"] for wh in group["warehouses"].values())
        
        # Count raw orders for this product (for validation)
        raw_orders = sum(1 for order in orders_data 
                        if order.get("supplierArticle") == article 
                        and order.get("nmId") == nm_id
                        and not order.get("isCancel", False))
        
        if warehouse_orders_sum != raw_orders:
            validation_errors += 1
            logger.warning(f"⚠️  Orders mismatch for {article}:")
            logger.warning(f"   Raw orders: {raw_orders}")
            logger.warning(f"   Warehouse sum: {warehouse_orders_sum}")
            logger.warning(f"   Difference: {warehouse_orders_sum - raw_orders}")
    
    if validation_errors == 0:
        logger.info("✅ All products passed orders validation")
    else:
        logger.warning(f"⚠️  {validation_errors} products failed validation")
    
    return dict(grouped_data)
'''

print("\n📝 Патч готов к применению")
print("\n" + "="*80)
print("НЕОБХОДИМЫЕ ИЗМЕНЕНИЯ В src/stock_tracker/core/calculator.py")
print("="*80)

print(patch_content)

print("\n" + "="*80)
print("🎯 КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ:")
print("="*80)

print("\n1️⃣ Добавить отслеживание уникальных заказов:")
print("""
    processed_order_ids = set()
    
    for order in orders_data:
        order_id = order.get("gNumber") or order.get("odid")
        
        if order_id in processed_order_ids:
            continue  # Skip duplicate
        
        processed_order_ids.add(order_id)
        # ... process order
""")

print("\n2️⃣ Удалить неиспользуемое поле:")
print("""
    # УДАЛИТЬ эту строку:
    # group["total_orders"] += 1  # ❌ Не используется!
""")

print("\n3️⃣ Добавить валидацию:")
print("""
    # После обработки всех заказов:
    for (article, nm_id), group in grouped_data.items():
        warehouse_sum = sum(wh["orders"] for wh in group["warehouses"].values())
        raw_orders_count = len([o for o in orders_data 
                               if o.get("nmId") == nm_id 
                               and not o.get("isCancel")])
        
        if warehouse_sum != raw_orders_count:
            logger.warning(f"Mismatch for {article}: {warehouse_sum} != {raw_orders_count}")
""")

print("\n" + "="*80)
print("📥 ПРИМЕНЕНИЕ ПАТЧА")
print("="*80)

print("\nВыберите вариант:")
print("   1. Применить автоматически (рекомендуется)")
print("   2. Показать детальный diff")
print("   3. Создать резервную копию и применить")
print("\nДля применения запустите:")
print("   python apply_order_fix_patch.py")

print("\n✅ Анализ завершен - готово к исправлению!")
