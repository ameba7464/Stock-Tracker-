"""
Test script to verify what warehouses are returned by warehouse_remains API.

This test will:
1. Fetch warehouse remains from WB API
2. Check what warehouse names are present
3. Specifically look for "Обухово МП" (known FBS warehouse from orders)
4. Analyze if FBS warehouses are included in warehouse_remains
"""

import asyncio
import sys
from collections import Counter, defaultdict

# Add parent directory to path
sys.path.insert(0, r"c:\Users\miros\Downloads\Stock Tracker\Stock-Tracker")

from src.stock_tracker.api.client import create_wildberries_client
from src.stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def test_warehouse_remains_coverage():
    """Test what warehouses are included in warehouse_remains API."""
    
    print("\n" + "="*80)
    print("TEST: Анализ складов в API warehouse_remains")
    print("="*80 + "\n")
    
    # Create WB API client
    client = create_wildberries_client()
    
    print("⏳ Шаг 1: Создание задачи warehouse_remains...")
    
    try:
        # Create warehouse remains task
        task_id = await client.create_warehouse_remains_task(
            groupByNm=True,
            groupBySa=True
        )
        
        print(f"✅ Задача создана: {task_id}")
        print("⏳ Ожидание 60 секунд для обработки задачи...\n")
        
        # Wait for task to complete
        await asyncio.sleep(60)
        
        print("⏳ Шаг 2: Загрузка данных остатков...")
        
        # Download warehouse remains
        warehouse_data = await client.download_warehouse_remains(task_id)
        
        print(f"✅ Получено записей: {len(warehouse_data)}")
        
        if not warehouse_data:
            print("⚠️  Нет данных по остаткам")
            return
        
        # Analyze warehouse structure
        print("\n" + "-"*80)
        print("СТРУКТУРА ПЕРВОЙ ЗАПИСИ:")
        print("-"*80)
        
        first_record = warehouse_data[0]
        print("\nДоступные поля:")
        for key in sorted(first_record.keys()):
            value = first_record[key]
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"  • {key}: {value}")
        
        # Extract all unique warehouses
        print("\n" + "-"*80)
        print("АНАЛИЗ СКЛАДОВ:")
        print("-"*80 + "\n")
        
        all_warehouses = set()
        warehouse_products = Counter()
        
        for record in warehouse_data:
            warehouses_list = record.get("warehouses", [])
            
            for wh in warehouses_list:
                wh_name = wh.get("warehouseName", "Unknown")
                all_warehouses.add(wh_name)
                warehouse_products[wh_name] += 1
        
        print(f"Всего уникальных складов: {len(all_warehouses)}")
        print("\nТоп-20 складов по количеству товаров:")
        
        for i, (wh_name, count) in enumerate(warehouse_products.most_common(20), 1):
            print(f"  {i:2d}. {wh_name}: {count} товаров")
        
        # Check for known FBS warehouse
        print("\n" + "-"*80)
        print("ПРОВЕРКА FBS СКЛАДА:")
        print("-"*80 + "\n")
        
        fbs_warehouse = "Обухово МП"
        
        if fbs_warehouse in all_warehouses:
            print(f"✅ FBS склад '{fbs_warehouse}' НАЙДЕН в warehouse_remains!")
            
            # Count products on this warehouse
            count = warehouse_products[fbs_warehouse]
            print(f"   Количество товаров: {count}")
            
            # Find example product on this warehouse
            for record in warehouse_data:
                warehouses_list = record.get("warehouses", [])
                for wh in warehouses_list:
                    if wh.get("warehouseName") == fbs_warehouse:
                        print(f"\n   Пример товара на '{fbs_warehouse}':")
                        print(f"   • Артикул продавца: {record.get('vendorCode')}")
                        print(f"   • Артикул WB: {record.get('nmId')}")
                        print(f"   • Баркод: {record.get('barcode')}")
                        print(f"   • Количество: {wh.get('quantity')}")
                        break
                else:
                    continue
                break
        else:
            print(f"❌ FBS склад '{fbs_warehouse}' НЕ НАЙДЕН в warehouse_remains!")
            print(f"\nСписок всех складов ({len(all_warehouses)}):")
            for wh in sorted(all_warehouses):
                print(f"  • {wh}")
        
        # Analyze warehouse names to identify potential FBS warehouses
        print("\n" + "-"*80)
        print("ПОИСК ПОТЕНЦИАЛЬНЫХ FBS СКЛАДОВ:")
        print("-"*80 + "\n")
        
        # Keywords that might indicate FBS/MP warehouses
        fbs_keywords = ["мп", "маркетплейс", "marketplace", "fbs", "seller"]
        
        potential_fbs = []
        for wh_name in all_warehouses:
            wh_lower = wh_name.lower()
            if any(keyword in wh_lower for keyword in fbs_keywords):
                potential_fbs.append(wh_name)
        
        if potential_fbs:
            print(f"Найдено потенциальных FBS складов: {len(potential_fbs)}")
            for wh in sorted(potential_fbs):
                count = warehouse_products[wh]
                print(f"  • {wh}: {count} товаров")
        else:
            print("Потенциальных FBS складов не найдено по ключевым словам")
        
        # CRITICAL ANALYSIS
        print("\n" + "="*80)
        print("🎯 КРИТИЧЕСКИЙ АНАЛИЗ:")
        print("="*80)
        
        if fbs_warehouse in all_warehouses:
            print(f"""
✅ API warehouse_remains ВКЛЮЧАЕТ FBS склады!

Найден склад: {fbs_warehouse}
Количество товаров: {warehouse_products[fbs_warehouse]}

Это означает что:
1. API warehouse_remains возвращает ВСЕ типы складов (FBO + FBS)
2. Предыдущее предположение о том, что он возвращает только FBO было ОШИБОЧНЫМ
3. Расхождение в остатках (475 vs 3459) вызвано ДРУГОЙ причиной

ВОЗМОЖНЫЕ ПРИЧИНЫ РАСХОЖДЕНИЯ:
• Неправильная агрегация данных по складам
• Баг в коде суммирования остатков
• Проблема с баркодами/артикулами
• Фильтрация данных в коде
            """)
        else:
            print(f"""
❌ API warehouse_remains НЕ ВКЛЮЧАЕТ FBS склады!

Склад '{fbs_warehouse}' не найден в ответе API.

Это подтверждает что:
1. API warehouse_remains возвращает ТОЛЬКО FBO склады
2. Для получения FBS остатков нужен другой подход
3. Расхождение (475 vs 3459) вызвано отсутствием FBS данных

РЕШЕНИЕ:
Необходимо найти другой API endpoint для получения FBS остатков
или использовать комбинированный подход (Аналитика V2 API).
            """)
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_warehouse_remains_coverage())
