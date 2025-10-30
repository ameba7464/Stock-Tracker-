"""
Прямая синхронизация через DualAPIStockFetcher
"""
import sys
import gspread
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
from google.oauth2.service_account import Credentials

def direct_sync():
    """Прямая синхронизация"""
    
    print("\n" + "="*100)
    print(f"ПРЯМАЯ СИНХРОНИЗАЦИЯ ДАННЫХ - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    config = get_config()
    
    # 1. Получаем данные из API
    print("\n1. Получение данных из Wildberries API...")
    fetcher = DualAPIStockFetcher(config.wildberries_api_key)
    
    target_articles = ['ItsSport2/50g', 'Its2/50g', 'Its1_2_3/50g']
    
    all_stocks = {}
    
    for article in target_articles:
        print(f"   Получение данных для {article}...")
        
        try:
            combined = fetcher.get_combined_stocks_by_article(article)
            
            if article in combined:
                all_stocks[article] = combined[article]
                data = combined[article]
                print(f"   [OK] {article}: FBO={data.get('fbo_stock', 0)}, FBS={data.get('fbs_stock', 0)}, Всего={data.get('total_stock', 0)}")
            else:
                print(f"   [WARN] Нет данных для {article}")
        
        except Exception as e:
            print(f"   [ERROR] Ошибка при получении данных для {article}: {e}")
    
    if not all_stocks:
        print("\n[ERROR] Не получено данных из API")
        return False
    
    print(f"\n[OK] Получено данных для {len(all_stocks)} артикулов")
    
    # 2. Подключаемся к Google Sheets
    print("\n2. Подключение к Google Sheets...")
    
    try:
        creds = Credentials.from_service_account_file(
            config.google_service_account_key_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        sheet = client.open_by_key(config.google_sheet_id)
        worksheet = sheet.worksheet(config.google_sheet_name)
        
        print(f"   [OK] Подключено к таблице: {config.google_sheet_id}")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка подключения: {e}")
        return False
    
    # 3. Формируем данные для записи
    print("\n3. Формирование данных...")
    
    rows = []
    
    # Заголовок
    header = ['Артикул', 'NM ID', 'Баркоды', 'FBO', 'FBS', 'Всего', 'Дата обновления']
    rows.append(header)
    
    for article, data in all_stocks.items():
        row = [
            article,
            str(data.get('nm_id', '')),
            ', '.join(data.get('barcodes', [])),
            data.get('fbo_stock', 0),
            data.get('fbs_stock', 0),
            data.get('total_stock', 0),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
        rows.append(row)
        
        print(f"   {article}: {data.get('total_stock', 0)} ед.")
    
    # 4. Записываем в Google Sheets
    print("\n4. Запись в Google Sheets...")
    
    try:
        # Очищаем таблицу
        worksheet.clear()
        
        # Записываем новые данные
        worksheet.update('A1', rows)
        
        print(f"   [OK] Записано {len(rows)-1} строк данных")
        print(f"   [OK] Дата синхронизации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка записи: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*100)
    print("СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
    print("="*100 + "\n")
    
    return True

if __name__ == '__main__':
    success = direct_sync()
    sys.exit(0 if success else 1)
