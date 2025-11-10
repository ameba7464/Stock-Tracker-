"""
Google Sheets table structure management for Wildberries Stock Tracker.

Manages the table structure, headers, and basic formatting to ensure
consistent data layout as specified in the requirements. Handles table
initialization and schema validation.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

import gspread

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.logger import get_logger
from stock_tracker.utils.exceptions import SheetsAPIError, ValidationError


logger = get_logger(__name__)


@dataclass
class ColumnDefinition:
    """Definition of a table column."""
    
    key: str              # Internal key for referencing
    header: str           # Display header text
    letter: str           # Excel column letter (A, B, C, etc.)
    width: int = 100      # Column width in pixels
    number_format: str = "TEXT"  # Number format (TEXT, NUMBER, CURRENCY, etc.)
    alignment: str = "LEFT"      # Text alignment (LEFT, CENTER, RIGHT)
    wrap_text: bool = False      # Whether to wrap text in cells


class SheetsTableStructure:
    """
    Manages Google Sheets table structure for stock tracking.
    
    Defines the exact table structure as specified in requirements:
    - Column A: Артикул продавца
    - Column B: Артикул товара  
    - Column C: Заказы (всего)
    - Column D: Остатки (всего)
    - Column E: Оборачиваемость
    - Column F: Название склада
    - Column G: Заказы со склада
    - Column H: Остатки на складе
    """
    
    # Table schema definition
    COLUMNS = [
        ColumnDefinition(
            key="seller_article",
            header="Артикул продавца",
            letter="A",
            width=150,
            number_format="TEXT",
            alignment="LEFT"
        ),
        ColumnDefinition(
            key="wildberries_article", 
            header="Артикул товара",
            letter="B",
            width=120,
            number_format="NUMBER",
            alignment="CENTER"
        ),
        ColumnDefinition(
            key="total_orders",
            header="Заказы (всего)",
            letter="C", 
            width=120,
            number_format="NUMBER",
            alignment="CENTER"
        ),
        ColumnDefinition(
            key="total_stock",
            header="Остатки (всего)",
            letter="D",
            width=120,
            number_format="NUMBER", 
            alignment="CENTER"
        ),
        ColumnDefinition(
            key="turnover",
            header="Оборачиваемость",
            letter="E",
            width=130,
            number_format="0",  # Целое число (без дробной части)
            alignment="CENTER"
        ),
        ColumnDefinition(
            key="warehouse_names",
            header="Название склада",
            letter="F",
            width=250,  # Увеличена ширина для длинных названий
            number_format="TEXT",
            alignment="LEFT",
            wrap_text=False  # ИСПРАВЛЕНО 10.11.2025: Отключён перенос текста для предотвращения смещения строк
        ),
        ColumnDefinition(
            key="warehouse_orders",
            header="Заказы со склада", 
            letter="G",
            width=130,
            number_format="TEXT",  # Multi-line numbers
            alignment="CENTER",
            wrap_text=True
        ),
        ColumnDefinition(
            key="warehouse_stock",
            header="Остатки на складе",
            letter="H", 
            width=130,
            number_format="TEXT",  # Multi-line numbers
            alignment="CENTER",
            wrap_text=True
        ),
        ColumnDefinition(
            key="warehouse_turnover",
            header="Оборачиваемость по складам",
            letter="I",
            width=180,
            number_format="TEXT",  # Multi-line numbers
            alignment="CENTER",
            wrap_text=True
        )
    ]
    
    # Create lookup dictionaries
    COLUMNS_BY_KEY = {col.key: col for col in COLUMNS}
    COLUMNS_BY_LETTER = {col.letter: col for col in COLUMNS}
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Initialize table structure manager.
        
        Args:
            sheets_client: Configured Google Sheets client
        """
        self.sheets_client = sheets_client
        logger.info("Initialized Google Sheets table structure manager")
    
    def get_headers(self) -> List[str]:
        """
        Get list of column headers.
        
        Returns:
            List of header strings in order
        """
        return [col.header for col in self.COLUMNS]
    
    def get_column_range(self, column_key: str, start_row: int = 1, end_row: Optional[int] = None) -> str:
        """
        Get range string for a specific column.
        
        Args:
            column_key: Key of the column
            start_row: Starting row number (1-based)
            end_row: Ending row number (None for open range)
            
        Returns:
            Range string (e.g., "A1:A10" or "B2:B")
            
        Raises:
            ValidationError: If column key is invalid
        """
        if column_key not in self.COLUMNS_BY_KEY:
            raise ValidationError(
                f"Invalid column key: {column_key}",
                field="column_key",
                value=column_key
            )
        
        letter = self.COLUMNS_BY_KEY[column_key].letter
        
        if end_row is None:
            return f"{letter}{start_row}:{letter}"
        else:
            return f"{letter}{start_row}:{letter}{end_row}"
    
    def get_row_range(self, row_number: int, start_col: str = "A", end_col: str = "I") -> str:
        """
        Get range string for a specific row.
        
        Args:
            row_number: Row number (1-based)
            start_col: Starting column letter
            end_col: Ending column letter
            
        Returns:
            Range string (e.g., "A2:I2")
        """
        return f"{start_col}{row_number}:{end_col}{row_number}"
    
    def get_data_range(self, start_row: int = 2, end_row: Optional[int] = None) -> str:
        """
        Get range string for all data (excluding headers).
        
        Args:
            start_row: Starting row number (default: 2, after headers)
            end_row: Ending row number (None for open range)
            
        Returns:
            Range string for all data columns
        """
        if end_row is None:
            return f"A{start_row}:I"
        else:
            return f"A{start_row}:I{end_row}"
    
    def initialize_table(self) -> None:
        """
        Initialize table with headers and basic formatting.
        
        Creates the header row and applies basic formatting to prepare
        the sheet for data entry.
        
        Raises:
            SheetsAPIError: If initialization fails
        """
        try:
            logger.info("Initializing Google Sheets table structure...")
            
            # Set headers in row 1
            headers = self.get_headers()
            self.sheets_client.update_range("A1:I1", [headers])
            
            # Apply header formatting
            self._format_headers()
            
            # Set column widths and basic formatting
            self._setup_column_formatting()
            
            logger.info("✅ Table structure initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize table structure: {e}")
            raise SheetsAPIError(f"Table initialization failed: {e}")
    
    def validate_table_structure(self) -> Dict[str, Any]:
        """
        Validate that the table has the correct structure.
        
        Returns:
            Dict with validation results
        """
        try:
            logger.info("Validating table structure...")
            
            # Read header row
            headers = self.sheets_client.read_range("A1:I1")
            
            if not headers:
                return {
                    "valid": False,
                    "error": "No headers found",
                    "expected_headers": self.get_headers()
                }
            
            actual_headers = headers[0] if headers else []
            expected_headers = self.get_headers()
            
            # Check header count
            if len(actual_headers) != len(expected_headers):
                return {
                    "valid": False,
                    "error": f"Header count mismatch: expected {len(expected_headers)}, got {len(actual_headers)}",
                    "expected_headers": expected_headers,
                    "actual_headers": actual_headers
                }
            
            # Check header content
            mismatched_headers = []
            for i, (expected, actual) in enumerate(zip(expected_headers, actual_headers)):
                if expected != actual:
                    mismatched_headers.append({
                        "column": chr(ord('A') + i),
                        "expected": expected,
                        "actual": actual
                    })
            
            if mismatched_headers:
                return {
                    "valid": False,
                    "error": "Header content mismatch",
                    "mismatched_headers": mismatched_headers,
                    "expected_headers": expected_headers,
                    "actual_headers": actual_headers
                }
            
            # Structure is valid
            return {
                "valid": True,
                "headers": actual_headers,
                "column_count": len(actual_headers)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate table structure: {e}")
            return {
                "valid": False,
                "error": f"Validation failed: {e}"
            }
    
    def apply_header_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply header formatting to worksheet.
        
        Args:
            worksheet: Google Sheets worksheet to format
        """
        try:
            # Apply header formatting to first row
            self._format_headers()
            logger.info("Applied header formatting to worksheet")
        except Exception as e:
            logger.warning(f"Failed to apply header formatting: {e}")
    
    def _format_headers(self) -> None:
        """Apply formatting to header row."""
        header_format = {
            "backgroundColor": {
                "red": 0.2,
                "green": 0.4, 
                "blue": 0.8
            },
            "textFormat": {
                "foregroundColor": {
                    "red": 1.0,
                    "green": 1.0,
                    "blue": 1.0
                },
                "fontSize": 11,
                "bold": True
            },
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE"
        }
        
        try:
            self.sheets_client.format_range("A1:I1", header_format)
            logger.debug("Applied header formatting")
        except Exception as e:
            logger.warning(f"Failed to format headers: {e}")
    
    def _setup_column_formatting(self) -> None:
        """Setup column-specific formatting."""
        try:
            # Set column widths and basic formatting for each column
            for col in self.COLUMNS:
                # Format specific columns based on their requirements
                column_format = {
                    "horizontalAlignment": col.alignment,
                    "verticalAlignment": "TOP",
                    "wrapStrategy": "WRAP" if col.wrap_text else "OVERFLOW_CELL"
                }
                
                # Special formatting for numbers
                if col.number_format != "TEXT":
                    if col.number_format == "NUMBER":
                        column_format["numberFormat"] = {"type": "NUMBER", "pattern": "#,##0"}
                    elif col.number_format.startswith("0."):
                        # Decimal format
                        column_format["numberFormat"] = {"type": "NUMBER", "pattern": col.number_format}
                
                # Apply formatting to entire column (excluding header)
                column_range = f"{col.letter}2:{col.letter}"
                self.sheets_client.format_range(column_range, column_format)
            
            logger.debug("Applied column formatting")
            
        except Exception as e:
            logger.warning(f"Failed to setup column formatting: {e}")
    
    def get_next_available_row(self) -> int:
        """
        Find the next available row for inserting data.
        
        Returns:
            Row number (1-based) where new data can be inserted
        """
        try:
            # Read all data to find the last non-empty row
            all_data = self.sheets_client.read_range("A:A")
            
            # Find last non-empty row
            last_row = 1  # Start with header row
            for i, row in enumerate(all_data):
                if row and len(row) > 0 and row[0].strip():
                    last_row = i + 1
            
            # Next available row is after the last used row
            next_row = last_row + 1
            
            logger.debug(f"Next available row: {next_row}")
            return next_row
            
        except Exception as e:
            logger.warning(f"Failed to find next available row: {e}")
            return 2  # Default to row 2 (after headers)
    
    def clear_data_rows(self, start_row: int = 2, end_row: Optional[int] = None) -> None:
        """
        Clear data rows while preserving headers and structure.
        
        Args:
            start_row: Starting row to clear (default: 2)
            end_row: Ending row to clear (None for all data)
        """
        try:
            logger.info(f"Clearing data rows from row {start_row}...")
            
            if end_row is None:
                range_str = f"A{start_row}:H"
            else:
                range_str = f"A{start_row}:H{end_row}"
            
            # Clear the data range
            self.sheets_client.update_range(range_str, [[]])
            
            logger.info("✅ Data rows cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear data rows: {e}")
            raise SheetsAPIError(f"Failed to clear data: {e}")
    
    def apply_number_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply number formatting to appropriate columns.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying number formatting...")
            
            # Format orders columns (C, G) as integers
            orders_format = {
                "numberFormat": {
                    "type": "NUMBER",
                    "pattern": "#,##0"
                }
            }
            
            # Format stock columns (D, H) as integers
            stock_format = {
                "numberFormat": {
                    "type": "NUMBER", 
                    "pattern": "#,##0"
                }
            }
            
            # Format turnover column (E) as integer (целое число)
            turnover_format = {
                "numberFormat": {
                    "type": "NUMBER",
                    "pattern": "#,##0"
                }
            }
            
            # Apply formatting using batch update
            requests = [
                # Total orders column (C)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,  # Skip header
                            "startColumnIndex": 2,  # Column C
                            "endColumnIndex": 3
                        },
                        "cell": {
                            "userEnteredFormat": orders_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Total stock column (D)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 3,  # Column D
                            "endColumnIndex": 4
                        },
                        "cell": {
                            "userEnteredFormat": stock_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Turnover column (E)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 4,  # Column E
                            "endColumnIndex": 5
                        },
                        "cell": {
                            "userEnteredFormat": turnover_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Warehouse orders column (G)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 6,  # Column G
                            "endColumnIndex": 7
                        },
                        "cell": {
                            "userEnteredFormat": orders_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Warehouse stock column (H)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 7,  # Column H
                            "endColumnIndex": 8
                        },
                        "cell": {
                            "userEnteredFormat": stock_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                },
                # Warehouse turnover column (I)
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 8,  # Column I
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": stock_format
                        },
                        "fields": "userEnteredFormat.numberFormat"
                    }
                }
            ]
            
            # Execute batch update
            worksheet.spreadsheet.batch_update({"requests": requests})
            
            logger.info("✅ Number formatting applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply number formatting: {e}")
            # Non-critical error, don't raise
    
    def apply_text_wrapping(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply text wrapping to multi-line columns.
        
        ИСПРАВЛЕНО 10.11.2025: Колонка F (Название склада) теперь использует OVERFLOW_CELL
        вместо WRAP, чтобы длинные названия не увеличивали высоту строки.
        Колонки G, H, I продолжают использовать WRAP для многострочных данных.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying text formatting (no wrap for warehouse names, wrap for data)...")
            
            # Format for multi-line warehouse data (orders, stock, turnover)
            wrap_format = {
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP"  # Align to top for better readability
            }
            
            # Format for warehouse names - NO WRAP to prevent row expansion
            no_wrap_format = {
                "wrapStrategy": "OVERFLOW_CELL",  # Text overflows into next cell, no row expansion
                "verticalAlignment": "TOP"
            }
            
            requests = [
                # Warehouse name column (F) - NO WRAP to prevent row height expansion
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,  # Skip header
                            "startColumnIndex": 5,  # Column F
                            "endColumnIndex": 6
                        },
                        "cell": {
                            "userEnteredFormat": {
                                **no_wrap_format,
                                "textFormat": {
                                    "fontSize": 10
                                }
                            }
                        },
                        "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat.fontSize"
                    }
                },
                # Warehouse orders column (G) - Centered numbers with wrapping
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 6,  # Column G
                            "endColumnIndex": 7
                        },
                        "cell": {
                            "userEnteredFormat": {
                                **wrap_format,
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "fontSize": 10
                                }
                            }
                        },
                        "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
                    }
                },
                # Warehouse stock column (H) - Centered numbers with wrapping
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 7,  # Column H
                            "endColumnIndex": 8
                        },
                        "cell": {
                            "userEnteredFormat": {
                                **wrap_format,
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "fontSize": 10
                                }
                            }
                        },
                        "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
                    }
                },
                # Warehouse turnover column (I) - Centered numbers with wrapping
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "startColumnIndex": 8,  # Column I
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": {
                                **wrap_format,
                                "horizontalAlignment": "CENTER",
                                "textFormat": {
                                    "fontSize": 10
                                }
                            }
                        },
                        "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
                    }
                }
            ]
            
            # Execute batch update
            worksheet.spreadsheet.batch_update({"requests": requests})
            
            logger.info("✅ Text formatting applied: Column F (OVERFLOW), Columns G/H/I (WRAP)")
            
        except Exception as e:
            logger.error(f"Failed to apply text wrapping: {e}")
            # Non-critical error, don't raise
    
    def apply_multi_line_cell_formatting(self, worksheet: gspread.Worksheet, 
                                       row_range: Optional[Tuple[int, int]] = None) -> None:
        """
        Apply specific formatting for multi-line cells in warehouse columns.
        
        New method for User Story 2 to handle newline character formatting
        and ensure proper display of synchronized warehouse data.
        
        Args:
            worksheet: Worksheet to format
            row_range: Optional tuple of (start_row, end_row) to limit formatting
        """
        try:
            logger.info("Applying multi-line cell formatting for warehouse data...")
            
            # Determine row range
            if row_range:
                start_row, end_row = row_range
            else:
                # Get all data to determine range
                all_data = worksheet.get_all_values()
                start_row = 2  # Skip header
                end_row = len(all_data) if all_data else 2
            
            # Multi-line cell format
            multiline_format = {
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP",
                "textFormat": {
                    "fontSize": 9,
                    "fontFamily": "Arial"
                },
                "padding": {
                    "top": 4,
                    "bottom": 4,
                    "left": 6,
                    "right": 6
                }
            }
            
            requests = []
            
            # Apply to warehouse columns F, G, H, I
            for col_idx, col_name in [(5, "F"), (6, "G"), (7, "H"), (8, "I")]:
                # Adjust alignment for different columns
                format_copy = multiline_format.copy()
                if col_name in ["G", "H", "I"]:  # Orders, stock and turnover columns
                    format_copy["horizontalAlignment"] = "CENTER"
                else:  # Names column
                    format_copy["horizontalAlignment"] = "LEFT"
                
                request = {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": start_row - 1,  # Convert to 0-based
                            "endRowIndex": end_row,
                            "startColumnIndex": col_idx,
                            "endColumnIndex": col_idx + 1
                        },
                        "cell": {
                            "userEnteredFormat": format_copy
                        },
                        "fields": "userEnteredFormat"
                    }
                }
                requests.append(request)
            
            # Execute batch update
            if requests:
                worksheet.spreadsheet.batch_update({"requests": requests})
                logger.info(f"✅ Multi-line formatting applied to rows {start_row}-{end_row}")
            
        except Exception as e:
            logger.error(f"Failed to apply multi-line cell formatting: {e}")
            # Non-critical error, don't raise
    
    def set_row_heights_for_multiline_data(self, worksheet: gspread.Worksheet, 
                                         min_height: int = 21) -> None:
        """
        Set fixed row heights to prevent row expansion from long warehouse names.
        
        ИСПРАВЛЕНО 10.11.2025: Вместо динамического расчёта высоты строк,
        устанавливаем фиксированную высоту для всех строк данных.
        Это предотвращает смещение данных при длинных названиях складов.
        
        Args:
            worksheet: Worksheet to format
            min_height: Fixed row height in pixels (default 21 - стандартная высота Google Sheets)
        """
        try:
            logger.info(f"Setting fixed row heights ({min_height}px) to prevent row expansion...")
            
            # Get current data to determine how many rows we have
            all_data = worksheet.get_all_values()
            if len(all_data) <= 1:
                logger.info("No data rows to adjust")
                return
            
            # Set fixed height for all data rows in one batch request
            request = {
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": worksheet.id,
                        "dimension": "ROWS",
                        "startIndex": 1,  # Start from row 2 (skip header)
                        "endIndex": len(all_data)  # All data rows
                    },
                    "properties": {
                        "pixelSize": min_height
                    },
                    "fields": "pixelSize"
                }
            }
            
            # Execute batch update
            worksheet.spreadsheet.batch_update({"requests": [request]})
            logger.info(f"✅ Set fixed height {min_height}px for {len(all_data)-1} data rows")
            
        except Exception as e:
            logger.error(f"Failed to set row heights: {e}")
            # Non-critical error, don't raise
    
    def apply_visual_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply comprehensive visual formatting to the worksheet.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying comprehensive visual formatting...")
            
            # Header formatting
            header_format = {
                "backgroundColor": {
                    "red": 0.2,
                    "green": 0.6,
                    "blue": 0.9,
                    "alpha": 1.0
                },
                "textFormat": {
                    "foregroundColor": {
                        "red": 1.0,
                        "green": 1.0,
                        "blue": 1.0,
                        "alpha": 1.0
                    },
                    "fontSize": 12,
                    "bold": True
                },
                "horizontalAlignment": "CENTER",
                "wrapStrategy": "WRAP"
            }
            
            # Data formatting
            data_format = {
                "textFormat": {
                    "fontSize": 10
                },
                "verticalAlignment": "TOP"
            }
            
            # Alternating row colors
            even_row_format = {
                "backgroundColor": {
                    "red": 0.95,
                    "green": 0.95,
                    "blue": 0.95,
                    "alpha": 1.0
                }
            }
            
            requests = [
                # Header row formatting
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": header_format
                        },
                        "fields": "userEnteredFormat"
                    }
                },
                # Data rows base formatting
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,
                            "endRowIndex": 1000,  # Format up to 1000 rows
                            "startColumnIndex": 0,
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": data_format
                        },
                        "fields": "userEnteredFormat.textFormat,userEnteredFormat.verticalAlignment"
                    }
                }
            ]
            
            # Add alternating row colors for even rows
            for row in range(2, 1000, 2):  # Every even row starting from 2
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": worksheet.id,
                            "startRowIndex": row,
                            "endRowIndex": row + 1,
                            "startColumnIndex": 0,
                            "endColumnIndex": 9
                        },
                        "cell": {
                            "userEnteredFormat": even_row_format
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })
            
            # Execute batch update
            worksheet.spreadsheet.batch_update({"requests": requests})
            
            logger.info("✅ Visual formatting applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply visual formatting: {e}")
            # Non-critical error, don't raise
    
    def set_column_widths(self, worksheet: gspread.Worksheet) -> None:
        """
        Set optimal column widths for better readability.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Setting column widths...")
            
            # Column width settings (in pixels)
            column_widths = {
                0: 120,  # A: Seller Article
                1: 100,  # B: WB Article  
                2: 80,   # C: Total Orders
                3: 80,   # D: Total Stock
                4: 100,  # E: Turnover
                5: 150,  # F: Warehouse Names
                6: 120,  # G: Warehouse Orders
                7: 120,  # H: Warehouse Stock
                8: 180   # I: Warehouse Turnover
            }
            
            requests = []
            for col_index, width in column_widths.items():
                requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": worksheet.id,
                            "dimension": "COLUMNS",
                            "startIndex": col_index,
                            "endIndex": col_index + 1
                        },
                        "properties": {
                            "pixelSize": width
                        },
                        "fields": "pixelSize"
                    }
                })
            
            # Execute batch update
            worksheet.spreadsheet.batch_update({"requests": requests})
            
            logger.info("✅ Column widths set successfully")
            
        except Exception as e:
            logger.error(f"Failed to set column widths: {e}")
            # Non-critical error, don't raise
    
    def apply_complete_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply all formatting options to the worksheet.
        
        Enhanced for User Story 2 with comprehensive multi-warehouse formatting
        including text wrapping and cell formatting for warehouse columns.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying complete worksheet formatting with multi-warehouse support...")
            
            # Apply all formatting in sequence
            self.apply_header_formatting(worksheet)
            self.apply_visual_formatting(worksheet)
            self.apply_number_formatting(worksheet) 
            self.apply_text_wrapping(worksheet)  # Enhanced for multi-warehouse
            
            # Apply User Story 2 specific formatting
            self.apply_multi_line_cell_formatting(worksheet)
            self.set_row_heights_for_multiline_data(worksheet)
            
            # Apply standard formatting last
            self.set_column_widths(worksheet)
            
            # Apply conditional formatting for turnover column
            self.apply_turnover_conditional_formatting(worksheet)
            
            logger.info("✅ Complete formatting with multi-warehouse support applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply complete formatting: {e}")
            raise SheetsAPIError(f"Failed to format worksheet: {e}")
    
    def apply_turnover_conditional_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply conditional formatting to the turnover column (E).
        
        Highlights cells in red when turnover is 14 days or less,
        indicating low stock that needs attention.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying conditional formatting for turnover column...")
            
            # Conditional format rule: highlight red when turnover <= 14
            conditional_format_rule = {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{
                            "sheetId": worksheet.id,
                            "startRowIndex": 1,  # Skip header (row 1)
                            "startColumnIndex": 4,  # Column E (0-indexed)
                            "endColumnIndex": 5
                        }],
                        "booleanRule": {
                            "condition": {
                                "type": "NUMBER_LESS_THAN_EQ",
                                "values": [{
                                    "userEnteredValue": "14"
                                }]
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.95,
                                    "green": 0.2,
                                    "blue": 0.2,
                                    "alpha": 1.0
                                },
                                "textFormat": {
                                    "foregroundColor": {
                                        "red": 1.0,
                                        "green": 1.0,
                                        "blue": 1.0,
                                        "alpha": 1.0
                                    },
                                    "bold": True
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
            
            # Execute the conditional formatting request
            worksheet.spreadsheet.batch_update({"requests": [conditional_format_rule]})
            
            logger.info("✅ Conditional formatting applied: turnover <= 14 days highlighted in red")
            
        except Exception as e:
            logger.error(f"Failed to apply conditional formatting: {e}")
            # Non-critical error, don't raise but log warning
            logger.warning("Conditional formatting will not be applied, but data sync will continue")
    
    def apply_warehouse_column_formatting(self, worksheet: gspread.Worksheet) -> None:
        """
        Apply specific formatting for warehouse columns F, G, H.
        
        New method for User Story 2 to handle warehouse-specific formatting
        including text wrapping, alignment, and multi-line cell support.
        
        Args:
            worksheet: Worksheet to format
        """
        try:
            logger.info("Applying warehouse column formatting...")
            
            # Enhanced formatting for warehouse columns
            warehouse_format = {
                "wrapStrategy": "WRAP",
                "verticalAlignment": "TOP",
                "textFormat": {
                    "fontSize": 9,
                    "fontFamily": "Arial"
                },
                "borders": {
                    "top": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "left": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "right": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}}
                }
            }
            
            requests = []
            
            # Column F: Warehouse Names - Left aligned
            names_format = {
                **warehouse_format,
                "horizontalAlignment": "LEFT",
                "backgroundColor": {"red": 0.98, "green": 0.98, "blue": 1.0, "alpha": 1.0}
            }
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 1,  # Skip header
                        "startColumnIndex": 5,  # Column F
                        "endColumnIndex": 6
                    },
                    "cell": {
                        "userEnteredFormat": names_format
                    },
                    "fields": "userEnteredFormat"
                }
            })
            
            # Column G: Warehouse Orders - Center aligned
            orders_format = {
                **warehouse_format,
                "horizontalAlignment": "CENTER",
                "backgroundColor": {"red": 0.98, "green": 1.0, "blue": 0.98, "alpha": 1.0}
            }
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 1,
                        "startColumnIndex": 6,  # Column G
                        "endColumnIndex": 7
                    },
                    "cell": {
                        "userEnteredFormat": orders_format
                    },
                    "fields": "userEnteredFormat"
                }
            })
            
            # Column H: Warehouse Stock - Center aligned
            stock_format = {
                **warehouse_format,
                "horizontalAlignment": "CENTER",
                "backgroundColor": {"red": 1.0, "green": 0.98, "blue": 0.98, "alpha": 1.0}
            }
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 1,
                        "startColumnIndex": 7,  # Column H
                        "endColumnIndex": 8
                    },
                    "cell": {
                        "userEnteredFormat": stock_format
                    },
                    "fields": "userEnteredFormat"
                }
            })
            
            # Column I: Warehouse Turnover - Center aligned
            turnover_format = {
                **warehouse_format,
                "horizontalAlignment": "CENTER",
                "backgroundColor": {"red": 0.98, "green": 1.0, "blue": 1.0, "alpha": 1.0}
            }
            
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": worksheet.id,
                        "startRowIndex": 1,
                        "startColumnIndex": 8,  # Column I
                        "endColumnIndex": 9
                    },
                    "cell": {
                        "userEnteredFormat": turnover_format
                    },
                    "fields": "userEnteredFormat"
                }
            })
            
            # Execute batch update
            if requests:
                worksheet.spreadsheet.batch_update({"requests": requests})
                logger.info("✅ Warehouse column formatting applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply warehouse column formatting: {e}")
            # Non-critical error, don't raise


def create_table_structure(sheets_client: GoogleSheetsClient) -> SheetsTableStructure:
    """
    Factory function to create a table structure manager.
    
    Args:
        sheets_client: Configured Google Sheets client
        
    Returns:
        SheetsTableStructure instance
    """
    return SheetsTableStructure(sheets_client)


if __name__ == "__main__":
    # Test table structure
    from stock_tracker.database.sheets import create_sheets_client
    
    try:
        sheets_client = create_sheets_client()
        table_structure = create_table_structure(sheets_client)
        
        print("✅ Table structure manager created")
        print(f"📊 Headers: {table_structure.get_headers()}")
        print(f"📍 Data range: {table_structure.get_data_range()}")
        print(f"📋 Column A range: {table_structure.get_column_range('seller_article', 2, 10)}")
        
        # Test validation
        validation = table_structure.validate_table_structure()
        if validation["valid"]:
            print("✅ Table structure is valid")
        else:
            print(f"❌ Table structure invalid: {validation['error']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")