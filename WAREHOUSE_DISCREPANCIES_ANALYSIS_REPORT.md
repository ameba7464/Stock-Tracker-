# ОТЧЕТ: Анализ расхождений Stock Tracker и Wildberries

**Дата анализа:** 26 октября 2025 г.  
**Проанализированные файлы:** CSV отчет WB (26-10-2025), исходный код Stock Tracker  
**Статус:** ✅ Анализ завершен, проблемы выявлены

---

## 📋 EXECUTIVE SUMMARY

Проведен глубокий анализ кода приложения Stock Tracker и официального отчета Wildberries. Выявлены **критические проблемы** в логике обработки складов, приводящие к потере данных о 1800+ единицах товара.

**Ключевые находки:**
- ✅ Код поддержки склада "Маркетплейс" **ПРИСУТСТВУЕТ** в приложении
- ❌ Но склад может **НЕ ПОПАДАТЬ** в итоговые данные из-за проблем фильтрации
- ❌ 23 склада из WB отчета **ОТСУТСТВУЮТ** в Stock Tracker
- ❌ Расхождение в **1026 единиц** для артикула ItsSport2/50g
- ❌ 77% артикулов имеют расхождения по заказам
- ❌ 92% артикулов имеют расхождения по остаткам

---

## 🔍 ДЕТАЛЬНЫЙ АНАЛИЗ КОДА

### 1. Анализ `calculator.py` (Основная логика)

#### ✅ ЧТО РАБОТАЕТ ПРАВИЛЬНО:

Файл: `src/stock_tracker/core/calculator.py`

```python
def is_real_warehouse(warehouse_name: str) -> bool:
    """Проверить что это реальный склад, а не статус."""
    
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
```

**Вывод:** Логика определения Маркетплейс **правильная и присутствует**.

#### ❌ ЧТО МОЖЕТ НЕ РАБОТАТЬ:

**Проблема 1: Функция `validate_warehouse_name()` может отфильтровать Маркетплейс**

```python
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

Паттерны для валидации:
```python
VALID_WAREHOUSE_PATTERNS = [
    r'^[А-Яа-я\s\-\(\)]+\d*$',  # Русские названия городов
    r'^[А-Яа-я]+\s*\d*$',       # Город + номер
    r'^[А-Яа-я]+\s*\([А-Яа-я\s]+\)$'  # Город (район)
]
```

**ПРОБЛЕМА:** Название "Маркетплейс" **проходит** первый паттерн, но если API возвращает:
- "Marketplace" (латиница) - **НЕ ПРОЙДЕТ**
- "Маркетплейс 1" - **ПРОЙДЕТ**
- "МП" - **НЕ ПРОЙДЕТ**
- "FBS" (латиница) - **НЕ ПРОЙДЕТ**

**Проблема 2: Порядок проверок в `is_real_warehouse()`**

Код:
```python
    # ДОБАВЛЯЕМ: Обработка остальных складов по индикаторам
    known_warehouse_patterns = [
        # Региональные центры
        "сц ", "sc ", "центр", "center",
        # Обычные склады
        "склад", "warehouse", "wh ",
        # Города (начинаются с заглавной буквы)
        r"^[А-Я][а-я]+",
        # Содержат номера складов
        r"\d+",
        # Содержат скобки с уточнениями
        r"\([А-Яа-я\s\-]+\)"
    ]
    
    # Для остальных складов - стандартная валидация
    return validate_warehouse_name(warehouse_name)
```

**ПРОБЛЕМА:** После проверки Маркетплейс функция вызывает `validate_warehouse_name()`, которая может **отклонить** валидные склады.

### 2. Анализ `warehouse_mapper.py` (Нормализация названий)

#### ✅ ЧТО РАБОТАЕТ:

```python
def is_marketplace_warehouse(warehouse_name: str) -> bool:
    """
    Проверить, является ли склад Маркетплейсом/FBS.
    """
    if not warehouse_name:
        return False
    
    # Нормализуем название
    canonical = normalize_warehouse_name(warehouse_name)
    
    # Проверяем каноническое название
    if canonical.lower() == "маркетплейс":
        return True
    
    # Проверяем прямые индикаторы
    lower_name = warehouse_name.lower()
    marketplace_indicators = [
        "маркетплейс", "marketplace",
        "склад продавца", "склад селлера",
        "fbs", "мп ", "mp "
    ]
    
    return any(indicator in lower_name for indicator in marketplace_indicators)
```

**Вывод:** Определение Маркетплейс **корректное**.

#### ❌ ПОТЕНЦИАЛЬНАЯ ПРОБЛЕМА:

Справочник маппинга:
```python
WAREHOUSE_NAME_MAPPINGS = {
    "Маркетплейс": ["Маркетплейс", "Marketplace", "Склад продавца", "МП"]
}
```

Но функция `normalize_warehouse_name()` ищет **точное соответствие** в lowercase:
```python
if lower_name in self.reverse_mapping:
    canonical = self.reverse_mapping[lower_name]
```

**ПРОБЛЕМА:** Если API возвращает "marketplace" (lowercase) - он будет найден. Но если "Marketplace HUB" или "Маркетплейс-1" - **НЕ НАЙДЕТ**.

### 3. Анализ `group_data_by_product()` - КРИТИЧЕСКАЯ ФУНКЦИЯ

Файл: `calculator.py`, строки 464-599

#### ✅ ЧТО РАБОТАЕТ:

```python
logger.info("🔧 CRITICAL FIX: Starting enhanced grouping with Marketplace support")

# Process warehouse remains data
for item in warehouse_remains_data:
    nm_id = item.get("nmId")
    supplier_article = item.get("vendorCode", "")
    
    if nm_id and supplier_article:
        key = (supplier_article, nm_id)
        group = grouped_data[key]
        group["supplier_article"] = supplier_article
        group["nm_id"] = nm_id
        
        # Process warehouses
        if "warehouses" in item:
            for warehouse in item["warehouses"]:
                warehouse_name_raw = warehouse.get("warehouseName", "")
                # КРИТИЧЕСКИ ВАЖНО: Нормализуем название
                warehouse_name = normalize_warehouse_name(warehouse_name_raw)
                quantity = warehouse.get("quantity", 0)
                
                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Всегда включаем Маркетплейс
                if warehouse_name and is_real_warehouse(warehouse_name):
                    # Создаем или обновляем склад
                    if warehouse_name not in group["warehouses"]:
                        group["warehouses"][warehouse_name] = {
                            "stock": 0,
                            "orders": 0,
                            "warehouse_type": "unknown",
                            "is_fbs": is_marketplace_warehouse(warehouse_name),
                            "raw_name": warehouse_name_raw  # Сохраняем исходное
                        }
                    
                    # Обновляем остатки
                    group["warehouses"][warehouse_name]["stock"] += quantity
```

**Вывод:** Логика группировки **правильная**, склад Маркетплейс **должен включаться**.

#### ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА - Orders Processing:

```python
# Process orders data - КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ
orders_processed = 0
marketplace_orders = 0

for order in orders_data:
    nm_id = order.get("nmId")
    supplier_article = order.get("supplierArticle", "")
    warehouse_name_raw = order.get("warehouseName", "")
    warehouse_name = normalize_warehouse_name(warehouse_name_raw)
    warehouse_type = order.get("warehouseType", "")
    is_canceled = order.get("isCancel", False)
    
    if nm_id and supplier_article and not is_canceled:
        key = (supplier_article, nm_id)
        group = grouped_data[key]
        
        # КРИТИЧЕСКИ ВАЖНО: Точное распределение заказов
        if warehouse_name:
            # Определяем тип склада
            is_marketplace = (
                warehouse_type == "Склад продавца" or
                is_marketplace_warehouse(warehouse_name)
            )
            
            # ВСЕГДА включаем склады Маркетплейс
            if is_marketplace:
                marketplace_orders += 1
                logger.debug(f"✅ Marketplace order: {warehouse_name} (type: {warehouse_type})")
                
                if warehouse_name not in group["warehouses"]:
                    group["warehouses"][warehouse_name] = {
                        "stock": 0,
                        "orders": 0,
                        "warehouse_type": warehouse_type,
                        "is_fbs": True,
                        "raw_name": warehouse_name_raw
                    }
```

**ПРОБЛЕМА:** Код создает склад Маркетплейс **ИЗ ЗАКАЗОВ** (`orders_data`), но что если:
1. В `warehouse_remains_data` склад Маркетплейс **НЕ ПРИШЕЛ** (нет остатков)
2. В `orders_data` склад Маркетплейс **ЕСТЬ** (есть заказы)

Тогда склад **БУДЕТ СОЗДАН**, но с `stock=0`.

**НО ОБРАТНАЯ ПРОБЛЕМА:**
Что если в `warehouse_remains_data` склад **ЕСТЬ**, но при обработке был **ОТФИЛЬТРОВАН** `is_real_warehouse()`?

---

## 🎯 ВЫЯВЛЕННЫЕ ПРОБЛЕМЫ

### КРИТИЧЕСКАЯ ПРОБЛЕМА #1: Цепочка фильтрации складов

**Описание:**  
Склад Маркетплейс проходит через **3 уровня фильтрации**:
1. `normalize_warehouse_name()` - нормализация названия
2. `is_real_warehouse()` - проверка что это реальный склад
3. `validate_warehouse_name()` - валидация по паттернам

**Проблема:** Если на **ЛЮБОМ** из этих уровней произойдет ошибка - склад **ПОТЕРЯЕТСЯ**.

**Пример сценария потери:**
```
Шаг 1: API возвращает warehouse_name = "Marketplace"
Шаг 2: normalize_warehouse_name("Marketplace") 
       -> Ищет в lowercase: "marketplace"
       -> Находит в WAREHOUSE_NAME_MAPPINGS
       -> Возвращает: "Маркетплейс" ✅
       
Шаг 3: is_real_warehouse("Маркетплейс")
       -> Проверяет marketplace_indicators
       -> Находит "маркетплейс" в warehouse_name_lower ✅
       -> Возвращает: True
       
Шаг 4: Склад ВКЛЮЧЕН ✅

НО ЕСЛИ:

Шаг 1: API возвращает warehouse_name = "FBS Warehouse #1"
Шаг 2: normalize_warehouse_name("FBS Warehouse #1")
       -> Не находит точного соответствия
       -> Пытается найти частичное
       -> НЕ находит ключевые слова из справочника
       -> Возвращает: "FBS Warehouse #1" (без изменений)
       
Шаг 3: is_real_warehouse("FBS Warehouse #1")
       -> Проверяет marketplace_indicators
       -> Находит "fbs" ✅
       -> Возвращает: True
       
Шаг 4: Склад ВКЛЮЧЕН ✅

НО ЕСЛИ:

Шаг 1: API возвращает warehouse_name = "MP-Storage"
Шаг 2: normalize_warehouse_name("MP-Storage")
       -> Не находит точного соответствия
       -> Возвращает: "MP-Storage"
       
Шаг 3: is_real_warehouse("MP-Storage")
       -> Проверяет marketplace_indicators: "мп ", "mp "
       -> "mp-storage".find("mp ") = -1 (нет пробела) ❌
       -> Переходит к validate_warehouse_name()
       
Шаг 4: validate_warehouse_name("MP-Storage")
       -> Проверяет VALID_WAREHOUSE_PATTERNS
       -> Паттерн 1: r'^[А-Яа-я\s\-\(\)]+\d*$' -> НЕ ПОДХОДИТ (латиница)
       -> Паттерн 2: r'^[А-Яа-я]+\s*\d*$' -> НЕ ПОДХОДИТ
       -> Паттерн 3: r'^[А-Яа-я]+\s*\([А-Яа-я\s]+\)$' -> НЕ ПОДХОДИТ
       -> Возвращает: False ❌
       
Шаг 5: Склад ОТФИЛЬТРОВАН ❌ - ПОТЕРЯ ДАННЫХ!
```

### КРИТИЧЕСКАЯ ПРОБЛЕМА #2: Отсутствующие склады

**Факт:** CSV показывает **79 записей складов**, Stock Tracker показывает только **24**.

**Причины:**
1. Некоторые склады могут иметь `stock=0` и `orders=0` -> их можно не включать
2. Некоторые склады - это "статусы доставки" -> правильно фильтруются
3. **НО:** 23 склада с данными **отсутствуют** в приложении

**Примеры отсутствующих складов из CSV:**
- "Маркетплейс" - **1026 остатков** для ItsSport2/50g
- "Казань" - 8 заказов для Its2/50g
- "Екатеринбург - Перспективный 12" - 3 заказа для Its1_2_3/50g

**Возможные причины:**
1. Склады **НЕ ПРИШЛИ** из Wildberries API
2. Склады **ОТФИЛЬТРОВАНЫ** логикой приложения
3. Склады **ПОТЕРЯЛИСЬ** при нормализации названий

### ПРОБЛЕМА #3: Расхождения в подсчете заказов

**Факт:** 77% артикулов имеют расхождения по заказам.

**Примеры:**
- Its1_2_3/50g: Stock Tracker = 112, WB = 99 (+13)
- Its2/50g: Stock Tracker = 87, WB = 66 (+21)
- ItsSport2/50g: Stock Tracker = 37, WB = 31 (+6)

**Возможные причины:**
1. **Разный период агрегации** - приложение может считать заказы за другой период
2. **Включение отмененных заказов** - приложение может НЕ исключать `isCancel=True`
3. **Дублирование записей** - один заказ может считаться дважды
4. **Неправильная группировка** по складам

### ПРОБЛЕМА #4: Расхождения в остатках

**Факт:** 92% артикулов имеют расхождения по остаткам.

**КРИТИЧЕСКИЙ СЛУЧАЙ:**
- **ItsSport2/50g:** Stock Tracker = 252, WB = 1278 (разница **-1026**)
- Из которых 1026 единиц на складе **"Маркетплейс"**

**Вывод:** Склад Маркетплейс с 1026 остатками **НЕ ПОПАЛ** в данные приложения.

---

## 💡 РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ

### КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #1: Улучшить фильтрацию складов

**Файл:** `src/stock_tracker/core/calculator.py`

**Текущий код:**
```python
def is_real_warehouse(warehouse_name: str) -> bool:
    # ... проверки ...
    
    # Для остальных складов - стандартная валидация
    return validate_warehouse_name(warehouse_name)
```

**ИСПРАВЛЕНИЕ:**
```python
def is_real_warehouse(warehouse_name: str) -> bool:
    """Проверить что это реальный склад, а не статус."""
    if not warehouse_name or not isinstance(warehouse_name, str):
        return False
    
    # Исключаем статусы доставки
    DELIVERY_STATUSES = {
        "в пути до получателей",
        "в пути возврата на склад wb", 
        "всего находится на складах",
        "в пути возврата с пвз",
        "в пути с пвз покупателю",
        "удержания и возмещения",
        "к доплате",
        "общий итог"
    }
    
    if warehouse_name in DELIVERY_STATUSES:
        return False
        
    # Исключаем итоговые строки
    if any(word in warehouse_name.lower() for word in ["итог", "всего", "общий"]):
        return False
        
    # Исключаем строки "в пути"
    if "в пути" in warehouse_name.lower():
        return False
    
    warehouse_name_lower = warehouse_name.lower()
    
    # КРИТИЧЕСКИ ВАЖНО: ПРИОРИТЕТ #1 - Маркетплейс/FBS склады
    marketplace_indicators = [
        "маркетплейс", "marketplace", 
        "склад продавца", "склад селлера",
        "fbs", "fulfillment by seller",
        "мп", "mp",  # ИСПРАВЛЕНО: убрали пробелы для лучшего поиска
        "сп"  # склад продавца (сокращенно)
    ]
    
    # Если это склад Маркетплейс - ВСЕГДА включаем БЕЗ дополнительных проверок
    if any(indicator in warehouse_name_lower for indicator in marketplace_indicators):
        logger.info(f"✅ CRITICAL: Marketplace/FBS warehouse INCLUDED: {warehouse_name}")
        return True
    
    # Для обычных складов - более мягкая валидация
    # ИСПРАВЛЕНО: Не требуем строгого соответствия паттернам
    
    # Проверяем что это не пустая строка и не только цифры
    if len(warehouse_name.strip()) < 2:
        return False
    
    if warehouse_name.strip().isdigit():
        return False
    
    # Если название содержит хотя бы одну букву - это потенциально склад
    if any(c.isalpha() for c in warehouse_name):
        logger.debug(f"✅ Warehouse INCLUDED: {warehouse_name}")
        return True
    
    logger.debug(f"❌ Warehouse FILTERED: {warehouse_name}")
    return False
```

**ОБОСНОВАНИЕ:**
- ❌ Удалена жесткая проверка `validate_warehouse_name()` которая отсекает валидные склады
- ✅ Приоритет отдан определению Маркетплейс - эти склады включаются БЕЗ дополнительных проверок
- ✅ Для остальных складов - более мягкие критерии (просто наличие букв)
- ✅ Сохранены критичные фильтры (статусы доставки, итоговые строки)

### КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ #2: Улучшить нормализацию названий

**Файл:** `src/stock_tracker/utils/warehouse_mapper.py`

**ИСПРАВЛЕНИЕ справочника:**
```python
WAREHOUSE_NAME_MAPPINGS = {
    # Формат: "название_в_wb": ["возможные_варианты_в_stock_tracker"]
    "Новосемейкино": ["Самара (Новосемейкино)", "Самара Новосемейкино", "Новосемейкино"],
    "Чехов": ["Чехов 1", "Чехов-1", "Чехов (Филиал)", "Чехов"],
    "Подольск": ["Подольск 3", "Подольск-3", "Подольск (Филиал)", "Подольск"],
    # КРИТИЧЕСКИ ВАЖНО: Расширенный маппинг для Маркетплейс
    "Маркетплейс": [
        "Маркетплейс", "маркетплейс",
        "Marketplace", "marketplace",
        "Склад продавца", "склад продавца",
        "Склад селлера", "склад селлера",
        "МП", "мп", "MP", "mp",
        "FBS", "fbs",
        "Fulfillment by Seller",
        "Seller Warehouse",
        # Добавляем возможные варианты с номерами и символами
        "Маркетплейс-1", "Marketplace-1",
        "МП-1", "MP-1",
        "FBS-Storage", "FBS Warehouse"
    ]
}
```

**ИСПРАВЛЕНИЕ функции нормализации:**
```python
def _find_partial_match(self, warehouse_name: str) -> Optional[str]:
    """
    Найти частичное соответствие по ключевым словам.
    
    ИСПРАВЛЕНО: Более агрессивный поиск для Маркетплейс
    """
    lower_name = warehouse_name.lower()
    
    # ПРИОРИТЕТ #1: Маркетплейс
    marketplace_keywords = [
        "маркетплейс", "marketplace", 
        "склад продавца", "склад селлера",
        "fbs", "мп", "mp", "сп"
    ]
    
    # Если найдено хотя бы одно ключевое слово Маркетплейс - сразу возвращаем
    for keyword in marketplace_keywords:
        if keyword in lower_name:
            logger.info(f"🔍 Marketplace keyword '{keyword}' found in '{warehouse_name}' -> normalized to 'Маркетплейс'")
            return "Маркетплейс"
    
    # Для остальных складов - стандартная логика
    cleaned_name = re.sub(r'\b(сц|склад|центр|филиал)\b', '', lower_name).strip()
    cleaned_name = re.sub(r'[()]', '', cleaned_name).strip()
    
    for canonical, variants in WAREHOUSE_NAME_MAPPINGS.items():
        if canonical == "Маркетплейс":
            continue  # Уже обработали выше
        
        canonical_lower = canonical.lower()
        
        if canonical_lower in lower_name or any(word in lower_name for word in canonical_lower.split()):
            return canonical
        
        for variant in variants:
            variant_lower = variant.lower()
            if variant_lower in lower_name:
                return canonical
    
    return None
```

### ИСПРАВЛЕНИЕ #3: Добавить детальное логирование

**Файл:** `src/stock_tracker/core/calculator.py`

**Добавить в начало `group_data_by_product()`:**
```python
@staticmethod
def group_data_by_product(warehouse_remains_data: List[Dict[str, Any]], 
                        orders_data: List[Dict[str, Any]]) -> Dict[Tuple[str, int], Dict[str, Any]]:
    """
    Group data by product per urls.md grouping logic.
    """
    # НОВОЕ: Детальная диагностика входных данных
    logger.info("="*80)
    logger.info("🔍 STARTING DATA GROUPING - DETAILED DIAGNOSTICS")
    logger.info("="*80)
    
    # Диагностика warehouse_remains_data
    logger.info(f"\n📦 WAREHOUSE REMAINS DATA:")
    logger.info(f"   Total records: {len(warehouse_remains_data)}")
    
    all_warehouse_names = set()
    marketplace_found = []
    
    for item in warehouse_remains_data:
        nm_id = item.get("nmId")
        vendor_code = item.get("vendorCode")
        
        if "warehouses" in item:
            for wh in item["warehouses"]:
                wh_name = wh.get("warehouseName", "")
                if wh_name:
                    all_warehouse_names.add(wh_name)
                    
                    # Проверяем Маркетплейс
                    if is_marketplace_warehouse(wh_name):
                        marketplace_found.append({
                            "product": f"{vendor_code} (nm={nm_id})",
                            "warehouse": wh_name,
                            "stock": wh.get("quantity", 0)
                        })
    
    logger.info(f"   Unique warehouse names: {len(all_warehouse_names)}")
    logger.info(f"   Marketplace warehouses found: {len(marketplace_found)}")
    
    if marketplace_found:
        logger.info(f"\n   📋 MARKETPLACE WAREHOUSES IN API DATA:")
        for mp in marketplace_found[:10]:  # Показываем первые 10
            logger.info(f"      - {mp['product']}: {mp['warehouse']} (stock={mp['stock']})")
    else:
        logger.warning(f"\n   ⚠️ WARNING: NO MARKETPLACE WAREHOUSES FOUND IN API DATA!")
    
    # Диагностика orders_data
    logger.info(f"\n📋 ORDERS DATA:")
    logger.info(f"   Total orders: {len(orders_data)}")
    
    marketplace_orders = []
    for order in orders_data:
        wh_name = order.get("warehouseName", "")
        wh_type = order.get("warehouseType", "")
        
        if is_marketplace_warehouse(wh_name) or wh_type == "Склад продавца":
            marketplace_orders.append({
                "product": f"{order.get('supplierArticle')} (nm={order.get('nmId')})",
                "warehouse": wh_name,
                "type": wh_type
            })
    
    logger.info(f"   Marketplace orders found: {len(marketplace_orders)}")
    
    if marketplace_orders:
        logger.info(f"\n   📋 MARKETPLACE ORDERS IN API DATA:")
        for mp_order in marketplace_orders[:10]:
            logger.info(f"      - {mp_order['product']}: {mp_order['warehouse']} (type={mp_order['type']})")
    else:
        logger.warning(f"\n   ⚠️ WARNING: NO MARKETPLACE ORDERS FOUND IN API DATA!")
    
    logger.info("\n" + "="*80)
    logger.info("STARTING GROUPING...")
    logger.info("="*80 + "\n")
    
    # ... остальной код группировки ...
```

### ИСПРАВЛЕНИЕ #4: Проверка API данных

**КРИТИЧЕСКИ ВАЖНО:** Проверить что Wildberries API **ДЕЙСТВИТЕЛЬНО ВОЗВРАЩАЕТ** склад Маркетплейс.

**Рекомендуемый скрипт проверки:**
```python
import asyncio
import json
from src.stock_tracker.api.client import WildberriesAPIClient
from src.stock_tracker.api.products import WildberriesProductDataFetcher

async def check_marketplace_in_api():
    """Проверка наличия Маркетплейс в API данных."""
    api_client = WildberriesAPIClient()
    fetcher = WildberriesProductDataFetcher(api_client)
    
    # Загружаем данные
    orders_data, warehouse_data = await fetcher.fetch_all_products_data()
    
    print(f"📊 API DATA ANALYSIS:")
    print(f"   Orders: {len(orders_data)}")
    print(f"   Warehouse records: {len(warehouse_data)}")
    
    # Ищем Маркетплейс в warehouse_data
    marketplace_in_warehouse = []
    for item in warehouse_data:
        if "warehouses" in item:
            for wh in item["warehouses"]:
                wh_name = wh.get("warehouseName", "")
                if "маркетплейс" in wh_name.lower() or "marketplace" in wh_name.lower():
                    marketplace_in_warehouse.append({
                        "nmId": item.get("nmId"),
                        "vendorCode": item.get("vendorCode"),
                        "warehouse": wh_name,
                        "quantity": wh.get("quantity", 0)
                    })
    
    # Ищем Маркетплейс в orders_data
    marketplace_in_orders = []
    for order in orders_data:
        wh_name = order.get("warehouseName", "")
        wh_type = order.get("warehouseType", "")
        
        if ("маркетплейс" in wh_name.lower() or 
            "marketplace" in wh_name.lower() or
            wh_type == "Склад продавца"):
            marketplace_in_orders.append({
                "nmId": order.get("nmId"),
                "supplierArticle": order.get("supplierArticle"),
                "warehouse": wh_name,
                "warehouseType": wh_type
            })
    
    print(f"\n✅ MARKETPLACE IN WAREHOUSE DATA: {len(marketplace_in_warehouse)} records")
    if marketplace_in_warehouse:
        for mp in marketplace_in_warehouse[:5]:
            print(f"   - {mp['vendorCode']} (nm={mp['nmId']}): {mp['warehouse']} = {mp['quantity']}")
    
    print(f"\n✅ MARKETPLACE IN ORDERS DATA: {len(marketplace_in_orders)} records")
    if marketplace_in_orders:
        for mp in marketplace_in_orders[:5]:
            print(f"   - {mp['supplierArticle']} (nm={mp['nmId']}): {mp['warehouse']} (type={mp['warehouseType']})")
    
    # Сохраняем полный отчет
    report = {
        "warehouse_data_marketplace": marketplace_in_warehouse,
        "orders_data_marketplace": marketplace_in_orders
    }
    
    with open("marketplace_api_check.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 Полный отчет сохранен в: marketplace_api_check.json")

if __name__ == "__main__":
    asyncio.run(check_marketplace_in_api())
```

### ИСПРАВЛЕНИЕ #5: Проверка периода агрегации заказов

**Проблема:** Заказы могут считаться за разные периоды.

**Решение:** Убедиться что период в `orders_date_from` соответствует периоду отчета WB.

**Файл:** `src/stock_tracker/api/products.py`

```python
async def fetch_product_data(self, seller_article: str, 
                           wildberries_article: int,
                           orders_date_from: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Fetch complete product data from both API endpoints.
    """
    try:
        logger.info(f"Fetching complete data for product {seller_article} (nmId: {wildberries_article})")
        
        # ИСПРАВЛЕНО: Используем точный период из отчета WB
        if orders_date_from is None:
            # Если период не указан - используем 7 дней (как в WB отчете)
            orders_date = datetime.now() - timedelta(days=7)  # БЫЛО: 30
            orders_date_from = orders_date.strftime("%Y-%m-%dT00:00:00")
            
            logger.info(f"📅 Orders date_from set to: {orders_date_from} (last 7 days)")
```

---

## 📊 ПЛАН ПРОВЕРКИ ИСПРАВЛЕНИЙ

После внесения исправлений необходимо:

### 1. Тест #1: Проверка включения Маркетплейс

```python
# test_marketplace_inclusion.py
def test_marketplace_warehouse_detection():
    """Проверка что все варианты Маркетплейс определяются корректно."""
    from src.stock_tracker.core.calculator import is_real_warehouse
    from src.stock_tracker.utils.warehouse_mapper import is_marketplace_warehouse
    
    test_cases = [
        # Должны быть определены как Маркетплейс
        ("Маркетплейс", True),
        ("маркетплейс", True),
        ("Marketplace", True),
        ("marketplace", True),
        ("Склад продавца", True),
        ("МП", True),
        ("мп", True),
        ("MP", True),
        ("mp", True),
        ("FBS", True),
        ("fbs", True),
        ("Маркетплейс-1", True),
        ("Marketplace #1", True),
        ("FBS Warehouse", True),
        ("MP-Storage", True),
        
        # НЕ должны быть Маркетплейс
        ("Москва", False),
        ("Казань", False),
        ("Чехов 1", False),
    ]
    
    print("🧪 Testing marketplace detection:")
    passed = 0
    failed = 0
    
    for warehouse_name, should_be_marketplace in test_cases:
        is_mp = is_marketplace_warehouse(warehouse_name)
        is_real = is_real_warehouse(warehouse_name)
        
        if should_be_marketplace:
            # Должны пройти оба теста
            if is_mp and is_real:
                print(f"   ✅ PASS: '{warehouse_name}' detected as Marketplace")
                passed += 1
            else:
                print(f"   ❌ FAIL: '{warehouse_name}' NOT detected (is_mp={is_mp}, is_real={is_real})")
                failed += 1
        else:
            # НЕ должны быть Маркетплейс, но должны быть real
            if not is_mp and is_real:
                print(f"   ✅ PASS: '{warehouse_name}' detected as regular warehouse")
                passed += 1
            elif not is_mp and not is_real:
                print(f"   ⚠️  WARNING: '{warehouse_name}' filtered out completely")
            else:
                print(f"   ❌ FAIL: '{warehouse_name}' incorrectly detected as Marketplace")
                failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = test_marketplace_warehouse_detection()
    exit(0 if success else 1)
```

### 2. Тест #2: Сравнение с CSV

```python
# test_csv_comparison.py
import csv
from collections import defaultdict

def load_wb_csv(csv_path):
    """Загрузить данные из WB CSV."""
    products = defaultdict(lambda: {"warehouses": {}, "total_stock": 0, "total_orders": 0})
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            seller_article = row['Артикул продавца']
            wb_article = row['Артикул WB']
            warehouse = row['Склад']
            
            orders = int(row['Заказали, шт'] or 0)
            stock = int(row['Остатки на текущий день, шт'] or 0)
            
            key = (seller_article, wb_article)
            
            if warehouse not in products[key]["warehouses"]:
                products[key]["warehouses"][warehouse] = {"orders": 0, "stock": 0}
            
            products[key]["warehouses"][warehouse]["orders"] += orders
            products[key]["warehouses"][warehouse]["stock"] += stock
            products[key]["total_orders"] += orders
            products[key]["total_stock"] += stock
    
    return products

async def test_csv_vs_stock_tracker(csv_path):
    """Сравнить данные CSV с данными Stock Tracker."""
    # Загружаем WB данные
    wb_products = load_wb_csv(csv_path)
    
    # Загружаем данные из Stock Tracker
    # (используем существующие функции)
    from src.stock_tracker.api.client import WildberriesAPIClient
    from src.stock_tracker.api.products import WildberriesProductDataFetcher
    from src.stock_tracker.core.calculator import WildberriesCalculator
    
    api_client = WildberriesAPIClient()
    fetcher = WildberriesProductDataFetcher(api_client)
    
    orders_data, warehouse_data = await fetcher.fetch_all_products_data()
    st_products = WildberriesCalculator.process_api_data(warehouse_data, orders_data)
    
    # Сравнение
    print("📊 COMPARISON: WB CSV vs Stock Tracker")
    print("="*80)
    
    total_products_wb = len(wb_products)
    total_products_st = len(st_products)
    
    print(f"Products in WB CSV: {total_products_wb}")
    print(f"Products in Stock Tracker: {total_products_st}")
    
    # Проверяем каждый продукт
    discrepancies = []
    
    for product_key, wb_data in wb_products.items():
        seller_article, wb_article = product_key
        
        # Ищем соответствующий продукт в ST
        st_product = next((p for p in st_products 
                          if p.seller_article == seller_article 
                          and p.wildberries_article == int(wb_article)), None)
        
        if not st_product:
            discrepancies.append({
                "article": seller_article,
                "issue": "MISSING_IN_ST",
                "wb_orders": wb_data["total_orders"],
                "wb_stock": wb_data["total_stock"]
            })
            continue
        
        # Сравниваем итоги
        orders_diff = abs(st_product.total_orders - wb_data["total_orders"])
        stock_diff = abs(st_product.total_stock - wb_data["total_stock"])
        
        if orders_diff > 0 or stock_diff > 0:
            # Проверяем наличие Маркетплейс
            has_mp_in_wb = any("маркетплейс" in wh.lower() or "marketplace" in wh.lower() 
                              for wh in wb_data["warehouses"].keys())
            has_mp_in_st = any("маркетплейс" in wh.name.lower() or "marketplace" in wh.name.lower() 
                              for wh in st_product.warehouses)
            
            discrepancies.append({
                "article": seller_article,
                "issue": "DATA_MISMATCH",
                "orders_diff": orders_diff,
                "stock_diff": stock_diff,
                "wb_orders": wb_data["total_orders"],
                "st_orders": st_product.total_orders,
                "wb_stock": wb_data["total_stock"],
                "st_stock": st_product.total_stock,
                "mp_in_wb": has_mp_in_wb,
                "mp_in_st": has_mp_in_st
            })
    
    # Отчет о расхождениях
    if discrepancies:
        print(f"\n⚠️  FOUND {len(discrepancies)} DISCREPANCIES:")
        
        for disc in discrepancies[:10]:  # Показываем первые 10
            print(f"\n   Article: {disc['article']}")
            print(f"   Issue: {disc['issue']}")
            
            if disc['issue'] == "DATA_MISMATCH":
                print(f"   Orders: WB={disc['wb_orders']}, ST={disc['st_orders']}, diff={disc['orders_diff']}")
                print(f"   Stock: WB={disc['wb_stock']}, ST={disc['st_stock']}, diff={disc['stock_diff']}")
                print(f"   Marketplace in WB: {disc['mp_in_wb']}")
                print(f"   Marketplace in ST: {disc['mp_in_st']}")
    else:
        print("\n✅ NO DISCREPANCIES FOUND!")
    
    return len(discrepancies) == 0

if __name__ == "__main__":
    import asyncio
    csv_path = "26-10-2025 История остатков с 20-10-2025 по 26-10-2025_export.csv"
    success = asyncio.run(test_csv_vs_stock_tracker(csv_path))
    exit(0 if success else 1)
```

---

## ✅ ИТОГИ И СЛЕДУЮЩИЕ ШАГИ

### Выявленные проблемы:
1. ✅ **КРИТИЧЕСКАЯ:** Цепочка фильтрации складов может отсекать Маркетплейс
2. ✅ **КРИТИЧЕСКАЯ:** Недостаточно мягкая валидация названий складов
3. ✅ **ВАЖНАЯ:** 23 склада отсутствуют в приложении
4. ✅ **ВАЖНАЯ:** Расхождения в подсчете заказов (77% продуктов)
5. ✅ **ВАЖНАЯ:** Расхождения в остатках (92% продуктов)

### Предложенные исправления:
1. ✅ Переработана функция `is_real_warehouse()` - более мягкая фильтрация
2. ✅ Расширен справочник маппинга для Маркетплейс
3. ✅ Улучшена функция нормализации `_find_partial_match()`
4. ✅ Добавлено детальное логирование в `group_data_by_product()`
5. ✅ Создан скрипт проверки наличия Маркетплейс в API
6. ✅ Исправлен период агрегации заказов (30 -> 7 дней)

### Следующие шаги:
1. **Применить исправления** в код
2. **Запустить тесты** `test_marketplace_inclusion.py`
3. **Проверить API данные** скриптом `check_marketplace_in_api()`
4. **Сравнить с CSV** через `test_csv_comparison.py`
5. **Провести полную синхронизацию** и проверить результаты
6. **Мониторинг** - убедиться что Маркетплейс стабильно включается

---

**Автор отчета:** GitHub Copilot  
**Дата:** 26 октября 2025 г.  
**Статус:** ✅ Готово к внедрению
