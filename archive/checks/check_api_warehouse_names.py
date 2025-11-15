"""
Проверка, какие названия складов возвращает API для ItsSport2/50g
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.api.wildberries_client import WildberriesAPIClient
from stock_tracker.utils.config import get_config
from stock_tracker.utils.warehouse_mapper import normalize_warehouse_name

async def check_api_warehouse_names():
    """Проверка названий складов из API"""
    
    print("\n" + "="*100)
    print("ПРОВЕРКА НАЗВАНИЙ СКЛАДОВ ИЗ WB API")
    print("="*100)
    
    config = get_config()
    client = WildberriesAPIClient(config)
    
    target_article = 'ItsSport2/50g'
    
    print(f"\nАртикул: {target_article}")
    print("-" * 100)
    
    # Получаем данные из Statistics API (FBO)
    print("\n1. Statistics API (FBO склады):")
    stats_data = client.get_statistics()
    
    article_data = [item for item in stats_data if item.get('subject') == target_article]
    
    if article_data:
        print(f"   Найдено {len(article_data)} записей")
        
        warehouses = {}
        for item in article_data:
            wh_name_raw = item.get('warehouseName', '')
            wh_name_normalized = normalize_warehouse_name(wh_name_raw)
            stock = item.get('quantityFull', 0)
            
            if wh_name_normalized not in warehouses:
                warehouses[wh_name_normalized] = {'raw_names': set(), 'stock': 0}
            
            warehouses[wh_name_normalized]['raw_names'].add(wh_name_raw)
            warehouses[wh_name_normalized]['stock'] += stock
        
        print(f"\n   Склады (после нормализации):")
        print(f"   {'Нормализованное':<40} {'Исходные варианты':<50} {'Остатки':<10}")
        print(f"   {'-'*100}")
        
        for norm_name, data in sorted(warehouses.items()):
            raw_names = ', '.join(data['raw_names'])
            print(f"   {norm_name:<40} {raw_names:<50} {data['stock']:<10}")
    else:
        print(f"   [WARN] Нет данных в Statistics API")
    
    # Получаем данные из Marketplace API (FBS)
    print(f"\n2. Marketplace API v3 (FBS склады):")
    
    try:
        from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher
        
        dual_fetcher = DualAPIStockFetcher(config.wildberries_api_key)
        
        # Получаем склады FBS
        fbs_warehouses = dual_fetcher.get_fbs_warehouses()
        print(f"   Всего FBS складов: {len(fbs_warehouses)}")
        
        # Получаем остатки для артикула
        # Нужно получить баркоды для артикула
        stats_for_barcodes = [item for item in stats_data if item.get('subject') == target_article]
        barcodes = list(set([item.get('barcode') for item in stats_for_barcodes if item.get('barcode')]))
        
        if barcodes:
            print(f"   Баркоды артикула: {barcodes}")
            
            fbs_stocks = dual_fetcher.get_fbs_stocks(barcodes)
            
            if fbs_stocks:
                print(f"\n   FBS остатки:")
                print(f"   {'Склад (нормализованное)':<40} {'Баркод':<15} {'Остатки':<10}")
                print(f"   {'-'*70}")
                
                for barcode, warehouses in fbs_stocks.items():
                    for wh_name, stock in warehouses.items():
                        print(f"   {wh_name:<40} {barcode:<15} {stock:<10}")
            else:
                print(f"   [INFO] Нет FBS остатков для этого артикула")
        else:
            print(f"   [WARN] Не найдены баркоды для артикула")
            
    except Exception as e:
        print(f"   [ERROR] Ошибка при получении FBS данных: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)

if __name__ == '__main__':
    asyncio.run(check_api_warehouse_names())
