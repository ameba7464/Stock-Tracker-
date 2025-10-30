# 🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМЫ FBS ОСТАТКОВ

**Дата анализа:** 30 октября 2025  
**Проблема:** Остатки Fulllog FBS не записываются корректно для некоторых артикулов

---

## 📊 ТЕКУЩАЯ СИТУАЦИЯ

### Артикулы с ПРОБЛЕМАМИ:

| Артикул | WB Остатки (Маркетплейс) | Tracker Остатки (Fulllog FBS) | Разница |
|---------|-------------------------|-------------------------------|---------|
| **Its2/50g** | **1884 шт** | **0 шт** | ❌ **-1884** |
| **ItsSport2/50g** | **957 шт** | **0 шт** | ❌ **-957** |
| Its1_2_3/50g | 2815 шт | Отсутствует в таблице | ❌ Не отслеживается |

### Артикулы БЕЗ ПРОБЛЕМ:

| Артикул | WB Остатки | Tracker Остатки | Статус |
|---------|------------|-----------------|--------|
| Its2/50g+Aks5/20g.FBS | 175 | 175 | ✅ |
| ItsSport2/50g+Aks5/20g.FBS | 175 | 175 | ✅ |
| Its1_2_3/50g+Aks5/20g.FBS | 175 | 175 | ✅ |
| Its1_2_3/50g+AksRecov/20g | 185 | 185 | ✅ |

---

## 🔎 КЛЮЧЕВОЕ НАБЛЮДЕНИЕ

### Закономерность проблемы:

1. ✅ **Артикулы с `.FBS` в названии** → Остатки ЗАПИСЫВАЮТСЯ правильно
2. ❌ **Артикулы БЕЗ `.FBS` в названии** → Остатки с Маркетплейса ТЕРЯЮТСЯ

**Пример:**
- `Its2/50g+Aks5/20g.FBS` (552086752) → ✅ 175 остатков учитываются
- `Its2/50g` (163383327) → ❌ 1884 остатка НЕ учитываются

---

## 🧩 АРХИТЕКТУРА ОБРАБОТКИ FBS

### 1. Источники данных:

```
┌─────────────────────────────────────────────────────────┐
│         WILDBERRIES API v1 (Statistics API)             │
│    GET /api/v1/supplier/stocks                         │
│                                                          │
│  Возвращает остатки ПО ВСЕМ складам:                    │
│  • FBO склады (Чехов, Коледино, Краснодар...)          │
│  • FBS склады (Маркетплейс, Склад продавца)            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              ОБРАБОТКА В calculator.py                   │
│       group_data_by_product()                           │
│                                                          │
│  1. Парсит все склады из API                            │
│  2. Нормализует названия через normalize_warehouse_name()│
│  3. Фильтрует через is_real_warehouse()                 │
│  4. Определяет FBS через is_marketplace_warehouse()     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│           ЗАПИСЬ В GOOGLE SHEETS                        │
│      operations.py → create_product()                   │
│                                                          │
│  Форматирует и записывает данные в таблицу             │
└─────────────────────────────────────────────────────────┘
```

---

## 🐛 КОРНЕВАЯ ПРИЧИНА ПРОБЛЕМЫ

### Гипотеза #1: Различие в структуре данных API

**Артикулы ДВА ТИПА:**

#### Тип A: Артикулы С суффиксом `.FBS` в vendorCode
```json
{
  "nmId": 552086752,
  "vendorCode": "Its2/50g+Aks5/20g.FBS",
  "warehouses": [
    {
      "warehouseName": "Маркетплейс",
      "quantity": 175
    }
  ]
}
```
**Результат:** ✅ Склад "Маркетплейс" корректно записывается как "Fulllog FBS"

#### Тип B: Артикулы БЕЗ суффикса `.FBS`
```json
{
  "nmId": 163383327,
  "vendorCode": "Its2/50g",
  "warehouses": [
    {
      "warehouseName": "Маркетплейс",
      "quantity": 1884
    },
    {
      "warehouseName": "Чехов 1", 
      "quantity": 212
    },
    // ... другие склады
  ]
}
```
**Результат:** ❌ Склад "Маркетплейс" НЕ записывается!

---

## 🔍 АНАЛИЗ КОДА

### Проблемная логика в `group_data_by_product()`:

```python
# Строка 531 - calculator.py
warehouse_name = normalize_warehouse_name(warehouse_name_raw)

# Строка 537 - Проверка реальности склада
if warehouse_name and is_real_warehouse(warehouse_name):
    
    # Строка 539 - Проверка Маркетплейса
    if is_marketplace_warehouse(warehouse_name):
        marketplace_warehouses_detected.append({...})
        logger.info(f"🏪 MARKETPLACE INCLUDED: '{warehouse_name_raw}'...")
```

### Проблема: normalize_warehouse_name()

**Файл:** `src/stock_tracker/utils/warehouse_mapper.py`

```python
def normalize_warehouse_name(raw_name: str) -> str:
    """Нормализует название склада согласно карте известных складов."""
    
    # Шаг 1: Поиск в CANONICAL_WAREHOUSE_MAP
    for canonical, variations in CANONICAL_WAREHOUSE_MAP.items():
        for variation in variations:
            if variation.lower() == raw_name.lower():
                return canonical  # ✅ Возвращает "Маркетплейс"
    
    # Шаг 2: Если не найдено - возвращает оригинал
    return raw_name  # ⚠️ Может вернуть неизвестное название
```

### Критическая карта: CANONICAL_WAREHOUSE_MAP

```python
CANONICAL_WAREHOUSE_MAP = {
    "Маркетплейс": [
        "Маркетплейс", "маркетплейс", "МАРКЕТПЛЕЙС",
        "Marketplace", "marketplace", "MARKETPLACE",
        "Маркетплейс-1", "Маркетплейс 1", "Маркетплейс1",
        # ... около 30 вариантов
    ],
    # ... другие склады
}
```

---

## 🎯 ВОЗМОЖНЫЕ ПРИЧИНЫ

### Теория #1: Различное написание "Маркетплейс" в API

**Вероятность:** 🟡 Средняя

WB API может возвращать разные варианты написания для разных типов товаров:
- Для FBS товаров: `"Маркетплейс"` (стандартный)
- Для обычных товаров: `"Маркетплейс "` (с пробелом), `"МП"`, `"Marketplace"`, etc.

**Проверка:**
```python
# Нужно залогировать RAW названия из API для проблемных артикулов
logger.info(f"RAW warehouse name from API: '{warehouse_name_raw}' (repr: {repr(warehouse_name_raw)})")
```

### Теория #2: Логика is_real_warehouse() отфильтровывает склад

**Вероятность:** 🔴 Высокая

**Файл:** `src/stock_tracker/core/calculator.py`, строка 65

```python
def is_real_warehouse(warehouse_name: str) -> bool:
    # ... проверки ...
    
    # ПРИОРИТЕТ #1 - Маркетплейс/FBS склады
    marketplace_indicators = [
        "маркетплейс", "marketplace", 
        "склад продавца", "склад селлера",
        "fbs", "fulfillment by seller",
        "мп", "mp",  # БЕЗ пробелов
    ]
    
    if any(indicator in warehouse_name_lower for indicator in marketplace_indicators):
        logger.info(f"✅ Marketplace/FBS warehouse: {warehouse_name}")
        return True
```

**Проблема:** Если `normalize_warehouse_name()` возвращает что-то КРОМЕ стандартных вариантов, а индикаторы не находятся - склад будет отфильтрован!

### Теория #3: Проблема в записи в Sheets (formatter.py)

**Вероятность:** 🟢 Низкая

При записи в таблицу используется `warehouse_mapper.py` для преобразования названий:

```python
# warehouse_mapper.py
def map_warehouse_to_display_name(canonical_name: str) -> str:
    """Маппинг канонических названий в отображаемые."""
    display_map = {
        "Маркетплейс": "Fulllog FBS",
        # ...
    }
    return display_map.get(canonical_name, canonical_name)
```

Если каноническое имя не "Маркетплейс", оно не будет преобразовано в "Fulllog FBS".

---

## 🔬 ТЕСТОВЫЙ СЦЕНАРИЙ

### Шаг 1: Добавить детальное логирование

```python
# В group_data_by_product(), строка ~520
for warehouse in item["warehouses"]:
    warehouse_name_raw = warehouse.get("warehouseName", "")
    quantity = warehouse.get("quantity", 0)
    
    # 🔍 ДОБАВИТЬ ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
    logger.info(f"🔍 WAREHOUSE DEBUG:")
    logger.info(f"   Article: {supplier_article} (nmId: {nm_id})")
    logger.info(f"   Raw name: '{warehouse_name_raw}' (repr: {repr(warehouse_name_raw)})")
    logger.info(f"   Quantity: {quantity}")
    
    warehouse_name = normalize_warehouse_name(warehouse_name_raw)
    logger.info(f"   Normalized: '{warehouse_name}'")
    
    is_real = is_real_warehouse(warehouse_name)
    logger.info(f"   is_real_warehouse: {is_real}")
    
    is_marketplace = is_marketplace_warehouse(warehouse_name)
    logger.info(f"   is_marketplace_warehouse: {is_marketplace}")
    
    if not is_real:
        logger.warning(f"   ❌ WAREHOUSE FILTERED OUT!")
```

### Шаг 2: Запустить синхронизацию для проблемного артикула

```bash
python update_table_fixed.py
# Или через тест:
python -c "from stock_tracker.core.calculator import WildberriesCalculator; ..."
```

### Шаг 3: Анализировать логи

Искать паттерны:
- Какое RAW название приходит для "Its2/50g" vs "Its2/50g+Aks5/20g.FBS"
- Проходит ли проверку `is_real_warehouse()`
- Какое нормализованное имя получается

---

## 💡 РЕШЕНИЯ

### Решение #1: Расширить CANONICAL_WAREHOUSE_MAP (Временное)

**Файл:** `src/stock_tracker/utils/warehouse_mapper.py`

```python
CANONICAL_WAREHOUSE_MAP = {
    "Маркетплейс": [
        # Существующие варианты...
        "Маркетплейс", "marketplace",
        
        # 🆕 ДОБАВИТЬ ВОЗМОЖНЫЕ ВАРИАНТЫ
        "Склад продавца",
        "Seller warehouse",
        "FBS",
        "Fulfillment by Seller",
        "МП",
        "MP",
        # Все с пробелами
        "Маркетплейс ", 
        "Marketplace ",
        " Маркетплейс",
        " Marketplace",
    ],
}
```

**Плюсы:** 
- ✅ Быстрое решение
- ✅ Минимальные изменения кода

**Минусы:**
- ❌ Не решает корневую проблему
- ❌ Может потребоваться постоянное обновление

### Решение #2: Улучшить normalize_warehouse_name() (Рекомендуется)

**Добавить нечеткое сравнение:**

```python
def normalize_warehouse_name(raw_name: str) -> str:
    """Нормализует название склада с улучшенной логикой."""
    if not raw_name:
        return ""
    
    # Очистка
    cleaned = raw_name.strip()
    cleaned_lower = cleaned.lower()
    
    # Шаг 1: Точное совпадение
    for canonical, variations in CANONICAL_WAREHOUSE_MAP.items():
        for variation in variations:
            if variation.lower() == cleaned_lower:
                return canonical
    
    # 🆕 Шаг 2: Нечеткое совпадение для Маркетплейса
    marketplace_fuzzy = [
        "маркет", "market", "мп", "mp",
        "склад продавца", "seller", "fbs"
    ]
    
    if any(indicator in cleaned_lower for indicator in marketplace_fuzzy):
        logger.info(f"✅ Fuzzy match detected Marketplace: '{raw_name}'")
        return "Маркетплейс"
    
    # Шаг 3: Точное совпадение для других складов
    # ...
    
    # Шаг 4: Возврат оригинала
    return cleaned
```

### Решение #3: Добавить fallback в is_real_warehouse()

**Файл:** `src/stock_tracker/core/calculator.py`

```python
def is_real_warehouse(warehouse_name: str) -> bool:
    """Проверить является ли склад реальным (не виртуальным)."""
    
    # ... существующая логика ...
    
    # 🆕 FALLBACK: Если количество > 0 и название не пустое
    # И не содержит исключающих паттернов - ВКЛЮЧАЕМ
    excluding_patterns = ["в пути", "in transit", "виртуальн", "virtual"]
    
    if warehouse_name and len(warehouse_name) > 2:
        has_excluding = any(pattern in warehouse_name_lower for pattern in excluding_patterns)
        if not has_excluding:
            logger.info(f"✅ Warehouse included by fallback: {warehouse_name}")
            return True
    
    return False
```

### Решение #4: Использовать warehouseType из API (ИДЕАЛЬНОЕ)

**Проблема:** WB API `/api/v1/supplier/stocks` НЕ возвращает `warehouseType`

**Решение:** Использовать данные из `/supplier/orders` для классификации:

```python
# В group_data_by_product()
# При обработке warehouse_remains_data сохранять mapping:
warehouse_type_map = {}  # {warehouse_name: warehouse_type}

# При обработке orders_data заполнять:
for order in orders_data:
    wh_name = order.get("warehouseName")
    wh_type = order.get("warehouseType")  # "Склад WB" или "Склад продавца"
    if wh_name and wh_type:
        warehouse_type_map[wh_name] = wh_type

# При создании складов использовать:
if warehouse_name not in group["warehouses"]:
    warehouse_type = warehouse_type_map.get(warehouse_name, "unknown")
    is_fbs = warehouse_type == "Склад продавца"
    
    group["warehouses"][warehouse_name] = {
        "stock": quantity,
        "orders": 0,
        "warehouse_type": warehouse_type,
        "is_fbs": is_fbs,  # ✅ Точное определение из API
        "raw_name": warehouse_name_raw
    }
```

---

## 🚨 КРИТИЧЕСКИЕ ТОЧКИ ПРОВЕРКИ

### 1. Входные данные API

```python
# Добавить в начало group_data_by_product()
logger.info("="*80)
logger.info("🔍 API INPUT DATA DEBUG")
logger.info("="*80)

for item in warehouse_remains_data:
    if item.get("vendorCode") in ["Its2/50g", "ItsSport2/50g"]:
        logger.info(f"\n📦 Product: {item.get('vendorCode')} (nmId: {item.get('nmId')})")
        logger.info(f"   Warehouses count: {len(item.get('warehouses', []))}")
        for wh in item.get("warehouses", []):
            logger.info(f"   - '{wh.get('warehouseName')}': {wh.get('quantity')} шт")
```

### 2. Нормализация

```python
# В normalize_warehouse_name()
result = # ... логика нормализации ...

if "маркет" in raw_name.lower() or "market" in raw_name.lower():
    logger.info(f"🔍 NORMALIZATION: '{raw_name}' -> '{result}'")
    
return result
```

### 3. Фильтрация

```python
# В is_real_warehouse()
result = # ... логика проверки ...

if not result and ("маркет" in warehouse_name.lower() or "мп" in warehouse_name.lower()):
    logger.warning(f"⚠️ POTENTIAL MARKETPLACE FILTERED: '{warehouse_name}'")
    
return result
```

### 4. Запись в словарь

```python
# В group_data_by_product() после создания warehouse
logger.info(f"✅ Warehouse STORED:")
logger.info(f"   Key: {warehouse_name}")
logger.info(f"   Stock: {group['warehouses'][warehouse_name]['stock']}")
logger.info(f"   is_fbs: {group['warehouses'][warehouse_name]['is_fbs']}")
```

---

## 📋 ПЛАН ДЕЙСТВИЙ

### Фаза 1: Диагностика (30 минут)

1. ✅ Добавить детальное логирование во все критические точки
2. ✅ Запустить синхронизацию
3. ✅ Проанализировать логи для артикулов Its2/50g и ItsSport2/50g
4. ✅ Определить точное место потери данных

### Фаза 2: Исправление (1 час)

**Если проблема в нормализации:**
- Расширить CANONICAL_WAREHOUSE_MAP
- Добавить нечеткое сравнение

**Если проблема в фильтрации:**
- Улучшить is_real_warehouse()
- Добавить fallback логику

**Если проблема в классификации FBS:**
- Использовать warehouseType из orders
- Улучшить is_marketplace_warehouse()

### Фаза 3: Тестирование (30 минут)

1. Запустить полную синхронизацию
2. Проверить что проблемные артикулы теперь имеют Fulllog FBS остатки
3. Убедиться что другие артикулы не сломались
4. Запустить сравнительный скрипт `compare_wb_vs_tracker.py`

### Фаза 4: Документация (15 минут)

1. Обновить CHANGELOG
2. Задокументировать найденную проблему
3. Добавить комментарии в код

---

## 🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После исправления:

| Артикул | WB Остатки | Tracker Остатки | Статус |
|---------|------------|-----------------|--------|
| Its2/50g | 1884 | 1884 | ✅ ИСПРАВЛЕНО |
| ItsSport2/50g | 957 | 957 | ✅ ИСПРАВЛЕНО |
| Its1_2_3/50g | 2815 | 2815 | ✅ ДОБАВЛЕНО |

**Критерий успеха:** 100% совпадение остатков "Маркетплейс" (WB) = "Fulllog FBS" (Tracker) для ВСЕХ артикулов.

---

## 🔗 СВЯЗАННЫЕ ФАЙЛЫ

### Для модификации:
- `src/stock_tracker/core/calculator.py` - группировка данных
- `src/stock_tracker/utils/warehouse_mapper.py` - нормализация складов
- `src/stock_tracker/database/formatter.py` - форматирование для Sheets

### Для проверки:
- `update_table_fixed.py` - скрипт синхронизации
- `compare_wb_vs_tracker.py` - скрипт сравнения
- Логи синхронизации в консоли

---

**Следующий шаг:** Запустить диагностику с детальным логированием для выявления точной причины.
