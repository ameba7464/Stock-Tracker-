"""Сервис для работы с Google Sheets API."""
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os
import time
import asyncio
from functools import wraps

from app.utils.logger import logger
from app.config import settings

try:
    import gspread
    from gspread.http_client import BackOffHTTPClient
    from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound, GSpreadException
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google API libraries not installed. Install: pip install gspread google-auth")


def retry_on_api_error(max_retries: int = 3, backoff_factor: float = 1.5):
    """
    Decorator для повтора операций при сетевых ошибках/rate limit.
    
    Args:
        max_retries: Максимальное количество попыток
        backoff_factor: Множитель для exponential backoff
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                    
                except (APIError, Exception) as e:
                    last_exception = e
                    
                    # Проверяем, стоит ли повторять
                    should_retry = False
                    
                    if hasattr(e, 'response') and e.response:
                        status_code = e.response.status_code
                        # Retry для 429 (rate limit), 500-599 (server errors)
                        should_retry = status_code == 429 or 500 <= status_code < 600
                    elif "429" in str(e) or "quota" in str(e).lower():
                        # Retry для rate limit в тексте ошибки
                        should_retry = True
                    
                    if should_retry and attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"API error on attempt {attempt + 1}/{max_retries}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        break
            
            raise last_exception
        
        return wrapper
    return decorator


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
            
            # Создаем клиент gspread для Service Account с BackOffHTTPClient
            self.client = gspread.authorize(
                sa_credentials,
                http_client=BackOffHTTPClient
            )
            
            logger.info("Google Sheets service initialized successfully (Service Account with BackOffHTTPClient)")
            
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
            
            # Создаем OAuth клиент с BackOffHTTPClient
            self.oauth_client = gspread.authorize(
                oauth_creds,
                http_client=BackOffHTTPClient
            )
            
            logger.info("OAuth client initialized successfully with BackOffHTTPClient")
            
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
            
        except APIError as e:
            status_code = e.response.status_code if e.response else None
            
            if status_code == 403:
                logger.error("Permission denied: Check OAuth token and API access")
                logger.error("1. Run get_oauth_token.py\n"
                           "2. Check Google Sheets API enabled\n"
                           "3. Check Google Drive API enabled")
            elif status_code == 429:
                logger.error("Rate limit exceeded")
            elif status_code == 404:
                logger.error(f"Folder not found: {settings.google_drive_folder_id}")
            else:
                logger.error(f"Google Sheets API error: {status_code} - {e}")
            
            return None
        except SpreadsheetNotFound as e:
            logger.error(f"Spreadsheet not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating sheet: {e}", exc_info=True)
            return None
    
    # ===== BATCH UPDATE HELPER METHODS =====
    
    def _build_unmerge_request(self, sheet_id: int, total_cols: int) -> dict:
        """Построить request для размержирования ячеек строки 1"""
        return {
            'unmergeCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': total_cols
                }
            }
        }
    
    def _build_clear_request(self, sheet_id: int, rows: int, cols: int) -> dict:
        """Построить request для очистки содержимого"""
        return {
            'updateCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': rows,
                    'startColumnIndex': 0,
                    'endColumnIndex': cols
                },
                'fields': 'userEnteredValue,userEnteredFormat'
            }
        }
    
    def _build_merge_requests(self, sheet_id: int, num_warehouses: int) -> List[dict]:
        """
        Построить requests для объединения ячеек заголовков.
        Оптимизировано: используем минимальное количество requests.
        """
        requests = []
        
        # Основная информация (A1:D1)
        requests.append({
            'mergeCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 4
                },
                'mergeType': 'MERGE_ALL'
            }
        })
        
        # Общие метрики (E1:I1)
        requests.append({
            'mergeCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 4,
                    'endColumnIndex': 9
                },
                'mergeType': 'MERGE_ALL'
            }
        })
        
        # Склады (по 3 колонки каждый) - все в одном batch
        if num_warehouses > 0:
            merge_ranges = []
            for i in range(num_warehouses):
                start_col = 9 + (i * 3)
                end_col = start_col + 3
                merge_ranges.append({
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': start_col,
                    'endColumnIndex': end_col
                })
            
            # Один request для всех складов
            for merge_range in merge_ranges:
                requests.append({
                    'mergeCells': {
                        'range': merge_range,
                        'mergeType': 'MERGE_ALL'
                    }
                })
        
        logger.debug(f"Created {len(requests)} merge requests for {num_warehouses} warehouses")
        return requests
    
    def _build_data_update_request(
        self, 
        sheet_id: int, 
        header_row1: List[str],
        header_row2: List[str], 
        data_rows: List[List]
    ) -> dict:
        """
        Построить request для записи всех данных (заголовки + данные).
        
        Использует 'userEnteredValue' вместо 'values' для правильной типизации:
        - Числа (int, float) → numberValue - обрабатываются как числа для формул
        - Строки → stringValue - сохраняются как текст
        - Пустые значения → {} - пустая ячейка
        
        Это эквивалентно valueInputOption='USER_ENTERED' в v4 API.
        """
        all_rows = [header_row1, header_row2] + data_rows
        
        return {
            'updateCells': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': len(all_rows),
                    'startColumnIndex': 0,
                    'endColumnIndex': len(header_row2)
                },
                'rows': [
                    {
                        'values': [
                            {
                                'userEnteredValue': (
                                    {'numberValue': cell} if isinstance(cell, (int, float)) and cell != '-'
                                    else {'stringValue': str(cell)} if cell not in ('', '-', None)
                                    else {}
                                )
                            }
                            for cell in row
                        ]
                    }
                    for row in all_rows
                ],
                'fields': 'userEnteredValue'
            }
        }
    
    def _build_format_requests(
        self, 
        sheet_id: int, 
        data_rows_count: int, 
        total_cols: int
    ) -> List[dict]:
        """Построить requests для форматирования"""
        requests = []
        
        # Заголовки (строки 1-2): синий фон, белый текст, жирный, центр
        requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 2,
                    'startColumnIndex': 0,
                    'endColumnIndex': total_cols
                },
                'cell': {
                    'userEnteredFormat': {
                        'backgroundColor': {'red': 0.4, 'green': 0.49, 'blue': 0.92},
                        'textFormat': {
                            'bold': True,
                            'fontSize': 10,
                            'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}
                        },
                        'horizontalAlignment': 'CENTER',
                        'verticalAlignment': 'MIDDLE',
                        'wrapStrategy': 'WRAP'
                    }
                },
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)'
            }
        })
        
        # Данные: первые 4 колонки - слева
        if data_rows_count > 0:
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': 0,
                        'endColumnIndex': 4
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'horizontalAlignment': 'LEFT',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat(horizontalAlignment,verticalAlignment)'
                }
            })
            
            # Остальные колонки - по центру
            requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 2,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': 4,
                        'endColumnIndex': total_cols
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE'
                        }
                    },
                    'fields': 'userEnteredFormat(horizontalAlignment,verticalAlignment)'
                }
            })
        
        return requests
    
    def _build_border_requests(
        self, 
        sheet_id: int, 
        data_rows_count: int, 
        total_cols: int, 
        num_warehouses: int
    ) -> List[dict]:
        """Построить requests для границ"""
        requests = []
        
        # Обычные границы для всех ячеек
        if data_rows_count > 0:
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
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
        
        # Толстая граница после заголовков
        requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 1,
                    'endRowIndex': 2,
                    'startColumnIndex': 0,
                    'endColumnIndex': total_cols
                },
                'bottom': {'style': 'SOLID_THICK', 'width': 3, 'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}
            }
        })
        
        # Толстые вертикальные границы между секциями
        requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': data_rows_count + 2,
                    'startColumnIndex': 3,
                    'endColumnIndex': 4
                },
                'right': {'style': 'SOLID_THICK', 'width': 3, 'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}
            }
        })
        
        requests.append({
            'updateBorders': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': data_rows_count + 2,
                    'startColumnIndex': 8,
                    'endColumnIndex': 9
                },
                'right': {'style': 'SOLID_THICK', 'width': 3, 'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}
            }
        })
        
        # Между складами
        for i in range(num_warehouses - 1):
            col_index = 9 + (i * 3) + 2
            requests.append({
                'updateBorders': {
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 0,
                        'endRowIndex': data_rows_count + 2,
                        'startColumnIndex': col_index,
                        'endColumnIndex': col_index + 1
                    },
                    'right': {'style': 'SOLID_THICK', 'width': 3, 'color': {'red': 0.2, 'green': 0.2, 'blue': 0.2}}
                }
            })
        
        return requests
    
    def _build_dimension_requests(self, sheet_id: int, total_cols: int) -> List[dict]:
        """Построить requests для установки размеров колонок и строк"""
        requests = []
        
        # Высота строк заголовков
        requests.append({
            'updateDimensionProperties': {
                'range': {
                    'sheetId': sheet_id,
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
                    'sheetId': sheet_id,
                    'dimension': 'ROWS',
                    'startIndex': 1,
                    'endIndex': 2
                },
                'properties': {'pixelSize': 40},
                'fields': 'pixelSize'
            }
        })
        
        # Ширина колонок (первые 4)
        col_widths = [150, 200, 180, 150]
        for i, width in enumerate(col_widths):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': i,
                        'endIndex': i + 1
                    },
                    'properties': {'pixelSize': width},
                    'fields': 'pixelSize'
                }
            })
        
        # Метрики - 120px
        for i in range(4, 9):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': i,
                        'endIndex': i + 1
                    },
                    'properties': {'pixelSize': 120},
                    'fields': 'pixelSize'
                }
            })
        
        # Колонки складов - 90px
        for i in range(9, total_cols):
            requests.append({
                'updateDimensionProperties': {
                    'range': {
                        'sheetId': sheet_id,
                        'dimension': 'COLUMNS',
                        'startIndex': i,
                        'endIndex': i + 1
                    },
                    'properties': {'pixelSize': 90},
                    'fields': 'pixelSize'
                }
            })
        
        return requests
    
    # ===== END BATCH UPDATE HELPER METHODS =====
    
    async def update_sheet(
        self,
        sheet_id: str,
        data: List[Any]
    ) -> bool:
        """
        Обновление существующей таблицы - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ с batch_update.
        ВСЕ операции выполняются в ОДНОМ API вызове.
        
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
            import time
            start_time = time.time()
            
            # Открываем таблицу
            spreadsheet = self.client.open_by_key(sheet_id)
            
            # Проверяем права доступа перед операциями
            await self._check_spreadsheet_permissions(spreadsheet)
            
            worksheet = spreadsheet.sheet1
            
            if worksheet.title != "Stock Tracker":
                worksheet.update_title("Stock Tracker")
            
            # Подготовка данных (без API вызовов)
            table_data, warehouse_names = self._prepare_table_data(data)
            
            if not table_data or len(table_data) < 2:
                logger.warning("No data to write")
                return False
            
            header_row1 = table_data[0]
            header_row2 = table_data[1]
            data_rows = table_data[2:]
            
            num_rows_needed = len(table_data)
            num_cols_needed = len(table_data[0])
            num_warehouses = len(warehouse_names)
            
            logger.info(f"Preparing batch update: {len(data_rows)} data rows, {num_warehouses} warehouses")
            
            # Расширяем лист если нужно (отдельный вызов, но обязательный)
            current_rows = worksheet.row_count
            current_cols = worksheet.col_count
            
            if current_cols < num_cols_needed or current_rows < num_rows_needed:
                new_cols = max(current_cols, num_cols_needed)
                new_rows = max(current_rows, num_rows_needed + 10)
                worksheet.resize(rows=new_rows, cols=new_cols)
                logger.info(f"Resized sheet to {new_rows}x{new_cols}")
            
            # === ЕДИНСТВЕННЫЙ BATCH_UPDATE ДЛЯ ВСЕХ ОПЕРАЦИЙ ===
            all_requests = []
            
            # 1. Размержирование существующих ячеек строки 1
            all_requests.append(self._build_unmerge_request(worksheet.id, num_cols_needed))
            
            # 2. Очистка (не используем worksheet.clear())
            all_requests.append(self._build_clear_request(
                worksheet.id, 
                current_rows, 
                current_cols
            ))
            
            # 3. Запись данных (заголовки + данные)
            all_requests.append(self._build_data_update_request(
                worksheet.id,
                header_row1,
                header_row2,
                data_rows
            ))
            
            # 4. Объединение ячеек заголовков
            all_requests.extend(self._build_merge_requests(worksheet.id, num_warehouses))
            
            # 5. Форматирование
            all_requests.extend(self._build_format_requests(
                worksheet.id,
                len(data_rows),
                num_cols_needed
            ))
            
            # 6. Границы
            all_requests.extend(self._build_border_requests(
                worksheet.id,
                len(data_rows),
                num_cols_needed,
                num_warehouses
            ))
            
            # 7. Размеры колонок и строк
            all_requests.extend(self._build_dimension_requests(worksheet.id, num_cols_needed))
            
            # ВЫПОЛНЯЕМ ВСЕ ОПЕРАЦИИ ОДНИМ ЗАПРОСОМ
            prep_time = time.time() - start_time
            logger.info(f"Executing batch update with {len(all_requests)} requests...")
            
            batch_start = time.time()
            
            # Применяем retry для критичной операции
            @retry_on_api_error(max_retries=3)
            async def execute_batch():
                return spreadsheet.batch_update({'requests': all_requests})
            
            batch_response = await execute_batch()
            batch_time = time.time() - batch_start
            
            # 8. Замораживание заголовков (отдельный метод, но быстрый)
            freeze_start = time.time()
            worksheet.freeze(rows=2, cols=0)
            freeze_time = time.time() - freeze_start
            
            elapsed = time.time() - start_time
            
            logger.info(
                f"✅ Updated in {elapsed:.2f}s | "
                f"Prep: {prep_time:.2f}s | "
                f"Batch: {batch_time:.2f}s | "
                f"Freeze: {freeze_time:.2f}s | "
                f"API calls: 3 (open/batch/freeze) | "
                f"Requests in batch: {len(all_requests)}"
            )
            
            return True
            
        except SpreadsheetNotFound:
            logger.error(f"Spreadsheet {sheet_id} not found")
            return False
        except WorksheetNotFound:
            logger.warning("Worksheet 'Stock Tracker' not found")
            return False
        except APIError as e:
            status_code = e.response.status_code if e.response else None
            
            if status_code == 403:
                logger.error("Permission denied - Service Account needs access")
            elif status_code == 429:
                logger.error("Rate limit exceeded despite BackOffHTTPClient")
            elif status_code and status_code >= 500:
                logger.error(f"Google Sheets server error: {status_code}")
            else:
                logger.error(f"API error: {status_code} - {e}")
            
            return False
        except Exception as e:
            logger.error(f"Error updating sheet: {e}", exc_info=True)
            return False
    
    async def _check_spreadsheet_permissions(self, spreadsheet: gspread.Spreadsheet) -> bool:
        """
        Проверить права доступа к таблице (writer/owner).
        
        Args:
            spreadsheet: Spreadsheet для проверки
            
        Returns:
            True если есть права на запись
            
        Raises:
            Exception: Нет прав на запись
        """
        try:
            # Пытаемся получить метаданные
            _ = spreadsheet.id
            _ = spreadsheet.title
            
            # Проверяем права на запись
            try:
                permissions = spreadsheet.list_permissions()
                
                # Получаем email текущего аккаунта
                if hasattr(self.client, 'auth'):
                    current_email = getattr(self.client.auth, 'service_account_email', None)
                    
                    if current_email:
                        has_write_access = False
                        for perm in permissions:
                            if perm.get('emailAddress') == current_email:
                                role = perm.get('role', '')
                                if role in ('writer', 'owner'):
                                    has_write_access = True
                                    break
                        
                        if not has_write_access:
                            raise Exception(
                                f"Account {current_email} не имеет прав writer/owner на таблицу"
                            )
                        
                        logger.debug(f"Permissions OK: {current_email} has {role} access")
                        return True
                
                # Если не удалось получить email, считаем OK
                logger.warning("Could not verify permissions - proceeding")
                return True
                
            except AttributeError:
                # list_permissions не доступен
                logger.warning("list_permissions not available, skipping permission check")
                return True
                
        except APIError as e:
            if e.response.status_code == 403:
                raise Exception(
                    f"Нет доступа к таблице. "
                    f"Проверьте права доступа."
                )
            raise
    
    def _prepare_table_data(self, products: List[Any]) -> tuple:
        """
        Подготовка данных для таблицы.
        
        Args:
            products: Список ProductMetrics
            
        Returns:
            Tuple (данные для таблицы, список складов)
        """
        if not products:
            logger.warning("No products to prepare for table")
            return ([["Нет данных"]], [])
        
        logger.info(f"Preparing table data for {len(products)} products")
        
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
        
        logger.info(f"Found {len(all_warehouses)} unique warehouses: {list(all_warehouses)[:5]}...")  # Показываем первые 5
        
        # Строка 1: Группы колонок с названиями складов (КАК И ДОЛЖНО БЫТЬ!)
        header_row1 = ['Основная информация', '', '', '']  # A1:D1 (4 колонки)
        header_row1.extend(['Общие метрики', '', '', '', ''])     # E1:I1 (5 колонок)
        
        # Добавляем НАЗВАНИЯ СКЛАДОВ в первую строку
        for warehouse in all_warehouses:
            header_row1.extend([warehouse, '', ''])  # J1, M1, P1... (3 колонки каждый)
        
        # DEBUG: Логируем первую строку
        logger.info(f"Header row 1 (first 15 cells): {header_row1[:15]}")
        logger.info(f"Header row 1 total length: {len(header_row1)}")
        
        # Строка 2: Подзаголовки колонок
        header_row2 = [
            'Бренд',
            'Предмет', 
            'Артикул продавца',
            'Артикул товара (nmid)',
            'В пути до покупателя',
            'В пути конв. на склад WB',
            'Заказы (всего)',
            'Остатки (всего)',
            'Оборачиваемость (дни)'
        ]
        
        # Добавляем подзаголовки для складов
        for _ in all_warehouses:
            header_row2.extend(['Остатки', 'Заказы', 'Оборач.'])
            
        # DEBUG: Логируем вторую строку
        logger.info(f"Header row 2 (subheaders, first 15 cells): {header_row2[:15]}")
        logger.info(f"Header row 2 total length: {len(header_row2)}")
        
        # Данные
        rows = [header_row1, header_row2]
        
        for i, product in enumerate(products):
            # Рассчитываем общую оборачиваемость в днях
            # Формула: Остатки / (Заказы / Период) = Остатки * Период / Заказы
            # Период по умолчанию 7 дней (стандартный период WB API)
            if product.orders_total > 0 and product.stocks_total > 0:
                total_turnover = round((product.stocks_total * 7) / product.orders_total, 1)
            else:
                total_turnover = 0
            
            # Отладочная информация для первых товаров
            if i < 3:
                logger.debug(f"Product {product.nm_id}: in_transit_to_customer={product.in_transit_to_customer}, in_transit_to_wb={product.in_transit_to_wb_warehouse}, stocks_by_warehouse keys={list(product.stocks_by_warehouse.keys())[:3]}")
            
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
            num_warehouses = len(warehouse_names) if warehouse_names else 0
            
            # Сначала разъединяем все ячейки в первой строке, чтобы избежать ошибок
            # Вычисляем общее количество колонок: 4 (базовые) + 5 (метрики) + 3*склады
            total_cols = 9 + (num_warehouses * 3)
            
            unmerge_requests = [{
                'unmergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': total_cols
                    }
                }
            }]
            
            try:
                spreadsheet.batch_update({'requests': unmerge_requests})
                logger.debug("Unmerged all cells in header row")
            except Exception as e:
                logger.debug(f"Unmerge skipped (probably no merged cells): {e}")
            
            # Теперь объединяем ячейки
            merge_requests = []
            
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
            
            # Общие метрики (E1:I1) - ПРАВИЛЬНО: 5 колонок с 4 по 8 (E,F,G,H,I)
            merge_requests.append({
                'mergeCells': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 4,  # E = 4
                        'endColumnIndex': 9     # I = 8, но endColumnIndex НЕ ВКЛЮЧАЕТСЯ, так что 9
                    },
                    'mergeType': 'MERGE_ALL'
                }
            })
            
            # Склады (каждый склад = 3 колонки, начиная с колонки J = индекс 9)
            for i in range(num_warehouses):
                start_col = 9 + (i * 3)  # J=9, M=12, P=15, etc.
                end_col = start_col + 3   # L=12, O=15, S=18, etc.
                
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
                try:
                    spreadsheet.batch_update({'requests': merge_requests})
                    logger.info(f"Merged cells for {num_warehouses} warehouses")
                except Exception as merge_error:
                    logger.warning(f"Merge failed (continuing anyway): {merge_error}")
            
            # Перезаписываем текст в ячейки ПОСЛЕ merge (merge очищает содержимое)
            try:
                # Записываем группы заголовков  
                worksheet.update('A1', [['Основная информация']])
                worksheet.update('E1', [['Общие метрики']])
                
                # Записываем НАЗВАНИЯ СКЛАДОВ в первую строку (как и должно быть!)
                for i, wh_name in enumerate(warehouse_names):
                    col_num = 10 + (i * 3)  # J=10, M=13, P=16, ...
                    col_letter = self._col_number_to_letter(col_num)
                    worksheet.update(f'{col_letter}1', [[wh_name]])
                    if i < 3:  # Логируем первые 3
                        logger.info(f"Writing warehouse header: {wh_name} at {col_letter}1")
                
                logger.info(f"Wrote warehouse names in ROW 1 for {num_warehouses} warehouses")
                
            except Exception as header_error:
                logger.warning(f"Failed to write headers after merge: {header_error}")
            
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
    
    async def _write_warehouse_headers_only(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, warehouse_names: List[str]):
        """НЕ ИСПОЛЬЗУЕТСЯ - склады теперь во второй строке"""
        pass
    
    async def _format_sheet_no_merge(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, warehouse_names: List[str] = None):
        """Форматирование БЕЗ merge cells"""
        try:
            # Получаем данные для определения количества строк и колонок
            all_data = worksheet.get_all_values()
            data_rows_count = len(all_data) - 2 if len(all_data) > 2 else 0
            total_cols = len(all_data[0]) if all_data else 9
            
            num_warehouses = len(warehouse_names) if warehouse_names else 0
            
            # 1. НЕ объединяем ячейки - просто цвета и границы
            
            # 2. Форматируем заголовки
            await self._format_headers_no_merge(spreadsheet, worksheet, total_cols, num_warehouses)
            
            # 3. Применяем границы
            await self._apply_borders(spreadsheet, worksheet, total_cols, data_rows_count, num_warehouses)
            
            logger.info(f"Sheet formatted successfully (warehouses: {num_warehouses}, rows: {data_rows_count}) WITHOUT MERGE")
            
        except Exception as e:
            logger.error(f"Error formatting sheet: {e}", exc_info=True)
    
    async def _format_headers_no_merge(self, spreadsheet: gspread.Spreadsheet, worksheet: gspread.Worksheet, total_cols: int, num_warehouses: int):
        """Форматирование заголовков без merge"""
        try:
            format_requests = []
            
            # Заголовки строк 1-2: жирный, выровненный по центру
            format_requests.append({
                'repeatCell': {
                    'range': {
                        'sheetId': worksheet.id,
                        'startRowIndex': 0,
                        'endRowIndex': 2,
                        'startColumnIndex': 0,
                        'endColumnIndex': total_cols
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'textFormat': {'bold': True},
                            'horizontalAlignment': 'CENTER',
                            'verticalAlignment': 'MIDDLE',
                            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                        }
                    },
                    'fields': 'userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,backgroundColor)'
                }
            })
            
            # Применяем форматирование
            if format_requests:
                spreadsheet.batch_update({'requests': format_requests})
            
        except Exception as e:
            logger.warning(f"Failed to format headers: {e}")


# Глобальный экземпляр сервиса
google_sheets_service = GoogleSheetsService()
