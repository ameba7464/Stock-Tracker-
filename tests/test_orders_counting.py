"""
Tests for orders counting logic in ProductService.

Verifies that _convert_api_record_to_product correctly counts orders
from API data and matches them with products.
"""

import pytest
from stock_tracker.services.product_service import ProductService


class TestOrdersCounting:
    """Test suite for orders counting functionality."""
    
    def setup_method(self):
        """Set up test instance."""
        self.service = ProductService()
    
    def test_orders_counting_by_nm_id(self):
        """Test that orders are correctly counted by nmId."""
        # Sample warehouse remains data
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 50},
                {'warehouseName': 'Подольск', 'quantity': 30}
            ]
        }
        
        # Sample orders data
        orders_data = [
            {'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'TEST-001'},
            {'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'TEST-001'},
            {'nmId': 12345, 'warehouseName': 'Подольск', 'supplierArticle': 'TEST-001'},
            {'nmId': 67890, 'warehouseName': 'Коледино', 'supplierArticle': 'OTHER-001'},  # Different product
        ]
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        assert product.total_orders == 3  # Should count 3 orders for nmId 12345
        assert product.total_stock == 80   # 50 + 30
        
        # Check warehouse-level orders
        koledino_warehouse = next(w for w in product.warehouses if w.name == 'Коледино')
        podolsk_warehouse = next(w for w in product.warehouses if w.name == 'Подольск')
        
        assert koledino_warehouse.orders == 2  # 2 orders in Коледино
        assert podolsk_warehouse.orders == 1   # 1 order in Подольск
    
    def test_orders_counting_without_warehouse_match(self):
        """Test orders counting when warehouse names don't match exactly."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 50}
            ]
        }
        
        # Orders with missing or different warehouse names
        orders_data = [
            {'nmId': 12345, 'warehouseName': '', 'supplierArticle': 'TEST-001'},  # Empty warehouse
            {'nmId': 12345, 'warehouseName': None, 'supplierArticle': 'TEST-001'},  # None warehouse
            {'nmId': 12345, 'warehouseName': 'Другой склад', 'supplierArticle': 'TEST-001'},  # Different warehouse
        ]
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        # Should still count orders for the same nmId even if warehouse doesn't match
        assert product.total_orders == 3
        
        # All orders should be attributed to the existing warehouse
        koledino_warehouse = product.warehouses[0]
        assert koledino_warehouse.orders == 3
    
    def test_orders_counting_by_supplier_article(self):
        """Test fallback matching by supplierArticle when warehouse doesn't match."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 50}
            ]
        }
        
        orders_data = [
            {'nmId': 12345, 'warehouseName': 'Другой склад', 'supplierArticle': 'TEST-001'},
            {'nmId': 12345, 'warehouseName': 'Третий склад', 'supplierArticle': 'TEST-001'},
        ]
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        assert product.total_orders == 2
        assert product.warehouses[0].orders == 2
    
    def test_empty_orders_data(self):
        """Test behavior with no orders data."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 50}
            ]
        }
        
        orders_data = []
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        assert product.total_orders == 0
        assert product.warehouses[0].orders == 0
        assert product.turnover_rate == 0.0
    
    def test_none_orders_data(self):
        """Test behavior with None orders data."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 50}
            ]
        }
        
        product = self.service._convert_api_record_to_product(api_record, None)
        
        assert product.total_orders == 0
        assert product.warehouses[0].orders == 0
    
    def test_turnover_calculation_with_orders(self):
        """Test turnover rate calculation when orders are present."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'TEST-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 100}
            ]
        }
        
        # 25 orders for 100 stock = 0.25 turnover
        orders_data = [{'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'TEST-001'}] * 25
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        assert product.total_orders == 25
        assert product.total_stock == 100
        assert product.turnover_rate == 0.25
    
    def test_complex_multi_warehouse_scenario(self):
        """Test complex scenario with multiple warehouses and mixed orders."""
        api_record = {
            'nmId': 12345,
            'vendorCode': 'COMPLEX-001',
            'warehouses': [
                {'warehouseName': 'Коледино', 'quantity': 100},
                {'warehouseName': 'Подольск', 'quantity': 50},
                {'warehouseName': 'Екатеринбург', 'quantity': 25}
            ]
        }
        
        orders_data = [
            # Коледино orders
            {'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'COMPLEX-001'},
            {'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'COMPLEX-001'},
            {'nmId': 12345, 'warehouseName': 'Коледино', 'supplierArticle': 'COMPLEX-001'},
            # Подольск orders
            {'nmId': 12345, 'warehouseName': 'Подольск', 'supplierArticle': 'COMPLEX-001'},
            {'nmId': 12345, 'warehouseName': 'Подольск', 'supplierArticle': 'COMPLEX-001'},
            # No Екатеринбург orders
            # Orders with missing warehouse (should be distributed)
            {'nmId': 12345, 'warehouseName': '', 'supplierArticle': 'COMPLEX-001'},
            {'nmId': 12345, 'warehouseName': None, 'supplierArticle': 'COMPLEX-001'},
        ]
        
        product = self.service._convert_api_record_to_product(api_record, orders_data)
        
        assert product.total_orders == 7
        assert product.total_stock == 175  # 100 + 50 + 25
        
        # Find warehouses by name
        warehouses_by_name = {wh.name: wh for wh in product.warehouses}
        
        assert warehouses_by_name['Коледино'].orders >= 3  # At least the exact matches
        assert warehouses_by_name['Подольск'].orders >= 2  # At least the exact matches
        # Екатеринбург might get some of the unmatched orders


if __name__ == "__main__":
    pytest.main([__file__, "-v"])