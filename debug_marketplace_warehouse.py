#!/usr/bin/env python3
"""
Debug script to inspect actual API response structure for warehouse_remains
Specifically looking for "Маркетплейс" warehouse and additional quantity fields
"""

import sys
import os
import asyncio
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.config import get_config

async def main():
    config = get_config()
    client = WildberriesAPIClient(config)
    
    print("\n" + "="*100)
    print("🔍 ИССЛЕДОВАНИЕ API: Структура данных warehouse_remains")
    print("="*100)
    
    # Create task
    print("\n1️⃣ Создаём задачу warehouse_remains...")
    task_id = await client.create_warehouse_remains_task()
    print(f"✅ Task ID: {task_id}")
    
    # Wait for processing
    print("\n2️⃣ Ждём 60 секунд обработки задачи...")
    await asyncio.sleep(60)
    
    # Download data
    print("\n3️⃣ Скачиваем данные...")
    data = await client.download_warehouse_remains(task_id)
    print(f"✅ Получено {len(data)} товаров")
    
    # Find Its1_2_3/50g
    print("\n4️⃣ Ищем товар Its1_2_3/50g...")
    target_product = None
    for record in data:
        if record.get('vendorCode') == 'Its1_2_3/50g':
            target_product = record
            break
    
    if not target_product:
        print("❌ Товар Its1_2_3/50g не найден в API ответе!")
        print("\n📋 Доступные товары:")
        for i, record in enumerate(data[:5], 1):
            print(f"   {i}. {record.get('vendorCode', 'Unknown')}")
        return
    
    print("✅ Товар найден!\n")
    
    # Analyze structure
    print("="*100)
    print("📦 ПОЛНАЯ СТРУКТУРА ЗАПИСИ API:")
    print("="*100)
    print(json.dumps(target_product, indent=2, ensure_ascii=False))
    
    # Analyze warehouses
    print("\n" + "="*100)
    print("🏢 АНАЛИЗ СКЛАДОВ:")
    print("="*100)
    
    warehouses = target_product.get('warehouses', [])
    print(f"\nВсего складов в API ответе: {len(warehouses)}")
    
    if not warehouses:
        print("❌ Массив warehouses пуст!")
        return
    
    # Check if "Маркетплейс" exists
    marketplace_found = False
    total_quantity = 0
    
    print("\n" + "-"*100)
    print(f"{'№':<5} {'Склад':<40} {'Quantity':<15} {'Дополнительные поля'}")
    print("-"*100)
    
    for i, wh in enumerate(warehouses, 1):
        name = wh.get('warehouseName', 'Unknown')
        quantity = wh.get('quantity', 0)
        
        # Check for additional fields
        additional_fields = []
        for key in wh.keys():
            if key not in ['warehouseName', 'quantity']:
                additional_fields.append(f"{key}={wh[key]}")
        
        additional_str = ", ".join(additional_fields) if additional_fields else "-"
        
        print(f"{i:<5} {name:<40} {quantity:<15,} {additional_str}")
        
        total_quantity += quantity
        
        if "маркетплейс" in name.lower() or "marketplace" in name.lower():
            marketplace_found = True
            print(f"{'':>5} ⭐ НАЙДЕН СКЛАД 'МАРКЕТПЛЕЙС'!")
    
    print("-"*100)
    print(f"ИТОГО quantity: {total_quantity:,} шт")
    print("-"*100)
    
    # Analysis results
    print("\n" + "="*100)
    print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print("="*100)
    
    if marketplace_found:
        print("\n✅ Склад 'Маркетплейс' НАЙДЕН в API ответе")
        print("   → Проблема в фильтрации кода (убираем из blacklist)")
    else:
        print("\n❌ Склад 'Маркетплейс' НЕ НАЙДЕН в API ответе")
        print("   → Проблема в самом API или нужен другой endpoint")
    
    print(f"\n📈 API вернул: {total_quantity:,} шт")
    print(f"📋 CSV показывает: 3,478 шт")
    print(f"❌ Разница: {3478 - total_quantity:,} шт ({((3478 - total_quantity) / 3478 * 100):.1f}%)")
    
    # Check for additional quantity fields
    print("\n" + "="*100)
    print("🔎 ПРОВЕРКА ДОПОЛНИТЕЛЬНЫХ ПОЛЕЙ QUANTITY:")
    print("="*100)
    
    if warehouses:
        sample_wh = warehouses[0]
        print(f"\nПример структуры warehouse (первый склад):")
        print(json.dumps(sample_wh, indent=2, ensure_ascii=False))
        
        # Look for quantity-related fields
        quantity_fields = [k for k in sample_wh.keys() if 'quantity' in k.lower() or 'orders' in k.lower() or 'stock' in k.lower()]
        
        if len(quantity_fields) > 1:
            print(f"\n✅ Найдены дополнительные поля с quantity: {quantity_fields}")
            print("   → Возможно нужно суммировать несколько полей")
        else:
            print(f"\n⚠️ Найдено только поле: {quantity_fields}")
            print("   → Нужно искать другой API endpoint")
    
    print("\n" + "="*100)
    print("💡 РЕКОМЕНДАЦИИ:")
    print("="*100)
    
    if marketplace_found:
        print("\n1. Убрать 'Маркетплейс' из списка фильтруемых складов")
        print("2. Пересинхронизировать данные")
        print("3. Проверить, что остатки теперь показывают ~3,478 шт")
    else:
        print("\n1. API не возвращает склад 'Маркетплейс'")
        print("2. Исследовать альтернативные endpoints:")
        print("   - /api/v2/stocks")
        print("   - /api/v1/supplier/stocks")
        print("3. Проверить документацию WB на наличие полей:")
        print("   - quantityInOrders")
        print("   - quantityInTransit")
        print("   - marketplaceQuantity")

if __name__ == "__main__":
    asyncio.run(main())
