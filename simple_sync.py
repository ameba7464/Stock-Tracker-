"""
Простая синхронизация данных без emoji
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.services.daily_sync import DailySyncService
from stock_tracker.utils.config import get_config

async def simple_sync():
    """Простая синхронизация"""
    
    print("\n" + "="*100)
    print("СИНХРОНИЗАЦИЯ ДАННЫХ С WILDBERRIES API")
    print("="*100)
    
    config = get_config()
    
    sync_service = DailySyncService(config)
    
    print("\nЗапуск синхронизации...")
    
    try:
        result = await sync_service.run_sync()
        
        print("\n" + "-"*100)
        print("РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ:")
        print("-"*100)
        
        if result.get('success'):
            print(f"[OK] Синхронизация завершена успешно")
            print(f"Синхронизировано продуктов: {result.get('products_synced', 0)}")
            print(f"Время выполнения: {result.get('execution_time', 0):.2f} сек")
        else:
            print(f"[ERROR] Синхронизация завершилась с ошибкой")
            print(f"Ошибка: {result.get('error', 'Unknown error')}")
        
        print("="*100 + "\n")
        
        return result.get('success', False)
    
    except Exception as e:
        print(f"\n[ERROR] Ошибка при синхронизации: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = asyncio.run(simple_sync())
    sys.exit(0 if success else 1)
