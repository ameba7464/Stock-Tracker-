"""
Проверка дедупликации заказов после применения исправлений.
Использует встроенные инструменты Stock Tracker.
"""

import asyncio
from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


# Эталонные данные из WB API
WB_REFERENCE = {
    "Its1_2_3/50g": {"orders": 7, "stock": 192},
    "Its2/50g": {"orders": 9, "stock": 132},
    "ItsSport2/50g": {"orders": 5, "stock": 185}
}


async def check_updated_products():
    """Проверка обновленных продуктов"""
    
    print("\n" + "=" * 70)
    print("🔍 ПРОВЕРКА ДЕДУПЛИКАЦИИ ЗАКАЗОВ")
    print("=" * 70)
    
    # Инициализация
    sheets_client = GoogleSheetsClient("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
    operations = SheetsOperations(sheets_client)
    
    # Даем API восстановиться
    print("\n⏳ Ожидание 60 секунд для восстановления Google Sheets API quota...")
    await asyncio.sleep(60)
    
    try:
        print("\n📊 Читаем обновленные данные из Google Sheets...")
        
        # Читаем все продукты
        products = await operations.read_all_products("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
        
        print(f"✅ Прочитано продуктов: {len(products)}")
        print("\n" + "=" * 70)
        
        issues_found = []
        success_count = 0
        
        # Проверяем каждый обновленный продукт
        for product in products:
            if product.seller_article in WB_REFERENCE:
                expected = WB_REFERENCE[product.seller_article]
                
                print(f"\n🔎 {product.seller_article}")
                print(f"   📦 Остаток: {product.total_stock}")
                print(f"   📋 Заказов: {product.total_orders}")
                
                orders_match = product.total_orders == expected["orders"]
                stock_match = product.total_stock == expected["stock"]
                
                if orders_match and stock_match:
                    print(f"   ✅ УСПЕХ: Данные совпадают с WB API")
                    success_count += 1
                else:
                    issue = {
                        "article": product.seller_article,
                        "orders": {
                            "sheets": product.total_orders,
                            "wb": expected["orders"],
                            "match": orders_match
                        },
                        "stock": {
                            "sheets": product.total_stock,
                            "wb": expected["stock"],
                            "match": stock_match
                        }
                    }
                    issues_found.append(issue)
                    
                    if not orders_match:
                        diff = product.total_orders - expected["orders"]
                        pct = (diff / expected["orders"] * 100) if expected["orders"] > 0 else 0
                        print(f"   ❌ ЗАКАЗЫ: Sheets={product.total_orders}, WB={expected['orders']}, "
                              f"Разница={diff:+d} ({pct:+.1f}%)")
                    
                    if not stock_match:
                        diff = product.total_stock - expected["stock"]
                        pct = (diff / expected["stock"] * 100) if expected["stock"] > 0 else 0
                        print(f"   ⚠️  ОСТАТОК: Sheets={product.total_stock}, WB={expected['stock']}, "
                              f"Разница={diff:+d} ({pct:+.1f}%)")
        
        # Итоговый отчет
        print("\n" + "=" * 70)
        print(f"\n📈 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
        print(f"   ✅ Проверено продуктов: 3")
        print(f"   🎯 Совпадений с WB API: {success_count}/3")
        
        if issues_found:
            print(f"\n   ❌ Обнаружено проблем: {len(issues_found)}")
            print("\n📋 ДЕТАЛИ ПРОБЛЕМ:")
            for issue in issues_found:
                print(f"\n   • {issue['article']}:")
                if not issue['orders']['match']:
                    print(f"     - Заказы: {issue['orders']['sheets']} вместо {issue['orders']['wb']}")
                if not issue['stock']['match']:
                    print(f"     - Остаток: {issue['stock']['sheets']} вместо {issue['stock']['wb']}")
        else:
            print("\n   🎉 ВСЕ ДАННЫЕ КОРРЕКТНЫ!")
            print("   ✅ Дедупликация заказов работает правильно")
            
        print("\n" + "=" * 70)
        
        return len(issues_found) == 0
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(check_updated_products())
    exit(0 if success else 1)
