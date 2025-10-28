#!/usr/bin/env python3
"""
Тесты валидации для проверки точности данных Stock Tracker против WB файла
"""

import json
import csv
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class ValidationResult:
    """Результат валидации отдельного товара"""
    article: str
    nm_id: int
    wb_stock: int
    st_stock: int
    wb_orders: int
    st_orders: int
    stock_diff_percent: float
    orders_diff_percent: float
    stock_within_tolerance: bool
    orders_within_tolerance: bool
    warehouses_comparison: Dict[str, Any]

class StockTrackerValidator:
    """Валидатор точности данных Stock Tracker против WB"""
    
    def __init__(self, stock_tolerance: float = 10.0, orders_tolerance: float = 5.0):
        """
        Инициализация валидатора
        
        Args:
            stock_tolerance: Допустимое отклонение по остаткам в %
            orders_tolerance: Допустимое отклонение по заказам в %
        """
        self.stock_tolerance = stock_tolerance
        self.orders_tolerance = orders_tolerance
        
        # Критичные данные из WB файла
        self.wb_data = {
            "Its1_2_3/50g": {
                "total_orders": 103,  # Сумма всех заказов включая Маркетплейс
                "total_stock": 694,   # Сумма всех остатков включая Маркетплейс
                "marketplace": {
                    "orders": 5,
                    "stock": 144
                },
                "warehouses": {
                    "Электросталь": {"orders": 25, "stock": 1},
                    "Котовск": {"orders": 19, "stock": 97},
                    "Подольск 3": {"orders": 19, "stock": 4},
                    "Краснодар": {"orders": 13, "stock": 54},
                    "Рязань (Тюшевское)": {"orders": 12, "stock": 54},
                    "Маркетплейс": {"orders": 5, "stock": 144},
                    "Чехов 1": {"orders": 5, "stock": 193},
                    "Екатеринбург - Перспективный 12": {"orders": 2, "stock": 0},
                    "Казань": {"orders": 2, "stock": 0},
                    "Новосемейкино": {"orders": 1, "stock": 43}
                }
            },
            "ItsSport2/50g": {
                "total_orders": 39,   # Включая Маркетплейс
                "total_stock": 1258,  # Включая Маркетплейс (1033 + остальные)
                "marketplace": {
                    "orders": 1,
                    "stock": 1033
                },
                "warehouses": {
                    "Электросталь": {"orders": 12, "stock": 0},
                    "Подольск 3": {"orders": 8, "stock": 26},
                    "Краснодар": {"orders": 6, "stock": 8},
                    "Рязань (Тюшевское)": {"orders": 5, "stock": 31},
                    "Котовск": {"orders": 3, "stock": 35},
                    "Виртуальный Ленина 77": {"orders": 1, "stock": 0},
                    "Воронеж WB": {"orders": 1, "stock": 0},
                    "Казань": {"orders": 1, "stock": 0},
                    "Маркетплейс": {"orders": 1, "stock": 1033},
                    "Чехов 1": {"orders": 0, "stock": 86},
                    "Новосемейкино": {"orders": 0, "stock": 49}
                }
            },
            "Its2/50g": {
                "total_orders": 80,
                "total_stock": 571,
                "marketplace": {
                    "orders": 0,
                    "stock": 41
                },
                "warehouses": {
                    "Электросталь": {"orders": 25, "stock": 89},
                    "Краснодар": {"orders": 23, "stock": 39},
                    "Казань": {"orders": 10, "stock": 0},
                    "Котовск": {"orders": 10, "stock": 69},
                    "Рязань (Тюшевское)": {"orders": 5, "stock": 88},
                    "Подольск 3": {"orders": 3, "stock": 26},
                    "Новосемейкино": {"orders": 2, "stock": 0},
                    "Остальные": {"orders": 2, "stock": 0},
                    "Маркетплейс": {"orders": 0, "stock": 41},
                    "Чехов 1": {"orders": 0, "stock": 212}
                }
            }
        }
        
        # FBS товары (с расширением .FBS)
        self.fbs_articles = [
            "Its1_2_3/50g+Aks5/20g.FBS",
            "Its2/50g+Aks5/20g.FBS", 
            "ItsSport2/50g+Aks5/20g.FBS"
        ]
    
    def calculate_percentage_difference(self, expected: int, actual: int) -> float:
        """Рассчитать процентное отклонение"""
        if expected == 0 and actual == 0:
            return 0.0
        if expected == 0:
            return 100.0  # Если ожидали 0, а получили что-то
        
        return abs(expected - actual) / expected * 100.0
    
    def validate_product_data(self, article: str, st_data: Dict[str, Any]) -> ValidationResult:
        """
        Валидировать данные одного товара
        
        Args:
            article: Артикул товара
            st_data: Данные от Stock Tracker
            
        Returns:
            Результат валидации
        """
        # Получаем эталонные данные WB
        wb_product = self.wb_data.get(article, {})
        if not wb_product:
            # Для товаров не из эталонного списка создаем базовую проверку
            wb_product = {"total_orders": 0, "total_stock": 0, "warehouses": {}}
        
        wb_total_stock = wb_product.get("total_stock", 0)
        wb_total_orders = wb_product.get("total_orders", 0)
        
        st_total_stock = st_data.get("total_stock", 0)
        st_total_orders = st_data.get("total_orders", 0)
        
        # Рассчитываем отклонения
        stock_diff = self.calculate_percentage_difference(wb_total_stock, st_total_stock)
        orders_diff = self.calculate_percentage_difference(wb_total_orders, st_total_orders)
        
        # Проверяем допустимость отклонений
        stock_within_tolerance = stock_diff <= self.stock_tolerance
        orders_within_tolerance = orders_diff <= self.orders_tolerance
        
        # Сравнение по складам
        warehouses_comparison = self._compare_warehouse_breakdown(
            wb_product.get("warehouses", {}),
            st_data.get("warehouses", {})
        )
        
        return ValidationResult(
            article=article,
            nm_id=st_data.get("nm_id", 0),
            wb_stock=wb_total_stock,
            st_stock=st_total_stock,
            wb_orders=wb_total_orders,
            st_orders=st_total_orders,
            stock_diff_percent=stock_diff,
            orders_diff_percent=orders_diff,
            stock_within_tolerance=stock_within_tolerance,
            orders_within_tolerance=orders_within_tolerance,
            warehouses_comparison=warehouses_comparison
        )
    
    def _compare_warehouse_breakdown(self, wb_warehouses: Dict[str, Dict], 
                                   st_warehouses: Dict[str, Dict]) -> Dict[str, Any]:
        """Сравнить распределение по складам"""
        comparison = {
            "marketplace_included": False,
            "warehouse_count_wb": len(wb_warehouses),
            "warehouse_count_st": len(st_warehouses),
            "missing_warehouses": [],
            "extra_warehouses": [],
            "stock_mismatches": [],
            "orders_mismatches": []
        }
        
        # Проверяем включение Маркетплейс
        wb_marketplace = wb_warehouses.get("Маркетплейс", {})
        st_marketplace = None
        
        for wh_name, wh_data in st_warehouses.items():
            if "маркетплейс" in wh_name.lower() or wh_data.get("is_fbs", False):
                st_marketplace = wh_data
                comparison["marketplace_included"] = True
                break
        
        if wb_marketplace and not st_marketplace:
            comparison["missing_warehouses"].append("Маркетплейс")
        
        # Сравниваем остальные склады
        for wb_wh, wb_data in wb_warehouses.items():
            # Пропускаем Маркетплейс - уже проверили отдельно
            if wb_wh == "Маркетплейс":
                continue
                
            found_match = False
            for st_wh, st_data in st_warehouses.items():
                # Простое соответствие по началу названия
                if wb_wh.lower() in st_wh.lower() or st_wh.lower() in wb_wh.lower():
                    found_match = True
                    
                    # Проверяем отклонения
                    wb_stock = wb_data.get("stock", 0)
                    st_stock = st_data.get("stock", 0)
                    wb_orders = wb_data.get("orders", 0)
                    st_orders = st_data.get("orders", 0)
                    
                    stock_diff = self.calculate_percentage_difference(wb_stock, st_stock)
                    orders_diff = self.calculate_percentage_difference(wb_orders, st_orders)
                    
                    if stock_diff > self.stock_tolerance:
                        comparison["stock_mismatches"].append({
                            "warehouse": wb_wh,
                            "wb_stock": wb_stock,
                            "st_stock": st_stock,
                            "diff_percent": stock_diff
                        })
                    
                    if orders_diff > self.orders_tolerance:
                        comparison["orders_mismatches"].append({
                            "warehouse": wb_wh,
                            "wb_orders": wb_orders,
                            "st_orders": st_orders,
                            "diff_percent": orders_diff
                        })
                    break
            
            if not found_match:
                comparison["missing_warehouses"].append(wb_wh)
        
        return comparison
    
    def validate_fbs_inclusion(self, st_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Проверить что все FBS товары включены в данные
        
        Args:
            st_data: Данные от Stock Tracker
            
        Returns:
            Отчет о включении FBS товаров
        """
        st_articles = set(item.get("supplier_article", "") for item in st_data)
        
        fbs_included = []
        fbs_missing = []
        
        for fbs_article in self.fbs_articles:
            if fbs_article in st_articles:
                fbs_included.append(fbs_article)
            else:
                fbs_missing.append(fbs_article)
        
        # Проверяем наличие склада Маркетплейс у включенных FBS товаров
        fbs_with_marketplace = []
        fbs_without_marketplace = []
        
        for item in st_data:
            article = item.get("supplier_article", "")
            if article in self.fbs_articles:
                has_marketplace = False
                for wh_name, wh_data in item.get("warehouses", {}).items():
                    if wh_data.get("is_fbs", False) or "маркетплейс" in wh_name.lower():
                        has_marketplace = True
                        break
                
                if has_marketplace:
                    fbs_with_marketplace.append(article)
                else:
                    fbs_without_marketplace.append(article)
        
        return {
            "total_fbs_articles": len(self.fbs_articles),
            "fbs_included": fbs_included,
            "fbs_missing": fbs_missing,
            "fbs_with_marketplace": fbs_with_marketplace,
            "fbs_without_marketplace": fbs_without_marketplace,
            "inclusion_rate": len(fbs_included) / len(self.fbs_articles) * 100 if self.fbs_articles else 100,
            "marketplace_rate": len(fbs_with_marketplace) / len(fbs_included) * 100 if fbs_included else 0
        }
    
    def run_comprehensive_validation(self, st_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Запустить полную валидацию
        
        Args:
            st_data: Данные от Stock Tracker для валидации
            
        Returns:
            Полный отчет валидации
        """
        print("🔍 Starting comprehensive validation against WB data...")
        
        # Валидация по товарам
        product_results = []
        products_passed = 0
        products_failed = 0
        critical_failures = []
        
        for item in st_data:
            article = item.get("supplier_article", "")
            if article in self.wb_data:  # Проверяем только эталонные товары
                result = self.validate_product_data(article, item)
                product_results.append(result)
                
                if result.stock_within_tolerance and result.orders_within_tolerance:
                    products_passed += 1
                else:
                    products_failed += 1
                    
                    # Критичные ошибки
                    if (result.stock_diff_percent > 50 or 
                        result.orders_diff_percent > 20 or
                        not result.warehouses_comparison["marketplace_included"]):
                        critical_failures.append({
                            "article": article,
                            "issues": []
                        })
                        
                        if result.stock_diff_percent > 50:
                            critical_failures[-1]["issues"].append(f"Stock diff: {result.stock_diff_percent:.1f}%")
                        if result.orders_diff_percent > 20:
                            critical_failures[-1]["issues"].append(f"Orders diff: {result.orders_diff_percent:.1f}%")
                        if not result.warehouses_comparison["marketplace_included"]:
                            critical_failures[-1]["issues"].append("Marketplace missing")
        
        # Валидация FBS
        fbs_validation = self.validate_fbs_inclusion(st_data)
        
        # Общая статистика
        overall_stats = {
            "products_tested": len(product_results),
            "products_passed": products_passed,
            "products_failed": products_failed,
            "pass_rate": products_passed / len(product_results) * 100 if product_results else 0,
            "critical_failures": len(critical_failures),
            "stock_tolerance": self.stock_tolerance,
            "orders_tolerance": self.orders_tolerance
        }
        
        # Детальные результаты
        detailed_results = []
        for result in product_results:
            detailed_results.append({
                "article": result.article,
                "stock_diff_percent": round(result.stock_diff_percent, 2),
                "orders_diff_percent": round(result.orders_diff_percent, 2),
                "stock_within_tolerance": result.stock_within_tolerance,
                "orders_within_tolerance": result.orders_within_tolerance,
                "marketplace_included": result.warehouses_comparison["marketplace_included"],
                "wb_data": {"stock": result.wb_stock, "orders": result.wb_orders},
                "st_data": {"stock": result.st_stock, "orders": result.st_orders}
            })
        
        # Финальный отчет
        validation_report = {
            "validation_timestamp": "2025-10-25T00:00:00Z",
            "overall_stats": overall_stats,
            "fbs_validation": fbs_validation,
            "critical_failures": critical_failures,
            "detailed_results": detailed_results,
            "validation_criteria": {
                "stock_tolerance_percent": self.stock_tolerance,
                "orders_tolerance_percent": self.orders_tolerance,
                "required_marketplace_inclusion": True,
                "required_fbs_inclusion": True
            }
        }
        
        # Печать результатов
        self._print_validation_summary(validation_report)
        
        return validation_report
    
    def _print_validation_summary(self, report: Dict[str, Any]):
        """Вывести краткий отчет валидации"""
        stats = report["overall_stats"]
        fbs = report["fbs_validation"]
        
        print(f"\n📊 VALIDATION SUMMARY:")
        print(f"   Products tested: {stats['products_tested']}")
        print(f"   Pass rate: {stats['pass_rate']:.1f}%")
        print(f"   Passed: {stats['products_passed']}")
        print(f"   Failed: {stats['products_failed']}")
        print(f"   Critical failures: {stats['critical_failures']}")
        
        print(f"\n🏭 FBS VALIDATION:")
        print(f"   FBS inclusion rate: {fbs['inclusion_rate']:.1f}%")
        print(f"   FBS with marketplace: {fbs['marketplace_rate']:.1f}%")
        print(f"   Missing FBS: {fbs['fbs_missing']}")
        
        if report["critical_failures"]:
            print(f"\n❌ CRITICAL FAILURES:")
            for failure in report["critical_failures"]:
                print(f"   {failure['article']}: {', '.join(failure['issues'])}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for result in report["detailed_results"]:
            status = "✅" if (result["stock_within_tolerance"] and result["orders_within_tolerance"]) else "❌"
            mp_status = "✅" if result["marketplace_included"] else "❌ NO MP"
            print(f"   {status} {result['article']}: Stock {result['stock_diff_percent']:.1f}%, Orders {result['orders_diff_percent']:.1f}% {mp_status}")


def mock_stock_tracker_data() -> List[Dict[str, Any]]:
    """Создать моковые данные Stock Tracker для тестирования"""
    return [
        {
            "supplier_article": "Its1_2_3/50g",
            "nm_id": 163383326,
            "total_stock": 550,  # Должно быть 694 (без Маркетплейс)
            "total_orders": 98,  # Должно быть 103 (без Маркетплейс)
            "warehouses": {
                "Электросталь": {"stock": 1, "orders": 25, "is_fbs": False},
                "Котовск": {"stock": 97, "orders": 19, "is_fbs": False},
                "Подольск 3": {"stock": 4, "orders": 19, "is_fbs": False},
                "Краснодар": {"stock": 54, "orders": 13, "is_fbs": False},
                "Чехов 1": {"stock": 193, "orders": 5, "is_fbs": False}
                # ПРОБЛЕМА: Маркетплейс отсутствует!
            }
        },
        {
            "supplier_article": "ItsSport2/50g", 
            "nm_id": 163383328,
            "total_stock": 225,  # Должно быть 1258 (без Маркетплейс 1033!)
            "total_orders": 38,  # Должно быть 39 (без Маркетплейс 1)
            "warehouses": {
                "Электросталь": {"stock": 0, "orders": 12, "is_fbs": False},
                "Подольск 3": {"stock": 26, "orders": 8, "is_fbs": False},
                "Краснодар": {"stock": 8, "orders": 6, "is_fbs": False},
                "Рязань (Тюшевское)": {"stock": 31, "orders": 5, "is_fbs": False},
                "Котовск": {"stock": 35, "orders": 3, "is_fbs": False},
                "Чехов 1": {"stock": 86, "orders": 0, "is_fbs": False},
                "Новосемейкино": {"stock": 49, "orders": 0, "is_fbs": False}
                # КРИТИЧЕСКАЯ ПРОБЛЕМА: Маркетплейс с 1033 остатками отсутствует!
            }
        }
    ]


def test_validation_system():
    """Тестирование системы валидации"""
    print("🧪 Testing Stock Tracker validation system...")
    
    # Создаем валидатор
    validator = StockTrackerValidator(stock_tolerance=10.0, orders_tolerance=5.0)
    
    # Тестируем с моковыми данными (демонстрируют проблемы)
    mock_data = mock_stock_tracker_data()
    
    # Запускаем валидацию
    report = validator.run_comprehensive_validation(mock_data)
    
    # Сохраняем отчет
    with open('validation_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Validation report saved to 'validation_report.json'")
    
    # Проверяем что тесты выявили проблемы
    assert report["overall_stats"]["critical_failures"] > 0, "Validation should detect critical failures"
    assert report["fbs_validation"]["inclusion_rate"] < 100, "Should detect missing FBS articles"
    
    return report


if __name__ == "__main__":
    test_validation_system()