"""
Проверка названий складов из API для ItsSport2/50g
"""
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

def check_api_warehouse_names():
    """Проверка названий складов из API"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА НАЗВАНИЙ СКЛАДОВ ИЗ WB API")
    print("="*100)
    
    config = get_config()
    api_key = config.wildberries.api_key
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    target_article = 'ItsSport2/50g'
    
    print(f"\nАртикул: {target_article}")
    print("-" * 100)
    
    # 1. Получаем данные из Statistics API (FBO)
    print("\n1. Statistics API v1 (FBO склады):")
    print("   URL: https://statistics-api.wildberries.ru/api/v1/supplier/stocks")
    
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    params = {"dateFrom": "2025-10-27"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        stats_data = response.json()
        article_data = [item for item in stats_data if item.get('subject') == target_article]
        
        if article_data:
            print(f"   Найдено {len(article_data)} записей")
            
            warehouses = {}
            barcodes = set()
            
            for item in article_data:
                wh_name_raw = item.get('warehouseName', '')
                wh_name_normalized = normalize_warehouse_name(wh_name_raw)
                stock = item.get('quantityFull', 0)
                barcode = item.get('barcode', '')
                
                barcodes.add(barcode)
                
                if wh_name_raw not in warehouses:
                    warehouses[wh_name_raw] = {
                        'normalized': wh_name_normalized,
                        'stock': 0
                    }
                
                warehouses[wh_name_raw]['stock'] += stock
            
            print(f"\n   Склады:")
            print(f"   {'Исходное название':<45} {'Нормализованное':<35} {'Остатки':<10}")
            print(f"   {'-'*95}")
            
            for wh_raw, data in sorted(warehouses.items()):
                print(f"   {wh_raw:<45} {data['normalized']:<35} {data['stock']:<10}")
            
            # Сохраним баркоды для FBS запроса
            barcodes_list = list(barcodes)
            print(f"\n   Уникальных баркодов: {len(barcodes_list)}")
            
        else:
            print(f"   [WARN] Нет данных в Statistics API")
            barcodes_list = []
    
    except Exception as e:
        print(f"   [ERROR] Ошибка при получении FBO данных: {e}")
        import traceback
        traceback.print_exc()
        barcodes_list = []
    
    # 2. Получаем данные из Marketplace API v3 (FBS)
    print(f"\n2. Marketplace API v3 (FBS склады):")
    print("   URL: https://marketplace-api.wildberries.ru/api/v3/warehouses")
    
    try:
        url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        fbs_warehouses = response.json()
        print(f"   Всего FBS складов: {len(fbs_warehouses)}")
        
        if barcodes_list:
            print(f"\n   Проверяем FBS остатки для артикула...")
            print(f"   {'Исходное название':<45} {'Нормализованное':<35} {'Остатки':<10}")
            print(f"   {'-'*95}")
            
            for warehouse in fbs_warehouses:
                wh_id = warehouse.get('id')
                wh_name_raw = warehouse.get('name', '')
                wh_name_normalized = normalize_warehouse_name(wh_name_raw)
                
                stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
                body = {"skus": barcodes_list}
                
                try:
                    stocks_response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
                    stocks_response.raise_for_status()
                    
                    stocks_data = stocks_response.json()
                    stocks = stocks_data.get('stocks', [])
                    
                    if stocks:
                        total_stock = sum(s.get('amount', 0) for s in stocks)
                        print(f"   {wh_name_raw:<45} {wh_name_normalized:<35} {total_stock:<10}")
                
                except Exception as e:
                    # Пропускаем ошибки для складов без остатков
                    pass
        else:
            print(f"   [WARN] Нет баркодов для проверки FBS остатков")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка при получении FBS данных: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)
    print("ИТОГИ:")
    print("="*100)
    print("\nСравним с данными из Google Sheets:")
    print("  - В Google Sheets: 'Самара (Новосемейкино)' с 68 ед.")
    print("  - В WB CSV: 'Новосемейкино' с 68 ед.")
    print("\nПроверим, какое название возвращает API для этого склада")
    print("="*100 + "\n")

if __name__ == '__main__':
    check_api_warehouse_names()
