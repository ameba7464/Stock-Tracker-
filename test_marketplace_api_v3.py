#!/usr/bin/env python3
"""
Test Marketplace API v3 for FBS stocks
This should return the missing "Маркетплейс" warehouse stocks
"""

import requests
import json
from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    print("\n" + "="*100)
    print("🔍 ТЕСТ: Marketplace API v3 для FBS остатков")
    print("="*100)
    
    # First, we need to get warehouse IDs
    # Let's try the stocks endpoint without warehouseId to see what happens
    
    base_url = "https://marketplace-api.wildberries.ru/api/v3/stocks"
    
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"\n📡 Base URL: {base_url}")
    print(f"🔑 API Key: {config.wildberries_api_key[:20]}...")
    
    # Try to get all stocks (without specific warehouseId)
    print("\n⏳ Попытка 1: GET all stocks...")
    try:
        response = requests.get(base_url, headers=headers, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Получено записей: {len(data) if isinstance(data, list) else 'N/A'}")
            
            # Look for Its1_2_3/50g
            if isinstance(data, list):
                target = [r for r in data if r.get('vendorCode') == 'Its1_2_3/50g' or r.get('supplierArticle') == 'Its1_2_3/50g']
                
                if target:
                    print(f"\n✅ Найдено записей для Its1_2_3/50g: {len(target)}")
                    print("\nПервая запись:")
                    print(json.dumps(target[0], indent=2, ensure_ascii=False))
                    
                    # Sum up quantities
                    total = sum(r.get('quantity', 0) for r in target)
                    print(f"\n📊 Общие остатки: {total:,} шт")
                    
                    if total >= 2500:
                        print("✅ УСПЕХ! Это близко к ожидаемым 2,993 шт из 'Маркетплейс'!")
                else:
                    print("\n⚠️ Its1_2_3/50g не найден")
                    print("Примеры товаров:")
                    for i, r in enumerate(data[:3], 1):
                        vendor = r.get('vendorCode') or r.get('supplierArticle', 'Unknown')
                        qty = r.get('quantity', 0)
                        print(f"  {i}. {vendor} - {qty} шт")
            else:
                print("Структура данных:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
        
        elif response.status_code == 401:
            print("❌ Ошибка аутентификации (401)")
            print("   Marketplace API может требовать другой тип токена")
        
        elif response.status_code == 404:
            print("⚠️ 404 - Endpoint не найден")
            print("   Возможно, требуется указать warehouseId в URL")
        
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"Ответ: {response.text[:500]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Try POST method
    print("\n⏳ Попытка 2: POST with body...")
    try:
        # Try with empty body or minimal body
        body = {}
        response = requests.post(base_url, headers=headers, json=body, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Получено данных")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
        else:
            print(f"Ответ: {response.text[:500]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    # Try to get warehouses list first
    print("\n⏳ Попытка 3: Получить список FBS складов...")
    warehouses_url = "https://marketplace-api.wildberries.ru/api/v3/warehouses"
    
    try:
        response = requests.get(warehouses_url, headers=headers, timeout=30)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            warehouses = response.json()
            print(f"✅ Получено складов: {len(warehouses) if isinstance(warehouses, list) else 'N/A'}")
            
            if isinstance(warehouses, list):
                print("\nFBS склады:")
                for wh in warehouses:
                    wh_id = wh.get('id') or wh.get('warehouseId')
                    wh_name = wh.get('name') or wh.get('warehouseName')
                    print(f"  - ID: {wh_id}, Name: {wh_name}")
                    
                    # Check if "Маркетплейс" is in the list
                    if wh_name and 'маркетплейс' in wh_name.lower():
                        print(f"    ⭐ НАЙДЕН СКЛАД МАРКЕТПЛЕЙС!")
                
                # Try to get stocks for first warehouse
                if warehouses:
                    first_wh_id = warehouses[0].get('id') or warehouses[0].get('warehouseId')
                    if first_wh_id:
                        print(f"\n⏳ Попытка 4: Получить остатки для склада ID={first_wh_id}...")
                        stocks_url = f"{base_url}/{first_wh_id}"
                        response = requests.post(stocks_url, headers=headers, json={}, timeout=30)
                        print(f"Статус: {response.status_code}")
                        
                        if response.status_code == 200:
                            stocks = response.json()
                            print(f"✅ Получено остатков: {len(stocks) if isinstance(stocks, list) else 'N/A'}")
                            
                            if isinstance(stocks, list) and stocks:
                                print("\nПримеры остатков:")
                                for s in stocks[:3]:
                                    print(json.dumps(s, indent=2, ensure_ascii=False))
        else:
            print(f"Ответ: {response.text[:500]}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n" + "="*100)
    print("💡 СЛЕДУЮЩИЕ ШАГИ:")
    print("="*100)
    print("\n1. Если Marketplace API работает:")
    print("   ✅ Получить список FBS складов")
    print("   ✅ Для каждого склада запросить остатки")
    print("   ✅ Агрегировать с FBO остатками из Statistics API")
    print("\n2. Если требуется другой токен:")
    print("   📧 Проверить документацию WB на тип токена для Marketplace API")
    print("   🔑 Возможно нужен отдельный API ключ для FBS")

if __name__ == "__main__":
    main()
