#!/usr/bin/env python3
"""
Test Statistics API /api/v1/supplier/stocks endpoint
This might return ALL stocks including "Маркетплейс"
"""

import sys
import os
import requests
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.utils.config import get_config

def main():
    config = get_config()
    
    print("\n" + "="*100)
    print("🔍 ТЕСТ: Statistics API /api/v1/supplier/stocks")
    print("="*100)
    
    # Statistics API endpoint
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
    
    # Query parameter: dateFrom (required)
    params = {
        'dateFrom': '2025-10-27'  # Yesterday
    }
    
    headers = {
        'Authorization': config.wildberries_api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"\n📡 URL: {url}")
    print(f"📅 dateFrom: {params['dateFrom']}")
    print(f"🔑 API Key: {config.wildberries_api_key[:20]}...")
    
    try:
        print("\n⏳ Отправляем запрос...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"✅ Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 Получено записей: {len(data)}")
            
            # Find Its1_2_3/50g
            target_product = None
            for record in data:
                if record.get('supplierArticle') == 'Its1_2_3/50g':
                    target_product = record
                    break
            
            if target_product:
                print("\n✅ Товар Its1_2_3/50g НАЙДЕН!")
                print("\n" + "-"*100)
                print("📦 ПОЛНАЯ СТРУКТУРА:")
                print("-"*100)
                print(json.dumps(target_product, indent=2, ensure_ascii=False))
                print("-"*100)
                
                # Analyze fields
                print("\n🔍 АНАЛИЗ ПОЛЕЙ:")
                print("-"*100)
                
                quantity_fields = {k: v for k, v in target_product.items() 
                                 if 'quantity' in k.lower() or 'stock' in k.lower() or 'qty' in k.lower()}
                
                if quantity_fields:
                    print("Поля с количеством:")
                    for key, value in quantity_fields.items():
                        print(f"  - {key}: {value}")
                else:
                    print("⚠️ Нет полей с quantity/stock")
                
                # Check warehouse field
                warehouse_fields = {k: v for k, v in target_product.items() 
                                   if 'warehouse' in k.lower() or 'склад' in k.lower()}
                
                if warehouse_fields:
                    print("\nПоля со складом:")
                    for key, value in warehouse_fields.items():
                        print(f"  - {key}: {value}")
                
                # Total stock
                total_stock = target_product.get('quantity', 0)
                print(f"\n📈 Общие остатки: {total_stock:,} шт")
                
                if total_stock >= 3000:
                    print("✅ УСПЕХ! Это близко к ожидаемым 3,478 шт!")
                elif total_stock == 475:
                    print("⚠️ Это тот же результат, что и warehouse_remains API")
                else:
                    print(f"⚠️ Неожиданное значение: {total_stock}")
                
            else:
                print("\n❌ Товар Its1_2_3/50g НЕ найден")
                print("\n📋 Первые 3 товара в ответе:")
                for i, record in enumerate(data[:3], 1):
                    article = record.get('supplierArticle', 'Unknown')
                    qty = record.get('quantity', 0)
                    print(f"  {i}. {article} - {qty} шт")
            
            # Check if there are multiple records per product (one per warehouse)
            articles = {}
            for record in data:
                article = record.get('supplierArticle')
                if article:
                    articles[article] = articles.get(article, 0) + 1
            
            multi_records = {k: v for k, v in articles.items() if v > 1}
            if multi_records:
                print(f"\n💡 Товары с несколькими записями (по складам):")
                for article, count in list(multi_records.items())[:5]:
                    print(f"  - {article}: {count} записей")
            
        elif response.status_code == 401:
            print("❌ Ошибка аутентификации (401)")
            print("   Возможно, нужен другой API ключ для Statistics API")
        
        elif response.status_code == 403:
            print("❌ Доступ запрещен (403)")
            print("   Возможно, требуется отдельный токен для Statistics API")
        
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"   Ответ: {response.text[:500]}")
    
    except requests.exceptions.Timeout:
        print("❌ Таймаут запроса (30 сек)")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n" + "="*100)
    print("💡 ВЫВОДЫ:")
    print("="*100)
    print("\nStatistics API - это отдельный API от Wildberries:")
    print("  - Может требовать отдельный токен")
    print("  - Обычно используется для отчетности и статистики")
    print("  - Возможно, возвращает более полные данные о остатках")
    print("\nЕсли этот API работает и возвращает ~3,478 шт:")
    print("  ✅ Это решение проблемы с 'Маркетплейс' складом")
    print("  ✅ Можно переключиться на этот endpoint")

if __name__ == "__main__":
    main()
