#!/usr/bin/env python3
"""
Скрипт для повторной синхронизации с задержкой для восстановления API quota.
"""

import asyncio
import time

async def wait_and_sync():
    """Ждем восстановления quota и запускаем синхронизацию"""
    
    print("="*80)
    print("🔧 ИСПРАВЛЕНИЕ ПРИМЕНЕНО")
    print("="*80)
    
    print("\n✅ Исправлена ошибка:")
    print("   'GoogleSheetsClient' object has no attribute 'service'")
    print("\n📝 Изменения:")
    print("   - performance.py: Заменен доступ к service.spreadsheets()")
    print("   - Теперь используется gspread.Client напрямую")
    print("   - Batch операции адаптированы под gspread API")
    
    print("\n⏳ Ожидание восстановления Google Sheets API quota...")
    print("   Таймер: 90 секунд (рекомендуемое время)")
    
    for remaining in range(90, 0, -10):
        print(f"   Осталось: {remaining} секунд...", end="\r")
        await asyncio.sleep(10)
    
    print("\n\n" + "="*80)
    print("✅ QUOTA ВОССТАНОВЛЕНА - ЗАПУСК СИНХРОНИЗАЦИИ")
    print("="*80)
    
    # Импортируем после ожидания
    from stock_tracker.services.product_service import ProductService
    
    print("\n🚀 Инициализация ProductService...")
    service = ProductService()
    
    print("\n📊 Запуск API-to-Sheets синхронизации...")
    result = await service.sync_from_api_to_sheets()
    
    print("\n" + "="*80)
    print("📈 РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ")
    print("="*80)
    
    if result.status.value == "completed":
        print(f"\n✅ УСПЕХ!")
        print(f"   Обработано: {result.products_synced} продуктов")
        print(f"   Время: {result.duration:.1f} секунд")
        
        if result.errors:
            print(f"\n⚠️  Предупреждения: {len(result.errors)} ошибок")
            for error in result.errors[:5]:
                print(f"      - {error}")
    else:
        print(f"\n⚠️  Статус: {result.status.value}")
        print(f"   Обработано: {result.products_synced}/{result.total_products}")
        
        if result.errors:
            print(f"\n❌ Ошибки ({len(result.errors)}):")
            for error in result.errors[:10]:
                print(f"      - {error}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(wait_and_sync())
