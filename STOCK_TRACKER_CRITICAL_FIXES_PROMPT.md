# 🚨 ПРОМПТ ДЛЯ КРИТИЧЕСКИХ ИСПРАВЛЕНИЙ STOCK TRACKER

**Дата создания**: 24 октября 2025 г.  
**Приоритет**: КРИТИЧЕСКИЙ  
**Основа**: Анализ официальных данных Wildberries за период 18-24 октября 2025  

## 🎯 ОПИСАНИЕ ПРОБЛЕМ

На основании сравнения с официальными данными Wildberries выявлены **критические расхождения** в алгоритме Stock Tracker, которые приводят к неточным данным и потере доверия пользователей.

### ❌ ПРОБЛЕМА 1: Полное игнорирование склада "Маркетплейс"

**Описание**: Stock Tracker **полностью игнорирует** склад "Маркетплейс", что приводит к:
- Потере остатков FBS товаров
- Неучету значительной части заказов
- Критическим расхождениям между фактическими и отображаемыми данными

**Техническая причина**: 
- Функция `is_real_warehouse()` исключает склады с названиями, содержащими "маркетплейс"
- Фильтрация в `group_data_by_product()` отбрасывает важные данные
- Отсутствует специальная обработка FBS товаров

### ❌ ПРОБЛЕМА 2: Ошибки в распределении заказов по складам

**Описание**: Заказы неправильно распределяются между одноименными складами.

**Пример**: 
- Склад "Чехов 1" для артикула Its1_2_3/50g
- WB показывает: **5 заказов**
- Stock Tracker показывает: **49 заказов** 
- **Расхождение: -44 заказа**

**Техническая причина**:
- Неточный алгоритм сопоставления складов и артикулов
- Дублирование подсчетов в функции `calculate_warehouse_orders()`
- Отсутствие валидации точности результатов

### ❌ ПРОБЛЕМА 3: Дублирование из-за разных названий складов

**Описание**: Различия в названиях складов между WB и Stock Tracker приводят к дублированию.

**Примеры**:
- WB: "Новосемейкино" → Stock Tracker: "Самара (Новосемейкино)"
- Результат: Дублирование записей и неточный учет

**Техническая причина**:
- Отсутствует нормализация названий складов
- Нет единого справочника соответствий
- Отсутствует "фасетное" сравнение по ключевым частям названий

### ❌ ПРОБЛЕМА 4: Неправильный подсчет остатков FBS товаров

**Описание**: FBS товары требуют обязательного учета остатков по данным WB, но алгоритм их теряет.

**Техническая причина**:
- Склады FBS не распознаются как критически важные
- Фильтрация исключает склады продавца
- Отсутствует специальная логика для FBS товаров

## 🔧 ТРЕБУЕМЫЕ ИСПРАВЛЕНИЯ

### 1. ✅ ОБЯЗАТЕЛЬНЫЙ УЧЕТ СКЛАДА "МАРКЕТПЛЕЙС"

#### 1.1. Исправить функцию фильтрации складов

**Файл**: `src/stock_tracker/core/calculator.py`

**Заменить в функции `is_real_warehouse()`**:

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
    
    # Для остальных складов - стандартная валидация
    return validate_warehouse_name(warehouse_name)
```

#### 1.2. Добавить обработку warehouseType в API данных

**Файл**: `src/stock_tracker/core/calculator.py`

**Добавить в функцию `group_data_by_product()`**:

```python
# Process orders data - ОБЯЗАТЕЛЬНО включаем FBS склады
for order in orders_data:
    nm_id = order.get("nmId")
    supplier_article = order.get("supplierArticle", "")
    warehouse_name = order.get("warehouseName", "")
    warehouse_type = order.get("warehouseType", "")  # КРИТИЧЕСКИ ВАЖНО
    
    if nm_id and supplier_article:
        key = (supplier_article, nm_id)
        group = grouped_data[key]
        
        # Count total orders
        group["total_orders"] += 1
        
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
                
            # Обычные склады WB с дополнительной валидацией
            elif warehouse_type == "Склад WB" and is_real_warehouse(warehouse_name):
                if warehouse_name not in group["warehouses"]:
                    group["warehouses"][warehouse_name] = {
                        "stock": 0,
                        "orders": 0,
                        "warehouse_type": warehouse_type,
                        "is_fbs": False
                    }
                
                group["warehouses"][warehouse_name]["orders"] += 1
                
            else:
                logger.warning(f"⚠️ Filtered out warehouse: {warehouse_name} (type: {warehouse_type})")
```

### 2. ✅ ИСПРАВИТЬ ТОЧНОСТЬ РАСПРЕДЕЛЕНИЯ ЗАКАЗОВ

#### 2.1. Добавить валидацию точности подсчетов

**Файл**: `src/stock_tracker/core/calculator.py`

**Добавить новый метод**:

```python
@staticmethod
def validate_warehouse_orders_accuracy(orders_data: List[Dict[str, Any]], 
                                     nm_id: int, 
                                     calculated_breakdown: Dict[str, int]) -> Dict[str, Any]:
    """
    Валидация точности распределения заказов по складам.
    
    Проверяет что сумма заказов по складам точно соответствует 
    общему количеству заказов для товара.
    """
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
    else:
        logger.info(f"✅ ACCURACY VALIDATED for nmId {nm_id}: {total_orders_actual} orders")
    
    return validation
```

#### 2.2. Исправить алгоритм подсчета заказов по складам

**Файл**: `src/stock_tracker/core/calculator.py`

**Заменить метод `calculate_warehouse_orders()`**:

```python
@staticmethod
def calculate_warehouse_orders(orders_data: List[Dict[str, Any]], 
                             nm_id: int, warehouse_name: str) -> int:
    """
    Calculate orders for specific warehouse with improved accuracy.
    
    ИСПРАВЛЕНИЕ: Точный подсчет без дублирования.
    """
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

### 3. ✅ ДОБАВИТЬ НОРМАЛИЗАЦИЮ НАЗВАНИЙ СКЛАДОВ

#### 3.1. Создать справочник соответствий

**Создать файл**: `src/stock_tracker/utils/warehouse_mapper.py`

```python
"""
Модуль для нормализации и сопоставления названий складов.

Решает проблему дублирования из-за разных названий одних и тех же складов
в разных источниках данных.
"""

import re
from typing import Dict, List, Optional, Tuple
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

# Справочник известных соответствий названий складов
WAREHOUSE_NAME_MAPPINGS = {
    # Формат: "название_в_wb": ["возможные_варианты_в_stock_tracker"]
    "Новосемейкино": ["Самара (Новосемейкино)", "Самара Новосемейкино", "Новосемейкино"],
    "Чехов": ["Чехов 1", "Чехов-1", "Чехов (Филиал)"],
    "Подольск": ["Подольск 3", "Подольск-3", "Подольск (Филиал)"],
    "Домодедово": ["Домодедово", "Домодедово (Московская область)"],
    "Тула": ["Тула", "Тула (Филиал)"],
    "Белые Столбы": ["Белые Столбы", "Белые столбы"],
    "Электросталь": ["Электросталь", "Электросталь (МО)"],
    "Маркетплейс": ["Маркетплейс", "Marketplace", "Склад продавца", "МП"]
}

class WarehouseNameMapper:
    """Класс для нормализации и сопоставления названий складов."""
    
    def __init__(self):
        self.mapping_cache = {}
        self.reverse_mapping = self._build_reverse_mapping()
    
    def _build_reverse_mapping(self) -> Dict[str, str]:
        """Построить обратный справочник: вариант -> канонический."""
        reverse = {}
        
        for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
            for variant in variants:
                reverse[variant.lower().strip()] = canonical
                
        return reverse
    
    def normalize_warehouse_name(self, warehouse_name: str) -> str:
        """
        Нормализовать название склада к каноническому виду.
        
        Args:
            warehouse_name: Исходное название склада
            
        Returns:
            Каноническое название склада
        """
        if not warehouse_name:
            return warehouse_name
            
        original = warehouse_name.strip()
        normalized_key = original.lower()
        
        # Проверяем кэш
        if normalized_key in self.mapping_cache:
            return self.mapping_cache[normalized_key]
        
        # Ищем точное соответствие
        if normalized_key in self.reverse_mapping:
            canonical = self.reverse_mapping[normalized_key]
            self.mapping_cache[normalized_key] = canonical
            logger.debug(f"Mapped '{original}' -> '{canonical}' (exact)")
            return canonical
        
        # Ищем частичное соответствие (фасетное сравнение)
        canonical = self._find_partial_match(original)
        if canonical:
            self.mapping_cache[normalized_key] = canonical
            logger.debug(f"Mapped '{original}' -> '{canonical}' (partial)")
            return canonical
        
        # Если соответствия не найдено - возвращаем исходное
        self.mapping_cache[normalized_key] = original
        return original
    
    def _find_partial_match(self, warehouse_name: str) -> Optional[str]:
        """
        Найти частичное соответствие по ключевым словам.
        
        Args:
            warehouse_name: Название склада для поиска
            
        Returns:
            Каноническое название или None
        """
        name_lower = warehouse_name.lower()
        
        # Извлекаем ключевые слова (убираем скобки, номера, филиалы)
        clean_name = re.sub(r'\s*\([^)]*\)', '', name_lower)  # Убираем скобки
        clean_name = re.sub(r'\s*-?\d+\s*', ' ', clean_name)  # Убираем номера
        clean_name = re.sub(r'\s*(филиал|фил\.?)\s*', ' ', clean_name)  # Убираем "филиал"
        clean_name = ' '.join(clean_name.split())  # Нормализуем пробелы
        
        # Ищем по ключевым словам
        for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
            canonical_clean = canonical.lower()
            
            # Проверяем вхождение ключевых слов
            if canonical_clean in clean_name or clean_name in canonical_clean:
                return canonical
                
            # Проверяем пересечение слов
            canonical_words = set(canonical_clean.split())
            name_words = set(clean_name.split())
            
            if canonical_words & name_words:  # Есть общие слова
                return canonical
        
        return None
    
    def get_warehouse_group(self, warehouse_names: List[str]) -> Dict[str, List[str]]:
        """
        Группировать названия складов по каноническим названиям.
        
        Args:
            warehouse_names: Список названий складов
            
        Returns:
            Словарь: каноническое_название -> [исходные_названия]
        """
        groups = {}
        
        for name in warehouse_names:
            canonical = self.normalize_warehouse_name(name)
            
            if canonical not in groups:
                groups[canonical] = []
            
            if name not in groups[canonical]:
                groups[canonical].append(name)
        
        return groups
    
    def validate_mapping_accuracy(self, wb_names: List[str], 
                                st_names: List[str]) -> Dict[str, any]:
        """
        Проверить точность сопоставления между WB и Stock Tracker названиями.
        
        Args:
            wb_names: Названия из Wildberries
            st_names: Названия из Stock Tracker
            
        Returns:
            Отчет о точности сопоставления
        """
        wb_normalized = [self.normalize_warehouse_name(name) for name in wb_names]
        st_normalized = [self.normalize_warehouse_name(name) for name in st_names]
        
        wb_set = set(wb_normalized)
        st_set = set(st_normalized)
        
        matched = wb_set & st_set
        wb_only = wb_set - st_set
        st_only = st_set - wb_set
        
        accuracy = len(matched) / len(wb_set) if wb_set else 0
        
        return {
            "total_wb_warehouses": len(wb_set),
            "total_st_warehouses": len(st_set),
            "matched_warehouses": len(matched),
            "wb_only_warehouses": list(wb_only),
            "st_only_warehouses": list(st_only),
            "accuracy_percent": accuracy * 100,
            "mapping_details": {
                "matched": list(matched),
                "wb_only": list(wb_only),
                "st_only": list(st_only)
            }
        }


# Глобальный экземпляр для использования
warehouse_mapper = WarehouseNameMapper()


def normalize_warehouse_name(warehouse_name: str) -> str:
    """Удобная функция для нормализации названия склада."""
    return warehouse_mapper.normalize_warehouse_name(warehouse_name)


def validate_warehouse_mapping(wb_names: List[str], st_names: List[str]) -> Dict[str, any]:
    """Удобная функция для валидации сопоставления складов."""
    return warehouse_mapper.validate_mapping_accuracy(wb_names, st_names)
```

#### 3.2. Интегрировать нормализацию в основной алгоритм

**Файл**: `src/stock_tracker/core/calculator.py`

**Добавить импорт и использование**:

```python
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

# В функции group_data_by_product() перед обработкой:
for warehouse in item["warehouses"]:
    warehouse_name_raw = warehouse.get("warehouseName", "")
    # КРИТИЧЕСКИ ВАЖНО: Нормализуем название
    warehouse_name = normalize_warehouse_name(warehouse_name_raw)
    quantity = warehouse.get("quantity", 0)
    
    if warehouse_name and is_real_warehouse(warehouse_name):
        # ... остальная логика
```

### 4. ✅ СПЕЦИАЛЬНАЯ ОБРАБОТКА FBS ТОВАРОВ

#### 4.1. Добавить определение FBS товаров

**Файл**: `src/stock_tracker/core/calculator.py`

**Добавить новые методы**:

```python
@staticmethod
def is_fbs_warehouse(warehouse_name: str, warehouse_type: str = "") -> bool:
    """
    Определить является ли склад FBS (Fulfillment by Seller).
    
    FBS склады КРИТИЧЕСКИ ВАЖНЫ для точности данных.
    """
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
    """
    Гарантировать включение всех FBS складов в результаты.
    
    КРИТИЧЕСКИ ВАЖНО: FBS остатки не должны теряться.
    """
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

## 🧪 СОЗДАТЬ ИНСТРУМЕНТЫ ДИАГНОСТИКИ

### Утилита проверки конкретных проблемных случаев

**Создать файл**: `diagnose_critical_issues.py`

```python
#!/usr/bin/env python3
"""
Диагностика критических проблем Stock Tracker.

Проверяет конкретные случаи расхождений с WB данными.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.core.calculator import WildberriesCalculator
from stock_tracker.utils.warehouse_mapper import validate_warehouse_mapping
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

async def diagnose_marketplace_warehouse_issue():
    """Диагностика проблемы со складом Маркетплейс."""
    logger.info("🔍 DIAGNOSING: Marketplace warehouse inclusion")
    
    # Проверяем фильтрацию склада Маркетплейс
    from stock_tracker.core.calculator import is_real_warehouse
    
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
        
        if "маркетплейс" in warehouse_name.lower() and not is_included:
            print(f"   🚨 CRITICAL ERROR: Marketplace warehouse excluded!")

async def diagnose_orders_accuracy_issue():
    """Диагностика точности подсчета заказов."""
    logger.info("🔍 DIAGNOSING: Orders counting accuracy")
    
    # Тестовые данные с известной проблемой
    test_nm_id = 12345678  # Заменить на реальный nmId
    test_warehouse = "Чехов 1"
    
    # Здесь должны быть реальные API вызовы для проверки
    print(f"📊 Testing orders accuracy for nmId: {test_nm_id}")
    print(f"📦 Focus warehouse: {test_warehouse}")
    print("   ⚠️ Replace with real API data for actual testing")

async def diagnose_warehouse_name_mapping():
    """Диагностика сопоставления названий складов."""
    logger.info("🔍 DIAGNOSING: Warehouse name mapping")
    
    # Примеры проблемных названий
    wb_names = ["Новосемейкино", "Чехов", "Маркетплейс"]
    st_names = ["Самара (Новосемейкино)", "Чехов 1", "Склад продавца"]
    
    validation = validate_warehouse_mapping(wb_names, st_names)
    
    print("🗺️ Warehouse name mapping validation:")
    print(f"   Accuracy: {validation['accuracy_percent']:.1f}%")
    print(f"   Matched: {validation['matched_warehouses']}")
    print(f"   WB only: {validation['wb_only_warehouses']}")
    print(f"   ST only: {validation['st_only_warehouses']}")

async def main():
    """Запуск всех диагностических проверок."""
    setup_logging()
    
    print("🚨 CRITICAL ISSUES DIAGNOSIS")
    print("=" * 50)
    
    await diagnose_marketplace_warehouse_issue()
    print()
    
    await diagnose_orders_accuracy_issue()
    print()
    
    await diagnose_warehouse_name_mapping()
    print()
    
    print("✅ Diagnosis completed")

if __name__ == "__main__":
    asyncio.run(main())
```

## 📋 ПЛАН РЕАЛИЗАЦИИ

### ФАЗА 1: КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ (24-48 часов)

1. **✅ Исправить функцию `is_real_warehouse()`**
   - Обязательно включить склад "Маркетплейс"
   - Добавить все FBS индикаторы
   - Валидировать на тестовых данных

2. **✅ Исправить `group_data_by_product()`**
   - Добавить обработку `warehouseType`
   - Специальная логика для FBS складов
   - Валидация точности подсчетов

3. **✅ Создать `warehouse_mapper.py`**
   - Справочник соответствий названий
   - Нормализация и фасетное сравнение
   - Интеграция в основной алгоритм

### ФАЗА 2: ВАЛИДАЦИЯ И ТЕСТИРОВАНИЕ (48-72 часа)

1. **✅ Создать диагностические утилиты**
   - `diagnose_critical_issues.py`
   - Проверка конкретных проблемных случаев
   - Сравнение с данными WB

2. **✅ Провести тестирование**
   - Артикул Its1_2_3/50g и склад "Чехов 1"
   - Проверка склада "Маркетплейс"
   - Валидация названий складов

### ФАЗА 3: МОНИТОРИНГ И ПОДДЕРЖКА (72+ часа)

1. **✅ Настроить мониторинг точности**
   - Автоматические проверки расхождений
   - Алерты при критических ошибках
   - Ежедневные отчеты точности

2. **✅ Документация и обучение**
   - Инструкции по использованию
   - Troubleshooting guide
   - Обновление пользовательской документации

## 🎯 КРИТЕРИИ УСПЕХА

### ✅ КРИТЕРИЙ 1: Склад "Маркетплейс" учитывается
- Все FBS товары отображаются с правильными остатками
- Склад "Маркетплейс" появляется в таблице
- Заказы с FBS складов корректно подсчитываются

### ✅ КРИТЕРИЙ 2: Точность подсчета заказов
- Расхождение для артикула Its1_2_3/50g устранено
- Склад "Чехов 1" показывает 5 заказов (как в WB)
- Общие итоги совпадают с данными WB

### ✅ КРИТЕРИЙ 3: Устранено дублирование
- "Новосемейкино" и "Самара (Новосемейкино)" объединены
- Нет дублированных записей складов
- Все склады имеют уникальные канонические названия

### ✅ КРИТЕРИЙ 4: FBS товары учитываются правильно
- Остатки FBS товаров не теряются
- Склады продавца отображаются в таблице
- Специальная логика для FBS работает корректно

## 🚨 КРИТИЧЕСКАЯ ВАЖНОСТЬ

Эти исправления **КРИТИЧЕСКИ ВАЖНЫ** для работоспособности Stock Tracker, так как:

1. **Потеря данных**: Игнорирование склада "Маркетплейс" приводит к потере значительной части данных
2. **Неточность расчетов**: Ошибки в подсчете заказов дискредитируют всю систему
3. **Дублирование**: Разные названия складов создают путаницу и неточности
4. **FBS товары**: Неучет FBS остатков критичен для многих продавцов

**БЕЗ ЭТИХ ИСПРАВЛЕНИЙ STOCK TRACKER НЕ МОЖЕТ СЧИТАТЬСЯ НАДЕЖНЫМ ИНСТРУМЕНТОМ.**

---

**Статус**: 🚨 **ТРЕБУЕТ НЕМЕДЛЕННОЙ РЕАЛИЗАЦИИ**  
**Приоритет**: **КРИТИЧЕСКИЙ**  
**Дедлайн**: **48 часов**  
**Ответственный**: **Development Team**  

**ВНИМАНИЕ**: Данные исправления должны быть реализованы в первую очередь, так как они затрагивают основную функциональность системы и точность данных.