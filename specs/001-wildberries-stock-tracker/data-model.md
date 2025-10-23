# Data Model: Wildberries Stock Tracker

**Date**: 21 октября 2025 г.  
**Feature**: Wildberries Stock Tracker  
**Phase**: 1 - Data Design

## Core Entities

### Product (Товар)

Основная единица учета товаров в системе.

**Fields:**
- `sellerArticle` (string, required) - Артикул продавца (уникальный идентификатор)
- `wildberriesArticle` (string, required) - Артикул товара в системе Wildberries  
- `totalOrders` (number, calculated) - Общее количество заказов по всем складам
- `totalStock` (number, calculated) - Общее количество остатков по всем складам
- `turnover` (number, calculated) - Оборачиваемость (totalOrders/totalStock, 0 если totalStock = 0)
- `warehouses` (Array<Warehouse>) - Массив данных по складам
- `lastUpdated` (Date) - Время последнего обновления данных

**Validation Rules:**
- `sellerArticle` должен быть уникальным в пределах таблицы
- `totalOrders` и `totalStock` должны быть неотрицательными числами
- `warehouses` массив не может быть пустым
- Порядок элементов в `warehouses` должен быть синхронизирован

**State Transitions:**
- Created → Active (при первом добавлении данных)
- Active → Updated (при изменении данных со складов)
- Active → Stale (если данные не обновлялись > 24 часов)

### Warehouse (Склад)

Данные о товаре на конкретном складе.

**Fields:**
- `name` (string, required) - Название склада (warehouseName из API)
- `orders` (number, required) - Количество заказов с этого склада
- `stock` (number, required) - Количество остатков на этом складе
- `lastSync` (Date) - Время последней синхронизации с API

**Validation Rules:**
- `name` не может быть пустым
- `orders` и `stock` должны быть неотрицательными числами
- Один склад может появляться только один раз для одного товара

### SyncSession (Сессия синхронизации)

Метаданные процесса синхронизации с Wildberries API.

**Fields:**
- `sessionId` (string, required) - Уникальный идентификатор сессии
- `startTime` (Date, required) - Время начала синхронизации
- `endTime` (Date) - Время завершения синхронизации
- `status` (enum) - Статус: "running", "completed", "failed"
- `productsProcessed` (number) - Количество обработанных товаров
- `errors` (Array<string>) - Массив ошибок, если есть
- `triggeredBy` (enum) - Источник запуска: "scheduled", "manual"

**Validation Rules:**
- `sessionId` должен быть уникальным
- `endTime` должен быть больше `startTime`
- `productsProcessed` должен быть неотрицательным

## Relationships

### Product ↔ Warehouse (1:N)
- Один товар может иметь данные по множественным складам
- Каждая запись склада принадлежит только одному товару
- Порядок складов в массиве должен сохраняться для корректного отображения в Google Sheets

### SyncSession ↔ Product (1:N)
- Одна сессия синхронизации обрабатывает множественные товары
- Каждое обновление товара связано с конкретной сессией синхронизации

## Data Flow

### Input (from Wildberries API)
```json
{
  "nmId": "12345678",
  "warehouseName": "СЦ Волгоград", 
  "quantity": 654
}
```

### Internal Representation
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Warehouse:
    name: str
    orders: int
    stock: int
    last_sync: datetime

@dataclass 
class Product:
    seller_article: str
    wildberries_article: str
    total_orders: int
    total_stock: int
    turnover: float
    warehouses: List[Warehouse]
    last_updated: datetime
```

### Output (to Google Sheets)
```
| WB001 | 12345678 | 92 | 1107 | 0.083 | СЦ Волгоград\nСЦ Москва | 32\n60 | 654\n453 |
```

## Calculated Fields Logic

### Total Orders Calculation
```python
def calculate_total_orders(warehouses: List[Warehouse]) -> int:
    return sum(warehouse.orders for warehouse in warehouses)
```

### Total Stock Calculation  
```python
def calculate_total_stock(warehouses: List[Warehouse]) -> int:
    return sum(warehouse.stock for warehouse in warehouses)
```

### Turnover Calculation
```python
def calculate_turnover(total_orders: int, total_stock: int) -> float:
    return 0.0 if total_stock == 0 else total_orders / total_stock
```

## Data Integrity Rules

1. **Uniqueness**: `sellerArticle` должен быть уникальным в пределах всей таблицы
2. **Consistency**: Порядок складов в `warehouses` массиве должен соответствовать порядку отображения в Google Sheets
3. **Completeness**: Все склады для товара должны иметь актуальные данные на момент последней синхронизации
4. **Validation**: Все числовые поля должны быть неотрицательными