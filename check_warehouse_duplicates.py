"""
Детальная проверка данных в Google Sheets для ItsSport2/50g
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.database.sheets import GoogleSheetsClient

def check_warehouse_details():
    """Проверка деталей по складам"""
    
    config = StockTrackerConfig()
    sheets = GoogleSheetsClient(
        config.google_sheets.service_account_key_path,
        config.google_sheets.sheet_id,
        config.google_sheets.sheet_name
    )
    
    spreadsheet = sheets._get_spreadsheet()
    worksheet = spreadsheet.worksheet("Stock Tracker")
    all_values = worksheet.get_all_values()
    
    target_article = 'ItsSport2/50g'
    
    print("\n" + "="*100)
    print(f"ДЕТАЛЬНАЯ ПРОВЕРКА СКЛАДОВ ДЛЯ {target_article}")
    print("="*100)
    
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) > 0 and row[0] == target_article:
            print(f"\nСтрока {i}: {target_article}")
            print(f"  Всего остатков: {row[3]}")
            
            # Парсим склады
            warehouse_names = row[5].split('\n') if len(row) > 5 else []
            warehouse_orders = row[6].split('\n') if len(row) > 6 else []
            warehouse_stocks = row[7].split('\n') if len(row) > 7 else []
            
            print(f"\n  Всего складов: {len(warehouse_names)}")
            print(f"\n  Детали по каждому складу:")
            print(f"  {'№':<4} {'Название склада':<40} {'Заказы':<10} {'Остатки':<10}")
            print(f"  {'-'*70}")
            
            for j, (name, orders, stock) in enumerate(zip(warehouse_names, warehouse_orders, warehouse_stocks), 1):
                print(f"  {j:<4} {name:<40} {orders:<10} {stock:<10}")
            
            # Проверка на дубликаты
            print(f"\n  Проверка на дубликаты названий:")
            name_counts = {}
            for name in warehouse_names:
                clean_name = name.strip()
                if clean_name:
                    name_counts[clean_name] = name_counts.get(clean_name, 0) + 1
            
            duplicates_found = False
            for name, count in name_counts.items():
                if count > 1:
                    print(f"    [ОШИБКА] '{name}' встречается {count} раз!")
                    duplicates_found = True
            
            if not duplicates_found:
                print(f"    [OK] Дубликатов не найдено")
            
            # Проверка вариантов "Новосемейкино" / "Самара (Новосемейкино)"
            print(f"\n  Варианты названий одного склада:")
            novosemeykin_variants = []
            for j, name in enumerate(warehouse_names):
                if 'Новосемейкино' in name or 'Самара' in name:
                    stock = warehouse_stocks[j] if j < len(warehouse_stocks) else '0'
                    novosemeykin_variants.append((name, stock))
            
            if len(novosemeykin_variants) > 1:
                print(f"    [КРИТИЧЕСКАЯ ОШИБКА] Найдено {len(novosemeykin_variants)} варианта:")
                for name, stock in novosemeykin_variants:
                    print(f"      - '{name}': {stock} ед.")
                print(f"    Это ОДИН склад, записанный под разными именами!")
            elif len(novosemeykin_variants) == 1:
                name, stock = novosemeykin_variants[0]
                print(f"    [OK] Найден 1 вариант: '{name}' с {stock} ед.")
            else:
                print(f"    [INFO] Новосемейкино не найден в списке складов")
            
            break
    
    print("\n" + "="*100)

if __name__ == '__main__':
    check_warehouse_details()
