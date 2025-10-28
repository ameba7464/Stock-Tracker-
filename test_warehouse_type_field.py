"""
Test script to verify warehouseType field in supplier/orders API.

According to urls.md documentation:
warehouseType: string, Enum: "Склад WB" "Склад продавца"

This test will:
1. Fetch recent orders from WB supplier/orders API
2. Check if warehouseType field exists
3. Analyze the values (FBO="Склад WB", FBS="Склад продавца")
4. Count orders by warehouse type
"""

import asyncio
import sys
from datetime import datetime, timedelta
from collections import Counter

# Add parent directory to path
sys.path.insert(0, r"c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker")

from src.stock_tracker.api.client import create_wildberries_client
from src.stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def test_warehouse_type_field():
    """Test if warehouseType field exists in supplier/orders API response."""
    
    print("\n" + "="*80)
    print("TEST: Проверка поля warehouseType в API supplier/orders")
    print("="*80 + "\n")
    
    # Create WB API client
    client = create_wildberries_client()
    
    # Get orders from last 30 days
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print(f"📅 Запрос заказов с {date_from}")
    print(f"🔗 Endpoint: https://statistics-api.wildberries.ru/api/v1/supplier/orders")
    print(f"⏳ Загрузка данных...\n")
    
    try:
        # Fetch orders
        orders = await client.get_supplier_orders(date_from=date_from, flag=0)
        
        print(f"✅ Получено заказов: {len(orders)}")
        
        if not orders:
            print("⚠️  Нет заказов за указанный период")
            return
        
        # Analyze first order to check structure
        print("\n" + "-"*80)
        print("СТРУКТУРА ПЕРВОГО ЗАКАЗА:")
        print("-"*80)
        
        first_order = orders[0]
        print("\nДоступные поля:")
        for key in sorted(first_order.keys()):
            value = first_order[key]
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"  • {key}: {value}")
        
        # Check if warehouseType field exists
        print("\n" + "-"*80)
        print("ПРОВЕРКА ПОЛЯ warehouseType:")
        print("-"*80 + "\n")
        
        if "warehouseType" in first_order:
            print("✅ Поле warehouseType НАЙДЕНО!")
            
            # Analyze all orders by warehouse type
            warehouse_types = Counter()
            warehouse_names_by_type = {}
            
            for order in orders:
                wh_type = order.get("warehouseType", "Unknown")
                wh_name = order.get("warehouseName", "Unknown")
                
                warehouse_types[wh_type] += 1
                
                if wh_type not in warehouse_names_by_type:
                    warehouse_names_by_type[wh_type] = set()
                warehouse_names_by_type[wh_type].add(wh_name)
            
            print("\nРаспределение заказов по типам складов:")
            for wh_type, count in warehouse_types.most_common():
                percentage = (count / len(orders)) * 100
                print(f"\n  📦 {wh_type}: {count} заказов ({percentage:.1f}%)")
                
                # Show warehouse names for this type
                names = warehouse_names_by_type.get(wh_type, set())
                if names:
                    print(f"     Склады: {', '.join(sorted(names)[:5])}")
                    if len(names) > 5:
                        print(f"     ... и еще {len(names) - 5} складов")
            
            # Find example of each warehouse type
            print("\n" + "-"*80)
            print("ПРИМЕРЫ ЗАКАЗОВ ПО ТИПАМ СКЛАДОВ:")
            print("-"*80)
            
            examples_by_type = {}
            for order in orders:
                wh_type = order.get("warehouseType")
                if wh_type and wh_type not in examples_by_type:
                    examples_by_type[wh_type] = order
                
                if len(examples_by_type) >= 2:  # We expect 2 types
                    break
            
            for wh_type, example in examples_by_type.items():
                print(f"\n📋 {wh_type}:")
                print(f"   Артикул продавца: {example.get('supplierArticle')}")
                print(f"   Артикул WB: {example.get('nmId')}")
                print(f"   Склад: {example.get('warehouseName')}")
                print(f"   Дата заказа: {example.get('date')}")
                print(f"   Статус отмены: {example.get('isCancel')}")
            
            # CRITICAL FINDING
            print("\n" + "="*80)
            print("🎯 КРИТИЧЕСКИЙ ВЫВОД:")
            print("="*80)
            print("""
✅ Поле warehouseType СУЩЕСТВУЕТ в API supplier/orders!

Это означает что:
1. Можно получить тип склада для КАЖДОГО ЗАКАЗА
2. "Склад WB" = FBO (товары на складах Wildberries)
3. "Склад продавца" = FBS/MP (товары на складах продавца)

ОДНАКО:
⚠️  Это поле есть только в API ЗАКАЗОВ (supplier/orders)
⚠️  В API ОСТАТКОВ (warehouse_remains) такого поля НЕТ!

Это означает, что API warehouse_remains возвращает ТОЛЬКО остатки FBO,
а остатки FBS/MP нужно вычислять через другие методы.
            """)
            
        else:
            print("❌ Поле warehouseType НЕ НАЙДЕНО!")
            print("\nДоступные поля в ответе:")
            print(", ".join(sorted(first_order.keys())))
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_warehouse_type_field())
