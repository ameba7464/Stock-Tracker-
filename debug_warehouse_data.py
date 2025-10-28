"""
Диагностический скрипт для анализа структуры данных warehouse_remains V1 API
"""
import asyncio
import sys
import json
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.config import get_config


async def main():
    """Анализ структуры warehouse_remains"""
    
    print("=" * 80)
    print("ДИАГНОСТИКА СТРУКТУРЫ WAREHOUSE_REMAINS V1 API")
    print("=" * 80)
    
    # Создаем клиент
    config = get_config()
    client = WildberriesAPIClient(config.wildberries_api_key)
    
    try:
        # Запрашиваем данные
        print("\n1. Запрос warehouse_remains...")
        warehouse_data = await client.get_warehouse_remains_with_retry()
        
        print(f"   ✓ Получено продуктов: {len(warehouse_data)}")
        
        if not warehouse_data:
            print("   ✗ ОШИБКА: Нет данных!")
            return
        
        # Берем первый продукт для детального анализа
        first_product = warehouse_data[0]
        
        print(f"\n2. Анализ первого продукта (nmId: {first_product.get('nmId', 'N/A')}):")
        print(f"   Артикул: {first_product.get('supplierArticle', 'N/A')}")
        print(f"   Баркод: {first_product.get('barcode', 'N/A')}")
        
        # Проверяем поля верхнего уровня
        print(f"\n3. Поля верхнего уровня:")
        for key in sorted(first_product.keys()):
            value = first_product[key]
            if key == 'warehouses':
                print(f"   - {key}: список из {len(value)} складов")
            else:
                print(f"   - {key}: {type(value).__name__} = {value}")
        
        # Анализируем структуру warehouses
        warehouses = first_product.get('warehouses', [])
        
        if not warehouses:
            print("\n   ✗ ПРОБЛЕМА: Массив warehouses пустой!")
            return
        
        print(f"\n4. Анализ складов (всего {len(warehouses)}):")
        
        for i, wh in enumerate(warehouses[:3], 1):  # Первые 3 склада
            print(f"\n   Склад #{i}:")
            print(f"   - Название: {wh.get('warehouseName', 'N/A')}")
            print(f"   - ID: {wh.get('warehouseId', 'N/A')}")
            
            # Ключевой момент - ищем поле с заказами
            print(f"\n   - Все ключи склада:")
            for key in sorted(wh.keys()):
                value = wh[key]
                print(f"     * {key}: {type(value).__name__} = {value}")
            
            # Проверяем разные варианты названий
            orders_variants = [
                'ordersCount',
                'orders',
                'inWayToClient',
                'inWayFromClient',
                'quantityFull',
                'quantity',
                'quantityNotInOrders'
            ]
            
            print(f"\n   - Поиск полей с заказами:")
            found_orders = False
            for variant in orders_variants:
                if variant in wh:
                    print(f"     ✓ Найдено: {variant} = {wh[variant]}")
                    found_orders = True
            
            if not found_orders:
                print(f"     ✗ НЕ НАЙДЕНО полей с заказами!")
        
        # Сохраняем полную структуру первого продукта в JSON
        output_file = Path(__file__).parent / "warehouse_structure_debug.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(first_product, f, ensure_ascii=False, indent=2)
        
        print(f"\n5. Полная структура сохранена в: {output_file}")
        
        # Итоговый вывод
        print("\n" + "=" * 80)
        print("ИТОГИ ДИАГНОСТИКИ:")
        print("=" * 80)
        
        # Проверяем наличие ordersCount на уровне склада
        has_orders_count = any(
            'ordersCount' in wh 
            for wh in warehouses
        )
        
        if has_orders_count:
            print("✓ Поле 'ordersCount' найдено в данных складов")
            total_orders = sum(wh.get('ordersCount', 0) for wh in warehouses)
            print(f"  Общее количество заказов: {total_orders}")
        else:
            print("✗ ПРОБЛЕМА: Поле 'ordersCount' НЕ найдено в данных складов!")
            print("  Возможные причины:")
            print("  1. V1 API не предоставляет данные о заказах")
            print("  2. Используется неправильное название поля")
            print("  3. Заказы находятся в других полях (inWayToClient, etc.)")
        
        # Проверяем наличие quantity
        has_quantity = any(
            'quantity' in wh or 'quantityFull' in wh
            for wh in warehouses
        )
        
        if has_quantity:
            print("✓ Поля остатков найдены в данных складов")
        else:
            print("✗ ПРОБЛЕМА: Поля остатков НЕ найдены!")
        
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
