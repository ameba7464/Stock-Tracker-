# 🔧 ПРОМПТ ДЛЯ ИСПРАВЛЕНИЯ ПРОБЛЕМ СО СКЛАДАМИ В WILDBERRIES STOCK TRACKER

**Дата создания**: 23 октября 2025 г.  
**Статус**: Требует реализации  
**Приоритет**: Высокий  

## 🎯 АНАЛИЗ ТЕКУЩИХ ПРОБЛЕМ

### Проблема 1: Отсутствуют склады продавца (МП)
**Описание**: Приложение учитывает остатки только на складах WB, но не учитывает остатки на складах Селлера (МП). В графу "Название склада" должны подгружаться склады селлера.

**Техническая причина**: 
- В `urls.md` API `/supplier/orders` содержит поле `warehouseType` с возможными значениями:
  - `"Склад WB"`
  - `"Склад продавца"`
- В коде фильтрации складов (`src/stock_tracker/core/calculator.py`) нет логики для различения и включения складов продавца
- Функция `is_real_warehouse()` не учитывает склады МП

**Затронутые файлы**:
- `src/stock_tracker/core/calculator.py`
- `src/stock_tracker/api/products.py`
- `src/stock_tracker/api/warehouses.py`

### Проблема 2: Отсутствуют склады с нулевыми остатками
**Описание**: Если на складе 0 остатков, но за текущий период есть заказы, то приложение все равно не пишет этот склад в названия.

**Техническая причина**: 
- API `/warehouse_remains` возвращает только склады с `quantity > 0` (согласно `urls.md`: "Будут в ответе только при ненулевом quantity")
- Заказы могут быть со складов с нулевыми остатками
- Логика `group_data_by_product()` не создает записи складов для заказов при отсутствии остатков

**Затронутые файлы**:
- `src/stock_tracker/core/calculator.py` (функция `group_data_by_product`)
- `src/stock_tracker/api/warehouses.py`

### Проблема 3: Неточный подсчет заказов
**Описание**: "Заказы (всего)" и "Заказы со склада" не соответствуют действительности. 

**Примеры расхождений**:
- Артикул 163383326: WB показывает 98 заказов всего, а таблица 108
- Котовск по этому артикулу: WB показывает 18 заказов, а таблица 27

**Возможные технические причины**:
1. Ошибки в логике подсчета в `calculate_total_orders()` и `calculate_warehouse_orders()`
2. Неправильная фильтрация периода (`dateFrom` параметр)
3. Различие в логике группировки WB и приложения
4. Включение/исключение отмененных заказов (`isCancel` поле)
5. Различная обработка `warehouseType`

**Затронутые файлы**:
- `src/stock_tracker/core/calculator.py`
- `src/stock_tracker/api/products.py`

## ✅ ТРЕБУЕМЫЕ ИСПРАВЛЕНИЯ

### 1. Добавить поддержку складов продавца (МП)

#### 1.1. Обновить функцию фильтрации складов

**Файл**: `src/stock_tracker/core/calculator.py`

**Изменить функцию** `is_real_warehouse()`:

```python
def is_real_warehouse(warehouse_name: str) -> bool:
    """Проверить что это реальный склад, а не статус."""
    if not warehouse_name or not isinstance(warehouse_name, str):
        return False
    
    # Исключаем статусы доставки
    if warehouse_name in DELIVERY_STATUSES:
        return False
        
    # Исключаем итоговые строки
    if any(word in warehouse_name.lower() for word in ["итог", "всего", "общий"]):
        return False
        
    # Исключаем строки "в пути"
    if "в пути" in warehouse_name.lower():
        return False
    
    # ДОБАВИТЬ: Поддержка складов продавца (МП)
    # Склады продавца имеют типичные названия
    mp_indicators = ["мп", "маркетплейс", "склад продавца", "сп ", "sp "]
    warehouse_name_lower = warehouse_name.lower()
    
    # Если это склад МП - точно включаем
    if any(indicator in warehouse_name_lower for indicator in mp_indicators):
        logger.debug(f"Identified MP warehouse: {warehouse_name}")
        return True
    
    # Остальная логика для обычных складов
    return True
```

#### 1.2. Добавить обработку warehouseType в группировке заказов

**Файл**: `src/stock_tracker/core/calculator.py`

**Изменить функцию** `group_data_by_product()` в части обработки заказов:

```python
# Process orders data to count orders per warehouse and total
for order in orders_data:
    nm_id = order.get("nmId")
    supplier_article = order.get("supplierArticle", "")
    warehouse_name = order.get("warehouseName", "")
    warehouse_type = order.get("warehouseType")  # НОВОЕ ПОЛЕ
    
    if nm_id and supplier_article:
        key = (supplier_article, nm_id)
        group = grouped_data[key]
        group["supplier_article"] = supplier_article
        group["nm_id"] = nm_id
        
        # Count total orders
        group["total_orders"] += 1
        
        # Count orders per warehouse
        if warehouse_name:
            # ИСПРАВЛЕНИЕ: Включаем склады продавца
            # Проверяем тип склада из API
            is_valid_warehouse_type = (
                warehouse_type in ["Склад WB", "Склад продавца"] or 
                warehouse_type is None  # Для совместимости со старыми данными
            )
            
            if is_valid_warehouse_type and is_real_warehouse(warehouse_name) and validate_warehouse_name(warehouse_name):
                # СОЗДАЕМ СКЛАД ЕСЛИ ЕГО НЕТ (для случаев с нулевыми остатками)
                if warehouse_name not in group["warehouses"]:
                    group["warehouses"][warehouse_name] = {
                        "stock": 0,  # Остатки = 0, будут обновлены из warehouse_remains
                        "orders": 0,
                        "warehouse_type": warehouse_type  # Сохраняем тип склада
                    }
                    logger.debug(f"Created warehouse entry for zero-stock warehouse: {warehouse_name} (type: {warehouse_type})")
                
                group["warehouses"][warehouse_name]["orders"] += 1
            else:
                logger.debug(f"Filtered out order warehouse: {warehouse_name} (type: {warehouse_type})")
```

#### 1.3. Обновить обработку в warehouse_remains

**Файл**: `src/stock_tracker/core/calculator.py`

**Изменить функцию** `group_data_by_product()` в части обработки остатков:

```python
# Process warehouse remains data
for item in warehouse_remains_data:
    nm_id = item.get("nmId")
    # vendorCode is supplierArticle in warehouse_remains response
    supplier_article = item.get("vendorCode", "")
    
    if nm_id and supplier_article:
        key = (supplier_article, nm_id)
        group = grouped_data[key]
        group["supplier_article"] = supplier_article
        group["nm_id"] = nm_id
        
        # Process warehouses
        if "warehouses" in item:
            for warehouse in item["warehouses"]:
                warehouse_name = warehouse.get("warehouseName", "")
                quantity = warehouse.get("quantity", 0)
                
                # ИСПРАВЛЕНИЕ: Применяем расширенную фильтрацию
                if warehouse_name and is_real_warehouse(warehouse_name):
                    if validate_warehouse_name(warehouse_name):
                        # Создаем или обновляем склад
                        if warehouse_name not in group["warehouses"]:
                            group["warehouses"][warehouse_name] = {
                                "stock": 0,
                                "orders": 0,
                                "warehouse_type": "unknown"  # Будет обновлен из orders если есть
                            }
                        
                        # Обновляем остатки
                        group["warehouses"][warehouse_name]["stock"] += quantity
                        logger.debug(f"Updated warehouse stock: {warehouse_name} += {quantity}")
                    else:
                        logger.warning(f"Invalid warehouse name format: {warehouse_name}")
                else:
                    logger.debug(f"Filtered out warehouse remains: {warehouse_name}")
```

### 2. Включить склады с нулевыми остатками но с заказами

Логика уже добавлена в пункте 1.2 выше через создание записей складов при обработке заказов:

```python
# СОЗДАЕМ СКЛАД ЕСЛИ ЕГО НЕТ (для случаев с нулевыми остатками)
if warehouse_name not in group["warehouses"]:
    group["warehouses"][warehouse_name] = {
        "stock": 0,  # Остатки = 0
        "orders": 0,
        "warehouse_type": warehouse_type
    }
```

### 3. Исправить подсчет заказов

#### 3.1. Добавить функцию с детальной диагностикой

**Файл**: `src/stock_tracker/core/calculator.py`

**Добавить новые методы**:

```python
@staticmethod
def calculate_total_orders_with_debug(orders_data: List[Dict[str, Any]], nm_id: int) -> Tuple[int, Dict[str, Any]]:
    """
    Calculate total orders for product with detailed debugging.
    
    Args:
        orders_data: Data from /supplier/orders API
        nm_id: Product nmId to calculate for
        
    Returns:
        Tuple of (order_count, debug_info)
    """
    order_count = 0
    debug_info = {
        "nm_id": nm_id,
        "total_records_checked": len(orders_data),
        "matching_records": [],
        "filtered_out": [],
        "warehouse_breakdown": {},
        "warehouse_type_breakdown": {}
    }
    
    for i, order in enumerate(orders_data):
        order_nm_id = order.get("nmId")
        warehouse_name = order.get("warehouseName", "")
        warehouse_type = order.get("warehouseType", "Unknown")
        is_canceled = order.get("isCancel", False)
        order_date = order.get("date", "")
        
        if order_nm_id == nm_id:
            # Детальная диагностика каждого заказа
            order_info = {
                "warehouse": warehouse_name,
                "type": warehouse_type,
                "canceled": is_canceled,
                "date": order_date,
                "index": i
            }
            
            # Проверяем фильтры как в WB
            if is_canceled:
                debug_info["filtered_out"].append({
                    **order_info,
                    "reason": "canceled_order"
                })
                continue
            
            # Фильтр по типу склада (включаем WB и МП)
            if warehouse_type not in ["Склад WB", "Склад продавца"] and warehouse_type != "":
                debug_info["filtered_out"].append({
                    **order_info,
                    "reason": f"unknown_warehouse_type: {warehouse_type}"
                })
                continue
            
            # Фильтр по названию склада
            if not is_real_warehouse(warehouse_name):
                debug_info["filtered_out"].append({
                    **order_info,
                    "reason": f"invalid_warehouse_name: {warehouse_name}"
                })
                continue
            
            # Валидный заказ - считаем
            order_count += 1
            debug_info["matching_records"].append(order_info)
            
            # Группировка по складам
            if warehouse_name not in debug_info["warehouse_breakdown"]:
                debug_info["warehouse_breakdown"][warehouse_name] = 0
            debug_info["warehouse_breakdown"][warehouse_name] += 1
            
            # Группировка по типам складов
            if warehouse_type not in debug_info["warehouse_type_breakdown"]:
                debug_info["warehouse_type_breakdown"][warehouse_type] = 0
            debug_info["warehouse_type_breakdown"][warehouse_type] += 1
    
    debug_info["total_orders_calculated"] = order_count
    debug_info["wb_warehouses"] = sum(count for wh, count in debug_info["warehouse_breakdown"].items() 
                                     if not any(mp in wh.lower() for mp in ["мп", "маркетплейс", "склад продавца"]))
    debug_info["mp_warehouses"] = debug_info["total_orders_calculated"] - debug_info["wb_warehouses"]
    
    logger.info(f"🔍 DEBUG orders for nmId {nm_id}:")
    logger.info(f"   Total API records: {debug_info['total_records_checked']}")
    logger.info(f"   Matching orders: {order_count}")
    logger.info(f"   - WB warehouses: {debug_info['wb_warehouses']}")
    logger.info(f"   - MP warehouses: {debug_info['mp_warehouses']}")
    logger.info(f"   Warehouse breakdown: {debug_info['warehouse_breakdown']}")
    logger.info(f"   Type breakdown: {debug_info['warehouse_type_breakdown']}")
    logger.info(f"   Filtered out: {len(debug_info['filtered_out'])} records")
    
    return order_count, debug_info

@staticmethod
def validate_orders_calculation(nm_id: int, calculated_total: int, 
                              calculated_by_warehouse: Dict[str, int]) -> Dict[str, Any]:
    """
    Validate that warehouse orders sum equals total orders.
    
    Args:
        nm_id: Product nmId
        calculated_total: Total orders calculated
        calculated_by_warehouse: Orders per warehouse
        
    Returns:
        Validation report
    """
    warehouse_sum = sum(calculated_by_warehouse.values())
    is_valid = warehouse_sum == calculated_total
    
    validation = {
        "nm_id": nm_id,
        "calculated_total": calculated_total,
        "warehouse_sum": warehouse_sum,
        "difference": abs(warehouse_sum - calculated_total),
        "is_valid": is_valid,
        "warehouse_breakdown": calculated_by_warehouse
    }
    
    if not is_valid:
        logger.warning(f"⚠️ Orders validation failed for nmId {nm_id}:")
        logger.warning(f"   Total calculated: {calculated_total}")
        logger.warning(f"   Warehouse sum: {warehouse_sum}")
        logger.warning(f"   Difference: {validation['difference']}")
        logger.warning(f"   Warehouse breakdown: {calculated_by_warehouse}")
    else:
        logger.info(f"✅ Orders validation passed for nmId {nm_id}")
    
    return validation
```

#### 3.2. Добавить точную фильтрацию по дате

**Файл**: `src/stock_tracker/api/products.py`

**Добавить новый метод**:

```python
async def fetch_supplier_orders_precise(self, date_from: str, 
                                      date_to: Optional[str] = None,
                                      flag: int = 0,
                                      include_canceled: bool = False) -> List[Dict[str, Any]]:
    """
    Fetch supplier orders with precise date filtering to match WB logic.
    
    Args:
        date_from: Start date in RFC3339 format
        date_to: End date (optional, for range filtering)
        flag: Query flag (0 for incremental, 1 for full day data)
        include_canceled: Whether to include canceled orders (default: False like WB)
        
    Returns:
        List of order records filtered by date range and cancellation status
        
    Raises:
        APIError: If API request fails
        ValidationError: If parameters are invalid
    """
    try:
        logger.info(f"Fetching precise orders: {date_from} to {date_to or 'latest'}, "
                   f"include_canceled: {include_canceled}")
        
        # Get raw data from API
        response_data = await self.fetch_supplier_orders(date_from, flag)
        
        filtered_orders = []
        stats = {
            "raw_count": len(response_data),
            "canceled_filtered": 0,
            "date_filtered": 0,
            "final_count": 0
        }
        
        for order in response_data:
            # Filter canceled orders if required (matching WB logic)
            if not include_canceled and order.get("isCancel", False):
                stats["canceled_filtered"] += 1
                continue
            
            # Filter by date range if date_to provided
            if date_to:
                order_date = order.get("date", "")
                if order_date and order_date > date_to:
                    stats["date_filtered"] += 1
                    continue
            
            filtered_orders.append(order)
        
        stats["final_count"] = len(filtered_orders)
        
        logger.info(f"Orders filtering stats: {stats}")
        logger.info(f"   Raw from API: {stats['raw_count']}")
        logger.info(f"   Filtered canceled: {stats['canceled_filtered']}")
        logger.info(f"   Filtered by date: {stats['date_filtered']}")
        logger.info(f"   Final count: {stats['final_count']}")
        
        return filtered_orders
        
    except Exception as e:
        logger.error(f"Failed to fetch precise supplier orders: {e}")
        raise APIError(f"Precise orders fetch failed: {e}")
```

### 4. Создать инструменты верификации

#### 4.1. Создать модуль верификации расчетов

**Создать файл**: `src/stock_tracker/utils/calculation_verifier.py`

```python
"""
Verification utilities for validating calculation accuracy against WB data.

This module provides tools to verify that our calculations match the expected
results from Wildberries interface, helping to identify and fix discrepancies.
"""

from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import asyncio

from stock_tracker.utils.logger import get_logger
from stock_tracker.core.calculator import WildberriesCalculator

logger = get_logger(__name__)


class CalculationVerifier:
    """Verify calculation accuracy against expected WB results."""
    
    @staticmethod
    def verify_orders_accuracy(nm_id: int, 
                             our_calculation: Dict[str, Any],
                             expected_wb_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify orders calculation accuracy against WB interface data.
        
        Args:
            nm_id: Product nmId being verified
            our_calculation: Our calculated results
            expected_wb_data: Expected results from WB interface
            
        Returns:
            Detailed verification report
        """
        verification = {
            "nm_id": nm_id,
            "timestamp": datetime.now().isoformat(),
            "total_orders": {
                "our_result": our_calculation.get("total_orders", 0),
                "wb_expected": expected_wb_data.get("total_orders", 0),
                "difference": 0,
                "match": False,
                "accuracy_percent": 0.0
            },
            "warehouse_orders": {},
            "overall_accuracy": 0.0,
            "issues_found": [],
            "recommendations": []
        }
        
        # Verify total orders
        our_total = our_calculation.get("total_orders", 0)
        wb_total = expected_wb_data.get("total_orders", 0)
        verification["total_orders"]["difference"] = abs(our_total - wb_total)
        verification["total_orders"]["match"] = our_total == wb_total
        
        if wb_total > 0:
            verification["total_orders"]["accuracy_percent"] = (
                min(our_total, wb_total) / max(our_total, wb_total) * 100
            )
        
        if not verification["total_orders"]["match"]:
            verification["issues_found"].append(
                f"Total orders mismatch: calculated {our_total}, expected {wb_total} "
                f"(difference: {verification['total_orders']['difference']})"
            )
            
            if our_total > wb_total:
                verification["recommendations"].append(
                    "Our calculation is higher - check for duplicate counting or incorrect filtering"
                )
            else:
                verification["recommendations"].append(
                    "Our calculation is lower - check for missing warehouse types or date filtering"
                )
        
        # Verify warehouse-level orders
        our_warehouses = our_calculation.get("warehouse_breakdown", {})
        wb_warehouses = expected_wb_data.get("warehouse_breakdown", {})
        
        all_warehouses = set(our_warehouses.keys()) | set(wb_warehouses.keys())
        
        for warehouse in all_warehouses:
            our_count = our_warehouses.get(warehouse, 0)
            wb_count = wb_warehouses.get(warehouse, 0)
            
            warehouse_accuracy = 0.0
            if max(our_count, wb_count) > 0:
                warehouse_accuracy = min(our_count, wb_count) / max(our_count, wb_count) * 100
            
            verification["warehouse_orders"][warehouse] = {
                "our_result": our_count,
                "wb_expected": wb_count,
                "difference": abs(our_count - wb_count),
                "match": our_count == wb_count,
                "accuracy_percent": warehouse_accuracy
            }
            
            if our_count != wb_count:
                verification["issues_found"].append(
                    f"Warehouse {warehouse}: calculated {our_count}, expected {wb_count} "
                    f"(difference: {abs(our_count - wb_count)})"
                )
        
        # Calculate overall accuracy
        total_matches = sum(1 for result in verification["warehouse_orders"].values() if result["match"])
        total_matches += 1 if verification["total_orders"]["match"] else 0
        total_checks = len(verification["warehouse_orders"]) + 1
        
        verification["overall_accuracy"] = (total_matches / total_checks) * 100 if total_checks > 0 else 0
        
        logger.info(f"Verification for nmId {nm_id}: {verification['overall_accuracy']:.1f}% accurate")
        
        return verification
    
    @staticmethod
    def create_verification_report(verifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create comprehensive verification report for multiple products.
        
        Args:
            verifications: List of verification results
            
        Returns:
            Comprehensive report with statistics and recommendations
        """
        if not verifications:
            return {"error": "No verifications provided"}
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "products_verified": len(verifications),
            "overall_accuracy": 0.0,
            "accuracy_by_product": {},
            "common_issues": {},
            "accuracy_distribution": {"perfect": 0, "good": 0, "fair": 0, "poor": 0},
            "recommendations": [],
            "summary_statistics": {
                "total_orders_our": 0,
                "total_orders_wb": 0,
                "total_difference": 0
            }
        }
        
        total_accuracy = 0
        issue_counts = {}
        total_our = 0
        total_wb = 0
        
        for verification in verifications:
            nm_id = verification["nm_id"]
            accuracy = verification["overall_accuracy"]
            
            report["accuracy_by_product"][nm_id] = accuracy
            total_accuracy += accuracy
            
            # Accumulate totals
            total_our += verification["total_orders"]["our_result"]
            total_wb += verification["total_orders"]["wb_expected"]
            
            # Categorize accuracy
            if accuracy == 100:
                report["accuracy_distribution"]["perfect"] += 1
            elif accuracy >= 90:
                report["accuracy_distribution"]["good"] += 1
            elif accuracy >= 70:
                report["accuracy_distribution"]["fair"] += 1
            else:
                report["accuracy_distribution"]["poor"] += 1
            
            # Count issue types
            for issue in verification["issues_found"]:
                issue_type = issue.split(":")[0].strip()
                issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        report["overall_accuracy"] = total_accuracy / len(verifications)
        report["common_issues"] = {
            k: v for k, v in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        }
        
        # Summary statistics
        report["summary_statistics"] = {
            "total_orders_our": total_our,
            "total_orders_wb": total_wb,
            "total_difference": abs(total_our - total_wb),
            "overall_ratio": total_our / total_wb if total_wb > 0 else 0
        }
        
        # Generate recommendations
        if report["overall_accuracy"] < 90:
            report["recommendations"].append("Overall accuracy below 90% - investigate common issues")
        
        if report["accuracy_distribution"]["poor"] > 0:
            report["recommendations"].append(
                f"{report['accuracy_distribution']['poor']} products have poor accuracy (<70%) - priority fix needed"
            )
        
        most_common_issue = max(issue_counts.items(), key=lambda x: x[1]) if issue_counts else None
        if most_common_issue:
            report["recommendations"].append(
                f"Most common issue: {most_common_issue[0]} ({most_common_issue[1]} occurrences)"
            )
        
        return report
    
    @staticmethod
    def generate_test_cases(problematic_nm_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Generate test cases for known problematic products.
        
        Args:
            problematic_nm_ids: List of nmIds with known issues
            
        Returns:
            List of test case definitions
        """
        test_cases = []
        
        # Known problematic case from user report
        if 163383326 in problematic_nm_ids:
            test_cases.append({
                "nm_id": 163383326,
                "expected_wb_data": {
                    "total_orders": 98,  # According to user report
                    "warehouse_breakdown": {
                        "Котовск": 18  # According to user report
                    }
                },
                "test_description": "User reported discrepancy case",
                "priority": "high"
            })
        
        # Add generic test structure for other cases
        for nm_id in problematic_nm_ids:
            if nm_id != 163383326:  # Skip already added
                test_cases.append({
                    "nm_id": nm_id,
                    "expected_wb_data": {
                        "total_orders": None,  # To be filled manually
                        "warehouse_breakdown": {}
                    },
                    "test_description": f"Test case for nmId {nm_id}",
                    "priority": "medium"
                })
        
        return test_cases


class AccuracyMonitor:
    """Monitor calculation accuracy over time."""
    
    def __init__(self):
        self.verification_history = []
    
    def add_verification(self, verification: Dict[str, Any]) -> None:
        """Add verification result to history."""
        verification["recorded_at"] = datetime.now().isoformat()
        self.verification_history.append(verification)
    
    def get_accuracy_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get accuracy trend over specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_verifications = [
            v for v in self.verification_history 
            if datetime.fromisoformat(v["recorded_at"]) >= cutoff
        ]
        
        if not recent_verifications:
            return {"error": f"No verifications in last {days} days"}
        
        accuracies = [v["overall_accuracy"] for v in recent_verifications]
        
        return {
            "period_days": days,
            "verification_count": len(recent_verifications),
            "average_accuracy": sum(accuracies) / len(accuracies),
            "min_accuracy": min(accuracies),
            "max_accuracy": max(accuracies),
            "trend": "improving" if accuracies[-1] > accuracies[0] else "declining"
        }
```

### 5. Обновить основной процесс синхронизации

#### 5.1. Добавить использование новых методов в сервисе

**Файл**: `src/stock_tracker/services/product_service.py`

**Добавить новый метод**:

```python
async def sync_product_with_verification(self, seller_article: str, 
                                       wildberries_article: int,
                                       expected_wb_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Sync single product with calculation verification and detailed debugging.
    
    Args:
        seller_article: Product seller article
        wildberries_article: Product WB article (nmId)
        expected_wb_data: Expected WB data for verification (optional)
        
    Returns:
        Sync result with verification data and debugging info
    """
    try:
        logger.info(f"Starting verified sync for product {seller_article} (nmId: {wildberries_article})")
        
        # Fetch data with precise parameters (last 30 days, exclude canceled)
        orders_data, warehouse_data = await self.data_fetcher.fetch_product_data(
            seller_article=seller_article,
            wildberries_article=wildberries_article,
            orders_date_from=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        )
        
        # Use improved calculation with debugging
        calculator = WildberriesCalculator()
        
        # Calculate total orders with debugging
        total_orders, debug_info = calculator.calculate_total_orders_with_debug(
            orders_data, wildberries_article
        )
        
        # Calculate orders per warehouse
        warehouse_orders = {}
        for warehouse_name in debug_info["warehouse_breakdown"]:
            warehouse_orders[warehouse_name] = calculator.calculate_warehouse_orders(
                orders_data, wildberries_article, warehouse_name
            )
        
        # Validate calculation consistency
        validation = calculator.validate_orders_calculation(
            wildberries_article, total_orders, warehouse_orders
        )
        
        # Create product with corrected data
        product = Product(seller_article=seller_article, wildberries_article=wildberries_article)
        
        # Add warehouses including zero-stock ones with orders
        for warehouse_name, orders_count in warehouse_orders.items():
            stock = calculator.calculate_warehouse_stock(
                warehouse_data, wildberries_article, warehouse_name
            )
            warehouse = Warehouse(
                name=warehouse_name, 
                orders=orders_count, 
                stock=stock
            )
            product.add_warehouse(warehouse)
        
        # Perform verification if expected data provided
        verification_result = None
        if expected_wb_data:
            from stock_tracker.utils.calculation_verifier import CalculationVerifier
            
            our_calculation = {
                "total_orders": total_orders,
                "warehouse_breakdown": warehouse_orders
            }
            
            verification_result = CalculationVerifier.verify_orders_accuracy(
                wildberries_article, our_calculation, expected_wb_data
            )
        
        result = {
            "success": True,
            "product": product,
            "debug_info": debug_info,
            "validation": validation,
            "verification": verification_result,
            "calculated_totals": {
                "total_orders": total_orders,
                "warehouse_count": len(warehouse_orders),
                "total_stock": product.total_stock
            }
        }
        
        logger.info(f"✅ Verified sync completed for {seller_article}")
        logger.info(f"   Total orders: {total_orders}")
        logger.info(f"   Warehouses: {len(warehouse_orders)}")
        logger.info(f"   Validation: {'✅ PASSED' if validation['is_valid'] else '❌ FAILED'}")
        
        if verification_result:
            logger.info(f"   Verification accuracy: {verification_result['overall_accuracy']:.1f}%")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync product with verification: {e}")
        return {
            "success": False,
            "error": str(e),
            "product": None,
            "debug_info": None,
            "validation": None,
            "verification": None
        }
```

### 6. Создать инструмент диагностики конкретных артикулов

#### 6.1. Создать утилиту диагностики

**Создать файл**: `diagnose_article_issues.py`

```python
#!/usr/bin/env python3
"""
Диагностика проблем с конкретными артикулами.

Использование:
python diagnose_article_issues.py --nm-id 163383326 --expected-total 98 --expected-warehouse "Котовск:18"
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.api.products import WildberriesProductDataFetcher
from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.calculation_verifier import CalculationVerifier
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


async def diagnose_article(nm_id: int, expected_total: int = None, 
                         expected_warehouses: Dict[str, int] = None) -> Dict[str, Any]:
    """
    Проводит полную диагностику артикула для выявления проблем.
    
    Args:
        nm_id: Номер артикула WB
        expected_total: Ожидаемое общее количество заказов
        expected_warehouses: Ожидаемые заказы по складам
        
    Returns:
        Результат диагностики
    """
    try:
        logger.info(f"🔍 Starting diagnosis for nmId: {nm_id}")
        
        # Initialize API client
        config = get_config()
        wb_client = WildberriesAPIClient(config)
        data_fetcher = WildberriesProductDataFetcher(wb_client)
        
        # Fetch raw data
        logger.info("📥 Fetching raw data from APIs...")
        
        # Get orders for last 30 days
        from datetime import datetime, timedelta
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00")
        
        orders_data = await data_fetcher.fetch_supplier_orders(date_from, flag=0)
        warehouse_data = await data_fetcher.fetch_complete_warehouse_remains()
        
        logger.info(f"📊 Raw data fetched:")
        logger.info(f"   Orders: {len(orders_data)} records")
        logger.info(f"   Warehouse: {len(warehouse_data)} records")
        
        # Filter for specific nmId
        logger.info(f"🎯 Filtering for nmId {nm_id}...")
        
        relevant_orders = [order for order in orders_data if order.get("nmId") == nm_id]
        relevant_warehouse = [item for item in warehouse_data if item.get("nmId") == nm_id]
        
        logger.info(f"📋 Filtered data:")
        logger.info(f"   Orders for nmId: {len(relevant_orders)}")
        logger.info(f"   Warehouse for nmId: {len(relevant_warehouse)}")
        
        # Analyze orders in detail
        logger.info("🔍 Analyzing orders in detail...")
        
        calculator = WildberriesCalculator()
        total_orders, debug_info = calculator.calculate_total_orders_with_debug(
            orders_data, nm_id
        )
        
        # Calculate warehouse orders
        warehouse_orders = {}
        for warehouse_name in debug_info["warehouse_breakdown"]:
            warehouse_orders[warehouse_name] = calculator.calculate_warehouse_orders(
                orders_data, nm_id, warehouse_name
            )
        
        # Validate calculation
        validation = calculator.validate_orders_calculation(nm_id, total_orders, warehouse_orders)
        
        # Perform verification if expected data provided
        verification = None
        if expected_total is not None or expected_warehouses:
            expected_data = {
                "total_orders": expected_total,
                "warehouse_breakdown": expected_warehouses or {}
            }
            
            our_calculation = {
                "total_orders": total_orders,
                "warehouse_breakdown": warehouse_orders
            }
            
            verification = CalculationVerifier.verify_orders_accuracy(
                nm_id, our_calculation, expected_data
            )
        
        # Compile diagnosis result
        diagnosis = {
            "nm_id": nm_id,
            "timestamp": datetime.now().isoformat(),
            "raw_data": {
                "orders_count": len(orders_data),
                "warehouse_count": len(warehouse_data),
                "relevant_orders": len(relevant_orders),
                "relevant_warehouse": len(relevant_warehouse)
            },
            "calculation_results": {
                "total_orders": total_orders,
                "warehouse_orders": warehouse_orders,
                "debug_info": debug_info,
                "validation": validation
            },
            "verification": verification,
            "issues_detected": [],
            "recommendations": []
        }
        
        # Detect issues
        if not validation["is_valid"]:
            diagnosis["issues_detected"].append(
                f"Validation failed: warehouse sum ({validation['warehouse_sum']}) != "
                f"total ({validation['calculated_total']})"
            )
        
        if verification and verification["overall_accuracy"] < 100:
            diagnosis["issues_detected"].append(
                f"Accuracy issue: {verification['overall_accuracy']:.1f}% accuracy vs expected WB data"
            )
        
        # Generate recommendations
        if len(diagnosis["issues_detected"]) > 0:
            diagnosis["recommendations"].append("Review calculation logic for accuracy")
        
        if debug_info["filtered_out"]:
            diagnosis["recommendations"].append(
                f"Review {len(debug_info['filtered_out'])} filtered out records"
            )
        
        logger.info(f"✅ Diagnosis completed for nmId {nm_id}")
        return diagnosis
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed for nmId {nm_id}: {e}")
        return {
            "nm_id": nm_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def print_diagnosis_report(diagnosis: Dict[str, Any]) -> None:
    """Выводит отчет диагностики в читаемом формате."""
    
    nm_id = diagnosis["nm_id"]
    print(f"\n{'='*60}")
    print(f"🔍 DIAGNOSIS REPORT FOR nmId: {nm_id}")
    print(f"{'='*60}")
    
    if "error" in diagnosis:
        print(f"❌ ERROR: {diagnosis['error']}")
        return
    
    # Raw data info
    raw = diagnosis["raw_data"]
    print(f"\n📊 RAW DATA:")
    print(f"   Total orders in API: {raw['orders_count']}")
    print(f"   Total warehouse records: {raw['warehouse_count']}")
    print(f"   Orders for this nmId: {raw['relevant_orders']}")
    print(f"   Warehouse records for this nmId: {raw['relevant_warehouse']}")
    
    # Calculation results
    calc = diagnosis["calculation_results"]
    print(f"\n🧮 CALCULATION RESULTS:")
    print(f"   Total orders calculated: {calc['total_orders']}")
    print(f"   Warehouses found: {len(calc['warehouse_orders'])}")
    
    print(f"\n🏭 WAREHOUSE BREAKDOWN:")
    for warehouse, orders in calc["warehouse_orders"].items():
        print(f"   📦 {warehouse}: {orders} orders")
    
    # Debug info
    debug = calc["debug_info"]
    print(f"\n🔍 DEBUG INFO:")
    print(f"   Records checked: {debug['total_records_checked']}")
    print(f"   Matching records: {len(debug['matching_records'])}")
    print(f"   Filtered out: {len(debug['filtered_out'])}")
    print(f"   WB warehouses orders: {debug['wb_warehouses']}")
    print(f"   MP warehouses orders: {debug['mp_warehouses']}")
    
    if debug['filtered_out']:
        print(f"\n⚠️ FILTERED OUT RECORDS:")
        for record in debug['filtered_out'][:5]:  # Show first 5
            print(f"   - {record['reason']}: {record['warehouse']} (type: {record['type']})")
        if len(debug['filtered_out']) > 5:
            print(f"   ... and {len(debug['filtered_out']) - 5} more")
    
    # Validation
    validation = calc["validation"]
    print(f"\n✅ VALIDATION:")
    print(f"   Valid: {'✅ YES' if validation['is_valid'] else '❌ NO'}")
    print(f"   Total: {validation['calculated_total']}")
    print(f"   Warehouse sum: {validation['warehouse_sum']}")
    if not validation['is_valid']:
        print(f"   ⚠️ Difference: {validation['difference']}")
    
    # Verification
    if diagnosis["verification"]:
        verif = diagnosis["verification"]
        print(f"\n🎯 VERIFICATION vs EXPECTED:")
        print(f"   Overall accuracy: {verif['overall_accuracy']:.1f}%")
        
        total_check = verif["total_orders"]
        print(f"   Total orders: {total_check['our_result']} vs {total_check['wb_expected']} expected")
        if not total_check['match']:
            print(f"   ❌ Difference: {total_check['difference']}")
        
        if verif["warehouse_orders"]:
            print(f"   Warehouse comparison:")
            for wh, data in verif["warehouse_orders"].items():
                status = "✅" if data['match'] else "❌"
                print(f"     {status} {wh}: {data['our_result']} vs {data['wb_expected']} expected")
    
    # Issues and recommendations
    if diagnosis["issues_detected"]:
        print(f"\n❌ ISSUES DETECTED:")
        for issue in diagnosis["issues_detected"]:
            print(f"   - {issue}")
    
    if diagnosis["recommendations"]:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in diagnosis["recommendations"]:
            print(f"   - {rec}")
    
    print(f"\n{'='*60}")


async def main():
    """Main entry point for diagnosis tool."""
    parser = argparse.ArgumentParser(description="Diagnose article calculation issues")
    parser.add_argument("--nm-id", type=int, required=True, help="WB article ID (nmId)")
    parser.add_argument("--expected-total", type=int, help="Expected total orders")
    parser.add_argument("--expected-warehouse", action="append", 
                       help="Expected warehouse orders (format: 'WarehouseName:count')")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    import os
    os.environ["LOG_LEVEL"] = args.log_level
    setup_logging()
    
    # Parse expected warehouse data
    expected_warehouses = {}
    if args.expected_warehouse:
        for wh_spec in args.expected_warehouse:
            try:
                name, count = wh_spec.split(":")
                expected_warehouses[name.strip()] = int(count.strip())
            except ValueError:
                print(f"⚠️ Invalid warehouse spec: {wh_spec} (use 'WarehouseName:count')")
    
    # Run diagnosis
    try:
        diagnosis = await diagnose_article(
            nm_id=args.nm_id,
            expected_total=args.expected_total,
            expected_warehouses=expected_warehouses if expected_warehouses else None
        )
        
        print_diagnosis_report(diagnosis)
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
```

## 🚀 ПЛАН РЕАЛИЗАЦИИ

### Фаза 1: Основные исправления (Приоритет: Высокий)
1. ✅ Обновить `is_real_warehouse()` для поддержки складов МП
2. ✅ Модифицировать `group_data_by_product()` для включения складов с нулевыми остатками
3. ✅ Добавить обработку `warehouseType` в группировке заказов
4. ✅ Реализовать `calculate_total_orders_with_debug()` для диагностики

### Фаза 2: Верификация и диагностика (Приоритет: Средний)
1. ✅ Создать модуль `calculation_verifier.py`
2. ✅ Добавить `sync_product_with_verification()` в сервис
3. ✅ Создать утилиту `diagnose_article_issues.py`
4. ✅ Добавить точную фильтрацию дат в API

### Фаза 3: Тестирование (Приоритет: Высокий)
1. 🔄 Протестировать с артикулом 163383326
2. 🔄 Сравнить результаты с интерфейсом WB
3. 🔄 Проверить включение складов МП
4. 🔄 Валидировать склады с нулевыми остатками

## 📋 ТЕСТОВЫЕ СЦЕНАРИИ

### Тест 1: Склады продавца (МП)
```bash
# Проверить что склады с warehouseType="Склад продавца" включены
python diagnose_article_issues.py --nm-id [TEST_ID] --log-level DEBUG
```

### Тест 2: Склады с нулевыми остатками
```bash
# Проверить что склады с заказами но без остатков отображаются
# Ожидается: склады появляются в списке с stock=0, orders>0
```

### Тест 3: Точность подсчета заказов
```bash
# Проверить конкретный проблемный артикул
python diagnose_article_issues.py --nm-id 163383326 --expected-total 98 --expected-warehouse "Котовск:18"
```

## 📊 КРИТЕРИИ УСПЕХА

1. **Склады МП включены**: ✅ Склады с `warehouseType="Склад продавца"` появляются в таблице
2. **Нулевые остатки учтены**: ✅ Склады с заказами но нулевыми остатками отображаются
3. **Точность заказов**: ✅ Расхождения с WB интерфейсом устранены
4. **Артикул 163383326**: ✅ Показывает 98 заказов всего и 18 для Котовска

## 🔧 МОНИТОРИНГ И ПОДДЕРЖКА

После внедрения необходимо:

1. **Мониторинг точности**: Регулярная проверка соответствия с WB
2. **Логирование**: Детальные логи для диагностики проблем
3. **Алерты**: Уведомления при значительных расхождениях
4. **Обновления**: Адаптация при изменениях в API WB

---

**Статус**: 🔄 Готов к реализации  
**Последнее обновление**: 23 октября 2025 г.  
**Ответственный**: Development Team  