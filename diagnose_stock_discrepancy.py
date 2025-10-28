#!/usr/bin/env python3
"""
Диагностика расхождения остатков для Its1_2_3/50g (nmId: 163383326)

Проблема: 
- WB показывает 3,459 остатков (всего) + 2,984 МП
- Таблица показывает 475 остатков (всего)

Причина:
- Warehouse API v1 возвращает ТОЛЬКО остатки на складах WB (FBO)
- НЕ включает остатки FBS/МП (на складе продавца)
- Analytics API v2 возвращает ПОЛНЫЕ остатки (FBO + FBS/МП)

Решение:
- Использовать Analytics API v2 для total_stock
- Использовать Warehouse API v1 для breakdown по складам FBO
- Добавить отдельную строку "МП/FBS" с остатками = total_stock - sum(FBO stocks)
"""

import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.utils.config import get_config
from stock_tracker.api.client import WildberriesAPIClient
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def diagnose_stock_discrepancy():
    """Диагностика расхождения остатков для Its1_2_3/50g"""
    
    print("\n" + "=" * 80)
    print("🔍 ДИАГНОСТИКА РАСХОЖДЕНИЯ ОСТАТКОВ")
    print("=" * 80)
    print(f"Товар: Its1_2_3/50g")
    print(f"WB Article (nmId): 163383326")
    print(f"Проблема: Остатки в таблице (475) != Остатки на WB (3,459)")
    print("=" * 80)
    
    config = get_config()
    wb_client = WildberriesAPIClient(config)
    
    target_nm_id = 163383326
    target_vendor_code = "Its1_2_3/50g"
    
    # 1. Получаем данные из Warehouse API v1 (текущий источник)
    print("\n📦 ШАГ 1: Warehouse API v1 (текущий источник данных)")
    print("-" * 80)
    
    try:
        task_id = await wb_client.create_warehouse_remains_task()
        print(f"✅ Создана задача: {task_id}")
        print("⏳ Ожидание 60 секунд для обработки...")
        await asyncio.sleep(60)
        
        warehouse_data = await wb_client.download_warehouse_remains(task_id)
        print(f"✅ Получено записей: {len(warehouse_data)}")
        
        # Находим наш товар
        target_product_v1 = None
        for item in warehouse_data:
            if item.get('nmId') == target_nm_id:
                target_product_v1 = item
                break
        
        if target_product_v1:
            print(f"\n✅ Найден товар в Warehouse API v1:")
            print(f"   nmId: {target_product_v1.get('nmId')}")
            print(f"   vendorCode: {target_product_v1.get('vendorCode')}")
            
            warehouses_v1 = target_product_v1.get('warehouses', [])
            print(f"\n   Склады ({len(warehouses_v1)}):")
            
            total_v1_stock = 0
            fbo_stock = 0
            
            for wh in warehouses_v1:
                wh_name = wh.get('warehouseName', '')
                wh_qty = wh.get('quantity', 0)
                
                print(f"   - {wh_name:<40} {wh_qty:>6}")
                
                # Считаем только реальные склады (не служебные)
                if wh_name not in ("В пути до получателей", "В пути возвраты на склад WB", 
                                   "Всего находится на складах"):
                    fbo_stock += wh_qty
                
                total_v1_stock += wh_qty
            
            print(f"\n   📊 ИТОГО из Warehouse API v1:")
            print(f"   - Всего записей в warehouses: {total_v1_stock}")
            print(f"   - FBO остатки (реальные склады): {fbo_stock}")
        else:
            print(f"❌ Товар НЕ найден в Warehouse API v1")
            
    except Exception as e:
        print(f"❌ Ошибка Warehouse API v1: {e}")
        warehouse_data = []
        target_product_v1 = None
        fbo_stock = 0
    
    # 2. Получаем данные из Analytics API v2 (полные остатки)
    print("\n📊 ШАГ 2: Analytics API v2 (полные остатки FBO + FBS)")
    print("-" * 80)
    
    try:
        analytics_data = await wb_client.get_all_product_stock_data()
        print(f"✅ Получено записей: {len(analytics_data)}")
        
        # Находим наш товар
        target_product_v2 = None
        for item in analytics_data:
            if item.get('nmID') == target_nm_id:
                target_product_v2 = item
                break
        
        if target_product_v2:
            print(f"\n✅ Найден товар в Analytics API v2:")
            print(f"   nmID: {target_product_v2.get('nmID')}")
            print(f"   vendorCode: {target_product_v2.get('vendorCode')}")
            
            metrics = target_product_v2.get('metrics', {})
            total_v2_stock = metrics.get('stockCount', 0)
            total_v2_orders = metrics.get('ordersCount', 0)
            
            print(f"\n   📊 МЕТРИКИ из Analytics API v2:")
            print(f"   - stockCount (всего остатков): {total_v2_stock}")
            print(f"   - ordersCount (всего заказов): {total_v2_orders}")
        else:
            print(f"❌ Товар НЕ найден в Analytics API v2")
            total_v2_stock = 0
            total_v2_orders = 0
            
    except Exception as e:
        print(f"❌ Ошибка Analytics API v2: {e}")
        total_v2_stock = 0
        total_v2_orders = 0
    
    # 3. Анализ расхождения
    print("\n🔍 ШАГ 3: АНАЛИЗ РАСХОЖДЕНИЯ")
    print("=" * 80)
    
    if target_product_v1 and target_product_v2:
        print(f"\n📊 Сравнение источников данных:")
        print(f"   Analytics API v2 (полные остатки):  {total_v2_stock:>6}")
        print(f"   Warehouse API v1 (FBO остатки):     {fbo_stock:>6}")
        print(f"   Разница (FBS/МП остатки):           {total_v2_stock - fbo_stock:>6}")
        
        fbs_stock = total_v2_stock - fbo_stock
        fbs_percentage = (fbs_stock / total_v2_stock * 100) if total_v2_stock > 0 else 0
        
        print(f"\n💡 ВЫВОД:")
        print(f"   ✅ FBO (склады WB):     {fbo_stock:>6} ({100 - fbs_percentage:.1f}%)")
        print(f"   ✅ FBS/МП (свой склад): {fbs_stock:>6} ({fbs_percentage:.1f}%)")
        print(f"   📦 ВСЕГО:               {total_v2_stock:>6} (100%)")
        
        print(f"\n🎯 РЕКОМЕНДАЦИЯ:")
        print(f"   1. Использовать Analytics API v2 для total_stock ({total_v2_stock})")
        print(f"   2. Использовать Warehouse API v1 для breakdown по FBO складам")
        print(f"   3. Добавить отдельную строку 'МП/FBS' с остатками {fbs_stock}")
        
    else:
        print(f"❌ Недостаточно данных для анализа")
    
    print("\n" + "=" * 80)
    print("✅ ДИАГНОСТИКА ЗАВЕРШЕНА")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_stock_discrepancy())
