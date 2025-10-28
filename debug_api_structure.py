"""
Отладочный скрипт для проверки реальной структуры данных из Wildberries API.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def debug_api_structure():
    """Проверить реальную структуру данных из API."""
    
    print("=" * 80)
    print("ОТЛАДКА СТРУКТУРЫ ДАННЫХ WILDBERRIES API")
    print("=" * 80)
    
    # Создаем клиент
    client = WildberriesAPIClient()
    
    try:
        print("\n1. Создаем задачу warehouse_remains...")
        task_id = await client.create_warehouse_remains_task()
        print(f"✅ Задача создана: {task_id}")
        
        print("\n2. Ожидаем обработки задачи (макс. 60 сек)...")
        await asyncio.sleep(20)  # Ждем 20 секунд
        
        print("\n3. Пытаемся скачать данные...")
        try:
            data = await client.download_warehouse_remains(task_id)
            
            if data and len(data) > 0:
                print(f"✅ Получено {len(data)} записей")
                
                # Выводим структуру первой записи
                first_item = data[0]
                print("\n" + "=" * 80)
                print("СТРУКТУРА ПЕРВОЙ ЗАПИСИ:")
                print("=" * 80)
                print(json.dumps(first_item, indent=2, ensure_ascii=False))
                
                # Проверяем наличие ключевых полей
                print("\n" + "=" * 80)
                print("АНАЛИЗ ПОЛЕЙ:")
                print("=" * 80)
                
                print(f"\n📋 Поля верхнего уровня:")
                for key in first_item.keys():
                    value = first_item[key]
                    value_type = type(value).__name__
                    print(f"  - {key}: {value_type}")
                
                # Проверяем warehouses
                if 'warehouses' in first_item and isinstance(first_item['warehouses'], list):
                    print(f"\n🏭 Склады (warehouses): {len(first_item['warehouses'])} шт")
                    
                    if len(first_item['warehouses']) > 0:
                        first_warehouse = first_item['warehouses'][0]
                        print(f"\n📦 Поля первого склада:")
                        for key in first_warehouse.keys():
                            value = first_warehouse[key]
                            print(f"  - {key}: {value} (тип: {type(value).__name__})")
                        
                        # КРИТИЧЕСКИ ВАЖНО: проверяем наличие ordersCount
                        print("\n" + "=" * 80)
                        print("🔍 ПРОВЕРКА КРИТИЧЕСКИХ ПОЛЕЙ:")
                        print("=" * 80)
                        
                        has_orders_count = 'ordersCount' in first_warehouse
                        has_orders_amount = 'ordersAmount' in first_warehouse
                        has_orders = 'orders' in first_warehouse
                        
                        print(f"  ❓ ordersCount: {'✅ ЕСТЬ' if has_orders_count else '❌ НЕТ'}")
                        print(f"  ❓ ordersAmount: {'✅ ЕСТЬ' if has_orders_amount else '❌ НЕТ'}")
                        print(f"  ❓ orders: {'✅ ЕСТЬ' if has_orders else '❌ НЕТ'}")
                        
                        if has_orders_count:
                            print(f"\n  ✅ ordersCount = {first_warehouse['ordersCount']}")
                        if has_orders_amount:
                            print(f"\n  ✅ ordersAmount = {first_warehouse['ordersAmount']}")
                        if has_orders:
                            print(f"\n  ✅ orders = {first_warehouse['orders']}")
                        
                        if not (has_orders_count or has_orders_amount or has_orders):
                            print("\n  ⚠️ ПРЕДУПРЕЖДЕНИЕ: Нет полей с заказами!")
                            print("  💡 Возможно заказы нужно получать из другого endpoint")
                
                # Сохраняем в файл для подробного анализа
                output_file = "api_structure_debug.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data[:3], f, indent=2, ensure_ascii=False)  # Первые 3 записи
                print(f"\n💾 Первые 3 записи сохранены в {output_file}")
                
            else:
                print("❌ Данных нет или пустой массив")
                
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            print(f"  Возможно задача еще не готова, попробуйте увеличить время ожидания")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()
    
    print("\n" + "=" * 80)
    print("ОТЛАДКА ЗАВЕРШЕНА")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_api_structure())
