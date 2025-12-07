"""
Custom exceptions for Wildberries Stock Tracker.

Defines application-specific exception classes for different error scenarios
including API errors, authentication failures, and data validation issues.
"""

from typing import Optional, Dict, Any


class StockTrackerError(Exception):
    """Base exception for all Stock Tracker errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize exception with message and optional details.
        
        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(StockTrackerError):
    """Raised when configuration is invalid or missing."""
    pass


class AuthenticationError(StockTrackerError):
    """Raised when authentication fails."""
    pass


class APIError(StockTrackerError):
    """Base class for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            status_code: HTTP status code
            response_data: API response data
        """
        details = {}
        if status_code:
            details["status_code"] = status_code
        if response_data:
            details["response_data"] = response_data
            
        super().__init__(message, details)
        self.status_code = status_code
        self.response_data = response_data


class WildberriesAPIError(APIError):
    """Raised when Wildberries API calls fail."""
    
    def __init__(self, message: str, endpoint: Optional[str] = None,
                 status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        """
        Initialize Wildberries API error.
        
        Args:
            message: Error message
            endpoint: API endpoint that failed
            status_code: HTTP status code
            response_data: API response data
        """
        super().__init__(message, status_code, response_data)
        self.endpoint = endpoint
        
        if endpoint:
            self.details["endpoint"] = endpoint


class SheetsAPIError(APIError):
    """Базовое исключение для Google Sheets API."""
    
    def __init__(self, message: str, sheet_id: Optional[str] = None,
                 range_name: Optional[str] = None,
                 status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        """
        Initialize Sheets API error.
        
        Args:
            message: Error message
            sheet_id: Google Sheet ID
            range_name: Sheet range that failed
            status_code: HTTP status code
            response_data: API response data
        """
        super().__init__(message, status_code, response_data)
        self.sheet_id = sheet_id
        self.range_name = range_name
        
        if sheet_id:
            self.details["sheet_id"] = sheet_id
        if range_name:
            self.details["range_name"] = range_name


class SheetsRateLimitError(SheetsAPIError):
    """Rate limit exceeded для Google Sheets API."""
    pass


class SheetsPermissionError(SheetsAPIError):
    """Permission denied для Google Sheets API."""
    pass


class SheetsNotFoundError(SheetsAPIError):
    """Spreadsheet or worksheet not found."""
    pass


class ValidationError(StockTrackerError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None,
                 value: Optional[Any] = None, expected_type: Optional[str] = None):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value
            expected_type: Expected data type
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        if expected_type:
            details["expected_type"] = expected_type
            
        super().__init__(message, details)
        self.field = field
        self.value = value
        self.expected_type = expected_type


class DataSyncError(StockTrackerError):
    """Raised when data synchronization fails."""
    
    def __init__(self, message: str, sync_session_id: Optional[str] = None,
                 failed_products: Optional[list] = None):
        """
        Initialize data sync error.
        
        Args:
            message: Error message
            sync_session_id: ID of failed sync session
            failed_products: List of products that failed to sync
        """
        details = {}
        if sync_session_id:
            details["sync_session_id"] = sync_session_id
        if failed_products:
            details["failed_products"] = failed_products
            details["failed_count"] = len(failed_products)
            
        super().__init__(message, details)
        self.sync_session_id = sync_session_id
        self.failed_products = failed_products or []


class CalculationError(StockTrackerError):
    """Raised when calculations fail."""
    
    def __init__(self, message: str, calculation_type: Optional[str] = None,
                 input_data: Optional[Dict[str, Any]] = None):
        """
        Initialize calculation error.
        
        Args:
            message: Error message
            calculation_type: Type of calculation that failed
            input_data: Input data that caused the error
        """
        details = {}
        if calculation_type:
            details["calculation_type"] = calculation_type
        if input_data:
            details["input_data"] = input_data
            
        super().__init__(message, details)
        self.calculation_type = calculation_type
        self.input_data = input_data


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None,
                 endpoint: Optional[str] = None):
        """
        Initialize rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            endpoint: API endpoint that was rate limited
        """
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        if endpoint:
            details["endpoint"] = endpoint
            
        super().__init__(message, 429, details)
        self.retry_after = retry_after
        self.endpoint = endpoint


class TaskTimeoutError(StockTrackerError):
    """Raised when async tasks timeout."""
    
    def __init__(self, message: str, task_id: Optional[str] = None,
                 timeout_seconds: Optional[int] = None):
        """
        Initialize task timeout error.
        
        Args:
            message: Error message
            task_id: ID of timed out task
            timeout_seconds: Timeout duration
        """
        details = {}
        if task_id:
            details["task_id"] = task_id
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
            
        super().__init__(message, details)
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds


class DataFormatError(StockTrackerError):
    """Raised when data is in unexpected format."""
    
    def __init__(self, message: str, expected_format: Optional[str] = None,
                 actual_format: Optional[str] = None, data_sample: Optional[str] = None):
        """
        Initialize data format error.
        
        Args:
            message: Error message
            expected_format: Expected data format
            actual_format: Actual data format
            data_sample: Sample of problematic data
        """
        details = {}
        if expected_format:
            details["expected_format"] = expected_format
        if actual_format:
            details["actual_format"] = actual_format
        if data_sample:
            details["data_sample"] = data_sample
            
        super().__init__(message, details)
        self.expected_format = expected_format
        self.actual_format = actual_format
        self.data_sample = data_sample


class HealthCheckError(StockTrackerError):
    """Raised when health checks fail."""
    
    def __init__(self, message: str, check_name: Optional[str] = None,
                 component: Optional[str] = None, severity: str = "error"):
        """
        Initialize health check error.
        
        Args:
            message: Error message
            check_name: Name of the failed health check
            component: Component that failed the check
            severity: Severity level (error, warning, critical)
        """
        details = {}
        if check_name:
            details["check_name"] = check_name
        if component:
            details["component"] = component
        details["severity"] = severity
            
        super().__init__(message, details)
        self.check_name = check_name
        self.component = component
        self.severity = severity


class SecurityError(StockTrackerError):
    """Raised when security-related operations fail."""
    
    def __init__(self, message: str, security_component: Optional[str] = None,
                 action: Optional[str] = None):
        """
        Initialize security error.
        
        Args:
            message: Error message
            security_component: Security component involved (encryption, authentication, etc.)
            action: Action that failed (encrypt, decrypt, store, retrieve, etc.)
        """
        details = {}
        if security_component:
            details["security_component"] = security_component
        if action:
            details["action"] = action
            
        super().__init__(message, details)
        self.security_component = security_component
        self.action = action


class PerformanceError(StockTrackerError):
    """Raised when performance thresholds are exceeded."""
    
    def __init__(self, message: str, metric_name: Optional[str] = None,
                 actual_value: Optional[float] = None, threshold_value: Optional[float] = None):
        """
        Initialize performance error.
        
        Args:
            message: Error message
            metric_name: Name of the performance metric
            actual_value: Actual measured value
            threshold_value: Threshold that was exceeded
        """
        details = {}
        if metric_name:
            details["metric_name"] = metric_name
        if actual_value is not None:
            details["actual_value"] = actual_value
        if threshold_value is not None:
            details["threshold_value"] = threshold_value
            
        super().__init__(message, details)
        self.metric_name = metric_name
        self.actual_value = actual_value
        self.threshold_value = threshold_value


class BatchProcessingError(StockTrackerError):
    """Raised when batch processing operations fail."""
    
    def __init__(self, message: str, batch_id: Optional[str] = None,
                 batch_size: Optional[int] = None, processed_count: Optional[int] = None):
        """
        Initialize batch processing error.
        
        Args:
            message: Error message
            batch_id: ID of the failed batch
            batch_size: Size of the batch
            processed_count: Number of items successfully processed before failure
        """
        details = {}
        if batch_id:
            details["batch_id"] = batch_id
        if batch_size is not None:
            details["batch_size"] = batch_size
        if processed_count is not None:
            details["processed_count"] = processed_count
            
        super().__init__(message, details)
        self.batch_id = batch_id
        self.batch_size = batch_size
        self.processed_count = processed_count


class SyncError(DataSyncError):
    """Alias for DataSyncError for backward compatibility."""
    pass


def handle_api_error(response, endpoint: str = None) -> None:
    """
    Handle HTTP response and raise appropriate API error.
    
    Args:
        response: HTTP response object
        endpoint: API endpoint that was called
        
    Raises:
        Appropriate APIError subclass based on response status.
    """
    status_code = getattr(response, 'status_code', None)
    
    try:
        response_data = response.json() if hasattr(response, 'json') else None
    except:
        response_data = None
    
    if status_code == 401:
        raise AuthenticationError(
            "API authentication failed - check your API key",
            {"status_code": status_code, "endpoint": endpoint}
        )
    elif status_code == 403:
        raise AuthenticationError(
            "API access forbidden - check permissions",
            {"status_code": status_code, "endpoint": endpoint}
        )
    elif status_code == 429:
        retry_after = getattr(response.headers, 'Retry-After', None)
        raise RateLimitError(
            "API rate limit exceeded",
            retry_after=int(retry_after) if retry_after else None,
            endpoint=endpoint
        )
    elif status_code >= 500:
        raise APIError(
            f"Server error: {status_code}",
            status_code=status_code,
            response_data=response_data
        )
    else:
        raise APIError(
            f"API request failed: {status_code}",
            status_code=status_code,
            response_data=response_data
        )


class DatabaseError(StockTrackerError):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None,
                 table: Optional[str] = None):
        """
        Initialize database error.
        
        Args:
            message: Error message
            operation: Database operation that failed
            table: Table involved in operation
        """
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table
            
        super().__init__(message, details=details)
        self.operation = operation
        self.table = table


if __name__ == "__main__":
    # Test exception classes
    print("Testing Stock Tracker exceptions...")
    
    # Test base exception
    try:
        raise StockTrackerError("Test error", {"test": "data"})
    except StockTrackerError as e:
        print(f"✅ StockTrackerError: {e}")
    
    # Test API error
    try:
        raise WildberriesAPIError(
            "API test error", 
            endpoint="/test",
            status_code=400,
            response_data={"error": "test"}
        )
    except WildberriesAPIError as e:
        print(f"✅ WildberriesAPIError: {e}")
    
    # Test validation error
    try:
        raise ValidationError(
            "Invalid value",
            field="test_field",
            value="invalid",
            expected_type="int"
        )
    except ValidationError as e:
        print(f"✅ ValidationError: {e}")
    
    print("Exception tests completed!")