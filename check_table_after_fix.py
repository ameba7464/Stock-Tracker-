#!/usr/bin/env python3
"""
Проверка результатов обновления таблицы после исправления.

Сравнивает данные в таблице с WB ground truth.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.database.operations import SheetsOperations
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)

def check_table_results():
    """Проверить результаты в таблице после обновления."""
    try:
        print("=" * 80)
        print("ПРОВЕРКА РЕЗУЛЬТАТОВ ПОСЛЕ ИСПРАВЛЕНИЯ")
        print("=" * 80)
        
        config = get_config()
        spreadsheet_id = config.google_sheet_id
        
        service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')
        sheets_client = GoogleSheetsClient(service_account_path)
        operations = SheetsOperations(sheets_client)
        
        print("\n📊 Чтение данных из таблицы...")
        
        # Читаем основные товары
        main_products = [
            ('Its1_2_3/50g', 163383326),  # WB: 97 заказов
            ('Its2/50g', 163383327),       # WB: 68 заказов
            ('ItsSport2/50g', 163383328)   # WB: 23 заказов
        ]
        
        print("\n" + "=" * 80)
        print("СРАВНЕНИЕ С WB GROUND TRUTH (22-28 окт)")
        print("=" * 80)
        print(f"{'Товар':<20} {'WB Truth':<12} {'Таблица':<12} {'Расхождение':<15} {'Статус'}")
        print("-" * 80)
        
        wb_ground_truth = {
            'Its1_2_3/50g': 97,
            'Its2/50g': 68,
            'ItsSport2/50g': 23
        }
        
        all_good = True
        total_table_orders = 0
        total_wb_orders = 0
        
        for seller_article, wb_article in main_products:
            try:
                product = operations.read_product(spreadsheet_id, seller_article)
                
                if product:
                    table_orders = product.total_orders
                    wb_orders = wb_ground_truth.get(seller_article, 0)
                    
                    total_table_orders += table_orders
                    total_wb_orders += wb_orders
                    
                    if wb_orders > 0:
                        diff_percent = abs(table_orders - wb_orders) / wb_orders * 100
                        diff_str = f"{diff_percent:+.1f}%"
                        
                        if diff_percent <= 10:
                            status = "✅ OK"
                        elif diff_percent <= 20:
                            status = "⚠️ WARNING"
                            all_good = False
                        else:
                            status = "❌ FAIL"
                            all_good = False
                    else:
                        diff_str = "N/A"
                        status = "❓"
                    
                    print(f"{seller_article:<20} {wb_orders:<12} {table_orders:<12} {diff_str:<15} {status}")
                else:
                    print(f"{seller_article:<20} {'N/A':<12} {'NOT FOUND':<12} {'N/A':<15} ❌ MISSING")
                    all_good = False
                    
            except Exception as e:
                print(f"{seller_article:<20} {'N/A':<12} {'ERROR':<12} {str(e)[:15]:<15} ❌ ERROR")
                all_good = False
        
        print("-" * 80)
        print(f"{'ИТОГО':<20} {total_wb_orders:<12} {total_table_orders:<12}")
        
        print("\n" + "=" * 80)
        print("РЕЗУЛЬТАТ ПРОВЕРКИ")
        print("=" * 80)
        
        if all_good:
            print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
            print("   Расхождение с WB ground truth не превышает 10%")
            print("   Таблица обновлена ПРАВИЛЬНЫМИ данными из Orders API v1")
        else:
            print("⚠️ ЕСТЬ РАСХОЖДЕНИЯ")
            print("   Некоторые значения отличаются от WB ground truth")
            print("   Возможные причины:")
            print("   - Разные периоды (таблица: неделя, WB: конкретные даты)")
            print("   - API вернул частичные данные")
            print("   - Квота Google Sheets исчерпана (проверьте логи)")
        
        print("\n" + "=" * 80)
        print("ДЕТАЛЬНАЯ ИНФОРМАЦИЯ")
        print("=" * 80)
        
        # Читаем все продукты для статистики
        all_products = []
        for seller_article, _ in main_products:
            try:
                product = operations.read_product(spreadsheet_id, seller_article)
                if product:
                    all_products.append(product)
            except:
                pass
        
        if all_products:
            total_stock = sum(p.total_stock for p in all_products)
            total_orders = sum(p.total_orders for p in all_products)
            
            print(f"\nВсего товаров в таблице: {len(all_products)}")
            print(f"Общий остаток: {total_stock}")
            print(f"Общее кол-во заказов: {total_orders}")
            
            print("\nТоп товары по заказам:")
            sorted_products = sorted(all_products, key=lambda p: p.total_orders, reverse=True)
            for i, product in enumerate(sorted_products[:5], 1):
                print(f"  {i}. {product.seller_article}: {product.total_orders} заказов, {product.total_stock} остаток")
        
        return all_good
        
    except Exception as e:
        print(f"\n❌ Ошибка при проверке: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_table_results()
    sys.exit(0 if success else 1)
