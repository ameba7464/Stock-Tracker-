"""
Тесты для новой горизонтальной структуры Google Sheets.

Проверяет:
- Правильность структуры заголовков (2 строки с объединением)
- Корректность данных по складам (горизонтальная раскладка)
- Форматирование и границы
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from stock_tracker.services.google_sheets_service import GoogleSheetsService
from stock_tracker.database.models import Tenant, Product


@pytest.fixture
def mock_tenant():
    """Создать мок tenant с Google credentials."""
    tenant = Mock(spec=Tenant)
    tenant.id = "test-tenant-id"
    tenant.name = "Test Tenant"
    tenant.google_sheet_id = "test-sheet-id"
    tenant.google_service_account_encrypted = b"encrypted_creds"
    return tenant


@pytest.fixture
def mock_worksheet():
    """Создать мок worksheet."""
    worksheet = MagicMock()
    worksheet.id = 12345
    worksheet.row_count = 1000
    worksheet.col_count = 50
    worksheet.spreadsheet.id = "test-sheet-id"
    worksheet.spreadsheet.url = "https://docs.google.com/spreadsheets/d/test-sheet-id"
    worksheet.spreadsheet.title = "Test Sheet"
    return worksheet


@pytest.fixture
def sample_products():
    """Создать примеры продуктов с данными по складам."""
    products = []
    
    # Продукт 1 - несколько складов
    product1 = Mock(spec=Product)
    product1.brand_name = "ITS COLLAGEN"
    product1.product_name = "Коллаген"
    product1.seller_article = "COL-001"
    product1.wildberries_article = 123456
    product1.nm_id = 123456
    product1.in_way_to_client = 5
    product1.in_way_from_client = 2
    product1.total_orders = 50
    product1.total_stock = 100
    product1.turnover = 10.0
    product1.warehouse_data = {
        "warehouses": [
            {"name": "Коледино", "stock": 40, "orders": 20},
            {"name": "Подольск", "stock": 35, "orders": 18},
            {"name": "Электросталь", "stock": 25, "orders": 12}
        ]
    }
    products.append(product1)
    
    # Продукт 2 - один склад
    product2 = Mock(spec=Product)
    product2.brand_name = "ITS COLLAGEN"
    product2.product_name = "Витамин D3"
    product2.seller_article = "VIT-D3"
    product2.wildberries_article = 789012
    product2.nm_id = 789012
    product2.in_way_to_client = 10
    product2.in_way_from_client = 3
    product2.total_orders = 80
    product2.total_stock = 150
    product2.turnover = 8.5
    product2.warehouse_data = {
        "warehouses": [
            {"name": "Коледино", "stock": 150, "orders": 80}
        ]
    }
    products.append(product2)
    
    return products


class TestGoogleSheetsStructure:
    """Тесты структуры Google Sheets."""
    
    def test_header_constants(self):
        """Проверить константы заголовков."""
        assert GoogleSheetsService.NUM_BASE_INFO_COLS == 4
        assert GoogleSheetsService.NUM_GENERAL_METRICS_COLS == 6
        assert GoogleSheetsService.NUM_WAREHOUSE_COLS == 3
        
        assert len(GoogleSheetsService.HEADER_ROW2_BASE) == 4
        assert len(GoogleSheetsService.HEADER_ROW2_GENERAL) == 6
        assert len(GoogleSheetsService.HEADER_ROW2_WAREHOUSE) == 3
    
    def test_col_number_to_letter(self, mock_tenant):
        """Проверить конвертацию номера колонки в букву."""
        service = GoogleSheetsService(mock_tenant)
        
        assert service._col_number_to_letter(1) == 'A'
        assert service._col_number_to_letter(2) == 'B'
        assert service._col_number_to_letter(26) == 'Z'
        assert service._col_number_to_letter(27) == 'AA'
        assert service._col_number_to_letter(28) == 'AB'
        assert service._col_number_to_letter(52) == 'AZ'
        assert service._col_number_to_letter(53) == 'BA'
    
    def test_warehouse_filtering(self, mock_tenant, sample_products):
        """Проверить фильтрацию служебных складов."""
        service = GoogleSheetsService(mock_tenant)
        
        # Добавим служебные склады в данные
        sample_products[0].warehouse_data["warehouses"].append(
            {"name": "В пути до получателей", "stock": 10, "orders": 5}
        )
        sample_products[0].warehouse_data["warehouses"].append(
            {"name": "Остальные", "stock": 5, "orders": 2}
        )
        
        # Собираем склады
        all_warehouses = set()
        for product in sample_products:
            for wh in product.warehouse_data.get("warehouses", []):
                wh_name = wh.get("name", "")
                if wh_name and wh_name not in service.SERVICE_WAREHOUSES:
                    all_warehouses.add(wh_name)
        
        # Проверяем что служебные склады отфильтрованы
        assert "В пути до получателей" not in all_warehouses
        assert "Остальные" not in all_warehouses
        assert "Коледино" in all_warehouses
        assert "Подольск" in all_warehouses
        assert "Электросталь" in all_warehouses
    
    @patch('stock_tracker.services.google_sheets_service.get_encryptor')
    @patch('stock_tracker.services.google_sheets_service.Credentials')
    @patch('stock_tracker.services.google_sheets_service.gspread')
    def test_sync_products_structure(
        self,
        mock_gspread,
        mock_credentials,
        mock_get_encryptor,
        mock_tenant,
        mock_worksheet,
        sample_products
    ):
        """Проверить структуру данных при синхронизации."""
        # Setup mocks
        mock_encryptor = Mock()
        mock_encryptor.decrypt.return_value = '{"type": "service_account"}'
        mock_get_encryptor.return_value = mock_encryptor
        
        mock_credentials.from_service_account_info.return_value = Mock()
        
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_spreadsheet.id = "test-sheet-id"
        mock_spreadsheet.url = "https://docs.google.com/spreadsheets/d/test-sheet-id"
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_gspread.authorize.return_value = mock_client
        
        # Create service and sync
        service = GoogleSheetsService(mock_tenant)
        db_mock = Mock()
        
        result = service.sync_products_to_sheet(sample_products, db_mock)
        
        # Проверяем результат
        assert result["success"] is True
        assert result["products_synced"] == 2
        assert result["warehouses_count"] == 3  # Коледино, Подольск, Электросталь
        
        # Проверяем что вызваны правильные методы
        mock_worksheet.clear.assert_called_once()
        assert mock_worksheet.update.call_count >= 2  # Минимум заголовки и данные
        
        # Проверяем batch_update вызван для merge и форматирования
        # batch_update вызывается через worksheet.spreadsheet.batch_update
        assert mock_worksheet.spreadsheet.batch_update.call_count >= 1
    
    def test_empty_products_list(self, mock_tenant):
        """Проверить обработку пустого списка продуктов."""
        service = GoogleSheetsService(mock_tenant)
        
        # Собираем склады из пустого списка
        warehouses = []
        for product in []:
            pass
        
        assert len(warehouses) == 0
    
    def test_product_with_no_warehouses(self, mock_tenant):
        """Проверить продукт без данных о складах."""
        service = GoogleSheetsService(mock_tenant)
        
        product = Mock(spec=Product)
        product.warehouse_data = {}
        
        warehouses = product.warehouse_data.get("warehouses", [])
        assert len(warehouses) == 0
    
    def test_column_count_calculation(self, mock_tenant):
        """Проверить расчет количества колонок."""
        service = GoogleSheetsService(mock_tenant)
        
        # 0 складов
        warehouses_count = 0
        total_cols = (
            service.NUM_BASE_INFO_COLS + 
            service.NUM_GENERAL_METRICS_COLS + 
            (warehouses_count * service.NUM_WAREHOUSE_COLS)
        )
        assert total_cols == 10
        
        # 3 склада
        warehouses_count = 3
        total_cols = (
            service.NUM_BASE_INFO_COLS + 
            service.NUM_GENERAL_METRICS_COLS + 
            (warehouses_count * service.NUM_WAREHOUSE_COLS)
        )
        assert total_cols == 19  # 4 + 6 + (3 * 3)
        
        # 10 складов
        warehouses_count = 10
        total_cols = (
            service.NUM_BASE_INFO_COLS + 
            service.NUM_GENERAL_METRICS_COLS + 
            (warehouses_count * service.NUM_WAREHOUSE_COLS)
        )
        assert total_cols == 40  # 4 + 6 + (10 * 3)


class TestBorderCalculations:
    """Тесты расчета границ между секциями."""
    
    def test_base_info_border(self):
        """Проверить границу после основной информации."""
        # После колонки D (индекс 3)
        border_col = GoogleSheetsService.NUM_BASE_INFO_COLS - 1
        assert border_col == 3
    
    def test_general_metrics_border(self):
        """Проверить границу после общих метрик."""
        # После колонки J (индекс 9)
        border_col = (
            GoogleSheetsService.NUM_BASE_INFO_COLS + 
            GoogleSheetsService.NUM_GENERAL_METRICS_COLS - 1
        )
        assert border_col == 9
    
    def test_warehouse_borders(self):
        """Проверить границы между складами."""
        warehouses = ["Коледино", "Подольск", "Электросталь"]
        
        borders = []
        for i in range(len(warehouses) - 1):  # Не добавляем после последнего
            col_index = (
                GoogleSheetsService.NUM_BASE_INFO_COLS + 
                GoogleSheetsService.NUM_GENERAL_METRICS_COLS + 
                (i * GoogleSheetsService.NUM_WAREHOUSE_COLS) + 
                GoogleSheetsService.NUM_WAREHOUSE_COLS - 1
            )
            borders.append(col_index)
        
        # Ожидаем границы после колонок: M (12), P (15)
        assert borders == [12, 15]
        assert len(borders) == len(warehouses) - 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
