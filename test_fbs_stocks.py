#!/usr/bin/env python3
"""
Get barcodes from Statistics API and test Marketplace stocks
"""

import requests
import json
from datetime import datetime, timedelta
from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    print("\n" + "="*100)
    print("🔍 ПОЛУЧЕНИЕ БАРКОДОВ из Statistics API → Тест Marketplace API")
    print("="*100)
    
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    # Step 1: Get barcodes from Statistics API
    print("\n📊 Шаг 1: Получаем баркоды из Statistics API...")
    
    stats_url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    params = {"dateFrom": date_from}
    
    response = requests.get(stats_url, headers=headers, params=params, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ Statistics API error: {response.status_code}")
        print(response.text[:500])
        return
    
    stats_data = response.json()
    print(f"✅ Получено записей: {len(stats_data)}")
    
    # Extract barcodes for Its1_2_3/50g
    target_records = [r for r in stats_data if 'Its1_2_3' in r.get('supplierArticle', '')]
    
    if not target_records:
        print("❌ Its1_2_3/50g не найден в Statistics API")
        return
    
    print(f"✅ Найдено записей Its1_2_3/50g: {len(target_records)}")
    
    # Collect unique barcodes
    barcodes = set()
    for rec in target_records:
        barcode = rec.get('barcode')
        if barcode:
            barcodes.add(barcode)
    
    barcodes_list = list(barcodes)
    print(f"✅ Уникальных баркодов: {len(barcodes_list)}")
    print(f"Баркоды: {barcodes_list}")
    
    # Show sample data
    print("\n📋 Пример записи из Statistics API:")
    sample = target_records[0]
    for key in ['nmId', 'supplierArticle', 'barcode', 'warehouseName', 'quantity']:
        print(f"  {key}: {sample.get(key)}")
    
    # Step 2: Get FBS warehouses
    print("\n📦 Шаг 2: Получаем FBS склады...")
    warehouses_url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
    
    response = requests.get(warehouses_url, headers=headers)
    warehouses = response.json()
    
    print(f"✅ Найдено FBS складов: {len(warehouses)}")
    for wh in warehouses:
        print(f"  - ID: {wh.get('id')}, Name: {wh.get('name')}, DeliveryType: {wh.get('deliveryType')}")
    
    # Step 3: Get stocks from Marketplace API
    print("\n📦 Шаг 3: Запрашиваем остатки с FBS складов...")
    
    for wh in warehouses:
        wh_id = wh.get('id')
        wh_name = wh.get('name')
        
        print(f"\n{'='*100}")
        print(f"Склад: {wh_name} (ID: {wh_id})")
        print('='*100)
        
        stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
        
        # Test 1: With specific barcodes
        print(f"\n🔍 Тест 1: Запрос с конкретными баркодами ({len(barcodes_list)} шт)")
        body = {"skus": barcodes_list}
        
        response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            stocks_data = response.json()
            stocks = stocks_data.get('stocks', [])
            
            if stocks:
                total = sum(s.get('amount', 0) for s in stocks)
                print(f"✅ Найдено остатков: {len(stocks)}, Количество: {total} шт")
                
                for stock in stocks:
                    print(f"  - Баркод: {stock.get('sku')}, Остаток: {stock.get('amount')} шт")
            else:
                print("⚠️ Нет остатков для этих баркодов")
        else:
            error = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"❌ Ошибка: {json.dumps(error, indent=2, ensure_ascii=False) if isinstance(error, dict) else error[:300]}")
        
        # Test 2: Empty array (all stocks)
        print(f"\n🔍 Тест 2: Запрос ВСЕХ остатков (пустой массив)")
        body = {"skus": []}
        
        response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            stocks_data = response.json()
            stocks = stocks_data.get('stocks', [])
            
            total = sum(s.get('amount', 0) for s in stocks)
            print(f"✅ Всего остатков: {len(stocks)} позиций, {total} шт")
            
            # Look for our product
            target_stocks = [s for s in stocks if s.get('sku') in barcodes_list]
            if target_stocks:
                target_total = sum(s.get('amount', 0) for s in target_stocks)
                print(f"✅ Its1_2_3/50g найден: {len(target_stocks)} баркодов, {target_total} шт")
                
                for stock in target_stocks:
                    print(f"  - Баркод: {stock.get('sku')}, Остаток: {stock.get('amount')} шт")
            else:
                print("⚠️ Its1_2_3/50g не найден среди остатков")
                
                # Show sample of what's there
                if stocks:
                    print("\nПримеры баркодов на складе:")
                    for stock in stocks[:5]:
                        print(f"  - {stock.get('sku')}: {stock.get('amount')} шт")
        else:
            error = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"❌ Ошибка: {json.dumps(error, indent=2, ensure_ascii=False) if isinstance(error, dict) else error[:300]}")
    
    print("\n" + "="*100)
    print("📊 СРАВНЕНИЕ ДАННЫХ")
    print("="*100)
    print(f"\n📈 Statistics API (FBO):")
    fbo_total = sum(r.get('quantity', 0) for r in target_records)
    print(f"  Записей: {len(target_records)}")
    print(f"  Общее количество: {fbo_total} шт")
    
    print(f"\n📦 Marketplace API (FBS):")
    print(f"  Складов: {len(warehouses)}")
    print(f"  (Результаты см. выше)")
    
    print("\n" + "="*100)
    print("✅ АНАЛИЗ ЗАВЕРШЕН")
    print("="*100)

if __name__ == "__main__":
    main()
