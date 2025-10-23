# API Contracts: Wildberries Stock Tracker

**Date**: 21 октября 2025 г.  
**Feature**: Wildberries Stock Tracker  
**Phase**: 1 - API Design

## Python Module Interfaces

### SyncService (services/sync.py)
Manual and scheduled synchronization operations.

```python
class SyncService:
    def trigger_sync(self, sync_type: str = "manual", user: str = "system") -> SyncSession:
        """Trigger immediate synchronization"""
        
    def get_sync_status(self, session_id: str) -> SyncSession:
        """Get synchronization session status"""
        
    def is_sync_running(self) -> bool:
        """Check if synchronization is currently running"""
```

### ProductService (services/analytics.py)
Product data management and analytics.

```python
class ProductService:
    def get_products(self, limit: int = 50, offset: int = 0, 
                    updated_since: datetime = None) -> List[Product]:
        """Get products with pagination and filtering"""
        
    def create_or_update_product(self, seller_article: str, 
                               wildberries_article: str,
                               warehouses: List[Warehouse]) -> Product:
        """Create or update product data"""
        
    def calculate_turnover(self, product: Product) -> float:
        """Calculate product turnover ratio"""
```

### SheetsService (database/sheets.py)
Google Sheets integration operations.

```python
class SheetsService:
    def __init__(self, service_account_path: str, sheet_id: str):
        """Initialize with Google service account credentials"""
        
    def read_sheet_data(self) -> List[List[str]]:
        """Read all data from the sheet"""
        
    def batch_update_products(self, products: List[Product]) -> bool:
        """Update multiple products in batch operation"""
        
    def format_sheet_headers(self) -> bool:
        """Apply formatting to sheet headers"""
```

### WildberriesAPI (api/client.py)
Wildberries API integration - MUST follow urls.md exactly.

```python
class WildberriesAPI:
    def __init__(self, api_key: str, base_url: str):
        """Initialize API client with credentials"""
        
    def create_warehouse_remains_task(self, **params) -> str:
        """Create task via /api/v1/warehouse_remains endpoint (see urls.md)"""
        
    def download_warehouse_remains(self, task_id: str) -> List[Dict]:
        """Download results via /api/v1/warehouse_remains/tasks/{task_id}/download (see urls.md)"""
        
    def get_supplier_orders(self, date_from: str, flag: int = 0) -> List[Dict]:
        """Get orders data via /api/v1/supplier/orders endpoint (see urls.md)"""
```

## External API Integration

### Wildberries API Integration (from urls.md)

**CRITICAL**: ALL Wildberries API calls MUST follow the exact specifications in `urls.md`

**Available Endpoints (ONLY these from urls.md)**:
1. **Warehouse Remains Task Creation**: `https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains`
2. **Warehouse Remains Download**: `https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains/tasks/{task_id}/download`  
3. **Supplier Orders**: `https://statistics-api.wildberries.ru/api/v1/supplier/orders`

**Required Parameters** (see urls.md for complete details):
- `locale`: "ru" (default)
- `groupByNm`: true (to get nmId in response)
- `groupBySa`: true (to get supplierArticle)
- `dateFrom`: RFC3339 format for orders
- `flag`: 0 or 1 for orders query type

**Expected Response Fields** (exact mapping from urls.md):
- `supplierArticle` (string) → Column A
- `nmId` (integer) → Column B  
- `warehouseName` (string) → Column F
- `quantity` (integer) → Column H

### Google Sheets API Integration

**Operations Required:**
- Read sheet structure and data using gspread
- Batch update ranges for multiple products
- Format cells (headers, text wrapping, number formats)
- Handle multi-line cells with newline characters

**Batch Update Pattern:**
```python
# Example using gspread
worksheet.batch_update([
    {
        'range': 'A2:H2',
        'values': [[seller_article, nm_id, total_orders, total_stock, 
                   turnover, warehouse_names, orders_per_warehouse, stock_per_warehouse]]
    }
])
```

## Error Handling

### Wildberries API Error Handling (from urls.md)

**CRITICAL**: Handle API errors according to Wildberries API documentation

**Common scenarios to handle**:
- Task creation failures for warehouse_remains
- Task completion polling timeouts
- API rate limiting (implement exponential backoff)
- Invalid API key or authentication errors
- Network timeouts during data download

**Error Response Pattern**:
```python
try:
    response = requests.post(warehouse_remains_url, headers=headers, json=params)
    response.raise_for_status()
    task_data = response.json()
except requests.exceptions.RequestException as e:
    logger.error(f"Wildberries API error: {e}")
    raise WildberriesAPIError(f"Failed to create warehouse remains task: {e}")
```

### Google Sheets API Error Handling

**Common scenarios**:
- Authentication failures with service account
- Quota exceeded errors
- Sheet not found or access denied
- Batch update failures

**Error Response Pattern**:
```python
try:
    worksheet.batch_update(requests)
except gspread.exceptions.APIError as e:
    logger.error(f"Google Sheets API error: {e}")
    raise SheetsAPIError(f"Failed to update sheet: {e}")
```