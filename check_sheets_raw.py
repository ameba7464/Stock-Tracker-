"""
Простая проверка данных в Google Sheets
"""
import sys
import gspread
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from google.oauth2.service_account import Credentials

def check_sheets_raw():
    """Проверка сырых данных из Google Sheets"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА RAW ДАННЫХ ИЗ GOOGLE SHEETS")
    print("="*100)
    
    config = get_config()
    
    # Подключение к Google Sheets
    creds = Credentials.from_service_account_file(
        config.google_service_account_key_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.google_sheet_id)
    
    print(f"\nGoogle Sheet ID: {config.google_sheet_id}")
    print(f"Sheet Name: {config.google_sheet_name}")
    
    worksheet = sheet.worksheet(config.google_sheet_name)
    
    # Получаем все данные
    all_values = worksheet.get_all_values()
    
    print(f"\nВсего строк: {len(all_values)}")
    
    if not all_values:
        print("Таблица пуста")
        return
    
    # Показываем первые 3 строки
    print(f"\nПервые 3 строки:")
    print("-" * 100)
    
    for i, row in enumerate(all_values[:3], start=1):
        print(f"Строка {i}:")
        print(f"  Колонок: {len(row)}")
        print(f"  Данные: {row[:5]}...")  # Первые 5 колонок
    
    # Ищем строки с ItsSport
    print(f"\nПоиск строк с 'ItsSport':")
    print("-" * 100)
    
    found = 0
    for i, row in enumerate(all_values, start=1):
        # Ищем в первых 3 колонках
        if any('ItsSport' in str(cell) for cell in row[:3]):
            found += 1
            if found <= 3:  # Показываем первые 3 найденные строки
                print(f"\nСтрока {i}:")
                print(f"  Первые 5 значений: {row[:5]}")
                
                # Ищем склад Новосемейкино или Самара
                for j, cell in enumerate(row):
                    cell_str = str(cell)
                    if 'Новосемейкино' in cell_str or 'Самара' in cell_str:
                        print(f"  Колонка {j}: {cell}")
    
    if found == 0:
        print("Не найдено строк с 'ItsSport'")
    else:
        print(f"\nВсего найдено строк с 'ItsSport': {found}")
    
    print("\n" + "="*100)

if __name__ == '__main__':
    check_sheets_raw()
