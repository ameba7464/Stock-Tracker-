"""
Полная проверка текущего состояния API для ItsSport2/50g
"""
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.services.dual_api_stock_fetcher import DualAPIStockFetcher

def check_current_api_state():
    """Полная проверка текущего состояния API"""
    
    print("\n" + "="*100)
    print("ПОЛНАЯ ПРОВЕРКА ТЕКУЩИХ ДАННЫХ API ДЛЯ ItsSport2/50g")
    print("="*100)
    
    config = get_config()
    api_key = config.wildberries_api_key
    
    # Создаём fetcher
    fetcher = DualAPIStockFetcher(api_key)
    
    target_article = 'ItsSport2/50g'
    
    print(f"\n🎯 Артикул: {target_article}")
    print(f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 100)
    
    # 1. Получаем FBO stocks
    print("\n1️⃣ STATISTICS API V1 (FBO)")
    print("   URL: https://statistics-api.wildberries.ru/api/v1/supplier/stocks")
    
    fbo_stocks = fetcher.get_fbo_stocks()
    article_fbo = [s for s in fbo_stocks if s.get('subject') == target_article]
    
    if article_fbo:
        print(f"   ✅ Найдено {len(article_fbo)} записей FBO")
        
        # Группируем по складам
        warehouses = {}
        barcodes = set()
        
        for stock in article_fbo:
            wh = stock.get('warehouseName', '')
            qty = stock.get('quantityFull', 0)
            barcode = stock.get('barcode', '')
            
            barcodes.add(barcode)
            
            if wh not in warehouses:
                warehouses[wh] = 0
            warehouses[wh] += qty
        
        print(f"\n   📦 Склады:")
        for wh, qty in sorted(warehouses.items()):
            print(f"      {wh}: {qty} ед.")
        
        print(f"\n   🏷️ Баркоды: {', '.join(barcodes)}")
        
        barcodes_list = list(barcodes)
    else:
        print(f"   ❌ НЕТ данных FBO для {target_article}")
        barcodes_list = []
    
    # 2. Получаем FBS stocks
    print(f"\n2️⃣ MARKETPLACE API V3 (FBS)")
    print("   URL: https://marketplace-api.wildberries.ru/api/v3/warehouses")
    
    fbs_warehouses = fetcher.get_fbs_warehouses()
    print(f"   📊 Всего FBS складов: {len(fbs_warehouses)}")
    
    if barcodes_list:
        fbs_stocks_dict = fetcher.get_fbs_stocks(barcodes_list)
        
        if fbs_stocks_dict:
            print(f"\n   📦 FBS остатки:")
            
            for wh_id, wh_data in fbs_stocks_dict.items():
                wh_name = wh_data.get('warehouse_name', '')
                stocks = wh_data.get('stocks', [])
                
                total = sum(s.get('amount', 0) for s in stocks)
                
                if total > 0:
                    print(f"      {wh_name}: {total} ед.")
                    for s in stocks:
                        print(f"         Баркод {s.get('sku')}: {s.get('amount')} ед.")
        else:
            print(f"   ❌ НЕТ данных FBS для {target_article}")
    else:
        print(f"   ⚠️ Не могу проверить FBS - нет баркодов")
    
    # 3. Проверяем combined stocks
    print(f"\n3️⃣ COMBINED STOCKS (FBO + FBS через DualAPIStockFetcher)")
    
    try:
        combined = fetcher.get_combined_stocks_by_article(target_article)
        
        if target_article in combined:
            data = combined[target_article]
            
            print(f"\n   ✅ Комбинированные данные:")
            print(f"      NM ID: {data.get('nm_id')}")
            print(f"      Баркоды: {data.get('barcodes')}")
            print(f"      FBO остатки: {data.get('fbo_stock', 0)}")
            print(f"      FBS остатки: {data.get('fbs_stock', 0)}")
            print(f"      ВСЕГО: {data.get('total_stock', 0)}")
            
            # Показываем детали по складам
            if data.get('fbo_details'):
                print(f"\n   📦 FBO склады (детали):")
                fbo_wh = {}
                for d in data['fbo_details']:
                    wh = d.get('warehouse_name', '')
                    qty = d.get('quantity', 0)
                    if wh not in fbo_wh:
                        fbo_wh[wh] = 0
                    fbo_wh[wh] += qty
                
                for wh, qty in sorted(fbo_wh.items()):
                    print(f"      {wh}: {qty} ед.")
            
            if data.get('fbs_details'):
                print(f"\n   📦 FBS склады (детали):")
                fbs_wh = {}
                for d in data['fbs_details']:
                    wh = d.get('warehouse_name', '')
                    qty = d.get('quantity', 0)
                    if wh not in fbs_wh:
                        fbs_wh[wh] = 0
                    fbs_wh[wh] += qty
                
                for wh, qty in sorted(fbs_wh.items()):
                    print(f"      {wh}: {qty} ед.")
        else:
            print(f"   ❌ НЕТ комбинированных данных для {target_article}")
    
    except Exception as e:
        print(f"   ❌ Ошибка при получении комбинированных данных: {e}")
    
    print("\n" + "="*100)
    print("🔍 ИТОГИ:")
    print("="*100)
    print(f"\n1. Statistics API (FBO): {'ДА' if article_fbo else 'НЕТ'} данных")
    print(f"2. Marketplace API (FBS): {'ДА' if barcodes_list and fbs_stocks_dict else 'НЕТ'} данных")
    print(f"3. Google Sheets: ПУСТО (1 пустая строка)")
    print(f"\n❗ Если API не возвращает данные о складе 'Новосемейкино' или 'Самара (Новосемейкино)',")
    print(f"   значит этих остатков больше НЕТ на WB!")
    print("="*100 + "\n")

if __name__ == '__main__':
    check_current_api_state()
