"""
Скрипт для отладки структуры данных Wildberries API V2
"""
import asyncio
import json
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.config import get_config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


async def debug_v2_structure():
    """Получить и проанализировать структуру данных V2 API"""
    
    print("=" * 80)
    print("ОТЛАДКА СТРУКТУРЫ ДАННЫХ WILDBERRIES API V2")
    print("=" * 80)
    
    # Initialize client
    client = WildberriesAPIClient()
    
    try:
        print("\n1. Запрашиваем данные через API v2...")
        
        # Get first 5 products
        response = await client.get_product_stock_data(limit=5, offset=0)
        
        print(f"\n📋 Полный ответ API:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # Check data structure
        if 'data' in response:
            data = response['data']
            items = data.get('items', [])
            total_count = data.get('totalCount', 0)
        else:
            items = response.get('items', [])
            total_count = response.get('totalCount', 0)
        
        print(f"\n✅ Получено {len(items)} записей из {total_count}")
        
        if not items:
            print("❌ Нет данных для анализа")
            return
        
        # Analyze first item structure
        first_item = items[0]
        
        print("\n" + "=" * 80)
        print("СТРУКТУРА ПЕРВОЙ ЗАПИСИ:")
        print("=" * 80)
        print(json.dumps(first_item, indent=2, ensure_ascii=False))
        
        print("\n" + "=" * 80)
        print("АНАЛИЗ ПОЛЕЙ:")
        print("=" * 80)
        
        # Top level fields
        print("\n📋 Поля верхнего уровня:")
        for key, value in first_item.items():
            value_type = type(value).__name__
            if isinstance(value, list):
                print(f"  - {key}: {value_type} ({len(value)} элементов)")
            elif isinstance(value, dict):
                print(f"  - {key}: {value_type} (ключи: {', '.join(value.keys())})")
            else:
                print(f"  - {key}: {value_type}")
        
        # Check for orders/stock fields
        print("\n" + "=" * 80)
        print("🔍 ПРОВЕРКА КРИТИЧЕСКИХ ПОЛЕЙ:")
        print("=" * 80)
        
        fields_to_check = [
            'orders', 'ordersCount', 'ordersAmount', 'ordersQuantity',
            'stock', 'stockCount', 'stockAmount', 'stockQuantity',
            'warehouses', 'warehouseStock', 'warehouseOrders',
            'sales', 'salesCount', 'salesAmount'
        ]
        
        found_fields = []
        for field in fields_to_check:
            if field in first_item:
                value = first_item[field]
                value_type = type(value).__name__
                if isinstance(value, (list, dict)):
                    found_fields.append((field, value_type, len(value) if isinstance(value, list) else 'dict'))
                else:
                    found_fields.append((field, value_type, value))
                print(f"  ✅ {field}: {value_type} = {value if not isinstance(value, (list, dict)) else f'{len(value)} элементов' if isinstance(value, list) else 'dict'}")
            else:
                print(f"  ❌ {field}: НЕТ")
        
        # Analyze warehouses structure if present
        if 'warehouses' in first_item and isinstance(first_item['warehouses'], list) and first_item['warehouses']:
            print("\n" + "=" * 80)
            print("🏭 СТРУКТУРА СКЛАДОВ:")
            print("=" * 80)
            
            first_warehouse = first_item['warehouses'][0]
            print("\nПоля первого склада:")
            for key, value in first_warehouse.items():
                value_type = type(value).__name__
                print(f"  - {key}: {value_type} = {value}")
        
        # Save to file
        output_file = Path(__file__).parent / "api_v2_structure_debug.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'totalCount': total_count,
                'items': items[:3]  # Save first 3 items
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Первые 3 записи сохранены в {output_file.name}")
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных: {e}", exc_info=True)
        print(f"\n❌ ОШИБКА: {e}")
        return
    
    print("\n" + "=" * 80)
    print("ОТЛАДКА ЗАВЕРШЕНА")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_v2_structure())
