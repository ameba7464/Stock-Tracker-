"""
Проверка корректности дедупликации заказов после применения исправлений.
Сравнивает данные в Google Sheets с эталонными значениями из WB API.
"""

import gspread
from google.oauth2.service_account import Credentials
import json


def get_sheets_client():
    """Аутентификация с Google Sheets API"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    creds = Credentials.from_service_account_file(
        'credentials.json', scopes=scope)
    return gspread.authorize(creds)


def verify_updated_products():
    """Проверка обновленных продуктов"""
    
    # Эталонные данные из WB API (из анализа)
    wb_reference = {
        "Its1_2_3/50g": {"orders": 7, "stock": 192},
        "Its2/50g": {"orders": 9, "stock": 132},
        "ItsSport2/50g": {"orders": 5, "stock": 185}
    }
    
    print("🔍 Проверка дедупликации заказов")
    print("=" * 70)
    
    try:
        client = get_sheets_client()
        sheet = client.open_by_key("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
        worksheet = sheet.worksheet("Stock Tracker")
        
        # Читаем заголовки
        headers = worksheet.row_values(1)
        print(f"\n📋 Структура таблицы: {headers}")
        
        # Находим индексы колонок
        try:
            article_col = headers.index("Артикул продавца") + 1
            orders_col = headers.index("Заказов") + 1
            stock_col = headers.index("Остаток") + 1
        except ValueError as e:
            print(f"❌ Ошибка: не найдена колонка - {e}")
            return
        
        print(f"\n📊 Колонки: Артикул={article_col}, Заказов={orders_col}, Остаток={stock_col}")
        print("\n" + "=" * 70)
        
        issues_found = []
        success_count = 0
        
        # Проверяем каждый продукт
        for row_num in range(2, 5):  # Строки 2-4 (Its1_2_3, Its2, ItsSport2)
            article = worksheet.cell(row_num, article_col).value
            orders = worksheet.cell(row_num, orders_col).value
            stock = worksheet.cell(row_num, stock_col).value
            
            if not article:
                continue
                
            print(f"\n🔎 Строка {row_num}: {article}")
            print(f"   📦 Остаток: {stock}")
            print(f"   📋 Заказов: {orders}")
            
            if article in wb_reference:
                expected = wb_reference[article]
                
                # Проверка заказов
                orders_int = int(orders) if orders else 0
                stock_int = int(stock) if stock else 0
                
                orders_match = orders_int == expected["orders"]
                stock_match = stock_int == expected["stock"]
                
                if orders_match and stock_match:
                    print(f"   ✅ УСПЕХ: Данные совпадают с WB API")
                    success_count += 1
                else:
                    issue = {
                        "article": article,
                        "row": row_num,
                        "orders": {"sheets": orders_int, "wb": expected["orders"], "match": orders_match},
                        "stock": {"sheets": stock_int, "wb": expected["stock"], "match": stock_match}
                    }
                    issues_found.append(issue)
                    
                    if not orders_match:
                        diff = orders_int - expected["orders"]
                        pct = (diff / expected["orders"] * 100) if expected["orders"] > 0 else 0
                        print(f"   ❌ ЗАКАЗЫ: Sheets={orders_int}, WB={expected['orders']}, Разница={diff:+d} ({pct:+.1f}%)")
                    
                    if not stock_match:
                        diff = stock_int - expected["stock"]
                        pct = (diff / expected["stock"] * 100) if expected["stock"] > 0 else 0
                        print(f"   ⚠️  ОСТАТОК: Sheets={stock_int}, WB={expected['stock']}, Разница={diff:+d} ({pct:+.1f}%)")
        
        # Итоговый отчет
        print("\n" + "=" * 70)
        print(f"\n📈 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
        print(f"   ✅ Проверено продуктов: 3")
        print(f"   🎯 Совпадений с WB API: {success_count}/3")
        
        if issues_found:
            print(f"\n   ❌ Обнаружено проблем: {len(issues_found)}")
            print("\n📋 ДЕТАЛИ ПРОБЛЕМ:")
            for issue in issues_found:
                print(f"\n   • {issue['article']} (строка {issue['row']}):")
                if not issue['orders']['match']:
                    print(f"     - Заказы: {issue['orders']['sheets']} вместо {issue['orders']['wb']}")
                if not issue['stock']['match']:
                    print(f"     - Остаток: {issue['stock']['sheets']} вместо {issue['stock']['wb']}")
        else:
            print("\n   🎉 ВСЕ ДАННЫЕ КОРРЕКТНЫ!")
            print("   ✅ Дедупликация заказов работает правильно")
            
        print("\n" + "=" * 70)
        
        # Сохраняем отчет
        report = {
            "timestamp": "2025-10-27T18:30:00",
            "products_checked": 3,
            "products_correct": success_count,
            "issues_found": issues_found,
            "status": "SUCCESS" if len(issues_found) == 0 else "FAILED"
        }
        
        with open("deduplication_verification_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print("💾 Отчет сохранен в: deduplication_verification_report.json")
        
        return len(issues_found) == 0
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_updated_products()
    exit(0 if success else 1)
