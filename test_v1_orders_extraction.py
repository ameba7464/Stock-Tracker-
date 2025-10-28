"""
Тестовый скрипт для проверки исправления извлечения заказов из V1 API
"""
import asyncio
import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_tracker.services.product_service import ProductService
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger


logger = get_logger(__name__)


async def main():
    """Тест извлечения заказов"""
    
    print("=" * 80)
    print("ТЕСТ ИСПРАВЛЕНИЯ ИЗВЛЕЧЕНИЯ ЗАКАЗОВ ИЗ V1 API")
    print("=" * 80)
    
    config = get_config()
    service = ProductService(config)
    
    try:
        print("\n1. Запуск синхронизации с API...")
        result = await service.sync_from_api_to_sheets()
        
        print(f"   ✓ Статус: {result.status}")
        print(f"   ✓ Продуктов обработано: {result.products_processed}")
        print(f"   ✓ Продуктов синхронизировано: {result.products_synced}")
        print(f"   ✓ Продуктов с ошибками: {len(result.errors)}")
        
        if result.errors:
            print(f"\n   ⚠️ Ошибки ({len(result.errors)}):")
            for error in result.errors[:5]:  # Первые 5 ошибок
                print(f"      - {error}")
        
        # Проверим данные в таблице
        print("\n2. Проверка данных в Google Sheets...")
        print("   ⏳ Ожидаем 10 секунд для восстановления API quota...")
        await asyncio.sleep(10)
        
        # Читаем продукты из таблицы напрямую
        spreadsheet = service.sheets_client._get_spreadsheet()
        worksheet = spreadsheet.worksheet("Stock Tracker")
        all_values = worksheet.get_all_values()
        
        # Пропускаем заголовок
        data_rows = all_values[1:] if len(all_values) > 1 else []
        
        print(f"   ✓ Прочитано строк: {len(data_rows)}")
        
        if not data_rows:
            print("   ✗ Нет данных в таблице!")
            return
        
        # Анализируем первые 5 продуктов
        print(f"\n3. Анализ данных продуктов:")
        print("-" * 80)
        
        for i, row in enumerate(data_rows[:5], 1):
            # Формат строки: [seller_article, wb_article, total_stock, total_orders, turnover, warehouses_json, last_sync, created_at]
            if len(row) < 4:
                print(f"\nПродукт #{i}: НЕДОСТАТОЧНО ДАННЫХ ({len(row)} колонок)")
                continue
                
            seller_article = row[0] if len(row) > 0 else "N/A"
            wb_article = row[1] if len(row) > 1 else "N/A"
            total_stock = row[2] if len(row) > 2 else "0"
            total_orders = row[3] if len(row) > 3 else "0"
            turnover = row[4] if len(row) > 4 else "0"
            
            print(f"\nПродукт #{i}: {seller_article}")
            print(f"  - Артикул WB: {wb_article}")
            print(f"  - Общий остаток: {total_stock}")
            print(f"  - Заказы: {total_orders} ← КРИТИЧЕСКОЕ ПОЛЕ")
            print(f"  - Оборачиваемость: {turnover}")
        
        # Итоговая статистика
        print("\n" + "=" * 80)
        print("ИТОГОВАЯ СТАТИСТИКА:")
        print("=" * 80)
        
        total_products = len(data_rows)
        
        # Подсчитываем продукты с заказами
        products_with_orders = 0
        for row in data_rows:
            if len(row) > 3:
                try:
                    orders = int(row[3]) if row[3] else 0
                    if orders > 0:
                        products_with_orders += 1
                except (ValueError, IndexError):
                    pass
        
        products_without_orders = total_products - products_with_orders
        
        print(f"Всего продуктов: {total_products}")
        print(f"С заказами (orders > 0): {products_with_orders}")
        print(f"Без заказов (orders = 0): {products_without_orders}")
        
        if products_without_orders == total_products:
            print("\n❌ ПРОБЛЕМА: Все продукты имеют 0 заказов!")
            print("   Исправление НЕ сработало")
        elif products_with_orders > 0:
            print(f"\n✅ УСПЕХ: {products_with_orders} продуктов имеют заказы!")
            print("   Исправление работает корректно")
            
            # Примеры продуктов с заказами
            print("\nПримеры продуктов с заказами:")
            count = 0
            for row in data_rows:
                if count >= 5:
                    break
                if len(row) > 3:
                    try:
                        orders = int(row[3]) if row[3] else 0
                        if orders > 0:
                            print(f"  - {row[0]}: {orders} заказов")
                            count += 1
                    except (ValueError, IndexError):
                        pass
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
