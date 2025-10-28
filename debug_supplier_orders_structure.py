#!/usr/bin/env python3
"""
Диагностика структуры ответа от /api/v1/supplier/orders
Выводит реальные поля и их значения для анализа
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

async def debug_supplier_orders_structure():
    """Изучить структуру ответа supplier/orders API"""
    
    print("\n" + "="*100)
    print("🔍 ДИАГНОСТИКА СТРУКТУРЫ ОТВЕТА /api/v1/supplier/orders")
    print("="*100)
    print()
    
    # Initialize API client
    api_client = WildberriesAPIClient()
    fetcher = WildberriesProductDataFetcher(api_client)
    
    # Fetch orders
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
    print(f"📅 Запрос заказов с: {date_from}")
    print(f"🔧 flag=0")
    print()
    
    try:
        orders_data = await fetcher.fetch_supplier_orders(date_from=date_from, flag=0)
        print(f"✅ Получено {len(orders_data)} заказов")
        print()
        
        if not orders_data:
            print("❌ Нет данных для анализа")
            return
        
        # Show first order (all fields)
        print("="*100)
        print("📋 ПРИМЕР ОДНОГО ЗАКАЗА (ВСЕ ПОЛЯ):")
        print("="*100)
        first_order = orders_data[0]
        print(json.dumps(first_order, indent=2, ensure_ascii=False))
        print()
        
        # Collect all unique fields
        print("="*100)
        print("📊 ВСЕ УНИКАЛЬНЫЕ ПОЛЯ ВО ВСЕХ ЗАКАЗАХ:")
        print("="*100)
        all_fields = set()
        field_counts = Counter()
        field_examples = {}
        
        for order in orders_data:
            for field in order.keys():
                all_fields.add(field)
                field_counts[field] += 1
                if field not in field_examples and order[field]:
                    field_examples[field] = order[field]
        
        for field in sorted(all_fields):
            count = field_counts[field]
            percent = (count / len(orders_data)) * 100
            example = field_examples.get(field, "N/A")
            
            # Truncate long examples
            if isinstance(example, str) and len(example) > 50:
                example = example[:50] + "..."
            
            print(f"{field:<30} | {count:>6}/{len(orders_data)} ({percent:>5.1f}%) | Пример: {example}")
        
        print()
        
        # Analyze specific critical fields
        print("="*100)
        print("🔍 АНАЛИЗ КРИТИЧЕСКИХ ПОЛЕЙ:")
        print("="*100)
        
        # 1. Check for unique IDs
        print("\n1️⃣  УНИКАЛЬНЫЕ ИДЕНТИФИКАТОРЫ:")
        unique_ids = ['srid', 'odid', 'gNumber', 'rid']
        for id_field in unique_ids:
            if id_field in all_fields:
                unique_values = set(order.get(id_field) for order in orders_data if order.get(id_field))
                print(f"   {id_field:<15} найдено, уникальных значений: {len(unique_values)}")
            else:
                print(f"   {id_field:<15} НЕ НАЙДЕНО ❌")
        
        # 2. Check for cancellation field
        print("\n2️⃣  ПОЛЕ ОТМЕНЫ ЗАКАЗА:")
        cancel_fields = ['is_cancel', 'isCancel', 'cancel', 'cancelled', 'status']
        for cancel_field in cancel_fields:
            if cancel_field in all_fields:
                values = [order.get(cancel_field) for order in orders_data if cancel_field in order]
                value_counts = Counter(values)
                print(f"   {cancel_field:<15} найдено, значения: {dict(value_counts)}")
            else:
                print(f"   {cancel_field:<15} НЕ НАЙДЕНО")
        
        # 3. Check for quantity field
        print("\n3️⃣  ПОЛЕ КОЛИЧЕСТВА:")
        quantity_fields = ['quantity', 'qty', 'count', 'amount']
        for qty_field in quantity_fields:
            if qty_field in all_fields:
                values = [order.get(qty_field) for order in orders_data if order.get(qty_field)]
                if values:
                    avg_qty = sum(values) / len(values)
                    max_qty = max(values)
                    print(f"   {qty_field:<15} найдено, среднее: {avg_qty:.2f}, максимум: {max_qty}")
                else:
                    print(f"   {qty_field:<15} найдено, но все значения пустые")
            else:
                print(f"   {qty_field:<15} НЕ НАЙДЕНО")
        
        # 4. Check warehouse names
        print("\n4️⃣  НАЗВАНИЯ СКЛАДОВ:")
        if 'warehouseName' in all_fields:
            warehouses = Counter(order.get('warehouseName') for order in orders_data if order.get('warehouseName'))
            print(f"   Найдено уникальных складов: {len(warehouses)}")
            print(f"   Топ-10 складов:")
            for wh, count in warehouses.most_common(10):
                print(f"      {wh:<40} {count:>4} заказов")
        else:
            print("   warehouseName НЕ НАЙДЕНО ❌")
        
        # 5. Check nmId
        print("\n5️⃣  АРТИКУЛЫ (nmId):")
        if 'nmId' in all_fields:
            nm_ids = Counter(order.get('nmId') for order in orders_data if order.get('nmId'))
            print(f"   Найдено уникальных nmId: {len(nm_ids)}")
            print(f"   Топ-5 nmId:")
            for nm_id, count in nm_ids.most_common(5):
                print(f"      {nm_id:<20} {count:>4} заказов")
        else:
            print("   nmId НЕ НАЙДЕНО ❌")
        
        # 6. Check dates
        print("\n6️⃣  ДАТЫ:")
        date_fields = ['date', 'lastChangeDate', 'orderDate', 'created_at']
        for date_field in date_fields:
            if date_field in all_fields:
                dates = [order.get(date_field) for order in orders_data if order.get(date_field)]
                if dates:
                    print(f"   {date_field:<20} найдено, пример: {dates[0]}")
                else:
                    print(f"   {date_field:<20} найдено, но все значения пустые")
            else:
                print(f"   {date_field:<20} НЕ НАЙДЕНО")
        
        print()
        
        # Calculate statistics
        print("="*100)
        print("📈 СТАТИСТИКА ПО ДАННЫМ:")
        print("="*100)
        
        # Group by nmId and warehouse
        orders_by_product = {}
        for order in orders_data:
            nm_id = order.get('nmId')
            wh_name = order.get('warehouseName', 'Unknown')
            key = (nm_id, wh_name)
            if key not in orders_by_product:
                orders_by_product[key] = []
            orders_by_product[key].append(order)
        
        print(f"Всего заказов: {len(orders_data)}")
        print(f"Уникальных комбинаций (nmId + склад): {len(orders_by_product)}")
        print()
        
        print("Пример распределения заказов:")
        for (nm_id, wh_name), orders in list(orders_by_product.items())[:5]:
            print(f"   nmId={nm_id}, склад={wh_name}: {len(orders)} заказов")
        
        print()
        
        # Recommendations
        print("="*100)
        print("💡 РЕКОМЕНДАЦИИ НА ОСНОВЕ АНАЛИЗА:")
        print("="*100)
        
        recommendations = []
        
        # Check for unique ID
        has_unique_id = any(field in all_fields for field in ['srid', 'odid', 'gNumber'])
        if has_unique_id:
            id_field = next((f for f in ['srid', 'odid', 'gNumber'] if f in all_fields), None)
            recommendations.append(
                f"✅ Использовать '{id_field}' для дедупликации заказов"
            )
        else:
            recommendations.append(
                "❌ НЕ НАЙДЕН уникальный ID заказа! Возможны дубликаты!"
            )
        
        # Check for cancellation
        has_cancel = any(field in all_fields for field in ['is_cancel', 'isCancel'])
        if has_cancel:
            cancel_field = next((f for f in ['is_cancel', 'isCancel'] if f in all_fields), None)
            recommendations.append(
                f"✅ Использовать '{cancel_field}' для фильтрации отменённых заказов"
            )
        else:
            recommendations.append(
                "⚠️  НЕ НАЙДЕНО поле отмены заказа - все заказы считаются активными"
            )
        
        # Check for quantity
        has_quantity = 'quantity' in all_fields
        if has_quantity:
            recommendations.append(
                "✅ Использовать 'quantity' при подсчёте (может быть >1)"
            )
        else:
            recommendations.append(
                "⚠️  НЕ НАЙДЕНО поле quantity - считаем каждый заказ как 1 шт"
            )
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print()
        
    except Exception as e:
        logger.error(f"Failed to fetch supplier orders: {e}", exc_info=True)
        print(f"❌ Ошибка: {e}")
        print()


if __name__ == "__main__":
    asyncio.run(debug_supplier_orders_structure())
