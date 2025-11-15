#!/usr/bin/env python
"""Проверка финального состояния Google Sheets после всех исправлений."""
import sys
import os
import gspread

# Путь к сервисному аккаунту
service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')

def main():
    print("📊 Проверка Google Sheets - финальное состояние\n")
    print("=" * 60)
    
    # Подключаемся к Google Sheets
    gc = gspread.service_account(filename=service_account_path)
    spreadsheet = gc.open_by_key("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
    worksheet = spreadsheet.worksheet("Stock Tracker")
    
    # Получаем все данные
    all_values = worksheet.get_all_values()
    
    if not all_values:
        print("❌ Таблица пустая!")
        return
    
    print(f"\n📋 Всего строк в таблице: {len(all_values)}")
    
    if len(all_values) < 1:
        print("❌ Нет заголовков!")
        return
    
    headers = all_values[0]
    print(f"📋 Заголовки: {headers}\n")
    
    if len(all_values) < 2:
        print("❌ Нет данных (только заголовки)!")
        return
    
    # Найдём индексы нужных колонок
    try:
        article_idx = headers.index("Артикул товара")
        warehouse_idx = headers.index("Название склада")
        orders_idx = headers.index("Заказы со склада")
        stock_idx = headers.index("Остатки на складе")
    except ValueError as e:
        print(f"❌ Не найден заголовок: {e}")
        return
    
    print(f"\n📋 Всего товаров в таблице: {len(all_values) - 1}")
    print(f"📋 Заголовки: {', '.join(headers)}\n")
    
    # Проверим несколько товаров
    print("=" * 60)
    print("🔍 ПРОВЕРКА ВИЗУАЛЬНОГО РАЗДЕЛЕНИЯ СКЛАДОВ\n")
    
    for row_idx in range(1, min(4, len(all_values))):  # Первые 3 товара
        row = all_values[row_idx]
        article = row[article_idx] if article_idx < len(row) else ""
        warehouses = row[warehouse_idx] if warehouse_idx < len(row) else ""
        orders = row[orders_idx] if orders_idx < len(row) else ""
        stock = row[stock_idx] if stock_idx < len(row) else ""
        
        print(f"Товар: {article}")
        print(f"─" * 60)
        
        # Проверяем наличие двойных переносов
        warehouse_list = warehouses.split("\n") if warehouses else []
        orders_list = orders.split("\n") if orders else []
        stock_list = stock.split("\n") if stock else []
        
        print(f"  Количество складов: {len([w for w in warehouse_list if w.strip()])}")
        print(f"  Количество пустых строк: {len([w for w in warehouse_list if not w.strip()])}")
        
        if "" in warehouse_list:
            print("  ✅ Визуальное разделение работает! (есть пустые строки)")
        else:
            print("  ⚠️  Нет пустых строк между складами")
        
        print(f"\n  Первые 5 складов:")
        for i, (wh, ord, st) in enumerate(zip(warehouse_list[:5], orders_list[:5], stock_list[:5])):
            if wh.strip():
                print(f"    {i+1}. {wh}: заказы={ord}, остаток={st}")
            else:
                print(f"    {i+1}. [пустая строка]")
        
        print()
    
    # Проверяем дедупликацию "Обухово МП"
    print("=" * 60)
    print("🔍 ПРОВЕРКА ДЕДУПЛИКАЦИИ 'Обухово МП'\n")
    
    found_obuhovo = False
    found_marketplace = False
    
    for row_idx in range(1, len(all_values)):
        row = all_values[row_idx]
        warehouses = row[warehouse_idx] if warehouse_idx < len(row) else ""
        article = row[article_idx] if article_idx < len(row) else ""
        
        if "Обухово" in warehouses:
            found_obuhovo = True
            print(f"⚠️  Товар '{article}': найдено 'Обухово' в складах!")
            
            # Покажем контекст
            warehouse_lines = [w.strip() for w in warehouses.split("\n") if w.strip()]
            for wh in warehouse_lines:
                if "Обухово" in wh or "Маркетплейс" in wh:
                    print(f"     - {wh}")
        
        if "Маркетплейс" in warehouses:
            found_marketplace = True
    
    if not found_obuhovo:
        print("✅ 'Обухово МП' не найдено - дедупликация работает!")
    
    if found_marketplace:
        print("✅ 'Маркетплейс' присутствует в таблице")
    
    print("\n" + "=" * 60)
    print("✅ Проверка завершена!")

if __name__ == "__main__":
    main()
