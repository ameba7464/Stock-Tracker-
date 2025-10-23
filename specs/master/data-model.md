# Data Model: Google Sheets Stock Tracker

**Date**: 21 октября 2025 г.  
**Purpose**: Определение структур данных и их отношений для Stock Tracker

## Core Entities

### 1. Product (Товар)
**Purpose**: Представление товара в системе учета

**Fields**:
- `sellerArticle: string` - Артикул продавца (уникальный идентификатор)
- `productArticle: string` - Артикул товара в системе Wildberries  
- `totalOrders: number` - Общее количество заказов по всем складам
- `totalStock: number` - Общее количество остатков по всем складам
- `turnover: number` - Коэффициент оборачиваемости (calculated)
- `warehouses: Warehouse[]` - Массив данных по складам

**Validation Rules**:
- `sellerArticle` - обязательное, уникальное в пределах таблицы
- `productArticle` - обязательное, строка
- `totalOrders, totalStock` - неотрицательные числа
- `turnover` - calculated field (totalOrders/totalStock), handle division by zero
- `warehouses` - минимум 1 элемент

**Business Rules**:
- Один товар может быть представлен на нескольких складах
- `totalOrders` и `totalStock` автоматически вычисляются из данных складов
- При `totalStock = 0`, `turnover = ∞` (отображается как "∞")

### 2. Warehouse (Склад)
**Purpose**: Данные о товаре на конкретном складе

**Fields**:
- `name: string` - Название склада
- `orders: number` - Количество заказов с данного склада
- `stock: number` - Количество остатков на складе

**Validation Rules**:
- `name` - обязательное, не пустая строка
- `orders, stock` - неотрицательные числа

**Business Rules**:
- Порядок складов должен быть синхронизирован в колонках F, G, H
- Склады с нулевыми показателями включаются в отчет

### 3. APIResponse (Ответ API)
**Purpose**: Структура данных от Wildberries API

**WildberriesStock**:
```typescript
interface WildberriesStock {
  nmId: number;           // Product ID
  vendorCode: string;     // Seller article
  stocks: StockWarehouse[];
}

interface StockWarehouse {
  warehouseName: string;
  quantity: number;
}
```

**WildberriesOrders**:
```typescript
interface WildberriesOrders {
  nmId: number;           // Product ID  
  vendorCode: string;     // Seller article
  orders: OrderWarehouse[];
}

interface OrderWarehouse {
  warehouseName: string;
  quantity: number;
  date: string;           // ISO date
}
```

**Validation Rules**:
- API response должен содержать валидные nmId и vendorCode
- Warehouse names должны быть не пустыми
- Quantities должны быть неотрицательными
- Dates должны быть в валидном ISO формате

## Data Transformations

### 1. API to Product Mapping
**Input**: WildberriesStock[] + WildberriesOrders[]  
**Output**: Product[]

**Algorithm**:
1. Group by `vendorCode` (seller article)
2. Merge stock and orders data by warehouse name
3. Calculate totals and turnover
4. Format for Google Sheets display

**Pseudo-code**:
```javascript
function transformAPIData(stocks, orders) {
  const productMap = new Map();
  
  // Process stocks
  stocks.forEach(stock => {
    const product = getOrCreateProduct(productMap, stock.vendorCode);
    product.productArticle = stock.nmId.toString();
    stock.stocks.forEach(warehouse => {
      addWarehouseData(product, warehouse.warehouseName, 0, warehouse.quantity);
    });
  });
  
  // Process orders (7-day aggregation)
  orders.forEach(order => {
    const product = productMap.get(order.vendorCode);
    if (product) {
      order.orders.forEach(warehouse => {
        updateWarehouseOrders(product, warehouse.warehouseName, warehouse.quantity);
      });
    }
  });
  
  // Calculate totals and turnover
  Array.from(productMap.values()).forEach(calculateTotals);
  
  return Array.from(productMap.values());
}
```

### 2. Product to Sheets Format
**Input**: Product[]  
**Output**: SheetRow[]

**SheetRow Structure**:
```javascript
interface SheetRow {
  sellerArticle: string;     // Column A
  productArticle: string;    // Column B  
  totalOrders: number;       // Column C
  totalStock: number;        // Column D
  turnover: number;          // Column E
  warehouseNames: string;    // Column F (newline separated)
  warehouseOrders: string;   // Column G (newline separated)
  warehouseStock: string;    // Column H (newline separated)
}
```

**Formatting Rules**:
- Warehouse data separated by `\n` (newline character)
- Order preserved across columns F, G, H
- Turnover formatted to 3 decimal places
- Empty warehouses included to maintain alignment

## State Transitions

### Update Cycle State Machine

**States**:
1. `IDLE` - Waiting for scheduled trigger
2. `FETCHING_API` - Retrieving data from Wildberries
3. `PROCESSING` - Transforming and aggregating data
4. `UPDATING_SHEETS` - Writing to Google Sheets
5. `COMPLETED` - Update successful
6. `ERROR` - Update failed (with retry logic)

**Transitions**:
- `IDLE → FETCHING_API` (daily trigger at 00:00)
- `FETCHING_API → PROCESSING` (API data received)
- `PROCESSING → UPDATING_SHEETS` (data transformed)
- `UPDATING_SHEETS → COMPLETED` (sheets updated)
- `Any → ERROR` (on exception)
- `ERROR → FETCHING_API` (on retry)
- `ERROR → IDLE` (after max retries)

**State Persistence**:
- Current state stored in Google Apps Script Properties
- Progress tracking for partial updates
- Error state includes retry count and last error message

## Data Quality Constraints

### Input Validation
- API responses must pass schema validation
- Numeric fields cannot be negative
- Required fields cannot be null/undefined
- Seller articles must be unique per update cycle

### Output Validation  
- Sheet rows must have exactly 8 columns
- Warehouse data alignment must be verified
- Turnover calculations must handle edge cases
- Format consistency across all rows

### Consistency Rules
- Total orders/stock must equal sum of warehouse values
- Warehouse order must be preserved across columns
- Empty string handling for missing warehouse data
- Timezone consistency for date-based filtering

## Error Handling

### Data Validation Errors
- **Invalid API Response**: Skip malformed records, log warnings
- **Missing Required Fields**: Use default values where possible
- **Negative Values**: Set to 0, log correction
- **Duplicate Seller Articles**: Use latest data, log collision

### Business Logic Errors
- **Division by Zero**: Set turnover to "∞", continue processing
- **Warehouse Mismatch**: Align by name, fill missing with 0
- **Format Errors**: Apply default formatting, log issue
- **Overflow Values**: Truncate/format for display, preserve raw data

### Recovery Strategies
- **Partial Data Loss**: Continue with available data
- **Complete API Failure**: Retry with exponential backoff
- **Sheets Write Failure**: Batch retry with smaller chunks
- **Validation Failures**: Quarantine invalid records, process valid ones

## Performance Considerations

### Memory Usage
- Stream processing for large datasets (>1000 products)
- Intermediate cleanup after each processing stage
- Efficient data structures (Maps vs Objects)

### Processing Optimization
- Batch API requests where possible
- Parallel processing of independent operations
- Early validation to fail fast on bad data

### Sheets Operations
- Bulk updates instead of row-by-row writes
- Minimize API calls to Google Sheets
- Efficient range operations for large datasets

## Schema Evolution

### Versioning Strategy
- Data model version stored in sheet metadata
- Backward compatibility for minor changes
- Migration scripts for major structural changes

### Future Extensions
- Additional calculated fields (profit margins, velocity)
- Historical data retention beyond 7 days  
- Multi-currency support for international sales
- Category-based grouping and analysis

**Next Phase**: Contract definitions and quickstart documentation