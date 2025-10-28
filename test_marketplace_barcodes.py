#!/usr/bin/env python3
"""
Test Marketplace API v3 with correct barcode format
"""

import requests
import json
from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    print("\n" + "="*100)
    print("🔍 ТЕСТ: Marketplace API v3 - Правильный формат с баркодами")
    print("="*100)
    
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    # Step 1: Get warehouses
    print("\n📦 Шаг 1: Получаем FBS склады...")
    warehouses_url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
    
    response = requests.get(warehouses_url, headers=headers)
    warehouses = response.json()
    
    print(f"✅ Найдено FBS складов: {len(warehouses)}")
    for wh in warehouses:
        print(f"  - ID: {wh.get('id')}, Name: {wh.get('name')}, DeliveryType: {wh.get('deliveryType')}, CargoType: {wh.get('cargoType')}")
    
    if not warehouses:
        print("❌ Нет FBS складов")
        return
    
    # Step 2: Get product cards to find barcodes
    print("\n📋 Шаг 2: Получаем карточки товаров для извлечения баркодов...")
    
    # Try content API v1
    content_url = "https://content-api.wildberries.ru/content/v1/cards/cursor/list"
    
    try:
        # Get first batch of cards
        body = {
            "sort": {
                "cursor": {
                    "limit": 100
                },
                "filter": {
                    "textSearch": "Its1_2_3/50g"  # Search for our test product
                }
            }
        }
        
        response = requests.post(content_url, headers=headers, json=body, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            cards = data.get('data', {}).get('cards', [])
            
            print(f"✅ Найдено карточек: {len(cards)}")
            
            # Extract barcodes
            all_barcodes = []
            
            for card in cards:
                nm_id = card.get('nmID')
                sizes = card.get('sizes', [])
                
                print(f"\n📦 Карточка nmID: {nm_id}")
                print(f"  Артикул продавца: {card.get('vendorCode')}")
                
                for size in sizes:
                    barcode = size.get('skus', [])
                    if barcode:
                        barcode_str = barcode[0]
                        all_barcodes.append(barcode_str)
                        print(f"  ├─ Размер: {size.get('techSize')}")
                        print(f"  └─ Баркод: {barcode_str}")
            
            if all_barcodes:
                print(f"\n✅ Всего баркодов: {len(all_barcodes)}")
                
                # Step 3: Get stocks for each warehouse
                for wh in warehouses:
                    wh_id = wh.get('id')
                    wh_name = wh.get('name')
                    
                    print(f"\n" + "="*100)
                    print(f"📦 Шаг 3: Запрашиваем остатки со склада: {wh_name} (ID: {wh_id})")
                    print("="*100)
                    
                    stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
                    
                    # Request with barcodes
                    body = {"skus": all_barcodes}
                    
                    print(f"📤 Отправляем запрос с {len(all_barcodes)} баркодами...")
                    print(f"Баркоды: {all_barcodes}")
                    
                    response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
                    
                    print(f"\n📥 Статус: {response.status_code}")
                    
                    if response.status_code == 200:
                        stocks_data = response.json()
                        stocks = stocks_data.get('stocks', [])
                        
                        print(f"✅ УСПЕХ! Получено остатков: {len(stocks)}")
                        
                        if stocks:
                            total_amount = sum(s.get('amount', 0) for s in stocks)
                            print(f"📊 Общее количество: {total_amount} шт")
                            
                            print("\nДетали:")
                            for stock in stocks:
                                sku = stock.get('sku')
                                amount = stock.get('amount', 0)
                                print(f"  - Баркод: {sku}, Остаток: {amount} шт")
                        else:
                            print("⚠️ Нет остатков для этих баркодов на складе")
                    
                    elif response.status_code == 400:
                        error = response.json()
                        print(f"❌ 400 Bad Request")
                        print(f"Ошибка: {json.dumps(error, indent=2, ensure_ascii=False)}")
                    
                    else:
                        print(f"❌ Ошибка {response.status_code}")
                        print(f"Ответ: {response.text[:500]}")
                
                # Try with empty array to get ALL stocks
                print(f"\n" + "="*100)
                print(f"📦 Шаг 4: Пробуем получить ВСЕ остатки (пустой массив баркодов)")
                print("="*100)
                
                for wh in warehouses:
                    wh_id = wh.get('id')
                    wh_name = wh.get('name')
                    
                    stocks_url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wh_id}"
                    body = {"skus": []}  # Empty array - should return all
                    
                    print(f"\n📤 Склад: {wh_name}")
                    response = requests.post(stocks_url, headers=headers, json=body, timeout=30)
                    
                    if response.status_code == 200:
                        stocks_data = response.json()
                        stocks = stocks_data.get('stocks', [])
                        total_amount = sum(s.get('amount', 0) for s in stocks)
                        
                        print(f"✅ Всего остатков: {len(stocks)}, Общее кол-во: {total_amount} шт")
                        
                        # Check for Its1_2_3
                        target_stocks = [s for s in stocks if any(b in s.get('sku', '') for b in all_barcodes)]
                        if target_stocks:
                            target_amount = sum(s.get('amount', 0) for s in target_stocks)
                            print(f"✅ Its1_2_3/50g найден: {len(target_stocks)} записей, {target_amount} шт")
                    else:
                        print(f"❌ Статус: {response.status_code}")
            
            else:
                print("❌ Не найдены баркоды в карточках")
        
        else:
            print(f"❌ Content API вернул: {response.status_code}")
            print(f"Ответ: {response.text[:500]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*100)

if __name__ == "__main__":
    main()
