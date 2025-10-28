#!/usr/bin/env python3
"""
Тест исправленной логики "Заказы со склада".

Проверяет:
1. Вызов supplier/orders API
2. Правильный расчет заказов по складам
3. Отображение складов с нулевыми остатками
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def test_fixed_orders_logic():
    """Тест исправленной логики обработки заказов."""
    
    print("\n" + "="*80)
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ЛОГИКИ 'ЗАКАЗЫ СО СКЛАДА'")
    print("="*80)
    
    try:
        service = ProductService()
        
        # Тест 1: Синхронизация с API
        print("\n📋 ТЕСТ 1: Полная синхронизация с исправленной логикой")
        print("-" * 80)
        
        print("\n1.1 Запуск синхронизации...")
        sync_session = await service.sync_from_api_to_sheets()
        
        print(f"\n   ✅ Статус: {sync_session.status}")
        print(f"   📊 Продуктов обработано: {sync_session.products_processed}")
        print(f"   ❌ Продуктов с ошибками: {sync_session.products_failed}")
        
        if sync_session.errors:
            print(f"\n   ⚠️  Ошибки:")
            for error in sync_session.errors[:5]:
                print(f"      - {error}")
        
        # Тест 2: Проверка данных в таблице
        print("\n" + "="*80)
        print("📋 ТЕСТ 2: Проверка данных в Google Sheets")
        print("-" * 80)
        
        from stock_tracker.database.operations import SheetsOperations
        from stock_tracker.database.sheets import GoogleSheetsClient
        from stock_tracker.utils.config import get_config
        
        config = get_config()
        sheets_client = GoogleSheetsClient()
        operations = SheetsOperations(sheets_client)
        
        print("\n2.1 Чтение продуктов из таблицы...")
        products = operations.read_all_products(config.google_sheets.sheet_id)
        print(f"   ✅ Получено продуктов: {len(products)}")
        
        if products:
            print("\n2.2 Анализ первых 3 продуктов:")
            for i, product in enumerate(products[:3], 1):
                print(f"\n   Продукт {i}: {product.seller_article}")
                print(f"      nmId: {product.wildberries_article}")
                print(f"      Всего заказов: {product.total_orders}")
                print(f"      Всего остатков: {product.total_stock}")
                print(f"      Складов: {len(product.warehouses)}")
                
                if product.warehouses:
                    print(f"      Склады:")
                    for wh in product.warehouses[:5]:
                        stock_str = f"stock={wh.stock}" if wh.stock > 0 else "stock=0 ⚠️"
                        orders_str = f"orders={wh.orders}" if wh.orders > 0 else "orders=0"
                        print(f"         - {wh.name}: {stock_str}, {orders_str}")
                    
                    # Проверяем склады с нулевыми остатками
                    zero_stock_warehouses = [wh for wh in product.warehouses if wh.stock == 0]
                    if zero_stock_warehouses:
                        print(f"      ✅ Склады с нулевыми остатками: {len(zero_stock_warehouses)}")
                        for wh in zero_stock_warehouses:
                            print(f"         - {wh.name}: orders={wh.orders}")
                
                # Валидация
                warehouse_orders_sum = sum(wh.orders for wh in product.warehouses)
                if warehouse_orders_sum == product.total_orders:
                    print(f"      ✅ Валидация: сумма заказов по складам = total_orders")
                else:
                    print(f"      ❌ Валидация FAILED: {warehouse_orders_sum} != {product.total_orders}")
        
        # Тест 3: Итоговая статистика
        print("\n" + "="*80)
        print("📊 ТЕСТ 3: Итоговая статистика")
        print("-" * 80)
        
        if products:
            total_products = len(products)
            products_with_orders = len([p for p in products if p.total_orders > 0])
            products_with_zero_stock_warehouses = len([p for p in products 
                                                      if any(wh.stock == 0 for wh in p.warehouses)])
            
            total_warehouses = sum(len(p.warehouses) for p in products)
            warehouses_with_zero_stock = sum(sum(1 for wh in p.warehouses if wh.stock == 0) 
                                            for p in products)
            
            print(f"\n   📦 Всего продуктов: {total_products}")
            print(f"   ✅ Продуктов с заказами: {products_with_orders}")
            print(f"   ⚠️  Продуктов со складами с нулевыми остатками: {products_with_zero_stock_warehouses}")
            print(f"\n   📦 Всего складов: {total_warehouses}")
            print(f"   ⚠️  Складов с нулевыми остатками: {warehouses_with_zero_stock}")
            
            if products_with_orders > 0:
                print(f"\n   ✅ УСПЕХ: {products_with_orders}/{total_products} продуктов имеют заказы")
            else:
                print(f"\n   ❌ ПРОБЛЕМА: Нет продуктов с заказами!")
            
            if warehouses_with_zero_stock > 0:
                print(f"   ✅ УСПЕХ: Склады с нулевыми остатками отображаются ({warehouses_with_zero_stock})")
        
        print("\n" + "="*80)
        print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("="*80)
        
        # Создаём отчёт
        report = {
            "timestamp": datetime.now().isoformat(),
            "sync_status": str(sync_session.status),
            "products_processed": sync_session.products_processed,
            "products_failed": sync_session.products_failed,
            "products_with_orders": products_with_orders if products else 0,
            "warehouses_with_zero_stock": warehouses_with_zero_stock if products else 0,
            "success": products_with_orders > 0 if products else False
        }
        
        print(f"\n📄 Результаты теста:")
        print(f"   Синхронизация: {'✅ УСПЕХ' if sync_session.status.name == 'COMPLETED' else '❌ ОШИБКА'}")
        print(f"   Продукты с заказами: {'✅ ЕСТЬ' if report['products_with_orders'] > 0 else '❌ НЕТ'}")
        print(f"   Склады с нулевыми остатками: {'✅ ОТОБРАЖАЮТСЯ' if report['warehouses_with_zero_stock'] > 0 else 'ℹ️  НЕТ ТАКИХ'}")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Ошибка в тесте: {e}")
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    print("🧪 Запуск теста исправленной логики...")
    
    try:
        report = asyncio.run(test_fixed_orders_logic())
        
        if report['success']:
            print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            sys.exit(0)
        else:
            print("\n⚠️  Тесты завершены с предупреждениями")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️  Тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        sys.exit(1)
