"""
Tests for ProductService performance analysis functionality.

Verifies _analyze_product_performance method correctly categorizes
products by turnover and stock status.
"""

import pytest
from stock_tracker.core.models import Product, Warehouse
from stock_tracker.services.product_service import ProductService


class TestPerformanceAnalysis:
    """Test suite for product performance analysis."""
    
    def setup_method(self):
        """Set up test instance."""
        # Create service instance without external dependencies
        self.service = ProductService()
    
    def create_test_product(self, seller_article: str, turnover: float, total_stock: int) -> Product:
        """Helper to create Product instance for testing."""
        product = Product(
            seller_article=seller_article,
            wildberries_article=12345,
            total_stock=total_stock,
            total_orders=int(turnover * total_stock) if total_stock > 0 else 0
        )
        product.turnover = turnover
        return product
    
    def test_high_performance_category(self):
        """Test high performance categorization (turnover >= 2.0)."""
        product = self.create_test_product("HIGH-001", 3.5, 100)
        
        result = self.service._analyze_product_performance(product)
        
        assert result["category"] == "high_performance"
        assert result["risk_level"] == "low"
        assert "excellent turnover" in result["recommendation"].lower()
        assert result["stock_status"] == "adequate"
    
    def test_medium_performance_category(self):
        """Test medium performance categorization (1.0 <= turnover < 2.0)."""
        product = self.create_test_product("MED-001", 1.5, 50)
        
        result = self.service._analyze_product_performance(product)
        
        assert result["category"] == "medium_performance"
        assert result["risk_level"] == "medium"
        assert "good performance" in result["recommendation"].lower()
        assert result["stock_status"] == "adequate"
    
    def test_low_performance_category(self):
        """Test low performance categorization (turnover < 1.0)."""
        product = self.create_test_product("LOW-001", 0.3, 30)
        
        result = self.service._analyze_product_performance(product)
        
        assert result["category"] == "low_performance"
        assert result["risk_level"] == "high"
        assert "low turnover" in result["recommendation"].lower()
        assert result["stock_status"] == "adequate"
    
    def test_out_of_stock_critical(self):
        """Test out of stock status overrides other risk levels."""
        product = self.create_test_product("OUT-001", 5.0, 0)  # High turnover but no stock
        
        result = self.service._analyze_product_performance(product)
        
        assert result["stock_status"] == "out_of_stock"
        assert result["risk_level"] == "critical"
        assert "restock immediately" in result["recommendation"].lower()
    
    def test_low_stock_warning(self):
        """Test low stock status (< 10 units)."""
        product = self.create_test_product("LOW-STOCK-001", 1.2, 5)
        
        result = self.service._analyze_product_performance(product)
        
        assert result["stock_status"] == "low_stock"
        assert result["risk_level"] == "high"
        assert result["category"] == "medium_performance"  # Should still categorize turnover
    
    def test_zero_turnover_edge_case(self):
        """Test product with zero turnover."""
        product = self.create_test_product("ZERO-001", 0.0, 100)
        
        result = self.service._analyze_product_performance(product)
        
        assert result["category"] == "low_performance"
        assert product.turnover == 0.0  # Check product directly, not analysis result
        assert result["stock_status"] == "adequate"
    
    def test_analysis_error_handling(self):
        """Test graceful error handling in analysis."""
        # Create malformed product that might cause errors
        product = Product(seller_article="ERROR-001", wildberries_article=0)
        product.turnover = None  # Invalid turnover
        
        result = self.service._analyze_product_performance(product)
        
        # Should return unknown category on error
        assert result["category"] == "unknown"
        assert "recommendation" in result
    
    def test_edge_case_turnover_boundaries(self):
        """Test exact boundary values for turnover categories."""
        # Exactly 2.0 turnover
        product_high = self.create_test_product("BOUND-HIGH", 2.0, 20)
        result_high = self.service._analyze_product_performance(product_high)
        assert result_high["category"] == "high_performance"
        
        # Exactly 1.0 turnover  
        product_med = self.create_test_product("BOUND-MED", 1.0, 20)
        result_med = self.service._analyze_product_performance(product_med)
        assert result_med["category"] == "medium_performance"
        
        # Just below 1.0 turnover
        product_low = self.create_test_product("BOUND-LOW", 0.99, 20)
        result_low = self.service._analyze_product_performance(product_low)
        assert result_low["category"] == "low_performance"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])