"""
Тестирование критических исправлений метрики "Заказы со склада"

Проверяем:
1. Фильтрацию отменённых заказов (isCancel=True)
2. Дедупликацию по srid
3. Нормализацию названий складов
4. Использование фиксированного периода (начало недели)
5. Детальное логирование

Дата: 28.10.2025
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.utils.config import StockTrackerConfig
from stock_tracker.services.product_service import ProductService


async def test_critical_fixes():
    """Тест критических исправлений"""
    
    print("=" * 70)
    print("TESTING CRITICAL FIXES - ORDERS METRIC")
    print("=" * 70)
    print()
    
    # Load config
    print("Loading configuration...")
    config = StockTrackerConfig()
    
    # Initialize service
    print("Initializing ProductService...")
    service = ProductService(config)
    
    print()
    print("=" * 70)
    print("STARTING FULL SYNCHRONIZATION")
    print("=" * 70)
    print()
    print("Expected improvements:")
    print("  [+] Cancelled orders filtered (~28 orders)")
    print("  [+] Duplicates removed (if any)")
    print("  [+] Warehouse names normalized")
    print("  [+] Fixed period (week start)")
    print("  [+] Detailed statistics in logs")
    print()
    
    # Run sync
    try:
        session = await service.sync_from_api_to_sheets()
        
        print()
        print("=" * 70)
        print("SYNCHRONIZATION RESULTS")
        print("=" * 70)
        print()
        print(f"Status: {session.status}")
        print(f"Products processed: {session.products_processed}")
        print(f"Errors: {session.products_failed}")
        
        if session.errors:
            print()
            print("Errors:")
            for error in session.errors[:5]:
                print(f"  - {error}")
        
        print()
        print("=" * 70)
        print("TESTING COMPLETED")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Check logs above for order statistics")
        print("  2. Verify cancelled orders are filtered")
        print("  3. Check Google Sheets for updated data")
        print("  4. Compare with WB export (22-28 Oct)")
        print()
        
    except Exception as e:
        print()
        print("=" * 70)
        print("SYNCHRONIZATION ERROR")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_critical_fixes())
