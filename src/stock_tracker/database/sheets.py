"""
Google Sheets API integration and authentication.

Provides authenticated access to Google Sheets using service account credentials.
Handles worksheet operations with proper error handling and batch processing.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

import gspread
from google.auth.exceptions import GoogleAuthError
from google.oauth2.service_account import Credentials

from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.config import get_config
from stock_tracker.utils.exceptions import SheetsAPIError, AuthenticationError


logger = get_logger(__name__)


class GoogleSheetsClient:
    """
    Google Sheets API client with authentication and worksheet operations.
    
    Provides high-level interface for interacting with Google Sheets API
    using service account authentication.
    """
    
    def __init__(self, service_account_path: Optional[str] = None, 
                 sheet_id: Optional[str] = None, sheet_name: Optional[str] = None):
        """
        Initialize Google Sheets client.
        
        Args:
            service_account_path: Path to service account JSON file
            sheet_id: Google Sheet ID 
            sheet_name: Sheet name/tab
        """
        self.config = get_config()
        
        # Use provided values or fall back to config
        self.service_account_path = service_account_path or self.config.google_sheets.service_account_key_path
        self.sheet_id = sheet_id or self.config.google_sheets.sheet_id
        self.sheet_name = sheet_name or self.config.google_sheets.sheet_name
        
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._worksheet: Optional[gspread.Worksheet] = None
        
        logger.info(f"Initializing Google Sheets client for sheet: {self.sheet_id}")
    
    def _authenticate(self) -> gspread.Client:
        """
        Authenticate with Google Sheets API using service account.
        
        Returns:
            Authenticated gspread client.
            
        Raises:
            AuthenticationError: If authentication fails.
        """
        try:
            logger.debug(f"Authenticating with service account: {self.service_account_path}")
            
            # Validate service account file exists
            if not Path(self.service_account_path).exists():
                raise AuthenticationError(
                    f"Service account file not found: {self.service_account_path}"
                )
            
            # Load credentials from service account file
            credentials = Credentials.from_service_account_file(
                self.service_account_path,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"
                ]
            )
            
            # Create authenticated client
            client = gspread.authorize(credentials)
            
            logger.info("Successfully authenticated with Google Sheets API")
            return client
            
        except GoogleAuthError as e:
            logger.error(f"Google authentication failed: {e}")
            raise AuthenticationError(f"Google authentication failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid service account JSON file: {e}")
            raise AuthenticationError(f"Invalid service account JSON file: {e}")
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def _get_client(self) -> gspread.Client:
        """Get authenticated client, creating if needed."""
        if self._client is None:
            self._client = self._authenticate()
        return self._client
    
    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Get spreadsheet, opening if needed."""
        if self._spreadsheet is None:
            try:
                client = self._get_client()
                self._spreadsheet = client.open_by_key(self.sheet_id)
                logger.info(f"Opened spreadsheet: {self._spreadsheet.title}")
            except gspread.exceptions.SpreadsheetNotFound:
                raise SheetsAPIError(f"Spreadsheet not found: {self.sheet_id}")
            except gspread.exceptions.APIError as e:
                raise SheetsAPIError(f"Failed to open spreadsheet: {e}")
        
        return self._spreadsheet
    
    def get_spreadsheet(self, spreadsheet_id: str = None) -> gspread.Spreadsheet:
        """
        Get spreadsheet by ID or return current spreadsheet.
        
        Args:
            spreadsheet_id: Optional spreadsheet ID. If None, uses current sheet_id.
            
        Returns:
            Google Spreadsheet object
        """
        if spreadsheet_id and spreadsheet_id != self.sheet_id:
            # Open different spreadsheet temporarily
            client = self._get_client()
            return client.open_by_key(spreadsheet_id)
        else:
            # Use current spreadsheet
            return self._get_spreadsheet()
    
    def _get_worksheet(self) -> gspread.Worksheet:
        """Get worksheet, creating if needed."""
        if self._worksheet is None:
            try:
                spreadsheet = self._get_spreadsheet()
                self._worksheet = spreadsheet.worksheet(self.sheet_name)
                logger.info(f"Opened worksheet: {self.sheet_name}")
            except gspread.exceptions.WorksheetNotFound:
                logger.info(f"Worksheet '{self.sheet_name}' not found, creating it...")
                spreadsheet = self._get_spreadsheet()
                self._worksheet = spreadsheet.add_worksheet(
                    title=self.sheet_name,
                    rows=1000,
                    cols=20
                )
                logger.info(f"Created worksheet: {self.sheet_name}")
            except gspread.exceptions.APIError as e:
                raise SheetsAPIError(f"Failed to access worksheet: {e}")
        
        return self._worksheet
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Google Sheets.
        
        Returns:
            Dict with connection test results.
        """
        try:
            logger.info("Testing Google Sheets connection...")
            
            # Test authentication
            client = self._get_client()
            
            # Test spreadsheet access
            spreadsheet = self._get_spreadsheet()
            
            # Test worksheet access
            worksheet = self._get_worksheet()
            
            # Get basic info
            result = {
                "success": True,
                "spreadsheet_title": spreadsheet.title,
                "worksheet_title": worksheet.title,
                "row_count": worksheet.row_count,
                "col_count": worksheet.col_count,
                "sheet_url": spreadsheet.url
            }
            
            logger.info("✅ Google Sheets connection test successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Google Sheets connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def read_all_values(self) -> List[List[str]]:
        """
        Read all values from the worksheet.
        
        Returns:
            List of rows, each row is a list of cell values.
        """
        try:
            worksheet = self._get_worksheet()
            values = worksheet.get_all_values()
            logger.debug(f"Read {len(values)} rows from worksheet")
            return values
        except gspread.exceptions.APIError as e:
            raise SheetsAPIError(f"Failed to read worksheet values: {e}")
    
    def read_range(self, range_name: str) -> List[List[str]]:
        """
        Read values from a specific range.
        
        Args:
            range_name: Range in A1 notation (e.g., "A1:D10")
            
        Returns:
            List of rows from the specified range.
        """
        try:
            worksheet = self._get_worksheet()
            values = worksheet.get(range_name)
            logger.debug(f"Read range {range_name}: {len(values)} rows")
            return values
        except gspread.exceptions.APIError as e:
            raise SheetsAPIError(f"Failed to read range {range_name}: {e}")
    
    def update_range(self, range_name: str, values: List[List[Any]]) -> None:
        """
        Update values in a specific range.
        
        Args:
            range_name: Range in A1 notation (e.g., 'A1:C3')
            values: 2D list of values to update
        """
        try:
            worksheet = self._get_worksheet()
            
            # Parse range to determine required capacity
            if values:
                # Extract end cell from range (e.g., 'A1:C3' -> row 3, col 3)
                if ':' in range_name:
                    end_cell = range_name.split(':')[1]
                    # Parse cell reference (e.g., 'C3' -> col 3, row 3)
                    import re
                    match = re.match(r'([A-Z]+)(\d+)', end_cell)
                    if match:
                        col_str, row_str = match.groups()
                        # Convert column letters to number (A=1, B=2, etc.)
                        required_col = sum((ord(c) - ord('A') + 1) * (26 ** i) 
                                         for i, c in enumerate(reversed(col_str)))
                        required_row = int(row_str)
                        
                        # Ensure capacity before update
                        self.ensure_sheet_capacity(required_row, required_col)
            
            worksheet.update(range_name, values)
            logger.debug(f"Updated range {range_name} with {len(values)} rows")
        except Exception as e:
            # Check for capacity errors and retry
            if "недостаточно места" in str(e).lower() or "insufficient space" in str(e).lower():
                logger.warning(f"Capacity error detected, attempting to expand sheet: {e}")
                try:
                    # Force expansion with larger buffer
                    worksheet = self._get_worksheet()
                    current_rows = worksheet.row_count
                    current_cols = worksheet.col_count
                    self.ensure_sheet_capacity(current_rows + 200, current_cols + 10)
                    # Retry the operation
                    worksheet.update(range_name, values)
                    logger.info(f"Successfully updated range {range_name} after sheet expansion")
                    return
                except Exception as retry_error:
                    logger.error(f"Failed even after sheet expansion: {retry_error}")
                    raise SheetsAPIError(f"Persistent capacity issue: {retry_error}")
            
            raise SheetsAPIError(f"Failed to update range {range_name}: {e}")
    
    def batch_update(self, updates: List[Dict[str, Any]]) -> None:
        """
        Perform batch update operations.
        
        Args:
            updates: List of update operations in gspread format
        """
        try:
            worksheet = self._get_worksheet()
            
            # Check capacity for all ranges in batch
            max_row = 0
            max_col = 0
            for update in updates:
                if 'range' in update:
                    range_name = update['range']
                    # Parse range to find maximum required dimensions
                    if ':' in range_name:
                        end_cell = range_name.split(':')[1]
                        import re
                        match = re.match(r'([A-Z]+)(\d+)', end_cell)
                        if match:
                            col_str, row_str = match.groups()
                            required_col = sum((ord(c) - ord('A') + 1) * (26 ** i) 
                                             for i, c in enumerate(reversed(col_str)))
                            required_row = int(row_str)
                            max_row = max(max_row, required_row)
                            max_col = max(max_col, required_col)
            
            if max_row > 0 and max_col > 0:
                self.ensure_sheet_capacity(max_row, max_col)
            
            worksheet.batch_update(updates)
            logger.debug(f"Performed batch update with {len(updates)} operations")
        except Exception as e:
            # Check for capacity errors and retry
            if "недостаточно места" in str(e).lower() or "insufficient space" in str(e).lower():
                logger.warning(f"Capacity error in batch update, attempting to expand: {e}")
                try:
                    worksheet = self._get_worksheet()
                    current_rows = worksheet.row_count
                    current_cols = worksheet.col_count
                    self.ensure_sheet_capacity(current_rows + 300, current_cols + 15)
                    worksheet.batch_update(updates)
                    logger.info(f"Successfully completed batch update after sheet expansion")
                    return
                except Exception as retry_error:
                    logger.error(f"Batch update failed even after expansion: {retry_error}")
                    raise SheetsAPIError(f"Persistent batch update capacity issue: {retry_error}")
            
            raise SheetsAPIError(f"Failed to perform batch update: {e}")
    
    def append_rows(self, values: List[List[Any]]) -> None:
        """
        Append rows to the end of the worksheet.
        
        Args:
            values: 2D list of values to append
        """
        try:
            worksheet = self._get_worksheet()
            
            # Calculate required capacity for append operation
            if values:
                num_new_rows = len(values)
                num_cols = len(values[0]) if values[0] else 0
                
                # Get current data size to find where append will happen
                all_data = worksheet.get_all_values()
                current_data_rows = len([row for row in all_data if any(cell.strip() for cell in row)])
                required_total_rows = current_data_rows + num_new_rows
                
                # Ensure capacity for append
                self.ensure_sheet_capacity(required_total_rows, num_cols)
            
            worksheet.append_rows(values)
            logger.debug(f"Appended {len(values)} rows")
        except Exception as e:
            # Check for capacity errors and retry
            if "недостаточно места" in str(e).lower() or "insufficient space" in str(e).lower():
                logger.warning(f"Capacity error in append_rows, attempting to expand: {e}")
                try:
                    worksheet = self._get_worksheet()
                    current_rows = worksheet.row_count
                    current_cols = worksheet.col_count
                    # Add generous buffer for append operations
                    self.ensure_sheet_capacity(current_rows + len(values) + 500, max(current_cols, 10))
                    worksheet.append_rows(values)
                    logger.info(f"Successfully appended rows after sheet expansion")
                    return
                except Exception as retry_error:
                    logger.error(f"Append failed even after expansion: {retry_error}")
                    raise SheetsAPIError(f"Persistent append capacity issue: {retry_error}")
            
            raise SheetsAPIError(f"Failed to append rows: {e}")
    
    def clear_worksheet(self) -> None:
        """Clear all data from the worksheet."""
        try:
            worksheet = self._get_worksheet()
            worksheet.clear()
            logger.debug("Cleared worksheet data")
        except gspread.exceptions.APIError as e:
            raise SheetsAPIError(f"Failed to clear worksheet: {e}")
    
    def format_range(self, range_name: str, format_options: Dict[str, Any]) -> None:
        """
        Apply formatting to a range.
        
        Args:
            range_name: Range in A1 notation
            format_options: Formatting options
        """
        try:
            worksheet = self._get_worksheet()
            worksheet.format(range_name, format_options)
            logger.debug(f"Applied formatting to range {range_name}")
        except gspread.exceptions.APIError as e:
            raise SheetsAPIError(f"Failed to format range {range_name}: {e}")
    
    def get_worksheet_info(self) -> Dict[str, Any]:
        """
        Get information about the current worksheet.
        
        Returns:
            Dict with worksheet information.
        """
        try:
            worksheet = self._get_worksheet()
            spreadsheet = self._get_spreadsheet()
            
            return {
                "spreadsheet_title": spreadsheet.title,
                "spreadsheet_id": spreadsheet.id,
                "worksheet_title": worksheet.title,
                "worksheet_id": worksheet.id,
                "row_count": worksheet.row_count,
                "col_count": worksheet.col_count,
                "url": spreadsheet.url
            }
        except Exception as e:
            raise SheetsAPIError(f"Failed to get worksheet info: {e}")
    
    def ensure_sheet_capacity(self, required_rows: int, required_cols: int = 8) -> None:
        """
        Ensure the worksheet has enough capacity for the required operations.
        
        Automatically expands the sheet if more rows or columns are needed.
        
        Args:
            required_rows: Minimum number of rows needed
            required_cols: Minimum number of columns needed (default: 8)
        """
        try:
            worksheet = self._get_worksheet()
            current_rows = worksheet.row_count
            current_cols = worksheet.col_count
            
            # Check if expansion is needed
            expand_needed = False
            new_rows = current_rows
            new_cols = current_cols
            
            if required_rows > current_rows:
                new_rows = max(required_rows, current_rows + 300)  # Increased buffer from 100 to 300
                expand_needed = True
                logger.info(f"Need to expand rows: {current_rows} -> {new_rows}")
            
            if required_cols > current_cols:
                new_cols = max(required_cols, current_cols + 15)  # Increased buffer from 5 to 15
                expand_needed = True
                logger.info(f"Need to expand columns: {current_cols} -> {new_cols}")
            
            if expand_needed:
                logger.info(f"Expanding worksheet to {new_rows}x{new_cols}")
                worksheet.resize(rows=new_rows, cols=new_cols)
                logger.info("Worksheet successfully expanded")
            
        except Exception as e:
            logger.error(f"Failed to expand worksheet: {e}")
            raise SheetsAPIError(f"Sheet capacity expansion failed: {e}")
    
    def _execute_with_capacity_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Universal wrapper for sheet operations with automatic capacity error handling.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            *args, **kwargs: Arguments for the function
        """
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            # Check for various capacity error messages
            error_msg = str(e).lower()
            capacity_errors = [
                "недостаточно места",
                "insufficient space", 
                "not enough space",
                "exceeds grid limits",
                "out of bounds"
            ]
            
            if any(err in error_msg for err in capacity_errors):
                logger.warning(f"Capacity error in {operation_name}, attempting emergency expansion: {e}")
                try:
                    worksheet = self._get_worksheet()
                    current_rows = worksheet.row_count
                    current_cols = worksheet.col_count
                    # Emergency expansion with very generous buffers
                    emergency_rows = current_rows + 500
                    emergency_cols = current_cols + 20
                    worksheet.resize(emergency_rows, emergency_cols)
                    logger.info(f"Emergency expansion to {emergency_rows}x{emergency_cols}")
                    
                    # Retry the operation
                    return operation_func(*args, **kwargs)
                except Exception as retry_error:
                    logger.error(f"{operation_name} failed even after emergency expansion: {retry_error}")
                    raise SheetsAPIError(f"Persistent capacity issue in {operation_name}: {retry_error}")
            
            # Re-raise non-capacity errors
            raise SheetsAPIError(f"{operation_name} failed: {e}")
            raise SheetsAPIError(f"Failed to ensure sheet capacity: {e}")
    
    def check_sheet_space(self, data_rows: int, data_cols: int = 8) -> Dict[str, Any]:
        """
        Check if there's enough space in the sheet for the data.
        
        Args:
            data_rows: Number of rows needed for data
            data_cols: Number of columns needed for data
            
        Returns:
            Dict with space check information
        """
        try:
            worksheet = self._get_worksheet()
            current_rows = worksheet.row_count
            current_cols = worksheet.col_count
            
            # Get current data size
            all_data = worksheet.get_all_values()
            used_rows = len([row for row in all_data if any(cell.strip() for cell in row)])
            
            available_rows = current_rows - used_rows
            available_cols = current_cols
            
            return {
                "current_dimensions": {"rows": current_rows, "cols": current_cols},
                "used_rows": used_rows,
                "available_rows": available_rows,
                "available_cols": available_cols,
                "space_sufficient": (available_rows >= data_rows and available_cols >= data_cols),
                "expansion_needed": {
                    "rows": max(0, data_rows - available_rows),
                    "cols": max(0, data_cols - available_cols)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to check sheet space: {e}")
            return {
                "error": str(e),
                "space_sufficient": False,
                "expansion_needed": {"rows": data_rows, "cols": data_cols}
            }
    
    def close(self) -> None:
        """Close the client and clear cached objects."""
        self._client = None
        self._spreadsheet = None
        self._worksheet = None
        logger.debug("Closed Google Sheets client")


def create_sheets_client(service_account_path: Optional[str] = None,
                        sheet_id: Optional[str] = None,
                        sheet_name: Optional[str] = None) -> GoogleSheetsClient:
    """
    Factory function to create a Google Sheets client.
    
    Args:
        service_account_path: Path to service account JSON
        sheet_id: Google Sheet ID
        sheet_name: Sheet name/tab
        
    Returns:
        Configured GoogleSheetsClient instance.
    """
    return GoogleSheetsClient(
        service_account_path=service_account_path,
        sheet_id=sheet_id,
        sheet_name=sheet_name
    )


if __name__ == "__main__":
    # Test the Google Sheets client
    try:
        client = create_sheets_client()
        result = client.test_connection()
        
        if result["success"]:
            print("✅ Google Sheets connection successful!")
            print(f"📊 Spreadsheet: {result['spreadsheet_title']}")
            print(f"📄 Worksheet: {result['worksheet_title']}")
            print(f"📐 Dimensions: {result['row_count']}x{result['col_count']}")
        else:
            print(f"❌ Connection failed: {result['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")