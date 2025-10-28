#!/usr/bin/env python3
"""
Диагностика критических проблем с метрикой "Заказы со склада".

Проверяет:
1. Источники данных (warehouse_remains vs supplier/orders)
2. Логику извлечения заказов
3. Склады с нулевыми остатками
4. Соответствие urls.md спецификации
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
import json

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def diagnose_warehouse_orders():
    """Полная диагностика проблем с заказами по складам."""
    
    print("\n" + "="*80)
    print("🔍 ДИАГНОСТИКА: МЕТРИКА 'ЗАКАЗЫ СО СКЛАДА'")
    print("="*80)
    
    try:
        client = WildberriesAPIClient()
        calculator = WildberriesCalculator()
        
        # ===== ТЕСТ 1: Проверка источников данных =====
        print("\n📋 ТЕСТ 1: Проверка источников данных API")
        print("-" * 80)
        
        # 1.1 Warehouse Remains
        print("\n1.1 Получение warehouse_remains (остатки)...")
        try:
            task_id = await client.create_warehouse_remains_task()
            print(f"   ✅ Создана задача: {task_id}")
            
            print("   ⏳ Ожидание 60 секунд...")
            await asyncio.sleep(60)
            
            warehouse_data = await client.download_warehouse_remains(task_id)
            print(f"   ✅ Получено продуктов: {len(warehouse_data)}")
            
            if warehouse_data:
                sample = warehouse_data[0]
                print(f"\n   📦 ПРИМЕР СТРУКТУРЫ warehouse_remains:")
                print(f"      vendorCode: {sample.get('vendorCode')}")
                print(f"      nmId: {sample.get('nmId')}")
                print(f"      warehouses: {len(sample.get('warehouses', []))} складов")
                
                # Проверяем наличие ordersCount
                has_orders_count = False
                for wh in sample.get('warehouses', []):
                    if 'ordersCount' in wh:
                        has_orders_count = True
                        break
                
                if has_orders_count:
                    print("      ✅ ordersCount: НАЙДЕНО в данных")
                else:
                    print("      ❌ ordersCount: НЕ НАЙДЕНО (это ПРОБЛЕМА!)")
                
                # Показываем первые склады
                print(f"\n   📋 Первые 3 склада:")
                for i, wh in enumerate(sample.get('warehouses', [])[:3], 1):
                    wh_name = wh.get('warehouseName', 'Unknown')
                    quantity = wh.get('quantity', 0)
                    orders = wh.get('ordersCount', 'N/A')
                    print(f"      {i}. {wh_name}")
                    print(f"         - quantity: {quantity}")
                    print(f"         - ordersCount: {orders}")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            warehouse_data = []
        
        # 1.2 Supplier Orders
        print("\n1.2 Получение supplier/orders (заказы)...")
        try:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
            print(f"   📅 Период: последние 7 дней от {date_from}")
            
            orders_data = await client.get_supplier_orders(date_from)
            print(f"   ✅ Получено заказов: {len(orders_data)}")
            
            if orders_data:
                sample_order = orders_data[0]
                print(f"\n   📦 ПРИМЕР СТРУКТУРЫ supplier/orders:")
                print(f"      supplierArticle: {sample_order.get('supplierArticle')}")
                print(f"      nmId: {sample_order.get('nmId')}")
                print(f"      warehouseName: {sample_order.get('warehouseName')}")
                print(f"      isCancel: {sample_order.get('isCancel')}")
                
                # Подсчитываем заказы по складам для первого продукта
                if warehouse_data:
                    first_product_nm_id = warehouse_data[0].get('nmId')
                    product_orders = [o for o in orders_data if o.get('nmId') == first_product_nm_id]
                    
                    print(f"\n   📊 Заказы для продукта nmId={first_product_nm_id}:")
                    print(f"      Всего заказов: {len(product_orders)}")
                    
                    # Группируем по складам
                    orders_by_warehouse = {}
                    for order in product_orders:
                        wh_name = order.get('warehouseName', 'Unknown')
                        if wh_name not in orders_by_warehouse:
                            orders_by_warehouse[wh_name] = 0
                        orders_by_warehouse[wh_name] += 1
                    
                    print(f"      По складам:")
                    for wh_name, count in sorted(orders_by_warehouse.items(), key=lambda x: x[1], reverse=True):
                        print(f"         {wh_name}: {count} заказов")
        
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            orders_data = []
        
        # ===== ТЕСТ 2: Проверка текущей логики =====
        print("\n" + "="*80)
        print("📋 ТЕСТ 2: Анализ текущей логики обработки")
        print("-" * 80)
        
        if warehouse_data:
            sample = warehouse_data[0]
            nm_id = sample.get('nmId')
            vendor_code = sample.get('vendorCode')
            
            print(f"\n2.1 Анализ продукта: {vendor_code} (nmId: {nm_id})")
            
            # Проверяем что делает текущий код
            print("\n   🔍 Текущая логика в product_service.py:")
            
            transit_warehouse = None
            real_warehouses = []
            
            for wh in sample.get('warehouses', []):
                wh_name = wh.get('warehouseName', '')
                quantity = wh.get('quantity', 0)
                
                if wh_name == "В пути до получателей":
                    transit_warehouse = {'name': wh_name, 'quantity': quantity}
                    print(f"      ✅ НАЙДЕН виртуальный склад: '{wh_name}'")
                    print(f"         - Текущий код берет quantity={quantity} как ЗАКАЗЫ")
                    print(f"         - ❌ ЭТО ОШИБКА! Это транзит, а не заказы")
                elif wh_name not in ("В пути возвраты на склад WB", "Всего находится на складах"):
                    real_warehouses.append({'name': wh_name, 'quantity': quantity})
            
            print(f"\n   📦 Реальные склады: {len(real_warehouses)}")
            for wh in real_warehouses[:3]:
                print(f"      - {wh['name']}: stock={wh['quantity']}")
            
            if transit_warehouse:
                print(f"\n   ⚠️  ПРОБЛЕМА: Текущий код использует '{transit_warehouse['name']}'")
                print(f"      quantity={transit_warehouse['quantity']} как заказы")
                print(f"      Но это ТРАНЗИТ, а не реальные заказы от клиентов!")
        
        # ===== ТЕСТ 3: Правильный расчет заказов =====
        print("\n" + "="*80)
        print("📋 ТЕСТ 3: Правильный расчет заказов по urls.md")
        print("-" * 80)
        
        if warehouse_data and orders_data:
            sample = warehouse_data[0]
            nm_id = sample.get('nmId')
            vendor_code = sample.get('vendorCode')
            
            print(f"\n3.1 Продукт: {vendor_code} (nmId: {nm_id})")
            
            # Правильный расчет заказов
            print("\n   ✅ ПРАВИЛЬНАЯ логика (urls.md):")
            print("      Источник: /supplier/orders эндпоинт")
            print("      Метод: Подсчет записей по nmId + warehouseName")
            
            # Общее количество заказов
            total_orders_correct = len([o for o in orders_data 
                                       if o.get('nmId') == nm_id 
                                       and not o.get('isCancel', False)])
            
            print(f"\n      Всего заказов (правильно): {total_orders_correct}")
            
            # По складам
            print(f"\n      По складам:")
            warehouse_orders = {}
            for order in orders_data:
                if order.get('nmId') == nm_id and not order.get('isCancel', False):
                    wh_name = order.get('warehouseName', 'Unknown')
                    warehouse_orders[wh_name] = warehouse_orders.get(wh_name, 0) + 1
            
            for wh_name, count in sorted(warehouse_orders.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"         {wh_name}: {count} заказов")
            
            # Сравниваем с текущей логикой
            print(f"\n   📊 СРАВНЕНИЕ:")
            if transit_warehouse:
                current_logic_orders = transit_warehouse['quantity']
                print(f"      Текущая логика (НЕПРАВИЛЬНО): {current_logic_orders} заказов")
                print(f"      Правильная логика (urls.md): {total_orders_correct} заказов")
                print(f"      Разница: {abs(current_logic_orders - total_orders_correct)}")
                
                if current_logic_orders != total_orders_correct:
                    print(f"      ❌ ЗНАЧЕНИЯ НЕ СОВПАДАЮТ! Текущая логика НЕПРАВИЛЬНАЯ!")
        
        # ===== ТЕСТ 4: Склады с нулевыми остатками =====
        print("\n" + "="*80)
        print("📋 ТЕСТ 4: Проверка складов с нулевыми остатками")
        print("-" * 80)
        
        if orders_data:
            print("\n4.1 Поиск складов где есть заказы, но может не быть остатков...")
            
            # Собираем все склады из заказов
            warehouses_with_orders = set()
            for order in orders_data:
                if not order.get('isCancel', False):
                    wh_name = order.get('warehouseName', '')
                    if wh_name:
                        warehouses_with_orders.add(wh_name)
            
            print(f"   📦 Уникальных складов с заказами: {len(warehouses_with_orders)}")
            
            # Собираем все склады из warehouse_remains
            warehouses_with_stock = set()
            for item in warehouse_data:
                for wh in item.get('warehouses', []):
                    wh_name = wh.get('warehouseName', '')
                    quantity = wh.get('quantity', 0)
                    if wh_name and quantity > 0:
                        warehouses_with_stock.add(wh_name)
            
            print(f"   📦 Уникальных складов с остатками: {len(warehouses_with_stock)}")
            
            # Находим склады только с заказами (без остатков)
            orders_only = warehouses_with_orders - warehouses_with_stock
            if orders_only:
                print(f"\n   ⚠️  НАЙДЕНЫ склады только с заказами (БЕЗ остатков): {len(orders_only)}")
                for wh_name in list(orders_only)[:5]:
                    order_count = sum(1 for o in orders_data 
                                    if o.get('warehouseName') == wh_name 
                                    and not o.get('isCancel', False))
                    print(f"      - {wh_name}: {order_count} заказов, stock=0")
                print(f"      ❌ ПРОБЛЕМА: Эти склады НЕ отобразятся в таблице!")
                print(f"         Текущий код создает склады только из warehouse_remains")
            else:
                print(f"   ✅ Все склады с заказами имеют остатки")
        
        # ===== ТЕСТ 5: Итоговый отчет =====
        print("\n" + "="*80)
        print("📊 ИТОГОВЫЙ ОТЧЕТ")
        print("="*80)
        
        problems_found = []
        
        # Проблема 1: Источник данных
        if warehouse_data and not any('ordersCount' in wh for item in warehouse_data for wh in item.get('warehouses', [])):
            problems_found.append({
                "id": 1,
                "severity": "КРИТИЧНО",
                "description": "warehouse_remains НЕ содержит ordersCount",
                "impact": "Невозможно получить заказы из этого эндпоинта",
                "solution": "Использовать /supplier/orders эндпоинт"
            })
        
        # Проблема 2: Неправильная интерпретация
        if transit_warehouse and total_orders_correct != transit_warehouse['quantity']:
            problems_found.append({
                "id": 2,
                "severity": "КРИТИЧНО",
                "description": "Заказы берутся из виртуального склада 'В пути до получателей'",
                "impact": f"Неправильные значения (транзит {transit_warehouse['quantity']} != заказы {total_orders_correct})",
                "solution": "Убрать логику с виртуальным складом, использовать supplier/orders"
            })
        
        # Проблема 3: Склады с нулевыми остатками
        if orders_only:
            problems_found.append({
                "id": 3,
                "severity": "ВАЖНО",
                "description": f"Найдены склады с заказами, но без остатков: {len(orders_only)}",
                "impact": "Эти склады НЕ отображаются в таблице, заказы теряются",
                "solution": "Создавать склады из orders_data даже если нет в warehouse_remains"
            })
        
        # Проблема 4: orders_data не используется
        problems_found.append({
            "id": 4,
            "severity": "КРИТИЧНО",
            "description": "В product_service.py orders_data = [] (пустой)",
            "impact": "Реальные заказы из /supplier/orders не обрабатываются",
            "solution": "Вызывать get_supplier_orders() и передавать в _convert_api_record_to_product()"
        })
        
        print(f"\n🚨 НАЙДЕНО ПРОБЛЕМ: {len(problems_found)}")
        print("-" * 80)
        
        for problem in problems_found:
            print(f"\n❌ ПРОБЛЕМА #{problem['id']}: [{problem['severity']}]")
            print(f"   Описание: {problem['description']}")
            print(f"   Влияние: {problem['impact']}")
            print(f"   Решение: {problem['solution']}")
        
        print("\n" + "="*80)
        print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
        print("="*80)
        
        # Сохраняем отчет
        report = {
            "timestamp": datetime.now().isoformat(),
            "problems_found": len(problems_found),
            "problems": problems_found,
            "warehouse_data_count": len(warehouse_data) if warehouse_data else 0,
            "orders_data_count": len(orders_data) if orders_data else 0,
            "warehouses_with_orders_only": list(orders_only) if orders_only else []
        }
        
        report_path = "warehouse_orders_diagnosis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Отчёт сохранён: {report_path}")
        print(f"📄 Полная диагностика: CRITICAL_WAREHOUSE_ORDERS_DIAGNOSIS.md")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка в диагностике: {e}")
        logger.error(f"Diagnosis failed: {e}")
        raise


if __name__ == "__main__":
    print("🔍 Запуск диагностики критических проблем с 'Заказы со склада'...")
    
    try:
        asyncio.run(diagnose_warehouse_orders())
        print("\n✅ Диагностика успешно завершена")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⏹️  Диагностика прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        sys.exit(1)
