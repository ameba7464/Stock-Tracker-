"""
Проверка текущего форматирования колонки F в Google Sheets.
"""

import os
import sys
import gspread
from google.oauth2.service_account import Credentials

# Change to script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Загрузка конфигурации
from dotenv import load_dotenv
load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "./config/service-account.json")

def check_column_f_formatting():
    """Проверка форматирования колонки F через Google Sheets API"""
    
    # Подключение
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Открыть таблицу
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Stock Tracker")
    
    print(f"📊 Проверка форматирования Google Sheets")
    print(f"📄 Таблица: {spreadsheet.title}")
    print(f"📝 Лист: {worksheet.title}")
    print(f"🆔 Sheet ID: {worksheet.id}")
    print()
    
    # Получить форматирование через spreadsheet API
    spreadsheet_data = spreadsheet.fetch_sheet_metadata({
        'includeGridData': True,
        'ranges': [f'{worksheet.title}!F2:F10']  # Первые несколько строк колонки F
    })
    
    # Найти наш лист
    sheet_data = None
    for sheet in spreadsheet_data.get('sheets', []):
        if sheet['properties']['sheetId'] == worksheet.id:
            sheet_data = sheet
            break
    
    if not sheet_data:
        print("❌ Не удалось найти данные листа")
        return
    
    # Проверить форматирование
    grid_data = sheet_data.get('data', [])
    if not grid_data:
        print("⚠️  Нет данных форматирования (возможно, лист пустой)")
        return
    
    print("🔍 Форматирование колонки F (Название склада):\n")
    
    row_data = grid_data[0].get('rowData', [])
    for idx, row in enumerate(row_data[:5], start=2):  # Первые 5 строк данных
        cells = row.get('values', [])
        if cells:
            cell = cells[0]  # Первая (и единственная) ячейка в диапазоне F
            
            user_format = cell.get('userEnteredFormat', {})
            wrap_strategy = user_format.get('wrapStrategy', 'НЕ УКАЗАНО')
            vertical_align = user_format.get('verticalAlignment', 'НЕ УКАЗАНО')
            
            # Получить значение
            value = cell.get('formattedValue', '(пусто)')
            
            print(f"Строка {idx}:")
            print(f"  Значение: {value}")
            print(f"  wrapStrategy: {wrap_strategy}")
            print(f"  verticalAlignment: {vertical_align}")
            
            if wrap_strategy == "OVERFLOW_CELL":
                print(f"  ✅ Правильно! Текст не переносится")
            elif wrap_strategy == "WRAP":
                print(f"  ❌ Проблема! Текст переносится (увеличивает высоту строки)")
            elif wrap_strategy == "CLIP":
                print(f"  ⚠️  Текст обрезается")
            else:
                print(f"  ⚠️  Стратегия не установлена явно")
            
            print()
    
    # Проверить высоту строк
    print("\n📏 Высота строк:")
    dimension_properties = sheet_data.get('properties', {}).get('gridProperties', {})
    default_row_height = dimension_properties.get('defaultRowPixelSize', 'НЕ УКАЗАНО')
    print(f"  Стандартная высота: {default_row_height}px")
    
    # Проверить ширину колонок
    print("\n📐 Ширина колонок:")
    column_metadata = sheet_data.get('columnMetadata', [])
    if len(column_metadata) > 5:  # Колонка F (индекс 5)
        col_f_width = column_metadata[5].get('pixelSize', 'НЕ УКАЗАНО')
        print(f"  Колонка F: {col_f_width}px")

if __name__ == "__main__":
    try:
        check_column_f_formatting()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
