#!/usr/bin/env python3
"""
Проверка результатов в Google Sheets после обновления.
Показывает сводку по заказам и остаткам.
"""

import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config


def check_table_results():
    """Проверить результаты в таблице."""
    try:
        print("🔍 Проверка данных в Google Sheets...\n")
        
        # Подключаемся к таблице
        config = get_config()
        service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')
        sheets_client = GoogleSheetsClient(service_account_path)
        
        spreadsheet_id = config.google_sheet_id
        client = sheets_client._get_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("Stock Tracker")
        
        # Читаем все данные
        all_data = worksheet.get_all_values()
        
        if len(all_data) < 2:
            print("❌ Таблица пустая (нет данных)")
            return
        
        # Заголовки
        headers = all_data[0]
        data_rows = all_data[1:]
        
        print(f"📊 Найдено записей: {len(data_rows)}\n")
        
        # Подсчёт общих метрик
        total_orders = 0
        total_stock = 0
        products_with_orders = 0
        
        print("🏷️  ТОВАРЫ:")
        print("=" * 80)
        
        for i, row in enumerate(data_rows, 1):
            if len(row) < 3:
                continue
                
            seller_article = row[0] if len(row) > 0 else ""
            orders = int(row[2]) if len(row) > 2 and row[2].strip().isdigit() else 0
            stock = int(row[3]) if len(row) > 3 and row[3].strip().isdigit() else 0
            
            total_orders += orders
            total_stock += stock
            
            if orders > 0:
                products_with_orders += 1
            
            print(f"{i:2}. {seller_article:40} | Заказы: {orders:3} | Остатки: {stock:4}")
        
        print("=" * 80)
        print(f"\n📈 ИТОГО:")
        print(f"   Всего товаров:              {len(data_rows)}")
        print(f"   Товаров с заказами:         {products_with_orders}")
        print(f"   Общее количество заказов:   {total_orders}")
        print(f"   Общее количество остатков:  {total_stock}")
        
        # Проверка на подозрительно большие значения
        if total_orders > 300:
            print(f"\n⚠️  ВНИМАНИЕ: {total_orders} заказов - это много!")
            print("   Возможные причины:")
            print("   1. Дублирование заказов")
            print("   2. Неправильная фильтрация отменённых")
            print("   3. Некорректный период")
        elif total_orders < 50:
            print(f"\n⚠️  ВНИМАНИЕ: {total_orders} заказов - это мало!")
            print("   Возможные причины:")
            print("   1. Слишком короткий период")
            print("   2. Проблемы с API")
        else:
            print(f"\n✅ Количество заказов ({total_orders}) выглядит нормально для периода 7 дней")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_table_results()
