#!/usr/bin/env python
"""Удаление ненужного листа Sheet1 из Google Sheets."""
import sys
import os
import gspread

# Путь к сервисному аккаунту
service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')

def main():
    print("🗑️  Удаление листа 'Sheet1'\n")
    print("=" * 60)
    
    # Подключаемся к Google Sheets
    gc = gspread.service_account(filename=service_account_path)
    spreadsheet = gc.open_by_key("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
    
    print(f"📊 Документ: {spreadsheet.title}")
    print(f"📋 Всего листов: {len(spreadsheet.worksheets())}\n")
    
    # Показываем все листы
    print("Текущие листы:")
    for i, ws in enumerate(spreadsheet.worksheets(), 1):
        print(f"  {i}. {ws.title} (id: {ws.id})")
    
    # Ищем Sheet1
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        print(f"\n🔍 Найден лист 'Sheet1' (id: {sheet1.id})")
        
        # Проверяем, не единственный ли это лист
        if len(spreadsheet.worksheets()) <= 1:
            print("⚠️  ВНИМАНИЕ: Это единственный лист в документе!")
            print("   Google Sheets требует хотя бы один лист.")
            print("   Сначала создам 'Stock Tracker', потом удалю 'Sheet1'.")
            
            # Создаём Stock Tracker, если его нет
            try:
                stock_tracker = spreadsheet.worksheet("Stock Tracker")
                print(f"✅ Лист 'Stock Tracker' уже существует")
            except gspread.exceptions.WorksheetNotFound:
                print("📝 Создаю лист 'Stock Tracker'...")
                stock_tracker = spreadsheet.add_worksheet(
                    title="Stock Tracker",
                    rows=1000,
                    cols=20
                )
                print(f"✅ Лист 'Stock Tracker' создан (id: {stock_tracker.id})")
        
        # Теперь можно безопасно удалить Sheet1
        print(f"\n🗑️  Удаляю лист 'Sheet1'...")
        spreadsheet.del_worksheet(sheet1)
        print("✅ Лист 'Sheet1' успешно удалён!")
        
    except gspread.exceptions.WorksheetNotFound:
        print("\n✅ Лист 'Sheet1' не найден - всё в порядке!")
    
    print("\n" + "=" * 60)
    print("📋 Финальный список листов:")
    for i, ws in enumerate(spreadsheet.worksheets(), 1):
        print(f"  {i}. {ws.title}")
    
    print("\n✅ Готово!")

if __name__ == "__main__":
    main()
