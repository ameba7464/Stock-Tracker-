"""
Проверка дат обновления данных в Google Sheets для ItsSport2/50g
"""
import sys
import gspread
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from google.oauth2.service_account import Credentials

def check_google_sheets_timestamps():
    """Проверка дат обновления в Google Sheets"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА ДАТ ОБНОВЛЕНИЯ В GOOGLE SHEETS")
    print("="*100)
    
    config = get_config()
    
    # Подключение к Google Sheets
    creds = Credentials.from_service_account_file(
        config.google_service_account_key_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.google_sheet_id)
    worksheet = sheet.worksheet(config.google_sheet_name)
    
    # Получаем все данные
    all_values = worksheet.get_all_values()
    
    if not all_values:
        print("Таблица пуста")
        return
    
    header = all_values[0]
    
    # Находим индексы нужных колонок
    try:
        idx_article = header.index('Артикул')
        idx_date = header.index('Дата обновления')  # Если такая колонка есть
    except ValueError:
        print("Не найдены нужные колонки")
        print(f"Заголовки: {header}")
        # Используем предполагаемые индексы
        idx_article = 0
        idx_date = len(header) - 1 if len(header) > 1 else None
    
    print(f"\nКолонка 'Артикул': индекс {idx_article}")
    if idx_date is not None:
        print(f"Колонка даты: индекс {idx_date}")
    
    # Находим строки с ItsSport2/50g
    target_article = 'ItsSport2/50g'
    
    print(f"\nПоиск данных для артикула: {target_article}")
    print("-" * 100)
    
    found_rows = []
    for i, row in enumerate(all_values[1:], start=2):  # Пропускаем заголовок
        if len(row) > idx_article and row[idx_article] == target_article:
            found_rows.append((i, row))
    
    if not found_rows:
        print(f"Артикул {target_article} не найден в таблице")
        return
    
    print(f"Найдено {len(found_rows)} строк с артикулом {target_article}")
    print(f"\nПоследние 5 строк:")
    print(f"{'Строка':<10} {'Артикул':<25} {'Последние колонки...'}")
    print("-" * 100)
    
    for row_num, row in found_rows[-5:]:
        article = row[idx_article] if len(row) > idx_article else ''
        # Показываем последние 3 колонки
        last_cols = row[-3:] if len(row) >= 3 else row
        last_cols_str = ' | '.join(last_cols)
        print(f"{row_num:<10} {article:<25} {last_cols_str}")
    
    # Проверяем склады для первой найденной строки
    print(f"\nДетали первой строки с {target_article} (строка {found_rows[0][0]}):")
    print("-" * 100)
    
    row = found_rows[0][1]
    
    # Показываем все склады (предполагаем, что они идут парами: название_склада, количество)
    print("Склады и остатки:")
    
    # Ищем колонки после артикула и барcodes
    for i in range(min(len(header), len(row))):
        col_name = header[i]
        col_value = row[i]
        
        if 'склад' in col_name.lower() or i > 2:  # Показываем склады и данные после первых колонок
            print(f"  [{i}] {col_name}: {col_value}")
    
    print("\n" + "="*100)
    print("ИТОГИ:")
    print("="*100)
    print("\n1. Проверить дату последнего обновления данных")
    print("2. Сравнить с данными из API")
    print("3. Возможно, данные о складе 'Самара (Новосемейкино)' устарели")
    print("="*100 + "\n")

if __name__ == '__main__':
    check_google_sheets_timestamps()
