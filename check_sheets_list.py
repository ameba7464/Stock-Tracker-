#!/usr/bin/env python
"""Проверка списка листов в Google Sheets."""
import gspread
import os

service_account_path = os.path.join(os.path.dirname(__file__), 'config', 'service-account.json')

def main():
    print("📋 Проверка списка листов в документе\n")
    print("=" * 60)
    
    gc = gspread.service_account(filename=service_account_path)
    spreadsheet = gc.open_by_key("1baGNbGKDSvFA1Cghh08onoG9PDGnO19UFzXhdKC9Sho")
    
    print(f"📊 Документ: {spreadsheet.title}")
    print(f"📝 Всего листов: {len(spreadsheet.worksheets())}\n")
    
    print("Список листов:")
    for i, ws in enumerate(spreadsheet.worksheets(), 1):
        print(f"  {i}. {ws.title} (id: {ws.id}, rows: {ws.row_count}, cols: {ws.col_count})")
    
    # Проверяем наличие Sheet1
    has_sheet1 = any(ws.title == "Sheet1" for ws in spreadsheet.worksheets())
    has_stock_tracker = any(ws.title == "Stock Tracker" for ws in spreadsheet.worksheets())
    
    print("\n" + "=" * 60)
    if has_sheet1:
        print("❌ ВНИМАНИЕ: Лист 'Sheet1' всё ещё существует!")
    else:
        print("✅ Лист 'Sheet1' отсутствует - правильно!")
    
    if has_stock_tracker:
        print("✅ Лист 'Stock Tracker' присутствует - правильно!")
    else:
        print("❌ ВНИМАНИЕ: Лист 'Stock Tracker' отсутствует!")
    
    print("\n✅ Проверка завершена!")

if __name__ == "__main__":
    main()
