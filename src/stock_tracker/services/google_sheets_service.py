"""
Google Sheets Service for multi-tenant product synchronization.

Manages Google Sheets creation, formatting, and data synchronization for tenants.
Each tenant gets their own Google Sheet with automatic updates.

НОВАЯ СТРУКТУРА (23.11.2025):
- 2 строки заголовков с объединением ячеек
- Горизонтальная раскладка складов (каждый склад = 3 колонки)
- Группы колонок: Основная информация | Общие метрики | Склады
- Улучшенное форматирование с толстыми границами между секциями
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

import gspread
from google.oauth2.service_account import Credentials
from sqlalchemy.orm import Session

from stock_tracker.database.models import Tenant, Product
from stock_tracker.services.tenant_credentials import get_encryptor
from stock_tracker.utils.exceptions import SheetsAPIError

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for managing tenant Google Sheets with horizontal warehouse layout"""
    
    # Константы структуры таблицы
    NUM_BASE_INFO_COLS = 4  # Бренд, Предмет, Артикул продавца, Артикул товара (nmid)
    NUM_GENERAL_METRICS_COLS = 5  # В пути до покупателя, В пути конв., Заказы, Остатки, Оборачиваемость (убрана "Всего заказов на складах WB")
    NUM_WAREHOUSE_COLS = 3  # Остатки, Заказы, Оборач. (для каждого склада)
    
    # Названия заголовков группы 1
    HEADER_GROUP_BASE_INFO = "Основная информация"
    HEADER_GROUP_GENERAL_METRICS = "Общие метрики"
    
    # Названия колонок строки 2
    HEADER_ROW2_BASE = [
        "Бренд",
        "Предмет", 
        "Артикул продавца",
        "Артикул товара (nmid)"
    ]
    
    HEADER_ROW2_GENERAL = [
        "В пути до покупателя",
        "В пути конв. на склад WB",
        # "Всего заказов на складах WB",  # Убрана метрика
        "Заказы (всего)",
        "Остатки (всего)",
        "Оборачиваемость (дни)"
    ]
    
    HEADER_ROW2_WAREHOUSE = ["Остатки", "Заказы", "Оборач."]
    
    # Цвета форматирования
    HEADER_BG_COLOR = {"red": 0.4, "green": 0.49, "blue": 0.92}  # Фиолетовый
    HEADER_TEXT_COLOR = {"red": 1.0, "green": 1.0, "blue": 1.0}  # Белый
    BORDER_COLOR_LIGHT = {"red": 0.8, "green": 0.8, "blue": 0.8}  # Светло-серый
    BORDER_COLOR_THICK = {"red": 0.2, "green": 0.2, "blue": 0.2}  # Темно-серый
    
    # Ширина колонок (в пикселях)
    COL_WIDTH_BRAND = 150
    COL_WIDTH_SUBJECT = 200
    COL_WIDTH_VENDOR_CODE = 180
    COL_WIDTH_NM_ID = 150
    COL_WIDTH_GENERAL = 120
    COL_WIDTH_WAREHOUSE = 90
    
    # Высота строк (в пикселях)
    ROW_HEIGHT_HEADER1 = 35
    ROW_HEIGHT_HEADER2 = 40
    
    # Служебные склады (исключаются из физических складов)
    SERVICE_WAREHOUSES = {
        'В пути до получателей',
        'В пути возвраты на склад WB',
        'Всего находится на складах',
        'Остальные'
    }
    
    # Google Sheets API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    def __init__(self, tenant: Tenant):
        """
        Initialize Google Sheets service for tenant.
        
        Args:
            tenant: Tenant instance with Google credentials
        """
        self.tenant = tenant
        self._client: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._warehouse_names: List[str] = []  # Will be populated dynamically
        
        logger.info(f"GoogleSheetsService initialized for tenant {tenant.id}")
    

    
    def _get_credentials(self) -> Credentials:
        """
        Get Google service account credentials for tenant.
        
        Returns:
            Google OAuth2 Credentials
            
        Raises:
            ValueError: If credentials are not configured
        """
        if not self.tenant.google_service_account_encrypted:
            raise ValueError(
                f"Google credentials not configured for tenant {self.tenant.id}. "
                "Please set up Google Sheets integration first."
            )
        
        # Decrypt credentials
        encryptor = get_encryptor()
        credentials_json = encryptor.decrypt(
            self.tenant.google_service_account_encrypted
        )
        
        # Parse JSON and create credentials
        credentials_dict = json.loads(credentials_json)
        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=self.SCOPES
        )
        
        return credentials
    
    def _get_client(self) -> gspread.Client:
        """Get authenticated gspread client, creating if needed."""
        if self._client is None:
            credentials = self._get_credentials()
            self._client = gspread.authorize(credentials)
            logger.info(f"Authenticated with Google Sheets API for tenant {self.tenant.id}")
        
        return self._client
    
    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Get tenant's spreadsheet, opening if needed."""
        if self._spreadsheet is None:
            if not self.tenant.google_sheet_id:
                raise ValueError(
                    f"Google Sheet ID not set for tenant {self.tenant.id}. "
                    "Please create a sheet first."
                )
            
            client = self._get_client()
            self._spreadsheet = client.open_by_key(self.tenant.google_sheet_id)
            logger.info(f"Opened spreadsheet: {self._spreadsheet.title}")
        
        return self._spreadsheet
    
    def create_new_sheet(
        self,
        title: str = None,
        share_with_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Google Sheet for tenant.
        
        Args:
            title: Sheet title (default: "{tenant_name} - Stock Tracker")
            share_with_email: Optional email to share sheet with
            
        Returns:
            Dict with sheet information
        """
        logger.info(f"Creating new Google Sheet for tenant {self.tenant.id}")
        
        client = self._get_client()
        
        # Generate title
        if not title:
            title = f"{self.tenant.name} - Stock Tracker"
        
        # Create spreadsheet
        spreadsheet = client.create(title)
        
        # Get main worksheet
        worksheet = spreadsheet.sheet1
        worksheet.update_title("Products")
        
        # Setup headers and formatting
        self._setup_sheet_formatting(worksheet)
        
        # Share with user if email provided
        if share_with_email:
            try:
                spreadsheet.share(
                    share_with_email,
                    perm_type='user',
                    role='writer',
                    notify=True,
                    email_message=f"Your Stock Tracker sheet for {self.tenant.name} is ready!"
                )
                logger.info(f"Shared sheet with {share_with_email}")
            except Exception as e:
                logger.warning(f"Failed to share sheet: {e}")
        
        # Store sheet ID in tenant
        sheet_id = spreadsheet.id
        sheet_url = spreadsheet.url
        
        result = {
            "sheet_id": sheet_id,
            "sheet_url": sheet_url,
            "title": title,
            "worksheet_name": "Products"
        }
        
        logger.info(f"Created Google Sheet: {sheet_url}")
        return result
    
    def _setup_sheet_formatting(self, worksheet: gspread.Worksheet, warehouses: List[str] = None):
        """
        Setup initial sheet formatting and headers with new horizontal layout.
        
        Args:
            worksheet: Worksheet to format
            warehouses: List of warehouse names (optional, empty list used if not provided)
        """
        if warehouses is None:
            warehouses = []
        
        # Подготовка заголовков
        header_row2 = self.HEADER_ROW2_BASE + self.HEADER_ROW2_GENERAL
        for _ in warehouses:
            header_row2.extend(self.HEADER_ROW2_WAREHOUSE)
        
        total_cols = len(header_row2)
        
        # Записываем строку 2 (названия колонок)
        worksheet.update(values=[header_row2], range_name='A2')
        
        # Объединяем ячейки для заголовков групп и записываем строку 1
        self._merge_and_write_group_headers(worksheet, warehouses)
        
        # Применяем форматирование
        self._apply_full_formatting(worksheet, total_cols, 0, warehouses)
        
        logger.info(f"Sheet formatting applied with {len(warehouses)} warehouses")
    
    def _merge_and_write_group_headers(self, worksheet: gspread.Worksheet, warehouses: List[str]):
        """
        Объединить ячейки для заголовков групп и записать их.
        
        Args:
            worksheet: Worksheet to format
            warehouses: List of warehouse names
        """
        try:
            merge_requests = []
            
            # Основная информация (A1:D1)
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': self.NUM_BASE_INFO_COLS
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
            
            # Общие метрики (E1:J1)
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': self.NUM_BASE_INFO_COLS,
                        'endColumnIndex': self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
            
            # Склады (каждый склад = 3 колонки)
            for i in range(len(warehouses)):
                start_col = self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS + (i * self.NUM_WAREHOUSE_COLS)
                end_col = start_col + self.NUM_WAREHOUSE_COLS
                
                merge_requests.append({
                    'mergeCells': {
                        'range': {
                            'sheetId': worksheet.id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': start_col,
                            'endColumnIndex': end_col
                        },
                        'mergeType': 'MERGE_ALL'
                    }
                })
            
            # Применяем объединение
            worksheet.spreadsheet.batch_update({'requests': merge_requests})
            
            # Записываем текст в объединенные ячейки
            worksheet.update(values=[[self.HEADER_GROUP_BASE_INFO]], range_name='A1')
            worksheet.update(values=[[self.HEADER_GROUP_GENERAL_METRICS]], range_name='E1')
            
            # Записываем названия складов
            for i, warehouse in enumerate(warehouses):
                col_letter = self._col_number_to_letter(11 + (i * self.NUM_WAREHOUSE_COLS))  # K, N, Q, ...
                worksheet.update(values=[[warehouse]], range_name=f'{col_letter}1')
            
            logger.debug(f"Merged cells for {len(warehouses)} warehouses")
            
        except Exception as e:
            logger.warning(f"Failed to merge cells: {e}")
    
    def _apply_full_formatting(
        self,
        worksheet: gspread.Worksheet,
        total_cols: int,
        data_rows_count: int,
        warehouses: List[str]
    ):
        """
        Применить полное форматирование к листу.
        
        Args:
            worksheet: Worksheet to format
            total_cols: Total number of columns
            data_rows_count: Number of data rows
            warehouses: List of warehouse names
        """
        try:
            # 1. Настройка размеров колонок и строк
            self._apply_dimension_properties(worksheet, total_cols)
            
            # 2. Форматирование заголовков
            self._format_headers(worksheet, total_cols)
            
            # 3. Форматирование данных
            if data_rows_count > 0:
                self._format_data_cells(worksheet, data_rows_count)
            
            # 4. Добавление границ
            self._apply_borders(worksheet, total_cols, data_rows_count, warehouses)
            
            # 5. Фиксация заголовков
            worksheet.freeze(rows=2, cols=0)
            
            logger.debug("Full formatting applied")
            
        except Exception as e:
            logger.warning(f"Failed to apply full formatting: {e}")
    
    def _apply_dimension_properties(self, worksheet: gspread.Worksheet, total_cols: int):
        """
        Установить ширину колонок и высоту строк.
        
        Args:
            worksheet: Worksheet to format
            total_cols: Total number of columns
        """
        requests = []
        
        # Ширина основных колонок (A-D)
        col_widths = [
            self.COL_WIDTH_BRAND,
            self.COL_WIDTH_SUBJECT,
            self.COL_WIDTH_VENDOR_CODE,
            self.COL_WIDTH_NM_ID
        ]
        
        for idx, width in enumerate(col_widths):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': worksheet.id,
                        'dimension': 'COLUMNS',
                        'startIndex': idx,
                        'endIndex': idx + 1
                    },
                    'properties': {'pixelSize': width},
                    'fields': 'pixelSize'
                }
            })
        
        # Ширина колонок общих метрик (E-J)
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': worksheet.id,
                    'dimension': 'COLUMNS',
                    'startIndex': self.NUM_BASE_INFO_COLS,
                    'endIndex': self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS
                },
                'properties': {'pixelSize': self.COL_WIDTH_GENERAL},
                'fields': 'pixelSize'
            }
        })
        
        # Ширина колонок складов
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': worksheet.id,
                    'dimension': 'COLUMNS',
                    'startIndex': self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS,
                    'endIndex': total_cols
                },
                'properties': {'pixelSize': self.COL_WIDTH_WAREHOUSE},
                'fields': 'pixelSize'
            }
        })
        
        # Высота строк заголовков
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': worksheet.id,
                    'dimension': 'ROWS',
                    'startIndex': 0,
                    'endIndex': 1
                },
                'properties': {'pixelSize': self.ROW_HEIGHT_HEADER1},
                'fields': 'pixelSize'
            }
        })
        
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': worksheet.id,
                    'dimension': 'ROWS',
                    'startIndex': 1,
                    'endIndex': 2
                },
                'properties': {'pixelSize': self.ROW_HEIGHT_HEADER2},
                'fields': 'pixelSize'
            }
        })
        
        # Применяем
        worksheet.spreadsheet.batch_update({'requests': requests})
        logger.debug("Dimension properties applied")
    
    def _format_headers(self, worksheet: gspread.Worksheet, total_cols: int):
        """
        Форматировать заголовки.
        
        Args:
            worksheet: Worksheet to format
            total_cols: Total number of columns
        """
        # Заголовки - фиолетовый фон, белый текст, жирный шрифт
        end_col_letter = self._col_number_to_letter(total_cols)
        worksheet.format(f'A1:{end_col_letter}2', {
            'backgroundColor': self.HEADER_BG_COLOR,
            'textFormat': {
                'bold': True,
                'fontSize': 10,
                'foregroundColor': self.HEADER_TEXT_COLOR
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE',
            'wrapStrategy': 'WRAP'
        })
        logger.debug("Header formatting applied")
    
    def _format_data_cells(self, worksheet: gspread.Worksheet, data_rows_count: int):
        """
        Форматировать ячейки данных.
        
        Args:
            worksheet: Worksheet to format
            data_rows_count: Number of data rows
        """
        # Первые 4 колонки данных - выравнивание слева
        worksheet.format(f'A3:D{data_rows_count + 2}', {
            'horizontalAlignment': 'LEFT',
            'verticalAlignment': 'MIDDLE'
        })
        
        # Остальные колонки - по центру
        worksheet.format(f'E3:ZZ{data_rows_count + 2}', {
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        })
        logger.debug("Data cell formatting applied")
    
    def _apply_borders(
        self,
        worksheet: gspread.Worksheet,
        total_cols: int,
        data_rows_count: int,
        warehouses: List[str]
    ):
        """
        Применить границы.
        
        Args:
            worksheet: Worksheet to format
            total_cols: Total number of columns
            data_rows_count: Number of data rows
            warehouses: List of warehouse names
        """
        border_requests = []
        
        # 1. Обычные границы для всех ячеек с данными
        if data_rows_count > 0:
            border_requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 1,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': 0,
                        'endColumnIndex': total_cols
                    },
                    'top': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT},
                    'bottom': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT},
                    'left': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT},
                    'right': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT},
                    'innerHorizontal': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT},
                    'innerVertical': {'style': 'SOLID', 'width': 1, 'color': self.BORDER_COLOR_LIGHT}
                }
            })
        
        # 2. Толстая горизонтальная граница после строки заголовков
        border_requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': worksheet.id,
                    'startRowIndex': 1,
                    'endRowIndex': 2,
                    'startColumnIndex': 0,
                    'endColumnIndex': total_cols
                },
                'bottom': {
                    'style': 'SOLID_THICK',
                    'width': 3,
                    'color': self.BORDER_COLOR_THICK
                }
            }
        })
        
        # 3. Толстые вертикальные границы для разделения секций
        # После "Основной информации" (колонка D, индекс 3)
        border_requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': worksheet.id,
                    'startRowIndex': 0,
                    'endRowIndex': max(data_rows_count + 2, 2),
                    'startColumnIndex': self.NUM_BASE_INFO_COLS - 1,
                    'endColumnIndex': self.NUM_BASE_INFO_COLS
                },
                'right': {
                    'style': 'SOLID_THICK',
                    'width': 3,
                    'color': self.BORDER_COLOR_THICK
                }
            }
        })
        
        # После "Общих метрик" (колонка J, индекс 9)
        border_requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': worksheet.id,
                    'startRowIndex': 0,
                    'endRowIndex': max(data_rows_count + 2, 2),
                    'startColumnIndex': self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS - 1,
                    'endColumnIndex': self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS
                },
                'right': {
                    'style': 'SOLID_THICK',
                    'width': 3,
                    'color': self.BORDER_COLOR_THICK
                }
            }
        })
        
        # Между складами
        for i in range(len(warehouses) - 1):
            col_index = self.NUM_BASE_INFO_COLS + self.NUM_GENERAL_METRICS_COLS + (i * self.NUM_WAREHOUSE_COLS) + self.NUM_WAREHOUSE_COLS - 1
            border_requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': max(data_rows_count + 2, 2),
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1
                    },
                    'right': {
                        'style': 'SOLID_THICK',
                        'width': 3,
                        'color': self.BORDER_COLOR_THICK
                    }
                }
            })
        
        # Применяем все границы
        if border_requests:
            worksheet.spreadsheet.batch_update({'requests': border_requests})
        
        logger.debug(f"Borders applied for {len(warehouses)} warehouses")
    
    def _col_number_to_letter(self, n: int) -> str:
        """
        Конвертировать номер колонки в букву (1=A, 2=B, ...).
        
        Args:
            n: Column number (1-based)
            
        Returns:
            Column letter (A, B, ..., Z, AA, AB, ...)
        """
        result = ""
        while n > 0:
            n -= 1
            result = chr(n % 26 + ord('A')) + result
            n //= 26
        return result
    
    def sync_products_to_sheet(
        self,
        products: List[Product],
        db: Session
    ) -> Dict[str, Any]:
        """
        Synchronize products to Google Sheet with new horizontal layout.
        
        Args:
            products: List of Product instances to sync
            db: Database session
            
        Returns:
            Dict with sync statistics
        """
        logger.info(
            f"Syncing {len(products)} products to Google Sheet "
            f"for tenant {self.tenant.id}"
        )
        
        start_time = datetime.utcnow()
        
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet("Products")
            
            # Собираем уникальные физические склады
            all_warehouse_names = set()
            for product in products:
                warehouse_data = product.warehouse_data or {}
                warehouses = warehouse_data.get("warehouses", [])
                for wh in warehouses:
                    wh_name = wh.get("name", "")
                    # Исключаем служебные склады
                    if wh_name and wh_name not in self.SERVICE_WAREHOUSES:
                        all_warehouse_names.add(wh_name)
            
            # Сортируем для консистентности
            self._warehouse_names = sorted(list(all_warehouse_names))
            logger.info(f"Found {len(self._warehouse_names)} physical warehouses")
            
            # Подготовка данных
            header_row2 = self.HEADER_ROW2_BASE + self.HEADER_ROW2_GENERAL
            for _ in self._warehouse_names:
                header_row2.extend(self.HEADER_ROW2_WAREHOUSE)
            
            data_rows = []
            for product in products:
                # Парсинг данных о складах
                warehouse_data = product.warehouse_data or {}
                warehouses = warehouse_data.get("warehouses", [])
                
                # Строим словарь складских данных
                warehouse_stocks = {}
                warehouse_orders = {}
                for wh in warehouses:
                    wh_name = wh.get("name", "")
                    if wh_name and wh_name not in self.SERVICE_WAREHOUSES:
                        warehouse_stocks[wh_name] = wh.get("stock", 0)
                        warehouse_orders[wh_name] = wh.get("orders", 0)
                
                # Рассчитываем общую оборачиваемость в днях
                # Формула: Остатки / (Заказы / Период) = Остатки * Период / Заказы
                # Период по умолчанию 7 дней (стандартный период WB API)
                total_stock = product.total_stock or 0
                total_orders = product.total_orders or 0
                if total_orders > 0 and total_stock > 0:
                    total_turnover = round((total_stock * 7) / total_orders, 1)
                else:
                    total_turnover = 0
                
                # Базовые колонки
                row = [
                    product.brand_name or "",  # Бренд
                    product.product_name or "",  # Предмет
                    product.seller_article or "",  # Артикул продавца
                    product.wildberries_article or product.nm_id or "",  # Артикул товара (nmid)
                    product.in_way_to_client or 0,  # В пути до покупателя
                    product.in_way_from_client or 0,  # В пути конв. на склад WB
                    # product.total_orders or 0,  # Убрана метрика "Всего заказов на складах WB"
                    total_orders,  # Заказы (всего)
                    total_stock,  # Остатки (всего)
                    total_turnover if total_turnover > 0 else '-'  # Рассчитанная оборачиваемость (дни)
                ]
                
                # Данные по складам
                for wh_name in self._warehouse_names:
                    stocks = warehouse_stocks.get(wh_name, 0)
                    orders = warehouse_orders.get(wh_name, 0)
                    
                    # Оборачиваемость склада в днях
                    # Формула: Остатки / (Заказы / Период) = Остатки * Период / Заказы
                    # Период по умолчанию 7 дней (стандартный период WB API)
                    if orders > 0 and stocks > 0:
                        turnover = round((stocks * 7) / orders, 1)
                    else:
                        turnover = 0
                    
                    row.extend([
                        stocks,
                        orders,
                        turnover if turnover > 0 else '-'
                    ])
                
                data_rows.append(row)
            
            # Проверка и расширение листа
            total_rows = len(data_rows) + 2  # +2 для заголовков
            total_cols = len(header_row2)
            
            current_rows = worksheet.row_count
            current_cols = worksheet.col_count
            
            if total_rows > current_rows or total_cols > current_cols:
                new_rows = max(total_rows + 10, current_rows)
                new_cols = max(total_cols + 5, current_cols)
                logger.info(f"Expanding sheet to {new_rows}x{new_cols}")
                worksheet.resize(rows=new_rows, cols=new_cols)
            
            # Очищаем лист
            logger.debug("Clearing worksheet")
            worksheet.clear()
            
            # Записываем строку 2 (названия колонок)
            logger.debug("Writing header row 2")
            worksheet.update(values=[header_row2], range_name='A2')
            
            # Записываем данные
            if data_rows:
                end_col_letter = self._col_number_to_letter(total_cols)
                range_name = f"A3:{end_col_letter}{len(data_rows) + 2}"
                logger.debug(f"Writing {len(data_rows)} data rows to {range_name}")
                worksheet.update(values=data_rows, range_name=range_name)
            
            # Объединяем ячейки и записываем заголовки групп
            logger.debug("Merging group headers")
            self._merge_and_write_group_headers(worksheet, self._warehouse_names)
            
            # Применяем форматирование
            logger.debug("Applying formatting")
            self._apply_full_formatting(worksheet, total_cols, len(data_rows), self._warehouse_names)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                "success": True,
                "products_synced": len(products),
                "warehouses_count": len(self._warehouse_names),
                "duration_seconds": round(duration, 2),
                "sheet_url": spreadsheet.url
            }
            
            logger.info(
                f"Successfully synced {len(products)} products with "
                f"{len(self._warehouse_names)} warehouses to Google Sheet "
                f"in {duration:.2f}s"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to sync products to Google Sheet: {e}", exc_info=True)
            raise SheetsAPIError(f"Google Sheets sync failed: {e}")
    
    def get_sheet_info(self) -> Dict[str, Any]:
        """
        Get information about tenant's Google Sheet.
        
        Returns:
            Dict with sheet information
        """
        try:
            spreadsheet = self._get_spreadsheet()
            worksheet = spreadsheet.worksheet("Products")
            
            # Count data rows (excluding 2 header rows)
            all_values = worksheet.get_all_values()
            data_rows = len([row for row in all_values[2:] if any(cell.strip() for cell in row)])
            
            return {
                "sheet_id": spreadsheet.id,
                "sheet_url": spreadsheet.url,
                "title": spreadsheet.title,
                "worksheet_name": "Products",
                "row_count": worksheet.row_count,
                "col_count": worksheet.col_count,
                "data_rows": data_rows,
                "header_rows": 2,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get sheet info: {e}")
            raise SheetsAPIError(f"Failed to get sheet info: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Google Sheets.
        
        Returns:
            Dict with test results
        """
        try:
            logger.info(f"Testing Google Sheets connection for tenant {self.tenant.id}")
            
            # Test authentication
            client = self._get_client()
            
            # Test spreadsheet access
            spreadsheet = self._get_spreadsheet()
            
            # Test worksheet access
            worksheet = spreadsheet.worksheet("Products")
            
            result = {
                "success": True,
                "sheet_title": spreadsheet.title,
                "sheet_url": spreadsheet.url,
                "worksheet_title": worksheet.title,
                "row_count": worksheet.row_count,
                "col_count": worksheet.col_count
            }
            
            logger.info("✅ Google Sheets connection test successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Google Sheets connection test failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
