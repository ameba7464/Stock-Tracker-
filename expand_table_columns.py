#!/usr/bin/env python3
"""
Expand Google Sheets table to include FBO/FBS columns (I and J)
"""

from stock_tracker.database.sheets import GoogleSheetsClient
from stock_tracker.utils.config import get_config
from stock_tracker.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    print("\n" + "="*100)
    print("🔧 РАСШИРЕНИЕ ТАБЛИЦЫ: Добавление столбцов FBO и FBS")
    print("="*100)
    
    config = get_config()
    sheets_client = GoogleSheetsClient()
    
    print(f"\nТаблица: {config.google_sheets.sheet_id}")
    print(f"Лист: Stock Tracker")
    
    try:
        # Get spreadsheet
        print("\n📊 Получаем spreadsheet...")
        spreadsheet = sheets_client.get_spreadsheet(config.google_sheets.sheet_id)
        worksheet = spreadsheet.worksheet("Stock Tracker")
        
        print(f"✅ Текущие размеры: {worksheet.row_count} rows x {worksheet.col_count} cols")
        
        # Check if columns I and J exist
        if worksheet.col_count >= 10:
            print(f"✅ Столбцы I и J уже существуют (всего {worksheet.col_count} столбцов)")
            
            # Check headers
            headers = worksheet.row_values(1)
            print(f"\n📋 Текущие заголовки: {headers}")
            
            if len(headers) < 10 or headers[8] != "FBO Остаток" or headers[9] != "FBS Остаток":
                print("\n⚠️ Заголовки FBO/FBS отсутствуют или некорректны")
                print("Обновляем заголовки...")
                
                # Update headers for columns I and J
                worksheet.update('I1:J1', [['FBO Остаток', 'FBS Остаток']])
                print("✅ Заголовки обновлены")
            else:
                print("✅ Заголовки FBO/FBS уже установлены")
        
        else:
            print(f"\n⚠️ Нужно расширить таблицу с {worksheet.col_count} до 10 столбцов")
            
            # Add columns
            cols_to_add = 10 - worksheet.col_count
            print(f"Добавляем {cols_to_add} столбц(а/ов)...")
            
            worksheet.add_cols(cols_to_add)
            print(f"✅ Добавлено {cols_to_add} столбц(а/ов)")
            
            # Set headers
            print("Устанавливаем заголовки для столбцов I и J...")
            worksheet.update('I1:J1', [['FBO Остаток', 'FBS Остаток']])
            print("✅ Заголовки установлены")
        
        # Verify final state
        worksheet = spreadsheet.worksheet("Stock Tracker")  # Refresh
        print(f"\n✅ ИТОГ: {worksheet.row_count} rows x {worksheet.col_count} cols")
        
        headers = worksheet.row_values(1)
        print(f"Заголовки: {headers}")
        
        print("\n" + "="*100)
        print("✅ РАСШИРЕНИЕ ЗАВЕРШЕНО")
        print("="*100)
    
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import time
    print("\n⏳ Ожидание 60 секунд для сброса квоты API...")
    time.sleep(60)
    main()
