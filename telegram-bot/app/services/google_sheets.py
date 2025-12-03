"""Сервис для работы с Google Sheets API."""
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os

from app.utils.logger import logger
from app.config import settings

try:
    import gspread
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google API libraries not installed. Install: pip install gspread google-auth")


class GoogleSheetsService:
    """Сервис для работы с Google Sheets API."""
    
    # Scopes для Service Account (полный доступ к Drive)
    SA_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    # Scopes для OAuth (ограниченный доступ - только созданные файлы)
    OAUTH_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file'
    ]
    
    def __init__(self):
        """Инициализация сервиса."""
        self.client = None
        self.oauth_client = None  # Клиент для создания файлов через OAuth
        self._initialize()
    
    def _initialize(self):
        """Инициализация Google API клиента."""
        if not GOOGLE_AVAILABLE:
            logger.error("Google API libraries not available")
            return
        
        try:
            # 1. Инициализация Service Account (для обновления таблиц)
            credentials_path = self._find_credentials_file()
            
            if not credentials_path:
                logger.warning("Google Service Account credentials not found. Please add credentials.json")
                return
            
            # Создаем Service Account credentials
            sa_credentials = ServiceAccountCredentials.from_service_account_file(
                credentials_path,
                scopes=self.SA_SCOPES
            )
            
            # Создаем клиент gspread для Service Account
            self.client = gspread.authorize(sa_credentials)
            
            logger.info("Google Sheets service initialized successfully (Service Account)")
            
            # 2. Инициализация OAuth (для создания файлов)
            self._initialize_oauth_client()
            
        except Exception as e:
            logger.error(f"Error initializing Google Sheets service: {e}")
    
    def _initialize_oauth_client(self):
        """Инициализация OAuth клиента для создания файлов."""
        try:
            token_path = Path(__file__).parent.parent.parent / "token.json"
            
            if not token_path.exists():
                logger.warning("OAuth token not found. Run get_oauth_token.py to authorize")
                return
            
            # Загружаем OAuth credentials (используем OAUTH_SCOPES)
            oauth_creds = OAuthCredentials.from_authorized_user_file(
                str(token_path),
                scopes=self.OAUTH_SCOPES
            )
            
            # Обновляем токен если истёк
            if oauth_creds and oauth_creds.expired and oauth_creds.refresh_token:
                logger.info("Refreshing OAuth token...")
                oauth_creds.refresh(Request())
                
                # Сохраняем обновлённый токен
                with open(token_path, 'w') as token:
                    token.write(oauth_creds.to_json())
                logger.info("OAuth token refreshed and saved")
            
            # Создаем OAuth клиент
            self.oauth_client = gspread.authorize(oauth_creds)
            
            logger.info("OAuth client initialized successfully")
            
        except Exception as e:
            logger.warning(f"Could not initialize OAuth client: {e}")
            logger.warning("Tables will not be created. Run get_oauth_token.py to authorize")
    
    def _find_credentials_file(self) -> Optional[str]:
        """
        Поиск файла с credentials.
        
        Returns:
            Путь к файлу или None
        """
        # Возможные расположения файла
        possible_paths = [
            Path(__file__).parent.parent.parent / "credentials.json",
            Path(__file__).parent.parent.parent / "config" / "credentials.json",
            Path(__file__).parent.parent.parent / ".credentials" / "credentials.json",
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found credentials file: {path}")
                return str(path)
        
        return None
    
    async def create_sheet(
        self,
        user_name: str,
        telegram_id: int,
        data: List[Any]
    ) -> Optional[str]:
        """
        Создание новой Google Таблицы для пользователя.
        
        Args:
            user_name: Имя пользователя
            telegram_id: Telegram ID пользователя
            data: Данные для заполнения (список ProductMetrics)
            
        Returns:
            ID созданной таблицы или None
        """
        # Используем OAuth если есть, иначе Service Account
        client_to_use = self.oauth_client or self.client
        
        if not client_to_use:
            logger.error("No Google client available. Cannot create sheets.")
            return None
        
        try:
            # Создаем таблицу
            title = f'Stock Tracker - {user_name}'
            
            # Если указана папка, создаём в ней
            if settings.google_drive_folder_id:
                logger.info(f"Creating sheet in folder: {settings.google_drive_folder_id}")
                spreadsheet = client_to_use.create(title, folder_id=settings.google_drive_folder_id)
            else:
                spreadsheet = client_to_use.create(title)
            
            sheet_id = spreadsheet.id
            logger.info(f"Created new sheet: {sheet_id}")
            
            # Переименовываем первый лист в "Stock Tracker"
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Stock Tracker")
            logger.info("Renamed sheet to 'Stock Tracker'")
            
            # Если создали через OAuth, даем доступ Service Account для обновлений
            if self.oauth_client and client_to_use == self.oauth_client:
                try:
                    spreadsheet.share(
                        'stocktr@stocktr-479319.iam.gserviceaccount.com',
                        perm_type='user',
                        role='writer',
                        notify=False
                    )
                    logger.info("Shared sheet with Service Account")
                except Exception as e:
                    logger.warning(f"Could not share with Service Account: {e}")
            
            # Даем доступ всем по ссылке
            spreadsheet.share('', perm_type='anyone', role='writer')
            logger.info(f"Permissions set for sheet {sheet_id}")
            
            # Заполняем данными (через Service Account или OAuth)
            await self.update_sheet(sheet_id, data)
            
            return sheet_id
            
        except gspread.exceptions.APIError as e:
            logger.error(f"API error creating sheet: {e}")
            logger.error("\n⚠️ ВОЗМОЖНЫЕ ПРИЧИНЫ:\n"
                        "1. OAuth токен истёк - запустите get_oauth_token.py\n"
                        "2. Google Sheets API не включен\n"
                        "3. Google Drive API не включен\n"
                        "4. Нет прав на создание файлов\n"
                        "\nПроверьте: https://console.cloud.google.com/apis/dashboard")
            return None
        except Exception as e:
            logger.error(f"Error creating sheet: {e}", exc_info=True)
            return None
    
    async def update_sheet(
        self,
        sheet_id: str,
        data: List[Any]
    ) -> bool:
        """
        Обновление существующей таблицы.
        
        Args:
            sheet_id: ID таблицы
            data: Данные для обновления (список ProductMetrics)
            
        Returns:
            True если успешно
        """
        if not self.client:
            logger.error("Google Sheets service not initialized")
            return False
        
        try:
            # Открываем таблицу
            spreadsheet = self.client.open_by_key(sheet_id)
            
            # Переименовываем первый лист в "Stock Tracker" если нужно
            worksheet = spreadsheet.sheet1
            if worksheet.title != "Stock Tracker":
                worksheet.update_title("Stock Tracker")
            
            # Преобразуем данные в формат для таблицы
            table_data, warehouse_names = self._prepare_table_data(data)
            
            # Очищаем и записываем новые данные
            worksheet.clear()
            worksheet.update('A1', table_data, value_input_option='USER_ENTERED')
            
            # Форматируем таблицу
            await self._format_sheet(spreadsheet, worksheet, warehouse_names)
            
            logger.info(f"Sheet {sheet_id} updated successfully")
            return True
            
        except gspread.exceptions.APIError as e:
            logger.error(f"API error updating sheet: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating sheet: {e}", exc_info=True)
            return False
    
    def _prepare_table_data(self, products: List[Any]) -> tuple:
        """
        Подготовка данных для таблицы.
        
        Args:
            products: Список ProductMetrics
            
        Returns:
            Tuple (данные для таблицы, список складов)
        """
        if not products:
            return ([["Нет данных"]], [])
        
        # Получаем все уникальные склады
        all_warehouses = set()
        service_warehouses = {
            'В пути до получателей',
            'В пути возвраты на склад WB',
            'Всего находится на складах',
            'Остальные'
        }
        
        for product in products:
            for wh in product.stocks_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
            for wh in product.orders_by_warehouse.keys():
                if wh not in service_warehouses:
                    all_warehouses.add(wh)
        
        all_warehouses = sorted(all_warehouses)
        
        # Строка 1: Группы колонок (записываем текст сразу, чтобы он был виден даже без merge)
        header_row1 = ['Основная информация', '', '', '']  # Основная информация
        header_row1.extend(['Общие метрики', '', '', '', ''])     # Общие метрики (5 колонок)
        
        for warehouse in all_warehouses:
            header_row1.extend([warehouse, '', ''])
        
        # Строка 2: Названия колонок
        header_row2 = [
            'Бренд',
            'Предмет',
            'Артикул продавца',
            'Артикул товара (nmid)',
            'В пути до покупателя',
            'В пути конв. на склад WB',
            # 'Всего заказов на складах WB',  # Убрана метрика
            'Заказы (всего)',
            'Остатки (всего)',
            'Оборачиваемость (дни)'
        ]
        
        for _ in all_warehouses:
            header_row2.extend(['Остатки', 'Заказы', 'Оборач.'])
        
        # Данные
        rows = [header_row1, header_row2]
        
        for product in products:
            # Рассчитываем общую оборачиваемость в днях
            # Формула: Остатки / (Заказы / Период) = Остатки * Период / Заказы
            # Период по умолчанию 7 дней (стандартный период WB API)
            if product.orders_total > 0 and product.stocks_total > 0:
                total_turnover = round((product.stocks_total * 7) / product.orders_total, 1)
            else:
                total_turnover = 0
            
            row = [
                product.brand,
                product.subject,
                product.vendor_code,
                product.nm_id,
                product.in_transit_to_customer,
                product.in_transit_to_wb_warehouse,
                # product.orders_wb_warehouses,  # Убрана метрика
                product.orders_total,
                product.stocks_total,
                total_turnover if total_turnover > 0 else ''  # Рассчитанная оборачиваемость
            ]
            
            # Добавляем данные по складам
            for warehouse in all_warehouses:
                stocks = product.stocks_by_warehouse.get(warehouse, 0)
                orders = product.orders_by_warehouse.get(warehouse, 0)
                
                # Рассчитываем оборачиваемость в днях
                # Формула: Остатки / (Заказы / Период) = Остатки * Период / Заказы
                # Период по умолчанию 7 дней (стандартный период WB API)
                if orders > 0 and stocks > 0:
                    turnover = round((stocks * 7) / orders, 1)
                else:
                    turnover = 0
                
                row.extend([stocks, orders, turnover if turnover > 0 else ''])
            
            rows.append(row)
        
        return (rows, list(all_warehouses))
    
    async def _format_sheet(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, warehouse_names: List[str] = None):
        """
        Форматирование таблицы (заголовки, цвета, границы, объединение ячеек).
        
        Args:
            spreadsheet: Объект таблицы
            worksheet: Объект листа
            warehouse_names: Список названий складов
        """
        try:
            # Получаем данные для определения количества строк и колонок
            all_data = worksheet.get_all_values()
            data_rows_count = len(all_data) - 2 if len(all_data) > 2 else 0
            total_cols = len(all_data[0]) if all_data else 9
            
            # Используем переданный список складов или вычисляем из данных
            if warehouse_names is None:
                warehouse_names = []
            num_warehouses = len(warehouse_names)
            
            # 1. Объединяем ячейки заголовков групп
            await self._merge_group_headers(spreadsheet, worksheet, warehouse_names)
            
            # 2. Устанавливаем размеры колонок и строк
            await self._apply_dimension_properties(spreadsheet, worksheet, total_cols)
            
            # 3. Форматируем заголовки (синий фон, белый текст)
            worksheet.format('A1:ZZ2', {
                'backgroundColor': {
                    'red': 0.4,
                    'green': 0.49,
                    'blue': 0.92
                },
                'textFormat': {
                    'bold': True,
                    'fontSize': 10,
                    'foregroundColor': {
                        'red': 1.0,
                        'green': 1.0,
                        'blue': 1.0
                    }
                },
                'horizontalAlignment': 'CENTER',
                'verticalAlignment': 'MIDDLE',
                'wrapStrategy': 'WRAP'
            })
            
            # 4. Форматируем данные
            if data_rows_count > 0:
                # Первые 4 колонки - выравнивание слева
                worksheet.format(f'A3:D{data_rows_count + 2}', {
                    'horizontalAlignment': 'LEFT',
                    'verticalAlignment': 'MIDDLE'
                })
                
                # Остальные колонки - по центру
                worksheet.format(f'E3:ZZ{data_rows_count + 2}', {
                    'horizontalAlignment': 'CENTER',
                    'verticalAlignment': 'MIDDLE'
                })
            
            # 5. Добавляем границы
            await self._apply_borders(spreadsheet, worksheet, total_cols, data_rows_count, num_warehouses)
            
            # 6. Замораживаем заголовки
            worksheet.freeze(rows=2, cols=0)
            
            logger.info(f"Sheet formatted successfully (warehouses: {num_warehouses}, rows: {data_rows_count})")
            
        except Exception as e:
            logger.error(f"Error formatting sheet: {e}", exc_info=True)
    
    async def _merge_group_headers(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, warehouse_names: List[str]):
        """
        Объединить ячейки для заголовков групп.
        
        Args:
            spreadsheet: Объект таблицы
            worksheet: Объект листа
            warehouse_names: Список названий складов
        """
        try:
            merge_requests = []
            num_warehouses = len(warehouse_names) if warehouse_names else 0
            
            # Основная информация (A1:D1)
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': 4
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
            
            # Общие метрики (E1:I1) - 5 колонок после удаления "Всего заказов на складах WB"
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 4,
                        'endColumnIndex': 9
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
            
            # Склады (каждый склад = 3 колонки, начиная с колонки J = индекс 9)
            for i in range(num_warehouses):
                start_col = 9 + (i * 3)
                end_col = start_col + 3
                
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
            if merge_requests:
                spreadsheet.batch_update({'requests': merge_requests})
            
            # Перезаписываем текст в объединенные ячейки ПОСЛЕ merge 
            # (merge очищает содержимое ячеек)
            # Собираем все обновления в один batch для эффективности
            batch_updates = [
                {'range': 'A1', 'values': [['Основная информация']]},
                {'range': 'E1', 'values': [['Общие метрики']]}
            ]
            
            # Добавляем названия складов
            for i, wh_name in enumerate(warehouse_names):
                col_letter = self._col_number_to_letter(10 + (i * 3))  # J=10, M=13, P=16, ...
                batch_updates.append({'range': f'{col_letter}1', 'values': [[wh_name]]})
                logger.debug(f"Adding warehouse header: {wh_name} at {col_letter}1")
            
            # Применяем все обновления одним запросом
            worksheet.batch_update(batch_updates)
            
            logger.info(f"Merged cells and wrote headers for {num_warehouses} warehouses: {warehouse_names}")
            
        except Exception as e:
            logger.warning(f"Failed to merge cells: {e}")
    
    async def _apply_dimension_properties(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, total_cols: int):
        """
        Установить размеры колонок и строк.
        
        Args:
            spreadsheet: Объект таблицы
            worksheet: Объект листа
            total_cols: Общее количество колонок
        """
        try:
            requests = []
            
            # Основные колонки (A-D)
            column_widths = [150, 200, 180, 150]
            for i, width in enumerate(column_widths):
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': i,
                            'endIndex': i + 1
                        },
                        'properties': {'pixelSize': width},
                        'fields': 'pixelSize'
                    }
                })
            
            # Общие метрики (E-I) - 120px (5 колонок после удаления "Всего заказов на складах WB")
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': worksheet.id,
                        'dimension': 'COLUMNS',
                        'startIndex': 4,
                        'endIndex': 9
                    },
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            })
            
            # Колонки складов - 90px
            if total_cols > 9:
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': 9,
                            'endIndex': total_cols
                        },
                        'properties': {'pixelSize': 90},
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
                    'properties': {'pixelSize': 35},
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
                    'properties': {'pixelSize': 40},
                    'fields': 'pixelSize'
                }
            })
            
            # Применяем все изменения
            if requests:
                spreadsheet.batch_update({'requests': requests})
            
            logger.debug("Dimension properties applied")
            
        except Exception as e:
            logger.warning(f"Failed to apply dimension properties: {e}")
    
    async def _apply_borders(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, total_cols: int, data_rows_count: int, num_warehouses: int):
        """
        Применить границы к таблице.
        
        Args:
            spreadsheet: Объект таблицы
            worksheet: Объект листа
            total_cols: Общее количество колонок
            data_rows_count: Количество строк с данными
            num_warehouses: Количество складов
        """
        try:
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
                        'top': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                        'bottom': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                        'left': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                        'right': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                        'innerHorizontal': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}},
                        'innerVertical': {'style': 'SOLID', 'width': 1, 'color': {'red': 0.8, 'green': 0.8, 'blue': 0.8}}
                    }
                })
            
            # 2. Толстая горизонтальная граница после заголовков
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
                        'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}
                    }
                }
            })
            
            # 3. Толстые вертикальные границы для разделения секций
            # После "Основной информации" (колонка D)
            border_requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': 3,
                        'endColumnIndex': 4
                    },
                    'right': {
                        'style': 'SOLID_THICK',
                        'width': 3,
                        'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}
                    }
                }
            })
            
            # После "Общих метрик" (колонка I)
            border_requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': 8,
                        'endColumnIndex': 9
                    },
                    'right': {
                        'style': 'SOLID_THICK',
                        'width': 3,
                        'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}
                    }
                }
            })
            
            # Между складами
            for i in range(num_warehouses - 1):
                col_index = 9 + (i * 3) + 2
                border_requests.append({
                    'updateBorders': {
                        'range': {
                            'sheetId': worksheet.id,
                            'startRowIndex': 0,
                            'endRowIndex': data_rows_count + 2,
                            'startColumnIndex': col_index,
                            'endColumnIndex': col_index + 1
                        },
                        'right': {
                            'style': 'SOLID_THICK',
                            'width': 3,
                            'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}
                        }
                    }
                })
            
            # Применяем границы
            if border_requests:
                spreadsheet.batch_update({'requests': border_requests})
            
            logger.debug("Borders applied")
            
        except Exception as e:
            logger.warning(f"Failed to apply borders: {e}")
    
    def _col_number_to_letter(self, n: int) -> str:
        """
        Конвертировать номер колонки в букву (1=A, 2=B, ..., 10=J, ...).
        
        Args:
            n: Номер колонки (1-based)
            
        Returns:
            Буква колонки (A, B, ..., Z, AA, AB, ...)
        """
        result = ""
        while n > 0:
            n -= 1
            result = chr(n % 26 + ord('A')) + result
            n //= 26
        return result


# Глобальный экземпляр сервиса
google_sheets_service = GoogleSheetsService()
