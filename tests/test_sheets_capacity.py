"""
Tests for Google Sheets capacity management and automatic expansion.

Verifies that the system can handle large amounts of data and automatically
expand sheets when needed.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.core.models import Product
from stock_tracker.utils.exceptions import SheetsAPIError


class TestSheetsCapacity:
    """Test suite for sheets capacity management."""
    
    def setup_method(self):
        """Set up test instance with mocked dependencies."""
        self.mock_config = Mock()
        self.mock_config.google_sheets.service_account_key_path = "test.json"
        self.mock_config.google_sheets.sheet_id = "test_sheet_id"
        self.mock_config.google_sheets.sheet_name = "Test Sheet"
        
        # Mock the sheets client
        with patch('stock_tracker.database.sheets.get_config', return_value=self.mock_config):
            self.sheets_client = GoogleSheetsClient()
    
    def test_check_sheet_space(self):
        """Test sheet space checking functionality."""
        # Mock worksheet with limited space
        mock_worksheet = Mock()
        mock_worksheet.row_count = 100
        mock_worksheet.col_count = 8
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2", "Header3", "Header4", "Header5", "Header6", "Header7", "Header8"],
            ["Data1", "Data2", "Data3", "Data4", "Data5", "Data6", "Data7", "Data8"],
            # 90 more rows would fill the sheet
        ] + [[""] * 8] * 90  # 90 empty rows
        
        self.sheets_client._worksheet = mock_worksheet
        
        # Test with data that fits
        space_check = self.sheets_client.check_sheet_space(10, 8)
        assert space_check["space_sufficient"] is True
        assert space_check["available_rows"] >= 10
        
        # Test with data that doesn't fit
        space_check = self.sheets_client.check_sheet_space(200, 8)
        assert space_check["space_sufficient"] is False
        assert space_check["expansion_needed"]["rows"] > 0
    
    def test_ensure_sheet_capacity_expansion_needed(self):
        """Test automatic sheet expansion when capacity is insufficient."""
        # Mock worksheet that needs expansion
        mock_worksheet = Mock()
        mock_worksheet.row_count = 100
        mock_worksheet.col_count = 5  # Not enough columns
        
        self.sheets_client._worksheet = mock_worksheet
        
        # Test expansion
        self.sheets_client.ensure_sheet_capacity(150, 8)
        
        # Verify resize was called with appropriate dimensions
        mock_worksheet.resize.assert_called_once()
        call_args = mock_worksheet.resize.call_args
        assert call_args[1]['rows'] >= 150
        assert call_args[1]['cols'] >= 8
    
    def test_ensure_sheet_capacity_no_expansion_needed(self):
        """Test that no expansion occurs when capacity is sufficient."""
        # Mock worksheet with sufficient capacity
        mock_worksheet = Mock()
        mock_worksheet.row_count = 1000
        mock_worksheet.col_count = 10
        
        self.sheets_client._worksheet = mock_worksheet
        
        # Test no expansion needed
        self.sheets_client.ensure_sheet_capacity(100, 8)
        
        # Verify resize was not called
        mock_worksheet.resize.assert_not_called()
    
    def test_create_product_with_capacity_check(self):
        """Test product creation with automatic capacity management."""
        # Mock dependencies
        mock_sheets_client = Mock()
        mock_formatter = Mock()
        mock_formatter.format_product_for_sheets.return_value = ["data"] * 8
        
        operations = SheetsOperations(mock_sheets_client)
        operations.formatter = mock_formatter
        
        # Mock worksheet
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [["Header"]] + [["Data"]] * 50
        operations.get_or_create_worksheet = Mock(return_value=mock_worksheet)
        operations._find_product_row = Mock(return_value=None)  # Product doesn't exist
        
        # Create test product
        product = Product(
            seller_article="TEST-CAPACITY-001",
            wildberries_article=12345
        )
        
        # Test creation
        row_number = operations.create_product("test_sheet", product)
        
        # Verify capacity check was called
        mock_sheets_client.ensure_sheet_capacity.assert_called_once()
        
        # Verify product was created
        assert row_number > 0
        mock_worksheet.update.assert_called_once()
    
    def test_batch_create_with_capacity_management(self):
        """Test batch product creation with capacity management."""
        # Mock dependencies
        mock_sheets_client = Mock()
        mock_formatter = Mock()
        
        operations = SheetsOperations(mock_sheets_client)
        operations.formatter = mock_formatter
        
        # Create test products
        products = []
        for i in range(100):  # Large batch
            products.append(Product(
                seller_article=f"BATCH-{i:03d}",
                wildberries_article=10000 + i
            ))
        
        # Mock methods
        mock_worksheet = Mock()
        operations.get_or_create_worksheet = Mock(return_value=mock_worksheet)
        operations._get_all_seller_articles = Mock(return_value=set())
        operations._find_next_empty_row = Mock(return_value=51)
        mock_formatter.format_products_batch.return_value = [["data"] * 8] * 100
        
        # Test batch creation
        row_numbers = operations.create_products_batch("test_sheet", products)
        
        # Verify capacity check was called for the batch
        mock_sheets_client.ensure_sheet_capacity.assert_called_once()
        expected_end_row = 51 + 100 - 1  # start_row + batch_size - 1
        mock_sheets_client.ensure_sheet_capacity.assert_called_with(expected_end_row, 8)
        
        # Verify batch was created
        assert len(row_numbers) == 100
        mock_worksheet.update.assert_called_once()
    
    def test_capacity_error_handling(self):
        """Test handling of capacity-related errors."""
        mock_worksheet = Mock()
        mock_worksheet.resize.side_effect = Exception("API quota exceeded")
        
        self.sheets_client._worksheet = mock_worksheet
        
        # Test that capacity error is properly wrapped
        with pytest.raises(SheetsAPIError):
            self.sheets_client.ensure_sheet_capacity(1000, 8)
    
    def test_space_check_error_handling(self):
        """Test handling of errors during space checking."""
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.side_effect = Exception("Network error")
        
        self.sheets_client._worksheet = mock_worksheet
        
        # Test that error is handled gracefully
        space_check = self.sheets_client.check_sheet_space(100, 8)
        assert "error" in space_check
        assert space_check["space_sufficient"] is False


class TestLargeDataHandling:
    """Test handling of large datasets."""
    
    def test_large_product_batch_processing(self):
        """Test processing of very large product batches."""
        # This would be an integration test that creates many products
        # For now, we'll test the logic without actual Google Sheets calls
        
        mock_sheets_client = Mock()
        mock_formatter = Mock()
        
        operations = SheetsOperations(mock_sheets_client)
        operations.formatter = mock_formatter
        
        # Simulate very large dataset
        num_products = 1000
        products = []
        for i in range(num_products):
            products.append(Product(
                seller_article=f"LARGE-BATCH-{i:04d}",
                wildberries_article=20000 + i,
                total_stock=i * 10,
                total_orders=i * 2
            ))
        
        # Mock the necessary methods
        mock_worksheet = Mock()
        operations.get_or_create_worksheet = Mock(return_value=mock_worksheet)
        operations._get_all_seller_articles = Mock(return_value=set())
        operations._find_next_empty_row = Mock(return_value=2)
        mock_formatter.format_products_batch.return_value = [["data"] * 8] * num_products
        
        # Test large batch processing
        row_numbers = operations.create_products_batch("test_sheet", products)
        
        # Verify capacity management was called for large dataset
        mock_sheets_client.ensure_sheet_capacity.assert_called_once()
        expected_end_row = 2 + num_products - 1
        mock_sheets_client.ensure_sheet_capacity.assert_called_with(expected_end_row, 8)
        
        # Verify all products were processed
        assert len(row_numbers) == num_products


if __name__ == "__main__":
    pytest.main([__file__, "-v"])