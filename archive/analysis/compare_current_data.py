"""
Сравнение ТЕКУЩИХ данных из Google Sheets с WB CSV от 30.10.2025
"""
import sys
import csv
import gspread
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from google.oauth2.service_account import Credentials

def compare_current_data():
    """Сравнение текущих данных"""
    
    print("\n" + "="*100)
    print("СРАВНЕНИЕ ТЕКУЩИХ ДАННЫХ: Google Sheets vs WB CSV от 30.10.2025")
    print("="*100)
    
    config = get_config()
    
    # 1. Читаем Google Sheets
    print("\n1. Чтение Google Sheets...")
    
    try:
        creds = Credentials.from_service_account_file(
            config.google_service_account_key_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.google_sheet_id)
        worksheet = sheet.worksheet(config.google_sheet_name)
        
        all_values = worksheet.get_all_values()
        
        print(f"   [OK] Прочитано {len(all_values)} строк")
        
        sheets_data = {}
        if len(all_values) > 1:  # Пропускаем заголовок
            for row in all_values[1:]:
                if len(row) >= 6:
                    article = row[0]
                    total = int(row[5]) if row[5] else 0
                    sheets_data[article] = total
        
        print(f"   [OK] Данные из Sheets:")
        for article, total in sheets_data.items():
            print(f"      {article}: {total} ед.")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка чтения: {e}")
        return False
    
    # 2. Читаем WB CSV
    print("\n2. Чтение WB CSV...")
    
    csv_file = "30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv"
    
    try:
        wb_data = {}
        
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Находим индекс колонки с количеством (Остатки)
            qty_idx = 16  # Обычно это колонка "Остатки"
            
            for row in reader:
                if len(row) > qty_idx:
                    article = row[0]
                    
                    # Нормализуем артикул (убираем суффиксы)
                    base_article = article.split('+')[0].split('.')[0]
                    
                    qty = int(row[qty_idx]) if row[qty_idx] and row[qty_idx].isdigit() else 0
                    
                    if base_article not in wb_data:
                        wb_data[base_article] = 0
                    wb_data[base_article] += qty
        
        print(f"   [OK] Данные из WB CSV:")
        for article in ['ItsSport2/50g', 'Its2/50g', 'Its1_2_3/50g']:
            total = wb_data.get(article, 0)
            print(f"      {article}: {total} ед.")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка чтения CSV: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Сравниваем
    print("\n3. Сравнение:")
    print(f"   {'Артикул':<25} {'Google Sheets':<20} {'WB CSV':<20} {'Разница':<20} {'Точность':<10}")
    print(f"   {'-'*95}")
    
    total_sheets = 0
    total_wb = 0
    
    for article in ['ItsSport2/50g', 'Its2/50g', 'Its1_2_3/50g']:
        sheets_qty = sheets_data.get(article, 0)
        wb_qty = wb_data.get(article, 0)
        
        diff = sheets_qty - wb_qty
        accuracy = (sheets_qty / wb_qty * 100) if wb_qty > 0 else 0
        
        total_sheets += sheets_qty
        total_wb += wb_qty
        
        status = "[OK]" if abs(diff) <= 100 else "[WARN]"
        
        print(f"   {article:<25} {sheets_qty:<20} {wb_qty:<20} {diff:+<20} {accuracy:.1f}% {status}")
    
    print(f"   {'-'*95}")
    
    total_diff = total_sheets - total_wb
    total_accuracy = (total_sheets / total_wb * 100) if total_wb > 0 else 0
    
    print(f"   {'ВСЕГО':<25} {total_sheets:<20} {total_wb:<20} {total_diff:+<20} {total_accuracy:.1f}%")
    
    print("\n" + "="*100)
    print("ИТОГИ:")
    print("="*100)
    print(f"\nТочность трекера: {total_accuracy:.1f}%")
    print(f"Разница: {total_diff:+} ед. ({abs(total_diff)/ total_wb * 100:.1f}%)")
    
    if total_accuracy >= 90:
        print("\n[OK] Данные трекера соответствуют WB CSV (точность >= 90%)")
    elif total_accuracy >= 80:
        print("\n[WARN] Небольшое расхождение с WB CSV (точность 80-90%)")
    else:
        print("\n[ERROR] Значительное расхождение с WB CSV (точность < 80%)")
    
    print("\n❗ ВНИМАНИЕ:")
    print("   - WB CSV от 30.10.2025 показывает ИСТОРИЧЕСКИЕ данные")
    print("   - Google Sheets содержит ТЕКУЩИЕ данные из API")
    print("   - Разница может быть из-за изменений остатков между снятием CSV и синхронизацией")
    print("="*100 + "\n")
    
    return True

if __name__ == '__main__':
    compare_current_data()
