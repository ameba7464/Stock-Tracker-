#!/usr/bin/env python3
"""
Комплексное тестирование критических исправлений.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.core.calculator import (
    is_real_warehouse, 
    WildberriesCalculator,
)
from stock_tracker.utils.warehouse_mapper import (
    normalize_warehouse_name,
    is_marketplace_warehouse,
    validate_warehouse_mapping
)

class TestCriticalFixes(unittest.TestCase):
    
    def test_marketplace_warehouse_inclusion(self):
        """Тест включения склада Маркетплейс."""
        
        marketplace_names = [
            "Маркетплейс",
            "маркетплейс",
            "Marketplace",
            "Склад продавца",
            "МП-1"
        ]
        
        for name in marketplace_names:
            with self.subTest(warehouse_name=name):
                self.assertTrue(
                    is_real_warehouse(name),
                    f"Warehouse '{name}' should be included"
                )
                self.assertTrue(
                    is_marketplace_warehouse(name),
                    f"Warehouse '{name}' should be detected as marketplace"
                )
    
    def test_fbs_warehouse_detection(self):
        """Тест определения FBS складов."""
        
        fbs_cases = [
            ("Маркетплейс", "Склад продавца", True),
            ("Склад продавца", "Склад продавца", True),
            ("Чехов 1", "Склад WB", False),
            ("Подольск", "Склад WB", False),
            ("Обычный склад", "Склад WB", False)
        ]
        
        for name, warehouse_type, expected in fbs_cases:
            with self.subTest(name=name, type=warehouse_type):
                result = WildberriesCalculator.is_fbs_warehouse(name, warehouse_type)
                self.assertEqual(
                    result, expected,
                    f"FBS detection failed for '{name}' (type: '{warehouse_type}')"
                )
    
    def test_warehouse_name_normalization(self):
        """Тест нормализации названий складов."""
        
        normalization_cases = [
            ("Самара (Новосемейкино)", "Новосемейкино"),
            ("Чехов 1", "Чехов"),
            ("Чехов-1", "Чехов"),
            ("Склад продавца", "Маркетплейс"),
            ("Маркетплейс", "Маркетплейс")
        ]
        
        for input_name, expected in normalization_cases:
            with self.subTest(input=input_name):
                result = normalize_warehouse_name(input_name)
                self.assertEqual(
                    result, expected,
                    f"Normalization failed: '{input_name}' -> '{result}' (expected: '{expected}')"
                )
    
    def test_orders_calculation_accuracy(self):
        """Тест точности подсчета заказов."""
        
        # Мок данные для тестирования
        mock_orders = [
            {"nmId": 12345, "warehouseName": "Чехов 1", "isCancel": False},
            {"nmId": 12345, "warehouseName": "Чехов 1", "isCancel": False},
            {"nmId": 12345, "warehouseName": "Чехов 1", "isCancel": True},  # Отменен - не считается
            {"nmId": 67890, "warehouseName": "Чехов 1", "isCancel": False}  # Другой товар
        ]
        
        # Тест для nmId 12345, склад "Чехов 1"
        result = WildberriesCalculator.calculate_warehouse_orders(
            mock_orders, 12345, "Чехов 1"
        )
        
        self.assertEqual(
            result, 2,  # Только 2 неотмененных заказа
            f"Expected 2 orders for Чехов 1, got {result}"
        )
        
        # Тест валидации точности
        calculated_breakdown = {"Чехов 1": 2}
        validation = WildberriesCalculator.validate_warehouse_orders_accuracy(
            mock_orders, 12345, calculated_breakdown
        )
        
        self.assertTrue(
            validation["is_accurate"],
            f"Validation should pass: {validation}"
        )
        self.assertEqual(
            validation["accuracy_percent"], 100.0,
            f"Accuracy should be 100%, got {validation['accuracy_percent']}%"
        )

    def test_critical_case_its1_2_3(self):
        """Тест конкретного критического случая Its1_2_3/50g."""
        
        # Воспроизводим проблемный случай из документации
        mock_nm_id = 999888777  # Симуляция Its1_2_3/50g
        target_warehouse = "Чехов 1"
        expected_orders = 5
        
        # Создаем корректные данные: 5 заказов + 3 отмененных
        orders_data = []
        
        # 5 валидных заказов
        for i in range(expected_orders):
            orders_data.append({
                "nmId": mock_nm_id,
                "warehouseName": target_warehouse,
                "isCancel": False,
                "date": f"2025-10-{20+i}"
            })
        
        # 3 отмененных заказа (не должны считаться)
        for i in range(3):
            orders_data.append({
                "nmId": mock_nm_id,
                "warehouseName": target_warehouse,
                "isCancel": True,
                "date": f"2025-10-{15+i}"
            })
        
        # Тестируем исправленный алгоритм
        result = WildberriesCalculator.calculate_warehouse_orders(
            orders_data, mock_nm_id, target_warehouse
        )
        
        self.assertEqual(
            result, expected_orders,
            f"Critical case failed: expected {expected_orders} orders, got {result}"
        )

    def test_fbs_data_processing_workflow(self):
        """Тест полного цикла обработки данных с FBS складами."""
        
        # Тестовые данные с FBS складами
        warehouse_data = [
            {
                "nmId": 11111,
                "vendorCode": "FBS-TEST",
                "warehouses": [
                    {"warehouseName": "Чехов 1", "quantity": 100},
                    {"warehouseName": "Маркетплейс", "quantity": 50}
                ]
            }
        ]
        
        orders_data = [
            {"nmId": 11111, "supplierArticle": "FBS-TEST", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
            {"nmId": 11111, "supplierArticle": "FBS-TEST", "warehouseName": "Маркетплейс", "warehouseType": "Склад продавца", "isCancel": False},
            {"nmId": 11111, "supplierArticle": "FBS-TEST", "warehouseName": "Маркетплейс", "warehouseType": "Склад продавца", "isCancel": False}
        ]
        
        # Обрабатываем данные
        grouped_data = WildberriesCalculator.group_data_by_product(
            warehouse_data, orders_data
        )
        
        # Проверяем результаты
        self.assertEqual(len(grouped_data), 1, "Should have 1 product")
        
        product_key = ("FBS-TEST", 11111)
        self.assertIn(product_key, grouped_data, "Product key should exist")
        
        product_data = grouped_data[product_key]
        
        # Проверяем общие итоги
        self.assertEqual(product_data["total_stock"], 150, "Total stock should be 150")
        self.assertEqual(product_data["total_orders"], 3, "Total orders should be 3")
        
        # Проверяем склады
        warehouses = product_data["warehouses"]
        self.assertIn("Чехов", warehouses, "Чехов warehouse should exist (normalized)")
        self.assertIn("Маркетплейс", warehouses, "Marketplace warehouse should exist")
        
        # Проверяем FBS пометки
        marketplace_wh = warehouses["Маркетплейс"]
        self.assertTrue(marketplace_wh.get("is_fbs", False), "Marketplace should be marked as FBS")
        self.assertEqual(marketplace_wh["orders"], 2, "Marketplace should have 2 orders")
        self.assertEqual(marketplace_wh["stock"], 50, "Marketplace should have 50 stock")

    def test_warehouse_mapping_validation(self):
        """Тест валидации сопоставления складов."""
        
        wb_names = ["Новосемейкино", "Чехов", "Маркетплейс"]
        st_names = ["Самара (Новосемейкино)", "Чехов 1", "Склад продавца"]
        
        validation = validate_warehouse_mapping(wb_names, st_names)
        
        # Все склады должны быть сопоставлены
        self.assertEqual(
            validation["accuracy_percent"], 100.0,
            f"Mapping accuracy should be 100%, got {validation['accuracy_percent']}%"
        )
        
        # Должны быть найдены соответствия для всех складов
        expected_matched = {"Новосемейкино", "Чехов", "Маркетплейс"}
        actual_matched = set(validation["matched_warehouses"])
        
        self.assertEqual(
            actual_matched, expected_matched,
            f"Matched warehouses mismatch: expected {expected_matched}, got {actual_matched}"
        )

    def test_canceled_orders_exclusion(self):
        """Тест исключения отмененных заказов."""
        
        mock_orders = [
            {"nmId": 12345, "supplierArticle": "TEST", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
            {"nmId": 12345, "supplierArticle": "TEST", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": False},
            {"nmId": 12345, "supplierArticle": "TEST", "warehouseName": "Чехов 1", "warehouseType": "Склад WB", "isCancel": True},  # Отменен
            {"nmId": 12345, "supplierArticle": "TEST", "warehouseName": "Маркетплейс", "warehouseType": "Склад продавца", "isCancel": True}  # Отменен FBS
        ]
        
        warehouse_data = [
            {
                "nmId": 12345,
                "vendorCode": "TEST",
                "warehouses": [
                    {"warehouseName": "Чехов 1", "quantity": 100},
                    {"warehouseName": "Маркетплейс", "quantity": 50}
                ]
            }
        ]
        
        grouped_data = WildberriesCalculator.group_data_by_product(
            warehouse_data, mock_orders
        )
        
        product_data = grouped_data[("TEST", 12345)]
        
        # Должно быть только 2 заказа (отмененные исключены)
        self.assertEqual(
            product_data["total_orders"], 2,
            f"Should have 2 orders (canceled excluded), got {product_data['total_orders']}"
        )
        
        # Чехов должен иметь 2 заказа
        self.assertEqual(
            product_data["warehouses"]["Чехов"]["orders"], 2,
            "Чехов should have 2 orders"
        )
        
        # Маркетплейс должен иметь 0 заказов (отменен)
        self.assertEqual(
            product_data["warehouses"]["Маркетплейс"]["orders"], 0,
            "Marketplace should have 0 orders (canceled)"
        )


if __name__ == "__main__":
    print("🧪 Running comprehensive critical fixes tests...")
    unittest.main(verbosity=2)