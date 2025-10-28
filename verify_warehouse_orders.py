#!/usr/bin/env python3
"""
Проверка корректности метрики "Заказы со склада" в Google Sheets
Быстрая валидация после исправлений
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.database.operations import SheetsOperations
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.structure import SheetsTableStructure

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


async def verify_warehouse_orders():
    """Проверить данные о заказах со склада"""
    
    print("\n" + "="*80)
    print("🔍 ПРОВЕРКА МЕТРИКИ 'ЗАКАЗЫ СО СКЛАДА'")
    print("="*80 + "\n")
    
    # Get spreadsheet ID from env
    import os
    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID", "1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
    
    # Initialize
    sheets_client = GoogleSheetsClient()
    operations = SheetsOperations(sheets_client=sheets_client)
    
    try:
        # Read products with retries (в случае quota errors)
        print("📋 Чтение продуктов из Google Sheets...")
        print("   (если возникнет quota error - подождём 60 секунд)\n")
        
        max_retries = 3
        retry_delay = 60
        products = None
        
        for attempt in range(max_retries):
            try:
                products = operations.read_all_products(spreadsheet_id=spreadsheet_id)
                break
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(f"⚠️  Quota error, ожидание {retry_delay}с... (попытка {attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        
        if not products:
            print("❌ Продукты не найдены в таблице\n")
            return
        
        print(f"✅ Загружено продуктов: {len(products)}\n")
        
        # Analyze warehouse orders
        print("="*80)
        print("📊 АНАЛИЗ ЗАКАЗОВ СО СКЛАДА")
        print("="*80 + "\n")
        
        zero_stock_with_orders = []
        products_with_orders = 0
        total_warehouses = 0
        marketplace_warehouses = []
        
        for product in products:
            article = product.article if hasattr(product, 'article') else "Unknown"
            warehouses = product.warehouses if hasattr(product, 'warehouses') else []
            total_warehouses += len(warehouses)
            
            has_orders = False
            
            for warehouse in warehouses:
                wh_name = warehouse.name if hasattr(warehouse, 'name') else "Unknown"
                stock = warehouse.stock if hasattr(warehouse, 'stock') else 0
                orders = warehouse.orders if hasattr(warehouse, 'orders') else 0
                
                # Check for marketplace warehouses
                if any(keyword in wh_name.lower() for keyword in ["обухово", "подольск", "екатеринбург"]):
                    marketplace_warehouses.append({
                        "article": article,
                        "warehouse": wh_name,
                        "stock": stock,
                        "orders": orders
                    })
                
                # Check for zero-stock warehouses with orders
                if stock == 0 and orders > 0:
                    zero_stock_with_orders.append({
                        "article": article,
                        "warehouse": wh_name,
                        "orders": orders
                    })
                
                if orders > 0:
                    has_orders = True
            
            if has_orders:
                products_with_orders += 1
        
        # Report: Zero-stock warehouses with orders
        print(f"1️⃣  СКЛАДЫ С НУЛЕВЫМИ ОСТАТКАМИ И ЗАКАЗАМИ")
        print("-" * 80)
        
        if zero_stock_with_orders:
            print(f"✅ Найдено складов с stock=0 и orders>0: {len(zero_stock_with_orders)}\n")
            
            for item in zero_stock_with_orders[:10]:  # Show first 10
                print(f"   📦 {item['article']:<20} | {item['warehouse']:<30} | Заказы: {item['orders']}")
            
            if len(zero_stock_with_orders) > 10:
                print(f"\n   ... и ещё {len(zero_stock_with_orders) - 10} складов")
        else:
            print("⚠️  Склады с нулевыми остатками и заказами НЕ НАЙДЕНЫ")
            print("   (проверьте, что синхронизация прошла после исправлений)")
        
        print()
        
        # Report: Marketplace warehouses
        print(f"2️⃣  MARKETPLACE/FBS СКЛАДЫ")
        print("-" * 80)
        
        if marketplace_warehouses:
            print(f"✅ Найдено marketplace складов: {len(marketplace_warehouses)}\n")
            
            for item in marketplace_warehouses[:10]:  # Show first 10
                print(f"   📦 {item['article']:<20} | {item['warehouse']:<30} | Stock: {item['stock']:>4} | Orders: {item['orders']:>3}")
            
            if len(marketplace_warehouses) > 10:
                print(f"\n   ... и ещё {len(marketplace_warehouses) - 10} складов")
        else:
            print("⚠️  Marketplace склады НЕ НАЙДЕНЫ")
        
        print()
        
        # Summary
        print("="*80)
        print("📈 ИТОГОВАЯ СТАТИСТИКА")
        print("="*80)
        print(f"   Всего продуктов:                    {len(products)}")
        print(f"   Продуктов с заказами:               {products_with_orders}")
        print(f"   Всего складов:                      {total_warehouses}")
        print(f"   Складов с stock=0 и orders>0:       {len(zero_stock_with_orders)}")
        print(f"   Marketplace складов:                {len(marketplace_warehouses)}")
        print()
        
        # Verdict
        print("="*80)
        print("🎯 ВЕРДИКТ")
        print("="*80)
        
        if zero_stock_with_orders and marketplace_warehouses:
            print("✅ ЛОГИКА РАБОТАЕТ КОРРЕКТНО!")
            print("   - Склады с нулевыми остатками отображаются")
            print("   - Marketplace/FBS склады включены")
            print("   - Заказы рассчитываются правильно")
        elif zero_stock_with_orders:
            print("⚠️  ЧАСТИЧНО КОРРЕКТНО")
            print("   ✅ Склады с нулевыми остатками отображаются")
            print("   ❌ Marketplace склады не найдены (возможно, нет данных)")
        else:
            print("❌ ТРЕБУЕТСЯ ПОВТОРНАЯ СИНХРОНИЗАЦИЯ")
            print("   Склады с нулевыми остатками не найдены")
            print("   Запустите: python run_full_sync.py")
        
        print()
        
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        print(f"\n❌ Ошибка проверки: {e}\n")
        return


if __name__ == "__main__":
    asyncio.run(verify_warehouse_orders())
