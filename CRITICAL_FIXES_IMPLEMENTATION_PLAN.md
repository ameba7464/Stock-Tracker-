# 📋 ДЕТАЛЬНЫЙ ПЛАН РЕАЛИЗАЦИИ КРИТИЧЕСКИХ ИСПРАВЛЕНИЙ

**Базовый документ**: STOCK_TRACKER_CRITICAL_FIXES_PROMPT.md  
**Дата создания**: 24 октября 2025 г.  
**Статус**: План к исполнению  

## 🎯 EXECUTIVE SUMMARY

На основании анализа расхождений с официальными данными Wildberries (18-24 октября 2025) выявлены **4 критические проблемы** в алгоритме Stock Tracker, которые требуют немедленного исправления:

1. **Полное игнорирование склада "Маркетплейс"** - потеря FBS данных
2. **Ошибки распределения заказов** - расхождения до -44 заказов 
3. **Дублирование из-за разных названий** - неточный учет
4. **Неправильный подсчет FBS остатков** - критичная потеря данных

## 📊 IMPACT ANALYSIS

### Влияние на бизнес:
- **Потеря доверия пользователей** из-за неточных данных
- **Неправильные бизнес-решения** на основе искаженной аналитики
- **Потеря конкурентного преимущества** перед другими решениями

### Технический долг:
- **Архитектурные недостатки** в алгоритмах фильтрации
- **Отсутствие нормализации данных**
- **Недостаточная валидация результатов**

## 🔧 ДЕТАЛЬНЫЙ ПЛАН ИСПРАВЛЕНИЙ

### PHASE 1: EMERGENCY FIXES (0-24 часа)

#### 1.1 ✅ Исправление игнорирования склада "Маркетплейс"

**Файлы к изменению:**
- `src/stock_tracker/core/calculator.py` (функция `is_real_warehouse`)
- `src/stock_tracker/core/calculator.py` (функция `group_data_by_product`)

**Конкретные изменения:**

1. **В функции `is_real_warehouse()`:**
```python
# КРИТИЧЕСКИ ВАЖНО: ОБЯЗАТЕЛЬНО включаем склад "Маркетплейс"
warehouse_name_lower = warehouse_name.lower()

# Точные индикаторы склада Маркетплейс (FBS)
marketplace_indicators = [
    "маркетплейс", "marketplace", 
    "склад продавца", "склад селлера", 
    "fbs", "fulfillment by seller",
    "мп ", "mp ", "сп "
]

# Если это склад Маркетплейс - ВСЕГДА включаем
if any(indicator in warehouse_name_lower for indicator in marketplace_indicators):
    logger.info(f"✅ CRITICAL: Marketplace warehouse INCLUDED: {warehouse_name}")
    return True

# НОВОЕ: Специальная проверка для точного названия "Маркетплейс"
if warehouse_name_lower.strip() == "маркетплейс":
    logger.info(f"✅ CRITICAL: Exact Marketplace warehouse INCLUDED: {warehouse_name}")
    return True
```

2. **В функции `group_data_by_product()`:**
```python
# КРИТИЧЕСКИ ВАЖНО: Обработка складов Маркетплейс
if warehouse_name:
    # Специальная обработка для FBS/Маркетплейс
    is_marketplace = (
        warehouse_type == "Склад продавца" or
        "маркетплейс" in warehouse_name.lower() or
        "marketplace" in warehouse_name.lower()
    )
    
    # ВСЕГДА включаем склады Маркетплейс
    if is_marketplace:
        logger.info(f"✅ FBS/Marketplace warehouse detected: {warehouse_name} (type: {warehouse_type})")
        
        if warehouse_name not in group["warehouses"]:
            group["warehouses"][warehouse_name] = {
                "stock": 0,
                "orders": 0,
                "warehouse_type": warehouse_type,
                "is_fbs": True  # Маркер FBS склада
            }
        
        group["warehouses"][warehouse_name]["orders"] += 1
```

**Тестирование:**
```bash
# Создать тестовый скрипт
python test_marketplace_fix.py --test-names "Маркетплейс,маркетплейс,Marketplace,Склад продавца"
```

#### 1.2 ✅ Исправление точности подсчета заказов

**Файлы к изменению:**
- `src/stock_tracker/core/calculator.py` (метод `calculate_warehouse_orders`)

**Новый метод валидации:**
```python
@staticmethod
def validate_warehouse_orders_accuracy(orders_data: List[Dict[str, Any]], 
                                     nm_id: int, 
                                     calculated_breakdown: Dict[str, int]) -> Dict[str, Any]:
    """Валидация точности распределения заказов по складам."""
    
    # Подсчет общего количества заказов для nmId
    total_orders_actual = sum(
        1 for order in orders_data 
        if order.get("nmId") == nm_id and not order.get("isCancel", False)
    )
    
    # Сумма заказов по складам
    total_orders_calculated = sum(calculated_breakdown.values())
    
    validation = {
        "nm_id": nm_id,
        "total_actual": total_orders_actual,
        "total_calculated": total_orders_calculated,
        "difference": abs(total_orders_actual - total_orders_calculated),
        "is_accurate": total_orders_actual == total_orders_calculated,
        "accuracy_percent": (min(total_orders_actual, total_orders_calculated) / 
                           max(total_orders_actual, total_orders_calculated) * 100) 
                           if max(total_orders_actual, total_orders_calculated) > 0 else 100,
        "warehouse_breakdown": calculated_breakdown
    }
    
    if not validation["is_accurate"]:
        logger.error(f"❌ ACCURACY ERROR for nmId {nm_id}:")
        logger.error(f"   Expected: {total_orders_actual} orders")
        logger.error(f"   Calculated: {total_orders_calculated} orders") 
        logger.error(f"   Difference: {validation['difference']}")
        logger.error(f"   Warehouse breakdown: {calculated_breakdown}")
    
    return validation
```

**Исправленный метод подсчета:**
```python
@staticmethod
def calculate_warehouse_orders(orders_data: List[Dict[str, Any]], 
                             nm_id: int, warehouse_name: str) -> int:
    """Calculate orders for specific warehouse with improved accuracy."""
    
    order_count = 0
    debug_matches = []
    
    for i, order in enumerate(orders_data):
        # Точное сопоставление
        order_nm_id = order.get("nmId")
        order_warehouse = order.get("warehouseName", "").strip()
        is_canceled = order.get("isCancel", False)
        
        # КРИТИЧЕСКИ ВАЖНО: Точное соответствие
        if (order_nm_id == nm_id and 
            order_warehouse == warehouse_name and 
            not is_canceled):
            
            order_count += 1
            debug_matches.append({
                "index": i,
                "date": order.get("date", ""),
                "warehouse_type": order.get("warehouseType", "")
            })
    
    logger.debug(f"Warehouse orders for nmId {nm_id}, warehouse '{warehouse_name}': {order_count}")
    logger.debug(f"Debug matches: {debug_matches[:3]}...")  # Показать первые 3
    
    return order_count
```

### PHASE 2: STRUCTURAL IMPROVEMENTS (24-48 часов)

#### 2.1 ✅ Создание модуля нормализации названий складов

**Создать файл:** `src/stock_tracker/utils/warehouse_mapper.py`

**Ключевые компоненты:**

1. **Справочник соответствий:**
```python
WAREHOUSE_NAME_MAPPINGS = {
    "Новосемейкино": ["Самара (Новосемейкино)", "Самара Новосемейкино", "Новосемейкино"],
    "Чехов": ["Чехов 1", "Чехов-1", "Чехов (Филиал)"],
    "Подольск": ["Подольск 3", "Подольск-3", "Подольск (Филиал)"],
    "Домодедово": ["Домодедово", "Домодедово (Московская область)"],
    "Тула": ["Тула", "Тула (Филиал)"],
    "Белые Столбы": ["Белые Столбы", "Белые столбы"],
    "Электросталь": ["Электросталь", "Электросталь (МО)"],
    "Маркетплейс": ["Маркетплейс", "Marketplace", "Склад продавца", "МП"]
}
```

2. **Класс WarehouseNameMapper:**
```python
class WarehouseNameMapper:
    """Класс для нормализации и сопоставления названий складов."""
    
    def normalize_warehouse_name(self, warehouse_name: str) -> str:
        """Нормализовать название склада к каноническому виду."""
        
    def _find_partial_match(self, warehouse_name: str) -> Optional[str]:
        """Найти частичное соответствие по ключевым словам."""
        
    def validate_mapping_accuracy(self, wb_names: List[str], 
                                st_names: List[str]) -> Dict[str, any]:
        """Проверить точность сопоставления между WB и Stock Tracker названиями."""
```

3. **Интеграция в основной алгоритм:**
```python
# В функции group_data_by_product()
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

for warehouse in item["warehouses"]:
    warehouse_name_raw = warehouse.get("warehouseName", "")
    # КРИТИЧЕСКИ ВАЖНО: Нормализуем название
    warehouse_name = normalize_warehouse_name(warehouse_name_raw)
    quantity = warehouse.get("quantity", 0)
```

#### 2.2 ✅ Специальная обработка FBS товаров

**Добавить в `calculator.py`:**

```python
@staticmethod
def is_fbs_warehouse(warehouse_name: str, warehouse_type: str = "") -> bool:
    """Определить является ли склад FBS (Fulfillment by Seller)."""
    
    if not warehouse_name:
        return False
    
    # Проверяем тип склада
    if warehouse_type == "Склад продавца":
        return True
    
    # Проверяем название
    warehouse_lower = warehouse_name.lower()
    fbs_indicators = [
        "маркетплейс", "marketplace",
        "склад продавца", "склад селлера",
        "fbs", "fulfillment"
    ]
    
    return any(indicator in warehouse_lower for indicator in fbs_indicators)

@staticmethod
def ensure_fbs_warehouse_inclusion(grouped_data: Dict[Tuple[str, int], Dict[str, Any]]) -> None:
    """Гарантировать включение всех FBS складов в результаты."""
    
    for product_key, product_data in grouped_data.items():
        fbs_warehouses = []
        
        for warehouse_name, warehouse_info in product_data["warehouses"].items():
            if warehouse_info.get("is_fbs", False):
                fbs_warehouses.append(warehouse_name)
        
        if fbs_warehouses:
            logger.info(f"✅ FBS warehouses ensured for {product_key}: {fbs_warehouses}")
        else:
            logger.warning(f"⚠️ No FBS warehouses found for {product_key}")
```

### PHASE 3: TESTING & VALIDATION (48-72 часа)

#### 3.1 ✅ Создание диагностических утилит

**Создать файл:** `diagnose_critical_issues.py`

**Функции диагностики:**

1. **Диагностика склада Маркетплейс:**
```python
async def diagnose_marketplace_warehouse_issue():
    """Диагностика проблемы со складом Маркетплейс."""
    
    test_cases = [
        "Маркетплейс",
        "маркетплейс", 
        "Marketplace",
        "Склад продавца",
        "МП-1",
        "FBS склад"
    ]
    
    print("🏭 Testing Marketplace warehouse detection:")
    for warehouse_name in test_cases:
        is_included = is_real_warehouse(warehouse_name)
        status = "✅ INCLUDED" if is_included else "❌ EXCLUDED"
        print(f"   {status}: '{warehouse_name}'")
```

2. **Диагностика точности заказов:**
```python
async def diagnose_orders_accuracy_issue():
    """Диагностика точности подсчета заказов."""
    
    # Тестирование с известными проблемными случаями
    test_cases = [
        {"nm_id": "Its1_2_3/50g", "warehouse": "Чехов 1", "expected": 5},
        # Добавить другие известные случаи
    ]
```

3. **Диагностика сопоставления складов:**
```python
async def diagnose_warehouse_name_mapping():
    """Диагностика сопоставления названий складов."""
    
    wb_names = ["Новосемейкино", "Чехов", "Маркетплейс"]
    st_names = ["Самара (Новосемейкино)", "Чехов 1", "Склад продавца"]
    
    validation = validate_warehouse_mapping(wb_names, st_names)
    
    print("🗺️ Warehouse name mapping validation:")
    print(f"   Accuracy: {validation['accuracy_percent']:.1f}%")
```

#### 3.2 ✅ Создание тестовых сценариев

**Создать файл:** `test_critical_fixes.py`

```python
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
    is_fbs_warehouse
)
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

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
                    f"Marketplace warehouse '{name}' должен быть включен"
                )
    
    def test_fbs_warehouse_detection(self):
        """Тест определения FBS складов."""
        
        fbs_cases = [
            ("Маркетплейс", "Склад продавца", True),
            ("Склад WB", "Склад WB", False),
            ("FBS-склад", "", True),
            ("Обычный склад", "Склад WB", False)
        ]
        
        for name, warehouse_type, expected in fbs_cases:
            with self.subTest(name=name, type=warehouse_type):
                result = is_fbs_warehouse(name, warehouse_type)
                self.assertEqual(
                    result, expected,
                    f"FBS detection failed for '{name}' (type: {warehouse_type})"
                )
    
    def test_warehouse_name_normalization(self):
        """Тест нормализации названий складов."""
        
        normalization_cases = [
            ("Самара (Новосемейкино)", "Новосемейкино"),
            ("Чехов 1", "Чехов"),
            ("Подольск 3", "Подольск"),
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
            {"nmId": 12345, "warehouseName": "Чехов 1", "isCancel": True},  # Отменен
            {"nmId": 12345, "warehouseName": "Маркетплейс", "isCancel": False},
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
        
        # Тест для nmId 12345, склад "Маркетплейс"
        result_mp = WildberriesCalculator.calculate_warehouse_orders(
            mock_orders, 12345, "Маркетплейс"
        )
        
        self.assertEqual(
            result_mp, 1,  # 1 заказ с Маркетплейс
            f"Expected 1 order for Маркетплейс, got {result_mp}"
        )

if __name__ == "__main__":
    unittest.main()
```

## 📊 TESTING CHECKLIST

### ✅ Обязательные тесты перед релизом:

#### Test Case 1: Склад Маркетплейс
- [ ] Склад "Маркетплейс" включается в результаты
- [ ] Вариации названий ("маркетплейс", "Marketplace") работают
- [ ] warehouseType="Склад продавца" корректно обрабатывается
- [ ] FBS товары не теряются при обработке

#### Test Case 2: Точность заказов
- [ ] Тест с артикулом Its1_2_3/50g и складом "Чехов 1"
- [ ] Ожидаемый результат: 5 заказов (не 49)
- [ ] Валидация суммы заказов по складам
- [ ] Исключение отмененных заказов

#### Test Case 3: Нормализация названий
- [ ] "Новосемейкино" = "Самара (Новосемейкино)"
- [ ] "Чехов" = "Чехов 1"
- [ ] Нет дублирования складов
- [ ] Точность сопоставления > 90%

#### Test Case 4: FBS товары
- [ ] Все FBS склады включены в результаты
- [ ] Остатки FBS товаров не теряются
- [ ] Специальная пометка FBS складов работает

## 🚨 КРИТИЧЕСКИЕ ПРОВЕРКИ ПЕРЕД РЕЛИЗОМ

### Performance Tests:
```bash
# Тест производительности с большим объемом данных
python test_performance.py --orders-count 10000 --warehouses-count 50

# Тест памяти
python test_memory_usage.py --duration 300s
```

### Integration Tests:
```bash
# Полный цикл синхронизации
python test_full_sync.py --spreadsheet-id [TEST_ID]

# Тест API интеграции
python test_api_integration.py --test-marketplace
```

### Accuracy Tests:
```bash
# Сравнение с реальными данными WB
python validate_accuracy.py --period "2025-10-18,2025-10-24"

# Тест конкретных проблемных случаев
python test_known_issues.py --test-cases Its1_2_3/50g,Маркетплейс
```

## 📋 DEPLOYMENT CHECKLIST

### Pre-deployment:
- [ ] Все unit tests пройдены
- [ ] Integration tests пройдены
- [ ] Performance tests показывают приемлемые результаты
- [ ] Accuracy tests показывают > 95% точность
- [ ] Code review завершен
- [ ] Documentation обновлена

### Deployment:
- [ ] Backup существующей версии
- [ ] Deploy в staging environment
- [ ] Smoke tests в staging
- [ ] Deploy в production
- [ ] Monitor критических метрик
- [ ] Rollback plan готов

### Post-deployment:
- [ ] Мониторинг точности данных (24 часа)
- [ ] Проверка пользовательских отчетов
- [ ] Performance monitoring
- [ ] Error tracking
- [ ] User feedback collection

## 🔍 MONITORING & ALERTING

### Критические метрики для мониторинга:

#### Accuracy Metrics:
- Процент точности подсчета заказов (цель: > 95%)
- Количество FBS складов в результатах (должно быть > 0)
- Процент успешной нормализации названий (цель: > 90%)

#### Performance Metrics:
- Время выполнения синхронизации (цель: < 3 минут)
- Использование памяти (цель: < 2GB)
- API response time (цель: < 5 секунд)

#### Error Metrics:
- Количество ошибок фильтрации складов (цель: 0)
- Количество потерянных FBS записей (цель: 0)
- Количество неразрешенных названий складов (мониторинг)

### Alerting Rules:
```yaml
# Критические алерты
- alert: MarketplaceWarehouseMissing
  expr: fbs_warehouses_count == 0
  severity: critical
  
- alert: OrdersAccuracyLow
  expr: orders_accuracy_percent < 90
  severity: critical

- alert: SyncTimeHigh  
  expr: sync_duration_seconds > 300
  severity: warning
```

## 🎯 SUCCESS CRITERIA

### Immediate Success (Week 1):
- ✅ Склад "Маркетплейс" включается в 100% случаев
- ✅ Точность подсчета заказов > 95%
- ✅ Устранено дублирование складов
- ✅ FBS товары учитываются корректно

### Medium-term Success (Month 1):
- ✅ Пользовательские жалобы на точность снижены на 80%
- ✅ Время синхронизации стабильно < 3 минут
- ✅ Нет критических ошибок в production

### Long-term Success (Quarter 1):
- ✅ Stock Tracker признан надежным инструментом
- ✅ Точность данных сопоставима с WB интерфейсом
- ✅ Положительная обратная связь от пользователей

---

**Status**: 📋 **READY FOR EXECUTION**  
**Priority**: 🚨 **CRITICAL**  
**Timeline**: **72 hours**  
**Owner**: **Development Team**

**IMPORTANT**: Данный план должен быть выполнен строго по фазам с обязательным тестированием после каждой фазы.