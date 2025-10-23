# API Contracts: Stock Tracker

**Version**: 1.0  
**Date**: 21 октября 2025 г.  
**Purpose**: Определение интерфейсов для интеграции с Wildberries API и Google Sheets

## Wildberries API Contracts

### Authentication
```http
Authorization: Bearer {api_token}
Content-Type: application/json
```

### 1. Get Stocks Endpoint

**Endpoint**: `GET /api/v3/stocks`  
**Purpose**: Получение текущих остатков по складам

**Request Parameters**:
```typescript
interface StocksRequest {
  dateFrom?: string;  // ISO date, optional filter
}
```

**Response Schema**:
```typescript
interface StocksResponse {
  stocks: Stock[];
}

interface Stock {
  lastChangeDate: string;    // ISO datetime
  supplierArticle: string;   // Seller article ID
  techSize: string;         // Size variant
  barcode: string;          // Product barcode  
  quantity: number;         // Available quantity
  isSupply: boolean;        // Is in supply
  isRealization: boolean;   // Is in realization
  quantityFull: number;     // Total quantity
  warehouseName: string;    // Warehouse name
  nmId: number;            // Wildberries product ID
  subject: string;         // Product category
  category: string;        // Product category
  daysOnSite: number;      // Days since publication
  brand: string;           // Brand name
  SCCode: string;          // Supply code
}
```

**Error Responses**:
```typescript
interface APIError {
  error: string;
  message: string;
  code: number;
}
```

**Example Request**:
```http
GET /api/v3/stocks?dateFrom=2025-10-14T00:00:00Z
Authorization: Bearer your_api_token
```

**Example Response**:
```json
{
  "stocks": [
    {
      "lastChangeDate": "2025-10-21T10:30:00Z",
      "supplierArticle": "WB001",
      "techSize": "M",
      "barcode": "1234567890123",
      "quantity": 150,
      "isSupply": true,
      "isRealization": false,
      "quantityFull": 150,
      "warehouseName": "СЦ Волгоград",
      "nmId": 12345678,
      "subject": "Одежда",
      "category": "Футболки",
      "daysOnSite": 45,
      "brand": "MyBrand",
      "SCCode": "SC001"
    }
  ]
}
```

### 2. Get Orders Endpoint

**Endpoint**: `GET /api/v3/orders`  
**Purpose**: Получение заказов за период

**Request Parameters**:
```typescript
interface OrdersRequest {
  dateFrom: string;  // ISO date, required (7 days ago)
  flag?: number;     // 0-new orders, 1-all orders (default 1)
}
```

**Response Schema**:
```typescript
interface OrdersResponse {
  orders: Order[];
}

interface Order {
  gNumber: string;          // Order number
  date: string;            // Order date ISO
  lastChangeDate: string;   // Last change ISO
  supplierArticle: string;  // Seller article
  techSize: string;        // Size variant
  barcode: string;         // Product barcode
  quantity: number;        // Order quantity
  totalPrice: number;      // Total price
  discountPercent: number; // Discount percentage
  warehouseName: string;   // Warehouse name
  oblast: string;          // Region
  incomeID: number;        // Income ID
  nmId: number;           // Wildberries product ID
  odid: number;           // Order detail ID
  subject: string;        // Product category
  category: string;       // Product category
  brand: string;          // Brand name
  isCancel: boolean;      // Is cancelled
  cancel_dt: string;      // Cancel datetime
}
```

**Example Request**:
```http
GET /api/v3/orders?dateFrom=2025-10-14T00:00:00Z&flag=1
Authorization: Bearer your_api_token
```

### 3. Rate Limiting

**Limits**:
- 10 requests per second
- 1000 requests per hour
- Retry-After header in 429 responses

**Rate Limit Headers**:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1634567890
```

## Google Sheets API Contracts

### 1. Spreadsheet Operations

**Read Range**:
```typescript
interface ReadRangeRequest {
  spreadsheetId: string;
  range: string;          // "Sheet1!A1:H100"
  valueRenderOption?: string; // "FORMATTED_VALUE" | "UNFORMATTED_VALUE"
}

interface ReadRangeResponse {
  range: string;
  majorDimension: string;
  values: string[][];
}
```

**Write Range**:
```typescript
interface WriteRangeRequest {
  spreadsheetId: string;
  range: string;
  valueInputOption: string; // "RAW" | "USER_ENTERED"
  values: any[][];
}

interface WriteRangeResponse {
  spreadsheetId: string;
  updatedRange: string;
  updatedRows: number;
  updatedColumns: number;
  updatedCells: number;
}
```

### 2. Batch Operations

**Batch Update**:
```typescript
interface BatchUpdateRequest {
  spreadsheetId: string;
  requests: UpdateRequest[];
}

interface UpdateRequest {
  updateCells?: UpdateCellsRequest;
  repeatCell?: RepeatCellRequest;
  autoResize?: AutoResizeRequest;
}
```

## Internal Service Contracts

### 1. WildberriesAPI Service

```typescript
interface WildberriesAPIService {
  /**
   * Get current stock levels for all products
   */
  getStocks(dateFrom?: Date): Promise<Stock[]>;
  
  /**
   * Get orders for specified date range
   */
  getOrders(dateFrom: Date, dateTo?: Date): Promise<Order[]>;
  
  /**
   * Health check for API availability
   */
  healthCheck(): Promise<boolean>;
}
```

### 2. DataProcessor Service

```typescript
interface DataProcessorService {
  /**
   * Transform API data to internal format
   */
  transformStockData(stocks: Stock[], orders: Order[]): Promise<Product[]>;
  
  /**
   * Aggregate data by time period
   */
  aggregateByPeriod(data: Product[], days: number): Promise<Product[]>;
  
  /**
   * Calculate business metrics
   */
  calculateMetrics(products: Product[]): Promise<Product[]>;
}
```

### 3. SheetsManager Service

```typescript
interface SheetsManagerService {
  /**
   * Initialize spreadsheet with headers
   */
  initializeSheet(spreadsheetId: string): Promise<void>;
  
  /**
   * Update sheet with product data
   */
  updateProductData(spreadsheetId: string, products: Product[]): Promise<void>;
  
  /**
   * Clear existing data
   */
  clearData(spreadsheetId: string): Promise<void>;
  
  /**
   * Apply formatting to sheet
   */
  applyFormatting(spreadsheetId: string): Promise<void>;
}
```

### 4. Scheduler Service

```typescript
interface SchedulerService {
  /**
   * Set up daily trigger
   */
  setupDailyTrigger(time: string): Promise<void>;
  
  /**
   * Execute update cycle
   */
  executeUpdate(): Promise<UpdateResult>;
  
  /**
   * Get last update status
   */
  getLastUpdateStatus(): Promise<UpdateStatus>;
}
```

## Error Handling Contracts

### 1. Standard Error Format

```typescript
interface ServiceError {
  code: string;           // ERROR_CODE
  message: string;        // Human readable message
  details?: any;         // Additional context
  timestamp: string;     // ISO datetime
  retryable: boolean;    // Can operation be retried
}
```

### 2. Error Codes

```typescript
enum ErrorCodes {
  // API Errors
  API_AUTHENTICATION_FAILED = "API_AUTH_FAILED",
  API_RATE_LIMIT_EXCEEDED = "API_RATE_LIMIT",
  API_NETWORK_ERROR = "API_NETWORK_ERROR",
  API_INVALID_RESPONSE = "API_INVALID_RESPONSE",
  
  // Data Processing Errors  
  DATA_VALIDATION_FAILED = "DATA_VALIDATION_FAILED",
  DATA_TRANSFORMATION_ERROR = "DATA_TRANSFORMATION_ERROR",
  AGGREGATION_ERROR = "AGGREGATION_ERROR",
  
  // Sheets Errors
  SHEETS_PERMISSION_DENIED = "SHEETS_PERMISSION_DENIED",
  SHEETS_QUOTA_EXCEEDED = "SHEETS_QUOTA_EXCEEDED",
  SHEETS_WRITE_ERROR = "SHEETS_WRITE_ERROR",
  
  // System Errors
  TIMEOUT_ERROR = "TIMEOUT_ERROR",
  MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED",
  EXECUTION_LIMIT_EXCEEDED = "EXECUTION_LIMIT_EXCEEDED"
}
```

## Configuration Contracts

### 1. Application Config

```typescript
interface AppConfig {
  // API Settings
  wildberries: {
    apiToken: string;
    baseUrl: string;
    rateLimitDelay: number;
    maxRetries: number;
    timeout: number;
  };
  
  // Google Sheets Settings
  sheets: {
    spreadsheetId: string;
    sheetName: string;
    headerRow: number;
    dataStartRow: number;
  };
  
  // Scheduler Settings
  scheduler: {
    timezone: string;
    updateTime: string;     // "00:00"
    enabled: boolean;
  };
  
  // Processing Settings
  processing: {
    dataRetentionDays: number;
    batchSize: number;
    maxProducts: number;
  };
}
```

### 2. Runtime State

```typescript
interface RuntimeState {
  lastUpdate: string;      // ISO datetime
  status: UpdateStatus;
  processedProducts: number;
  errors: ServiceError[];
  performance: {
    apiCallDuration: number;
    processingDuration: number;
    sheetsUpdateDuration: number;
    totalDuration: number;
  };
}

enum UpdateStatus {
  IDLE = "idle",
  RUNNING = "running", 
  COMPLETED = "completed",
  FAILED = "failed",
  PARTIAL = "partial"
}
```

## Testing Contracts

### 1. Mock Data Interfaces

```typescript
interface MockDataProvider {
  generateStocks(count: number): Stock[];
  generateOrders(count: number): Order[];
  generateProducts(count: number): Product[];
}
```

### 2. Test Scenarios

```typescript
interface TestScenario {
  name: string;
  description: string;
  mockData: any;
  expectedResult: any;
  validations: string[];
}
```

**Validation Notes**:
- All timestamps must be in ISO 8601 format
- Numeric values must be non-negative unless specified
- String fields must not contain null/undefined unless marked optional
- Array fields must not be null (empty arrays allowed)
- Error handling must include retry logic where applicable