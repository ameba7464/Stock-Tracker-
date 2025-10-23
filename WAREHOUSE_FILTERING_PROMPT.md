# 🔧 ПРОМПТ ДЛЯ ИСПРАВЛЕНИЯ ПРОБЛЕМ СО СКЛАДАМИ

## 🎯 ЦЕЛЬ
Исправить критические ошибки в обработке данных складов, где статусы доставки отображаются как названия складов вместо реальных физических складов.

## 🚨 ОБНАРУЖЕННЫЕ ПРОБЛЕМЫ

### Проблема 1: Статусы доставки вместо складов
**Что сейчас в таблице**:
```
- "В пути до получателей"
- "В пути возврата на склад WB"  
- "Всего находится на складах"
```
**Что должно быть**: Физические склады типа "Тула", "Белые Столбы", "Домодедово"

### Проблема 2: Смешанные источники данных
**Текущие названия**: "Подольск 3", "Электросталь", "Краснодар", "Чехов 1"
**Ожидаемые названия**: Только реальные склады из Warehouse API v1

### Проблема 3: Отсутствие фильтрации
Система не отличает статусы доставки от реальных складов

## ✅ ТРЕБУЕМЫЕ ИСПРАВЛЕНИЯ

### 1. Добавить фильтрацию статусов доставки
```python
# В метод process_combined_api_data() или group_data_by_product()
DELIVERY_STATUSES = {
    "В пути до получателей",
    "В пути возврата на склад WB", 
    "Всего находится на складах",
    "В пути возврата с ПВЗ",
    "В пути с ПВЗ покупателю",
    "Удержания и возмещения",
    "К доплате",
    "Общий итог"
}

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
        
    return True
```

### 2. Добавить валидацию названий складов
```python
VALID_WAREHOUSE_PATTERNS = [
    r'^[А-Яа-я\s\-\(\)]+\d*$',  # Русские названия городов
    r'^[А-Яа-я]+\s*\d*$',       # Город + номер
    r'^[А-Яа-я]+\s*\([А-Яа-я\s]+\)$'  # Город (район)
]

def validate_warehouse_name(warehouse_name: str) -> bool:
    """Валидация названия склада."""
    import re
    
    if not warehouse_name:
        return False
        
    # Проверяем паттерны
    for pattern in VALID_WAREHOUSE_PATTERNS:
        if re.match(pattern, warehouse_name):
            return True
            
    return False
```

### 3. Исправить обработку данных в group_data_by_product()
```python
# В методе group_data_by_product():
for warehouse in item["warehouses"]:
    warehouse_name = warehouse.get("warehouseName", "")
    quantity = warehouse.get("quantity", 0)
    
    # ДОБАВИТЬ ФИЛЬТРАЦИЮ:
    if warehouse_name and is_real_warehouse(warehouse_name):
        if validate_warehouse_name(warehouse_name):
            # Только тогда добавляем как склад
            if warehouse_name not in group["warehouses"]:
                group["warehouses"][warehouse_name] = {
                    "stock": 0,
                    "orders": 0
                }
            group["warehouses"][warehouse_name]["stock"] += quantity
        else:
            logger.warning(f"Invalid warehouse name format: {warehouse_name}")
    else:
        logger.debug(f"Filtered out delivery status: {warehouse_name}")
```

### 4. Добавить диагностику входящих данных
```python
def debug_warehouse_data(warehouse_data: List[Dict], source: str = "unknown"):
    """Диагностика данных складов."""
    logger.info(f"=== WAREHOUSE DATA DEBUG ({source}) ===")
    
    all_warehouse_names = set()
    for item in warehouse_data:
        for warehouse in item.get("warehouses", []):
            name = warehouse.get("warehouseName", "")
            if name:
                all_warehouse_names.add(name)
    
    logger.info(f"Total unique warehouse names: {len(all_warehouse_names)}")
    
    # Группируем по типам
    real_warehouses = []
    delivery_statuses = []
    unknown = []
    
    for name in all_warehouse_names:
        if is_real_warehouse(name):
            if validate_warehouse_name(name):
                real_warehouses.append(name)
            else:
                unknown.append(name)
        else:
            delivery_statuses.append(name)
    
    logger.info(f"✅ Real warehouses ({len(real_warehouses)}): {real_warehouses}")
    logger.warning(f"⚠️ Delivery statuses ({len(delivery_statuses)}): {delivery_statuses}")
    logger.error(f"❌ Unknown format ({len(unknown)}): {unknown}")
    
    return {
        "real_warehouses": real_warehouses,
        "delivery_statuses": delivery_statuses, 
        "unknown": unknown
    }
```

### 5. Интегрировать в основные методы
```python
# В process_combined_api_data():
def process_combined_api_data(analytics_v2_data, warehouse_v1_data):
    # ДОБАВИТЬ в начало:
    logger.info("🔍 Debugging warehouse data before processing...")
    debug_results = debug_warehouse_data(warehouse_v1_data, "Warehouse API v1")
    
    if not debug_results["real_warehouses"]:
        logger.error("❌ No real warehouses found in API data!")
        # Показать предупреждение вместо фиктивных данных
        
    # Далее существующая логика с добавленной фильтрацией...
```

## 🧪 ТЕСТИРОВАНИЕ

### Тест 1: Фильтрация статусов
```python
def test_delivery_status_filtering():
    test_data = [
        ("Тула", True),
        ("Белые Столбы", True), 
        ("В пути до получателей", False),
        ("В пути возврата на склад WB", False),
        ("Всего находится на складах", False),
        ("Подольск 3", True),
        ("Краснодар", True)
    ]
    
    for name, expected in test_data:
        result = is_real_warehouse(name)
        assert result == expected, f"Failed for {name}: expected {expected}, got {result}"
```

### Тест 2: Проверка что в продукты попадают только реальные склады
```python
def test_no_delivery_statuses_in_products():
    # Создать тестовые данные с доставочными статусами
    # Обработать через новую логику
    # Проверить что в продуктах нет статусов доставки
    # Удалить тестовую функцию после проверки
```

## 📊 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

### До исправления:
```
Склады в таблице:
❌ "В пути до получателей" - 3 заказа, 55 остатков
❌ "В пути возврата на склад WB" - 0 заказов, 5 остатков
❌ "Всего находится на складах" - 36 заказов, 547 остатков
```

### После исправления:
```
Склады в таблице:
✅ "Тула" - 15 заказов, 200 остатков
✅ "Белые Столбы" - 12 заказов, 150 остатков  
✅ "Домодедово" - 8 заказов, 100 остатков
```

## 🎯 КРИТЕРИИ УСПЕХА

1. ✅ В Google Sheets НЕТ статусов доставки как названий складов
2. ✅ Все склады имеют названия городов/регионов  
3. ✅ Логи показывают отфильтрованные статусы доставки
4. ✅ Валидация отклоняет некорректные названия
5. ✅ Диагностика четко разделяет типы данных

## 🚀 ПРИОРИТЕТ: КРИТИЧЕСКИЙ
Эти исправления должны быть внедрены немедленно, так как текущие данные в таблице полностью некорректны для принятия бизнес-решений.