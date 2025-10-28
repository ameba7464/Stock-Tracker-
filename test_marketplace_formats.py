#!/usr/bin/env python3
"""
Test Marketplace API v3 stocks with correct format
Based on WB API documentation
"""

import requests
import json
from datetime import datetime, timedelta
from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    print("\n" + "="*100)
    print("🔍 ТЕСТ: Marketplace API v3 - Правильный формат запроса")
    print("="*100)
    
    # Get warehouses first
    warehouses_url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.get(warehouses_url, headers=headers)
    warehouses = response.json()
    
    print(f"\n✅ FBS Склады ({len(warehouses)}):")
    for wh in warehouses:
        wh_id = wh.get('id')
        wh_name = wh.get('name')
        print(f"  - ID: {wh_id}, Name: {wh_name}")
    
    if not warehouses:
        print("❌ Нет FBS складов")
        return
    
    # Try different request formats for stocks
    wh_id = warehouses[0]['id']
    wh_name = warehouses[0]['name']
    
    print(f"\n📦 Тестируем склад: {wh_name} (ID: {wh_id})")
    print("="*100)
    
    # Format 1: POST with skus in body
    print("\n⏳ Формат 1: POST /api/v3/stocks/{warehouseId} с массивом skus...")
    stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
    
    # Try with empty skus array (should return all)
    body1 = {"skus": []}
    
    try:
        response = requests.post(stocks_url, headers=headers, json=body1, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            stocks = data.get('stocks', [])
            print(f"✅ Получено остатков: {len(stocks)}")
            
            # Look for Its1_2_3/50g
            target = [s for s in stocks if 'Its1_2_3' in str(s)]
            if target:
                print(f"\n✅ Найдено записей для Its1_2_3/50g: {len(target)}")
                for t in target:
                    print(json.dumps(t, indent=2, ensure_ascii=False))
            else:
                print("\n⚠️ Its1_2_3/50g не найден в этом складе")
                if stocks:
                    print("\nПримеры товаров:")
                    for s in stocks[:3]:
                        print(json.dumps(s, indent=2, ensure_ascii=False))
        
        elif response.status_code == 400:
            error = response.json()
            print(f"❌ 400 Bad Request")
            print(f"Детали: {json.dumps(error, indent=2, ensure_ascii=False)}")
            
            # Try format 2
            print("\n⏳ Формат 2: GET /api/v3/stocks/{warehouseId}...")
            response2 = requests.get(stocks_url, headers=headers, timeout=30)
            print(f"Статус: {response2.status_code}")
            
            if response2.status_code == 200:
                data = response2.json()
                print(f"✅ Успех!")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
            else:
                print(f"Ответ: {response2.text[:500]}")
        
        else:
            print(f"Ответ: {response.text[:500]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Format 3: Try without warehouseId parameter
    print("\n⏳ Формат 3: GET /api/v3/stocks (без warehouseId)...")
    stocks_url_all = "https://marketplace-api.wildberries.ru"
    
    try:
        response = requests.get(stocks_url_all, headers=headers, params={'warehouseId': wh_id}, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Успех!")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        else:
            print(f"Ответ: {response.text[:300]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Format 4: Check if there's a different endpoint
    print("\n⏳ Формат 4: Пробуем альтернативные endpoints...")
    
    alternative_endpoints = [
        f"https://marketplace-api.wildberries.ru/api/v2/stocks",
        f"https://marketplace-api.wildberries.ru/api/v3/fbs/stocks",
        f"https://marketplace-api.wildberries.ru/api/v3/supplier/stocks",
    ]
    
    for endpoint in alternative_endpoints:
        try:
            print(f"\n  {endpoint}...")
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code != 404:
                print(f"    Статус: {response.status_code}")
                if response.status_code == 200:
                    print(f"    ✅ НАЙДЕН РАБОТАЮЩИЙ ENDPOINT!")
                    data = response.json()
                    if isinstance(data, list):
                        print(f"    Записей: {len(data)}")
                    break
        except:
            pass
    
    print("\n" + "="*100)
    print("📚 ДОКУМЕНТАЦИЯ:")
    print("="*100)
    print("\nИспользуйте официальную документацию WB:")
    print("https://dev.wildberries.ru/openapi/marketplace/api/ru/")
    print("\nТам должен быть правильный формат запроса для /api/v3/stocks")

if __name__ == "__main__":
    main()
