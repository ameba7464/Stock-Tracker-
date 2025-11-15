"""
Проверка названий складов для конкретного баркода ItsSport2/50g (163383328)
"""
import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

def check_barcode_warehouse_names():
    """Проверка складов для конкретного баркода"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА НАЗВАНИЙ СКЛАДОВ ДЛЯ БАРКОДА 163383328 (ItsSport2/50g)")
    print("="*100)
    
    config = get_config()
    api_key = config.wildberries.api_key
    headers = {
        'Authorization': api_key,
        'Content-Type': 'application/json'
    }
    
    barcode = '163383328'
    
    # 1. Проверяем Statistics API
    print("\n1. Statistics API v1 (проверка баркода):")
    print("   URL: https://statistics-api.wildberries.ru/api/v1/supplier/stocks")
    
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    params = {"dateFrom": "2025-10-27"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        stats_data = response.json()
        barcode_data = [item for item in stats_data if item.get('barcode') == barcode]
        
        if barcode_data:
            print(f"   Найдено {len(barcode_data)} записей для баркода {barcode}")
            
            print(f"\n   Детали:")
            print(f"   {'Артикул':<25} {'Склад (исходный)':<45} {'Склад (нормализованный)':<35} {'Остатки'}")
            print(f"   {'-'*130}")
            
            for item in barcode_data:
                article = item.get('supplierArticle', '')
                wh_raw = item.get('warehouseName', '')
                wh_norm = normalize_warehouse_name(wh_raw)
                stock = item.get('quantityFull', 0)
                
                print(f"   {article:<25} {wh_raw:<45} {wh_norm:<35} {stock}")
        else:
            print(f"   [INFO] Нет данных для баркода {barcode} в Statistics API")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
    
    # 2. Проверяем Marketplace API v3
    print(f"\n2. Marketplace API v3 (FBS склады):")
    print("   URL: https://marketplace-api.wildberries.ru/api/v3/warehouses")
    
    try:
        url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        fbs_warehouses = response.json()
        print(f"   Всего FBS складов: {len(fbs_warehouses)}")
        
        print(f"\n   Проверяем каждый FBS склад для баркода {barcode}:")
        print(f"   {'Склад (исходный)':<45} {'Склад (нормализованный)':<35} {'Остатки'}")
        print(f"   {'-'*100}")
        
        found_any = False
        
        for warehouse in fbs_warehouses:
            wh_id = warehouse.get('id')
            wh_name_raw = warehouse.get('name', '')
            wh_name_normalized = normalize_warehouse_name(wh_name_raw)
            
            stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
            body = {"skus": [barcode]}
            
            try:
                stocks_response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
                stocks_response.raise_for_status()
                
                stocks_data = stocks_response.json()
                stocks = stocks_data.get('stocks', [])
                
                if stocks:
                    for stock in stocks:
                        if stock.get('sku') == barcode:
                            amount = stock.get('amount', 0)
                            if amount > 0:
                                print(f"   {wh_name_raw:<45} {wh_name_normalized:<35} {amount}")
                                found_any = True
            
            except Exception as e:
                # Пропускаем ошибки
                pass
        
        if not found_any:
            print(f"   [INFO] Нет FBS остатков для баркода {barcode}")
    
    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
    
    print("\n" + "="*100)
    print("ИТОГИ:")
    print("="*100)
    print(f"\nДля баркода {barcode} (ItsSport2/50g):")
    print("  - WB CSV показывает: 'Новосемейкино' с 68 ед.")
    print("  - Google Sheets показывает: 'Самара (Новосемейкино)' с 68 ед.")
    print("\nПроверим, из какого API приходит этот склад и с каким названием")
    print("="*100 + "\n")

if __name__ == '__main__':
    check_barcode_warehouse_names()
