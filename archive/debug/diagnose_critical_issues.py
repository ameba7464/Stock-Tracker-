#!/usr/bin/env python3
"""
Диагностика критических проблем Stock Tracker.

Проверяет конкретные случаи расхождений с WB данными.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.core.calculator import (
    is_real_warehouse, 
    WildberriesCalculator,
)
from stock_tracker.utils.warehouse_mapper import (
    validate_warehouse_mapping,
    normalize_warehouse_name,
    is_marketplace_warehouse
)
from stock_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

async def diagnose_marketplace_warehouse_issue():
    """Диагностика проблемы со складом Маркетплейс."""
    logger.info("🔍 DIAGNOSING: Marketplace warehouse inclusion")
    
    print("🏭 Testing Marketplace warehouse detection:")
    
    test_cases = [
        "Маркетплейс",
        "маркетплейс", 
        "Marketplace",
        "Склад продавца",
        "МП-1",
        "FBS склад"
    ]
    
    for warehouse_name in test_cases:
        is_included = is_real_warehouse(warehouse_name)
        is_mp = is_marketplace_warehouse(warehouse_name)
        status = "✅ INCLUDED" if is_included else "❌ EXCLUDED"
        mp_status = "🏪 MARKETPLACE" if is_mp else "🏢 REGULAR"
        print(f"   {status} {mp_status}: '{warehouse_name}'")
    
    # Test FBS detection with warehouse type
    print("\n📦 Testing FBS warehouse detection with warehouseType:")
    fbs_test_cases = [
        ("Маркетплейс", "Склад продавца"),
        ("Склад продавца", "Склад продавца"),
        ("Чехов 1", "Склад WB"),
        ("Подольск", "Склад WB"),
        ("МП", "")
    ]
    
    for warehouse_name, warehouse_type in fbs_test_cases:
        is_fbs = WildberriesCalculator.is_fbs_warehouse(warehouse_name, warehouse_type)
        status = "✅ FBS" if is_fbs else "❌ NOT FBS"
        print(f"   {status}: '{warehouse_name}' (type: '{warehouse_type}')")

async def diagnose_orders_accuracy_issue():
    """Диагностика точности подсчета заказов."""
    logger.info("🔍 DIAGNOSING: Orders counting accuracy")
    
    print("📊 Testing orders accuracy calculation:")
    
    # Создаем тестовые данные для проверки точности
    test_nm_id = 12345678
    test_warehouse = "Чехов 1"
    
    mock_orders = [
        {"nmId": test_nm_id, "warehouseName": "Чехов 1", "isCancel": False, "supplierArticle": "TEST1"},
        {"nmId": test_nm_id, "warehouseName": "Чехов 1", "isCancel": False, "supplierArticle": "TEST1"},
        {"nmId": test_nm_id, "warehouseName": "Чехов 1", "isCancel": True, "supplierArticle": "TEST1"},  # Отменен
        {"nmId": test_nm_id, "warehouseName": "Подольск", "isCancel": False, "supplierArticle": "TEST1"},
        {"nmId": test_nm_id, "warehouseName": "Маркетплейс", "isCancel": False, "supplierArticle": "TEST1", "warehouseType": "Склад продавца"},
        {"nmId": 87654321, "warehouseName": "Чехов 1", "isCancel": False, "supplierArticle": "TEST2"}  # Другой товар
    ]
    
    # Тест точности подсчета для конкретного склада
    warehouse_orders = WildberriesCalculator.calculate_warehouse_orders(
        mock_orders, test_nm_id, test_warehouse
    )
    
    print(f"   📦 Warehouse orders for nmId {test_nm_id}, warehouse '{test_warehouse}': {warehouse_orders}")
    print(f"   Expected: 2 orders (excluding canceled)")
    
    # Тест валидации точности
    calculated_breakdown = {
        "Чехов 1": 2,
        "Подольск": 1,
        "Маркетплейс": 1
    }
    
    validation = WildberriesCalculator.validate_warehouse_orders_accuracy(
        mock_orders, test_nm_id, calculated_breakdown
    )
    
    print(f"   🎯 Validation result:")
    print(f"      Total actual: {validation['total_actual']}")
    print(f"      Total calculated: {validation['total_calculated']}")
    print(f"      Accuracy: {validation['accuracy_percent']:.1f}%")
    print(f"      Is accurate: {'✅' if validation['is_accurate'] else '❌'}")

async def diagnose_warehouse_name_mapping():
    """Диагностика сопоставления названий складов."""
    logger.info("🔍 DIAGNOSING: Warehouse name mapping")
    
    print("🗺️ Testing warehouse name normalization:")
    
    # Примеры проблемных названий
    test_mappings = [
        "Самара (Новосемейкино)",
        "Чехов 1",
        "Чехов-1", 
        "Новосемейкино",
        "Маркетплейс",
        "Склад продавца",
        "Подольск 3"
    ]
    
    for warehouse_name in test_mappings:
        normalized = normalize_warehouse_name(warehouse_name)
        is_mp = is_marketplace_warehouse(warehouse_name)
        mp_indicator = " 🏪" if is_mp else ""
        print(f"   '{warehouse_name}' -> '{normalized}'{mp_indicator}")
    
    # Тест валидации сопоставления
    print("\n🔍 Testing WB vs Stock Tracker mapping:")
    wb_names = ["Новосемейкино", "Чехов", "Маркетплейс"]
    st_names = ["Самара (Новосемейкино)", "Чехов 1", "Склад продавца"]
    
    validation = validate_warehouse_mapping(wb_names, st_names)
    
    print(f"   Mapping validation results:")
    print(f"      Accuracy: {validation['accuracy_percent']:.1f}%")
    print(f"      Matched warehouses: {validation['matched_warehouses']}")
    print(f"      WB only: {validation['wb_only_warehouses']}")
    print(f"      ST only: {validation['st_only_warehouses']}")

async def diagnose_fbs_warehouse_inclusion():
    """Диагностика включения FBS складов."""
    logger.info("🔍 DIAGNOSING: FBS warehouse inclusion")
    
    print("🏪 Testing FBS warehouse data processing:")
    
    # Создаем тестовые данные с FBS складами
    mock_warehouse_data = [
        {
            "nmId": 12345,
            "vendorCode": "TEST-FBS",
            "warehouses": [
                {"warehouseName": "Чехов 1", "quantity": 100},
                {"warehouseName": "Маркетплейс", "quantity": 50},
                {"warehouseName": "Склад продавца", "quantity": 25}
            ]
        }
    ]
    
    mock_orders_data = [
        {"nmId": 12345, "supplierArticle": "TEST-FBS", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
        {"nmId": 12345, "supplierArticle": "TEST-FBS", "warehouseName": "Маркетплейс", "warehouseType": "Склад продавца", "isCancel": False},
        {"nmId": 12345, "supplierArticle": "TEST-FBS", "warehouseName": "Склад продавца", "warehouseType": "Склад продавца", "isCancel": False}
    ]
    
    # Обрабатываем данные
    grouped_data = WildberriesCalculator.group_data_by_product(
        mock_warehouse_data, mock_orders_data
    )
    
    # Анализируем результаты
    for product_key, product_data in grouped_data.items():
        print(f"   📦 Product: {product_key}")
        print(f"      Total stock: {product_data['total_stock']}")
        print(f"      Total orders: {product_data['total_orders']}")
        
        fbs_count = 0
        wb_count = 0
        
        for warehouse_name, warehouse_info in product_data["warehouses"].items():
            is_fbs = warehouse_info.get("is_fbs", False)
            stock = warehouse_info.get("stock", 0)
            orders = warehouse_info.get("orders", 0)
            
            if is_fbs:
                fbs_count += 1
                indicator = "🏪 FBS"
            else:
                wb_count += 1
                indicator = "🏢 WB"
            
            print(f"         {indicator} {warehouse_name}: stock={stock}, orders={orders}")
        
        print(f"      Summary: {fbs_count} FBS warehouses, {wb_count} WB warehouses")
        
        if fbs_count > 0:
            print(f"      ✅ FBS warehouses successfully included!")
        else:
            print(f"      ❌ NO FBS warehouses found - CRITICAL ERROR!")

async def run_critical_accuracy_test():
    """Тест на конкретном проблемном случае из документации."""
    logger.info("🔍 DIAGNOSING: Critical accuracy test case")
    
    print("🎯 Testing specific critical case: Its1_2_3/50g at Чехов 1:")
    
    # Симулируем проблемный случай из документации
    # WB показывает: 5 заказов
    # Stock Tracker показывал: 49 заказов (ОШИБКА)
    
    mock_nm_id = 999999  # Симуляция Its1_2_3/50g
    target_warehouse = "Чехов 1"
    expected_orders = 5
    
    # Создаем корректные тестовые данные
    correct_orders = []
    for i in range(expected_orders):
        correct_orders.append({
            "nmId": mock_nm_id,
            "supplierArticle": "Its1_2_3/50g",
            "warehouseName": target_warehouse,
            "warehouseType": "Склад WB",
            "isCancel": False,
            "date": f"2025-10-{20+i}"
        })
    
    # Добавляем отмененные заказы (должны игнорироваться)
    for i in range(3):
        correct_orders.append({
            "nmId": mock_nm_id,
            "supplierArticle": "Its1_2_3/50g", 
            "warehouseName": target_warehouse,
            "warehouseType": "Склад WB",
            "isCancel": True,  # ОТМЕНЕН - не должен считаться
            "date": f"2025-10-{15+i}"
        })
    
    # Добавляем заказы для других складов
    other_warehouses = ["Подольск", "Маркетплейс"]
    for warehouse in other_warehouses:
        warehouse_type = "Склад продавца" if warehouse == "Маркетплейс" else "Склад WB"
        for i in range(2):
            correct_orders.append({
                "nmId": mock_nm_id,
                "supplierArticle": "Its1_2_3/50g",
                "warehouseName": warehouse,
                "warehouseType": warehouse_type,
                "isCancel": False,
                "date": f"2025-10-{23+i}"
            })
    
    # Тестируем исправленный алгоритм
    calculated_orders = WildberriesCalculator.calculate_warehouse_orders(
        correct_orders, mock_nm_id, target_warehouse
    )
    
    print(f"   📊 Test results for warehouse '{target_warehouse}':")
    print(f"      Expected orders: {expected_orders}")
    print(f"      Calculated orders: {calculated_orders}")
    print(f"      Result: {'✅ ACCURATE' if calculated_orders == expected_orders else '❌ INACCURATE'}")
    
    # Проверяем общую точность
    warehouse_breakdown = {}
    for warehouse in [target_warehouse] + other_warehouses:
        warehouse_breakdown[warehouse] = WildberriesCalculator.calculate_warehouse_orders(
            correct_orders, mock_nm_id, warehouse
        )
    
    validation = WildberriesCalculator.validate_warehouse_orders_accuracy(
        correct_orders, mock_nm_id, warehouse_breakdown
    )
    
    print(f"   🎯 Overall validation:")
    print(f"      Total accuracy: {validation['accuracy_percent']:.1f}%")
    print(f"      Warehouse breakdown: {validation['warehouse_breakdown']}")
    print(f"      Status: {'✅ PASSED' if validation['is_accurate'] else '❌ FAILED'}")

async def test_complete_workflow():
    """Полный тест workflow с исправлениями."""
    logger.info("🔍 TESTING: Complete fixed workflow")
    
    print("🔄 Testing complete data processing workflow:")
    
    # Создаем комплексные тестовые данные
    test_warehouse_data = [
        {
            "nmId": 11111,
            "vendorCode": "CRITICAL-TEST-1",
            "warehouses": [
                {"warehouseName": "Самара (Новосемейкино)", "quantity": 100},
                {"warehouseName": "Чехов 1", "quantity": 200},
                {"warehouseName": "Маркетплейс", "quantity": 50}
            ]
        }
    ]
    
    test_orders_data = [
        # Обычные заказы
        {"nmId": 11111, "supplierArticle": "CRITICAL-TEST-1", "warehouseName": "Новосемейкино", "warehouseType": "Склад WB", "isCancel": False},
        {"nmId": 11111, "supplierArticle": "CRITICAL-TEST-1", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
        {"nmId": 11111, "supplierArticle": "CRITICAL-TEST-1", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
        # FBS заказы
        {"nmId": 11111, "supplierArticle": "CRITICAL-TEST-1", "warehouseName": "Маркетплейс", "warehouseType": "Склад продавца", "isCancel": False},
        # Отмененные заказы (должны игнорироваться)
        {"nmId": 11111, "supplierArticle": "CRITICAL-TEST-1", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": True}
    ]
    
    # Обрабатываем данные полным циклом
    grouped_data = WildberriesCalculator.group_data_by_product(
        test_warehouse_data, test_orders_data
    )
    
    products = WildberriesCalculator.create_products_from_grouped_data(grouped_data)
    
    # Анализируем результаты
    for product in products:
        print(f"   📦 Product: {product.seller_article} (nmId: {product.wildberries_article})")
        print(f"      Total stock: {product.total_stock}")
        print(f"      Total orders: {product.total_orders}")
        print(f"      Turnover: {product.turnover:.3f}")
        
        marketplace_found = False
        normalization_working = False
        
        for warehouse in product.warehouses:
            # Проверяем нормализацию названий
            if "новосемейкино" in warehouse.name.lower():
                normalization_working = True
                print(f"         ✅ Normalization: '{warehouse.name}' detected")
            
            # Проверяем включение Маркетплейс
            if "маркетплейс" in warehouse.name.lower():
                marketplace_found = True
                print(f"         ✅ Marketplace: '{warehouse.name}' included (stock: {warehouse.stock}, orders: {warehouse.orders})")
            else:
                print(f"         🏢 Regular: '{warehouse.name}' (stock: {warehouse.stock}, orders: {warehouse.orders})")
        
        print(f"      📊 Critical checks:")
        print(f"         Marketplace included: {'✅' if marketplace_found else '❌'}")
        print(f"         Name normalization: {'✅' if normalization_working else '❌'}")
        print(f"         Total stock > 0: {'✅' if product.total_stock > 0 else '❌'}")
        print(f"         Total orders > 0: {'✅' if product.total_orders > 0 else '❌'}")

async def main():
    """Запуск всех диагностических проверок."""
    setup_logging()
    
    print("🚨 CRITICAL ISSUES DIAGNOSIS - STOCK TRACKER")
    print("=" * 60)
    print("Проверка исправлений критических проблем:")
    print("1. Полное игнорирование склада 'Маркетплейс'")
    print("2. Ошибки в распределении заказов по складам")  
    print("3. Дублирование из-за разных названий складов")
    print("4. Неправильный подсчет FBS товаров")
    print("=" * 60)
    
    try:
        print("\n🔍 PHASE 1: Marketplace warehouse detection")
        await diagnose_marketplace_warehouse_issue()
        
        print("\n🔍 PHASE 2: Orders accuracy validation")
        await diagnose_orders_accuracy_issue()
        
        print("\n🔍 PHASE 3: Warehouse name mapping")
        await diagnose_warehouse_name_mapping()
        
        print("\n🔍 PHASE 4: FBS warehouse inclusion")
        await diagnose_fbs_warehouse_inclusion()
        
        print("\n🔍 PHASE 5: Critical accuracy test case")
        await run_critical_accuracy_test()
        
        print("\n🔍 PHASE 6: Complete workflow test")
        await test_complete_workflow()
        
        print("\n" + "=" * 60)
        print("✅ ALL DIAGNOSTIC PHASES COMPLETED")
        print("📋 Review results above to verify all critical fixes are working")
        print("🎯 Expected outcomes:")
        print("   - Marketplace warehouses are included ✅")
        print("   - Orders accuracy is 100% ✅") 
        print("   - Warehouse names are normalized ✅")
        print("   - FBS warehouses are processed ✅")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        print(f"\n❌ DIAGNOSTIC ERROR: {e}")
        print("🔧 Please check the implementation and try again")

if __name__ == "__main__":
    asyncio.run(main())