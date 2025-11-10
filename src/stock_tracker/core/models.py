"""
Data models for Wildberries Stock Tracker.

Defines core data structures for Analytics API v2 with proper field mappings.
Updated to support v2 response structure and new fields without complex analytics.

CRITICAL: All field names and types MUST match Analytics API v2 specification
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class SyncStatus(Enum):
    """Synchronization session status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class SyncTrigger(Enum):
    """Source of sync trigger."""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    AUTO = "auto"


class StockType(Enum):
    """Stock type from Analytics API v2."""
    ALL = ""  # All warehouses 
    WB = "wb"  # WB warehouses
    MP = "mp"  # Marketplace (FBS) warehouses


class AvailabilityFilter(Enum):
    """Availability filters from Analytics API v2."""
    DEFICIENT = "deficient"  # Дефицит
    ACTUAL = "actual"  # Актуальный
    BALANCED = "balanced"  # Баланс
    NON_ACTUAL = "nonActual"  # Неактуальный
    NON_LIQUID = "nonLiquid"  # Неликвид
    INVALID_DATA = "invalidData"  # Не рассчитано


@dataclass
@dataclass
class Warehouse:
    """
    Warehouse data model for Analytics API v2.
    
    Simplified model focused on essential warehouse stock tracking
    without complex analytics fields.
    """
    
    # Core fields for warehouse tracking
    name: str  # Warehouse name
    stock: int = 0  # Current stock quantity
    orders: int = 0  # Orders count
    turnover: int = 0  # Turnover rate in days: stock // orders (ИСПРАВЛЕНО 10.11.2025)
    
    # Metadata
    last_sync: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate warehouse data after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("Warehouse name cannot be empty")
        
        if self.stock < 0:
            raise ValueError("Stock quantity cannot be negative")
        
        if self.orders < 0:
            raise ValueError("Orders count cannot be negative")
        
        # Calculate turnover if not already set
        if self.turnover == 0:
            self.calculate_turnover()
    
    def calculate_turnover(self) -> None:
        """
        Calculate turnover rate for this warehouse: stock // orders (целое число дней).
        
        ИСПРАВЛЕНО 10.11.2025: Изменена формула с orders//stock на stock//orders.
        Оборачиваемость = сколько дней товар будет продаваться при текущих темпах заказов.
        
        Пример: stock=654, orders=32 за неделю → 654//32 = 20 дней
        
        Sets to 0 if orders is 0 to avoid division by zero.
        """
        if self.orders > 0:
            self.turnover = self.stock // self.orders
        else:
            self.turnover = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "stock": self.stock,
            "orders": self.orders,
            "turnover": self.turnover,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None
        }
    
    @classmethod
    def from_api_v2_data(cls, name: str, stock: int = 0, orders: int = 0) -> "Warehouse":
        """
        Create Warehouse from Analytics API v2 data.
        
        Args:
            name: Warehouse name
            stock: Stock quantity
            orders: Orders count
            
        Returns:
            Warehouse instance
        """
        warehouse = cls(
            name=name,
            stock=stock,
            orders=orders,
            last_sync=datetime.now()
        )
        warehouse.calculate_turnover()
        return warehouse


@dataclass
@dataclass
class Product:
    """
    Product data model for Analytics API v2.
    
    Maps Analytics API v2 response fields to our table structure:
    - nmID (integer) → wildberries_article 
    - supplierArticle (string) → seller_article (if available)
    - ordersCount (integer) → total_orders
    - stockCount (integer) → total_stock
    - Additional v2 fields: subjectID, brandName, tagID
    
    Focuses on essential data without complex analytics.
    """
    
    # Required fields from API v2
    wildberries_article: int  # nmID from API v2
    
    # Optional fields from API v2
    seller_article: str = ""  # supplierArticle (may not be in v2 response)
    total_orders: int = 0  # ordersCount from API v2
    total_stock: int = 0  # stockCount from API v2
    turnover: float = 0.0  # calculated: orders/stock
    
    # Stock breakdown by warehouse type (NEW: FBO/FBS classification)
    fbo_stock: int = 0  # Stock on WB warehouses (Fulfillment by Ozon/WB)
    fbs_stock: int = 0  # Stock on seller warehouses (Fulfillment by Seller)
    
    # New API v2 fields
    subject_id: Optional[int] = None  # subjectID from API v2
    brand_name: Optional[str] = None  # brandName from API v2  
    tag_id: Optional[int] = None  # tagID from API v2
    
    # Metadata
    last_updated: Optional[datetime] = None
    warehouses: Optional[List[Warehouse]] = None
    
    def __post_init__(self):
        """Validate product data after initialization."""
        # Initialize warehouses if None
        if self.warehouses is None:
            self.warehouses = []
        
        # Validate required fields
        if self.wildberries_article <= 0:
            raise ValueError("Wildberries article must be positive")
        
        if self.total_orders < 0:
            raise ValueError("Total orders cannot be negative")
        
        if self.total_stock < 0:
            raise ValueError("Total stock cannot be negative")
        
        # Calculate turnover
        self.calculate_turnover()
    
    def calculate_turnover(self) -> None:
        """
        Calculate turnover rate: total_orders / total_stock.
        
        Sets to 0.0 if total_stock is 0 to avoid division by zero.
        """
        if self.total_stock > 0:
            self.turnover = self.total_orders / self.total_stock
        else:
            self.turnover = 0.0
        
        self.last_updated = datetime.now()
    
    def add_warehouse(self, warehouse: Warehouse) -> None:
        """
        Add warehouse data and recalculate totals.
        
        Args:
            warehouse: Warehouse instance to add
        """
        # Check for duplicate warehouse names
        existing_names = [w.name for w in self.warehouses]
        if warehouse.name in existing_names:
            raise ValueError(f"Warehouse '{warehouse.name}' already exists for this product")
        
        self.warehouses.append(warehouse)
        self.recalculate_totals_from_warehouses()
    
    def recalculate_totals_from_warehouses(self) -> None:
        """
        Recalculate totals from warehouse data.
        
        Used when we have detailed warehouse breakdown.
        """
        if not self.warehouses:
            return
            
        self.total_stock = sum(warehouse.stock for warehouse in self.warehouses)
        self.total_orders = sum(warehouse.orders for warehouse in self.warehouses)
        self.calculate_turnover()
    
    def get_warehouse_names(self) -> str:
        """
        Get warehouse names formatted for Google Sheets (newline separated).
        
        УЛУЧШЕНО 30.10.2025: Добавлено визуальное разделение между складами.
        
        Returns:
            Warehouse names joined with double newlines for visual separation
        """
        return "\n\n".join(warehouse.name for warehouse in self.warehouses)
    
    def get_warehouse_orders(self) -> str:
        """
        Get warehouse orders formatted for Google Sheets (newline separated).
        
        УЛУЧШЕНО 30.10.2025: Добавлено визуальное разделение между складами.
        
        Returns:
            Warehouse orders joined with double newlines for visual separation
        """
        return "\n\n".join(str(warehouse.orders) for warehouse in self.warehouses)
    
    def get_warehouse_stock(self) -> str:
        """
        Get warehouse stock formatted for Google Sheets (newline separated).
        
        УЛУЧШЕНО 30.10.2025: Добавлено визуальное разделение между складами.
        
        Returns:
            Warehouse stock joined with double newlines for visual separation
        """
        return "\n\n".join(str(warehouse.stock) for warehouse in self.warehouses)
    
    def get_warehouse_turnover(self) -> str:
        """
        Get warehouse turnover formatted for Google Sheets (newline separated).
        
        ДОБАВЛЕНО 10.11.2025: Новый метод для получения оборачиваемости по складам.
        ИЗМЕНЕНО 10.11.2025: Оборачиваемость - целое число.
        
        Returns:
            Warehouse turnover joined with double newlines for visual separation
        """
        return "\n\n".join(str(warehouse.turnover) for warehouse in self.warehouses)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "seller_article": self.seller_article,
            "wildberries_article": self.wildberries_article,
            "total_orders": self.total_orders,
            "total_stock": self.total_stock,
            "turnover": self.turnover,
            "subject_id": self.subject_id,
            "brand_name": self.brand_name,
            "tag_id": self.tag_id,
            "warehouses": [warehouse.to_dict() for warehouse in self.warehouses],
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
    
    @classmethod
    def from_api_v2_data(cls, item_data: Dict[str, Any]) -> "Product":
        """
        Create Product from Analytics API v2 response data.
        
        Maps API v2 fields to our model:
        {
          "nmID": 12345,
          "ordersCount": 10,
          "stockCount": 50,
          "subjectID": 123,
          "brandName": "Brand",
          "tagID": 456,
          // other fields...
        }
        
        Args:
            item_data: Item from API v2 response items array
            
        Returns:
            Product instance
        """
        return cls(
            wildberries_article=item_data["nmID"],
            seller_article=item_data.get("supplierArticle", ""),  # May not be present in v2
            total_orders=item_data.get("ordersCount", 0),
            total_stock=item_data.get("stockCount", 0),
            subject_id=item_data.get("subjectID"),
            brand_name=item_data.get("brandName"),
            tag_id=item_data.get("tagID"),
            last_updated=datetime.now()
        )


@dataclass
class SyncSession:
    """
    Synchronization session tracking model.
    
    Tracks metadata and status of data synchronization operations
    between Wildberries API and Google Sheets.
    """
    
    # Core fields
    session_id: str
    start_time: datetime
    status: SyncStatus = SyncStatus.PENDING
    triggered_by: SyncTrigger = SyncTrigger.MANUAL
    
    # Timing
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Progress tracking
    products_processed: int = 0
    products_total: int = 0
    products_failed: int = 0
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    last_error: Optional[str] = None
    
    # API tracking
    api_calls_made: int = 0
    sheets_operations: int = 0
    
    def __post_init__(self):
        """Validate session data after initialization."""
        if not self.session_id or not self.session_id.strip():
            raise ValueError("Session ID cannot be empty")
    
    def start(self) -> None:
        """Mark session as started."""
        self.status = SyncStatus.RUNNING
        self.start_time = datetime.now()
    
    def complete(self) -> None:
        """Mark session as completed successfully."""
        self.status = SyncStatus.COMPLETED
        self.end_time = datetime.now()
        self._calculate_duration()
    
    def fail(self, error_message: str) -> None:
        """
        Mark session as failed.
        
        Args:
            error_message: Error description
        """
        self.status = SyncStatus.FAILED
        self.end_time = datetime.now()
        self.last_error = error_message
        self.add_error(error_message)
        self._calculate_duration()
    
    def timeout(self) -> None:
        """Mark session as timed out."""
        self.status = SyncStatus.TIMEOUT
        self.end_time = datetime.now()
        self.last_error = "Session timed out"
        self.add_error("Session timed out")
        self._calculate_duration()
    
    def add_error(self, error_message: str) -> None:
        """
        Add error to the session.
        
        Args:
            error_message: Error description
        """
        self.errors.append(error_message)
        self.last_error = error_message
    
    def increment_progress(self, success: bool = True) -> None:
        """
        Increment progress counters.
        
        Args:
            success: Whether the operation was successful
        """
        self.products_processed += 1
        if not success:
            self.products_failed += 1
    
    def _calculate_duration(self) -> None:
        """Calculate session duration."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = delta.total_seconds()
    
    def get_success_rate(self) -> float:
        """
        Calculate success rate percentage.
        
        Returns:
            Success rate as percentage (0-100)
        """
        if self.products_processed == 0:
            return 0.0
        
        successful = self.products_processed - self.products_failed
        return (successful / self.products_processed) * 100
    
    def is_running(self) -> bool:
        """Check if session is currently running."""
        return self.status == SyncStatus.RUNNING
    
    def is_completed(self) -> bool:
        """Check if session completed successfully."""
        return self.status == SyncStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if session failed."""
        return self.status in [SyncStatus.FAILED, SyncStatus.TIMEOUT]
    
    @property
    def products_synced(self) -> int:
        """Get number of successfully synced products."""
        return self.products_processed - self.products_failed
    
    @property
    def duration(self) -> str:
        """Get formatted duration string."""
        if self.duration_seconds is None:
            return "N/A"
        
        seconds = int(self.duration_seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "triggered_by": self.triggered_by.value,
            "products_processed": self.products_processed,
            "products_total": self.products_total,
            "products_failed": self.products_failed,
            "success_rate": self.get_success_rate(),
            "api_calls_made": self.api_calls_made,
            "sheets_operations": self.sheets_operations,
            "errors_count": len(self.errors),
            "last_error": self.last_error
        }


if __name__ == "__main__":
    # Test data models
    print("Testing Stock Tracker data models...")
    
    # Test Warehouse
    warehouse = Warehouse(name="СЦ Волгоград", stock=654, orders=32)
    print(f"✅ Warehouse: {warehouse}")
    
    # Test Product
    product = Product(seller_article="WB001", wildberries_article=12345678)
    product.add_warehouse(warehouse)
    print(f"✅ Product: {product}")
    print(f"   Turnover: {product.turnover}")
    
    # Test SyncSession
    session = SyncSession(session_id="test-123", start_time=datetime.now())
    session.start()
    session.increment_progress(True)
    session.complete()
    print(f"✅ SyncSession: {session}")
    print(f"   Success rate: {session.get_success_rate()}%")
    
    print("Data model tests completed!")