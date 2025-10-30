"""
Детальная проверка Statistics API для ItsSport2/50g
"""
import sys
import requests
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

def check_statistics_api_details():
    """Детальная проверка Statistics API"""
    
    print("\n" + "="*100)
    print("ДЕТАЛЬНАЯ ПРОВЕРКА STATISTICS API V1 ДЛЯ ItsSport2/50g")
    print("="*100)
    
    config = get_config()
    api_key = config.wildberries_api_key
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    params = {"dateFrom": "2025-10-27"}
    
    print(f"\nURL: {url}")
    print(f"Параметры: {params}")
    print("-"*100)
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        all_data = response.json()
        print(f"\n[OK] Получено {len(all_data)} записей")
        
        # Находим все записи для ItsSport
        itssport_records = [r for r in all_data if 'ItsSport' in r.get('subject', '')]
        
        print(f"\n[OK] Найдено {len(itssport_records)} записей с 'ItsSport'")
        
        # Группируем по subject (артикул)
        by_subject = defaultdict(list)
        for r in itssport_records:
            by_subject[r.get('subject', 'Unknown')].append(r)
        
        print(f"\nАртикулы (subject field):")
        for subject, records in by_subject.items():
            total = sum(r.get('quantityFull', 0) for r in records)
            print(f"  {subject}: {len(records)} записей, {total} ед.")
        
        # Детальный анализ для ItsSport2/50g
        target = 'ItsSport2/50g'
        if target in by_subject:
            records = by_subject[target]
            
            print(f"\nДетальный анализ для {target}:")
            print(f"{'supplierArticle':<30} {'Склад (raw)':<40} {'Склад (norm)':<35} {'Остатки'}")
            print("-"*120)
            
            warehouses = defaultdict(int)
            supplier_articles = set()
            
            for r in records:
                supplier_art = r.get('supplierArticle', '')
                wh_raw = r.get('warehouseName', '')
                qty = r.get('quantityFull', 0)
                wh_norm = normalize_warehouse_name(wh_raw)
                
                supplier_articles.add(supplier_art)
                warehouses[wh_norm] += qty
                
                print(f"{supplier_art:<30} {wh_raw:<40} {wh_norm:<35} {qty}")
            
            print("-"*120)
            print(f"{'ВСЕГО':<106} {sum(r.get('quantityFull', 0) for r in records)}")
            
            print(f"\nУникальные supplierArticle:")
            for art in sorted(supplier_articles):
                recs = [r for r in records if r.get('supplierArticle') == art]
                total = sum(r.get('quantityFull', 0) for r in recs)
                print(f"  {art}: {total} ед.")
            
            print(f"\nСклады (после нормализации):")
            for wh, qty in sorted(warehouses.items(), key=lambda x: -x[1]):
                print(f"  {wh}: {qty} ед.")
        else:
            print(f"\n[WARN] Нет данных для {target} (subject field)")
            
            # Проверяем по supplierArticle
            by_supplier = [r for r in all_data if 'ItsSport2/50g' in r.get('supplierArticle', '')]
            
            if by_supplier:
                print(f"\n[INFO] Найдено {len(by_supplier)} записей по supplierArticle")
                
                print(f"\n{'subject':<30} {'supplierArticle':<30} {'Склад':<40} {'Остатки'}")
                print("-"*115)
                
                for r in by_supplier:
                    subject = r.get('subject', '')
                    supplier_art = r.get('supplierArticle', '')
                    wh = r.get('warehouseName', '')
                    qty = r.get('quantityFull', 0)
                    
                    print(f"{subject:<30} {supplier_art:<30} {wh:<40} {qty}")
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)

if __name__ == '__main__':
    check_statistics_api_details()
