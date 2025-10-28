#!/usr/bin/env python3
"""
Test new Dual API synchronization
"""

import asyncio
from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def main():
    print("\n" + "="*100)
    print("🧪 ТЕСТ: Dual API Synchronization")
    print("="*100)
    
    # Initialize service
    service = ProductService()
    
    # Run sync with new Dual API method
    print("\n🚀 Запуск sync_from_dual_api_to_sheets...")
    
    try:
        session = await service.sync_from_dual_api_to_sheets(skip_existence_check=False)
        
        print("\n" + "="*100)
        print("📊 РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ")
        print("="*100)
        print(f"Session ID:         {session.session_id}")
        print(f"Status:             {session.status}")
        print(f"Start Time:         {session.start_time}")
        print(f"End Time:           {session.end_time}")
        print(f"Duration:           {(session.end_time - session.start_time).total_seconds():.1f}s")
        print(f"Products Total:     {session.products_total}")
        print(f"Products Processed: {session.products_processed}")
        print(f"Products Failed:    {session.products_failed}")
        
        if session.errors:
            print(f"\n❌ Errors ({len(session.errors)}):")
            for error in session.errors[:10]:
                print(f"  - {error}")
            if len(session.errors) > 10:
                print(f"  ... and {len(session.errors) - 10} more")
        else:
            print("\n✅ No errors!")
        
        # Verify Its1_2_3/50g
        print("\n" + "="*100)
        print("🔍 ПРОВЕРКА: Its1_2_3/50g")
        print("="*100)
        
        from stock_tracker.database.operations import SheetsOperations
        from stock_tracker.database.sheets import GoogleSheetsClient
        from stock_tracker.utils.config import get_config
        
        config = get_config()
        sheets_client = GoogleSheetsClient()
        operations = SheetsOperations(sheets_client)
        
        product = operations.read_product(config.google_sheets.sheet_id, 'Its1_2_3/50g')
        
        if product:
            print(f"✅ Товар найден:")
            print(f"   Артикул продавца:    {product.seller_article}")
            print(f"   nmID:                {product.wildberries_article}")
            print(f"   FBO остаток:         {product.fbo_stock} шт")
            print(f"   FBS остаток:         {product.fbs_stock} шт")
            print(f"   ОБЩИЙ остаток:       {product.total_stock} шт")
            print(f"   Заказы:              {product.total_orders}")
            print(f"   Оборачиваемость:     {product.turnover}")
            print(f"   Последнее обновление: {product.last_updated}")
            
            # Verify numbers
            print(f"\n🎯 Ожидаемые значения:")
            print(f"   FBO: ~475 шт")
            print(f"   FBS: ~2984 шт")
            print(f"   Итого: ~3459 шт")
            
            if 3400 <= product.total_stock <= 3500:
                print(f"\n✅ УСПЕХ! Количество в норме: {product.total_stock} шт")
            else:
                print(f"\n⚠️ ВНИМАНИЕ! Количество не соответствует ожиданиям: {product.total_stock} шт")
        else:
            print("❌ Товар не найден в таблице!")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)
    print("✅ ТЕСТ ЗАВЕРШЕН")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(main())
