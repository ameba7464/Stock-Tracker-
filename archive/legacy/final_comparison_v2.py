"""
Финальное сравнение - читаем напрямую из Google Sheets и WB CSV
"""
import sys
from pathlib import Path
import csv
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.database.sheets import GoogleSheetsClient

def parse_number(value):
    """Парсинг числовых значений"""
    if not value or value == '':
        return 0
    # Убираем ВСЕ виды пробелов, включая неразрывные пробелы (\xa0)
    value = str(value).replace(' ', '').replace('\xa0', '').replace(',', '.')
    try:
        return float(value)
    except:
        return 0

def load_wb_csv():
    """Загрузка данных из WB CSV"""
    wb_data = defaultdict(lambda: {'stock': 0, 'warehouses': {}})
    
    with open("30-10-2025 История остатков с 24-10-2025 по 30-10-2025_export.csv", 'r', encoding='utf-8') as f:
        next(f)  # Skip title
        reader = csv.DictReader(f)
        
        for row in reader:
            article = row.get('Артикул продавца', '')
            if not article:
                continue
            
            warehouse = row.get('Склад', '')
            stock_str = row.get('Остатки на текущий день, шт', '0')
            stock = int(stock_str) if stock_str and stock_str.strip() else 0
            
            wb_data[article]['stock'] += stock
            if warehouse and stock > 0:
                if warehouse not in wb_data[article]['warehouses']:
                    wb_data[article]['warehouses'][warehouse] = 0
                wb_data[article]['warehouses'][warehouse] += stock
    
    return wb_data

def load_tracker_from_sheets():
    """Загрузка данных напрямую из Google Sheets"""
    config = StockTrackerConfig()
    sheets = GoogleSheetsClient(
        config.google_sheets.service_account_key_path,
        config.google_sheets.sheet_id,
        config.google_sheets.sheet_name
    )
    
    spreadsheet = sheets._get_spreadsheet()
    worksheet = spreadsheet.worksheet("Stock Tracker")
    all_values = worksheet.get_all_values()
    
    tracker_data = {}
    
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) < 4:
            continue
        
        article = row[0]
        if not article or not article.startswith('Its'):
            continue
        
        stock_str = row[3].replace(' ', '')
        stock = int(parse_number(stock_str))
        
        # Парсим склады из multi-line cells
        warehouse_names = row[5].split('\n') if len(row) > 5 else []
        warehouse_stocks = row[7].split('\n') if len(row) > 7 else []
        
        warehouses = {}
        for name, stock_val in zip(warehouse_names, warehouse_stocks):
            if name and name.strip():
                wh_stock = int(parse_number(stock_val))
                if wh_stock > 0:
                    warehouses[name.strip()] = wh_stock
        
        tracker_data[article] = {
            'stock': stock,
            'warehouses': warehouses
        }
    
    return tracker_data

def compare_final():
    """Финальное сравнение"""
    
    print("\n" + "="*100)
    print("ФИНАЛЬНОЕ СРАВНЕНИЕ ПОСЛЕ ВСЕХ ИСПРАВЛЕНИЙ")
    print("="*100)
    print("\nИсточники:")
    print("  WB CSV: 30-10-2025 История остатков...")
    print("  Tracker: Google Sheets (прямое чтение через API)")
    print()
    
    wb_data = load_wb_csv()
    tracker_data = load_tracker_from_sheets()
    
    target_articles = ['Its2/50g', 'ItsSport2/50g', 'Its1_2_3/50g']
    
    total_wb_stock = 0
    total_tracker_stock = 0
    total_diff = 0
    
    for article in target_articles:
        wb = wb_data.get(article, {})
        tracker = tracker_data.get(article, {})
        
        wb_stock = wb.get('stock', 0)
        tracker_stock = tracker.get('stock', 0)
        diff = wb_stock - tracker_stock
        diff_percent = (abs(diff) / wb_stock * 100) if wb_stock > 0 else 0
        
        total_wb_stock += wb_stock
        total_tracker_stock += tracker_stock
        total_diff += abs(diff)
        
        print(f"\n{'='*100}")
        print(f"{article}")
        print(f"{'='*100}")
        print(f"  WB CSV Total:     {wb_stock:>6d} units")
        print(f"  Tracker Total:    {tracker_stock:>6d} units")
        print(f"  Difference:       {diff:>6d} units ({diff_percent:.1f}%)")
        
        # Маркетплейс
        wb_mp = wb.get('warehouses', {}).get('Маркетплейс', 0)
        tr_mp = tracker.get('warehouses', {}).get('Маркетплейс', 0)
        
        print(f"\n  'Marketpleys' warehouse:")
        print(f"    WB CSV:         {wb_mp:>6d} units")
        print(f"    Tracker:        {tr_mp:>6d} units")
        print(f"    Difference:     {wb_mp - tr_mp:>6d} units")
        
        if tr_mp > 0:
            print(f"    [SUCCESS] FBS warehouse FOUND in Tracker!")
        else:
            print(f"    [FAIL] FBS warehouse NOT FOUND in Tracker!")
        
        # Детали
        print(f"\n  Top warehouses with stock:")
        all_wh = set(wb.get('warehouses', {}).keys()) | set(tracker.get('warehouses', {}).keys())
        
        sorted_wh = sorted(all_wh, key=lambda x: -(wb.get('warehouses', {}).get(x, 0) + tracker.get('warehouses', {}).get(x, 0)))[:10]
        
        print(f"  {'Warehouse':<40} {'WB':>10} {'Tracker':>10} {'Diff':>10}")
        print(f"  {'-'*70}")
        
        for wh in sorted_wh:
            wb_wh = wb.get('warehouses', {}).get(wh, 0)
            tr_wh = tracker.get('warehouses', {}).get(wh, 0)
            diff_wh = wb_wh - tr_wh
            
            status = "[OK]" if abs(diff_wh) <= max(wb_wh, tr_wh) * 0.15 else "[!]"
            print(f"  {status} {wh:<35} {wb_wh:>10d} {tr_wh:>10d} {diff_wh:>10d}")
    
    print(f"\n{'='*100}")
    print(f"SUMMARY STATISTICS")
    print(f"{'='*100}")
    print(f"  Total stock (WB):      {total_wb_stock:>6d} units")
    print(f"  Total stock (Tracker): {total_tracker_stock:>6d} units")
    print(f"  Total difference:      {total_diff:>6d} units")
    
    accuracy = (1 - total_diff / total_wb_stock) * 100 if total_wb_stock > 0 else 0
    print(f"  Accuracy:              {accuracy:>6.1f}%")
    
    print(f"\n{'='*100}")
    
    if accuracy >= 90:
        print("[SUCCESS] Accuracy > 90% - system works correctly!")
        print("Small differences are due to natural sales between CSV export and sync.")
    elif accuracy >= 80:
        print("[WARNING] Accuracy 80-90% - minor discrepancies exist")
    else:
        print("[FAIL] Accuracy < 80% - additional verification required")
    
    print(f"{'='*100}\n")

if __name__ == '__main__':
    compare_final()
