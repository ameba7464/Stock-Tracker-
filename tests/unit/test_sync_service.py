"""
Unit tests for SyncService
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from sqlalchemy.orm import Session

from stock_tracker.services.sync_service import SyncService
from stock_tracker.database.models import Tenant, Product


class TestSyncService:
    """Test SyncService functionality"""
    
    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant"""
        tenant = MagicMock(spec=Tenant)
        tenant.id = "3eb1c21d-3538-4cab-a98a-9894460e2c4d"
        tenant.name = "Test Company"
        tenant.marketplace_type = "wildberries"
        tenant.marketplace_credentials = {"api_key": "test_key"}
        return tenant
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = MagicMock(spec=Session)
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.query = MagicMock()
        return db
    
    @pytest.fixture
    def mock_marketplace_client(self):
        """Create mock marketplace client"""
        client = MagicMock()
        client.get_products = AsyncMock(return_value=[
            {
                "nmId": 163383326,
                "vendorCode": "TEST-001",
                "name": "Test Product 1",
                "stocks": [],
                "price": 1000,
                "discount": 10,
                "totalQuantity": 50,
                "inWayToClient": 5,
                "inWayFromClient": 2
            },
            {
                "nmId": 163383327,
                "vendorCode": "TEST-002",
                "name": "Test Product 2",
                "stocks": [],
                "price": 2000,
                "discount": 0,
                "totalQuantity": 30,
                "inWayToClient": 0,
                "inWayFromClient": 0
            }
        ])
        return client
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    def test_sync_service_initialization(self, mock_factory, mock_tenant, mock_db):
        """Test SyncService initialization"""
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        
        assert service.tenant == mock_tenant
        assert service.db == mock_db
        mock_factory.create.assert_called_once()
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_products_success(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db, mock_marketplace_client):
        """Test successful product synchronization"""
        # Setup mocks
        mock_factory.create.return_value = mock_marketplace_client
        mock_asyncio_run.return_value = [
            {
                "nmId": 163383326,
                "vendorCode": "TEST-001",
                "name": "Test Product 1",
                "stocks": [],
                "price": 1000,
                "discount": 10,
                "totalQuantity": 50,
                "inWayToClient": 5,
                "inWayFromClient": 2
            }
        ]
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        result = service.sync_products()
        
        # Verify
        assert result["products_synced"] == 1
        assert result["status"] == "success"
        assert "duration_seconds" in result
        mock_db.commit.assert_called()
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_products_upsert_logic(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db, mock_marketplace_client):
        """Test product upsert logic"""
        # Setup mocks
        mock_factory.create.return_value = mock_marketplace_client
        mock_asyncio_run.return_value = [
            {
                "nmId": 163383326,
                "vendorCode": "TEST-001",
                "name": "Test Product 1",
                "stocks": [{"warehouseName": "Подольск", "quantity": 50}],
                "price": 1000,
                "discount": 10,
                "totalQuantity": 50,
                "inWayToClient": 5,
                "inWayFromClient": 2
            }
        ]
        
        # Mock existing product
        existing_product = MagicMock(spec=Product)
        existing_product.marketplace_article = "163383326"
        existing_product.total_stock = 30
        
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = existing_product
        mock_db.query.return_value = mock_query
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        result = service.sync_products()
        
        # Verify product was updated
        assert result["products_synced"] >= 1
        assert existing_product.total_stock == 50  # Updated value
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_products_handles_errors(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db):
        """Test error handling during sync"""
        # Setup mocks to raise exception
        mock_asyncio_run.side_effect = Exception("API connection error")
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        
        with pytest.raises(Exception) as exc_info:
            service.sync_products()
        
        assert "API connection error" in str(exc_info.value)
        mock_db.rollback.assert_called()
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_products_empty_response(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db, mock_marketplace_client):
        """Test sync with empty product list"""
        # Setup mocks
        mock_factory.create.return_value = mock_marketplace_client
        mock_asyncio_run.return_value = []
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        result = service.sync_products()
        
        # Verify
        assert result["products_synced"] == 0
        assert result["status"] == "success"
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_products_warehouse_data_parsing(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db, mock_marketplace_client):
        """Test warehouse data parsing and aggregation"""
        # Setup mocks with warehouse data
        mock_factory.create.return_value = mock_marketplace_client
        mock_asyncio_run.return_value = [
            {
                "nmId": 163383326,
                "vendorCode": "TEST-001",
                "name": "Test Product 1",
                "stocks": [
                    {"warehouseName": "Подольск", "quantity": 30},
                    {"warehouseName": "Электросталь", "quantity": 20}
                ],
                "price": 1000,
                "discount": 10,
                "totalQuantity": 50,
                "inWayToClient": 5,
                "inWayFromClient": 2
            }
        ]
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        result = service.sync_products()
        
        # Verify warehouse data was processed
        assert result["products_synced"] == 1
        mock_db.add.assert_called()


class TestProductModel:
    """Test Product model functionality"""
    
    def test_product_creation(self):
        """Test creating a Product instance"""
        product = Product(
            tenant_id="test-tenant-id",
            marketplace_article="163383326",
            seller_article="TEST-001",
            product_name="Test Product",
            total_stock=50,
            total_orders=10
        )
        
        assert product.marketplace_article == "163383326"
        assert product.seller_article == "TEST-001"
        assert product.total_stock == 50
        assert product.total_orders == 10
    
    def test_product_str_representation(self):
        """Test Product string representation"""
        product = Product(
            tenant_id="test-tenant-id",
            marketplace_article="163383326",
            seller_article="TEST-001",
            product_name="Test Product"
        )
        
        str_repr = str(product)
        assert "163383326" in str_repr or "TEST-001" in str_repr
    
    def test_product_warehouse_data_jsonb(self):
        """Test JSONB warehouse_data field"""
        warehouse_data = {
            "Подольск": {"stock": 30, "orders": 5},
            "Электросталь": {"stock": 20, "orders": 3}
        }
        
        product = Product(
            tenant_id="test-tenant-id",
            marketplace_article="163383326",
            seller_article="TEST-001",
            warehouse_data=warehouse_data
        )
        
        assert product.warehouse_data == warehouse_data
        assert "Подольск" in product.warehouse_data


class TestSyncServicePerformance:
    """Test SyncService performance characteristics"""
    
    @patch("stock_tracker.services.sync_service.MarketplaceClientFactory")
    @patch("asyncio.run")
    def test_sync_large_product_batch(self, mock_asyncio_run, mock_factory, mock_tenant, mock_db):
        """Test syncing large batch of products"""
        # Generate 1000 mock products
        products = [
            {
                "nmId": 163383000 + i,
                "vendorCode": f"TEST-{i:04d}",
                "name": f"Test Product {i}",
                "stocks": [],
                "price": 1000,
                "discount": 0,
                "totalQuantity": 10,
                "inWayToClient": 0,
                "inWayFromClient": 0
            }
            for i in range(1000)
        ]
        
        mock_asyncio_run.return_value = products
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Execute sync
        service = SyncService(tenant=mock_tenant, db_session=mock_db)
        result = service.sync_products()
        
        # Verify all products synced
        assert result["products_synced"] == 1000
        assert result["status"] == "success"
        assert result["duration_seconds"] > 0
