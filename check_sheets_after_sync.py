"""
Скрипт для проверки данных в Google Sheets после синхронизации
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


async def check_sheets_data():
    """Проверить данные в Google Sheets"""
    
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ДАННЫХ В GOOGLE SHEETS")
    print("=" * 80)
    
    # Initialize service
    service = ProductService()
    
    print("\n1. Получаем сводку из таблицы...")
    summary = service.get_inventory_summary()
    
    print(f"✅ Данные получены\n")
    
    print("=" * 80)
    print("📊 СВОДКА ДАННЫХ В GOOGLE SHEETS")
    print("=" * 80)
    print(f"\nВсего продуктов: {summary['total_products']}")
    print(f"Всего заказов: {summary['total_orders']}")
    print(f"Всего остатков: {summary['total_stock']}")
    print(f"Средняя оборачиваемость: {summary['average_turnover']:.3f}")
    print(f"Продуктов с низкой оборачиваемостью: {summary['low_stock_count']}")
    print(f"Продуктов требующих пополнения: {summary['replenishment_needed_count']}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(check_sheets_data())
