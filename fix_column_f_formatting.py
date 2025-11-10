"""
Применение исправленного форматирования к колонке F (Название склада).
Этот скрипт только изменяет форматирование, не трогая данные.
"""

import os
import sys

# Change to script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.insert(0, os.path.join(script_dir, 'src'))

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "./config/service-account.json")

def apply_fixed_formatting():
    """Применить исправленное форматирование к колонке F"""
    
    print("🔧 Применение исправленного форматирования к таблице")
    print("=" * 60)
    
    # Подключение
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    
    # Открыть таблицу
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet("Stock Tracker")
    
    print(f"📊 Таблица: {spreadsheet.title}")
    print(f"📝 Лист: {worksheet.title}")
    print(f"🆔 Sheet ID: {worksheet.id}")
    print()
    
    # Формат для колонки F - БЕЗ переноса текста
    no_wrap_format = {
        "wrapStrategy": "OVERFLOW_CELL",  # Текст выходит за границы, не увеличивает строку
        "verticalAlignment": "TOP"
    }
    
    # Формат для колонок G, H, I - С переносом текста для многострочных данных
    wrap_format = {
        "wrapStrategy": "WRAP",
        "verticalAlignment": "TOP"
    }
    
    requests = [
        # Колонка F (Название склада) - БЕЗ ПЕРЕНОСА
        {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 1,  # Пропустить заголовок
                    "startColumnIndex": 5,  # Колонка F (индекс 5)
                    "endColumnIndex": 6
                },
                "cell": {
                    "userEnteredFormat": {
                        **no_wrap_format,
                        "textFormat": {
                            "fontSize": 10
                        }
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.textFormat.fontSize"
            }
        },
        # Колонка G (Заказы со склада) - С ПЕРЕНОСОМ
        {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 6,  # Колонка G
                    "endColumnIndex": 7
                },
                "cell": {
                    "userEnteredFormat": {
                        **wrap_format,
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 10
                        }
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
            }
        },
        # Колонка H (Остатки на складе) - С ПЕРЕНОСОМ
        {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 7,  # Колонка H
                    "endColumnIndex": 8
                },
                "cell": {
                    "userEnteredFormat": {
                        **wrap_format,
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 10
                        }
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
            }
        },
        # Колонка I (Оборачиваемость по складам) - С ПЕРЕНОСОМ
        {
            "repeatCell": {
                "range": {
                    "sheetId": worksheet.id,
                    "startRowIndex": 1,
                    "startColumnIndex": 8,  # Колонка I
                    "endColumnIndex": 9
                },
                "cell": {
                    "userEnteredFormat": {
                        **wrap_format,
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "fontSize": 10
                        }
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy,userEnteredFormat.verticalAlignment,userEnteredFormat.horizontalAlignment,userEnteredFormat.textFormat.fontSize"
            }
        }
    ]
    
    print("🔄 Применение форматирования...")
    print("   - Колонка F: OVERFLOW_CELL (без переноса)")
    print("   - Колонки G, H, I: WRAP (с переносом)")
    print()
    
    # Применить изменения
    spreadsheet.batch_update({"requests": requests})
    
    print("✅ Форматирование успешно применено!")
    print()
    print("📋 Что изменилось:")
    print("   1. Колонка F (Название склада):")
    print("      - Текст НЕ переносится на новую строку")
    print("      - Длинные названия выходят за границы ячейки вправо")
    print("      - Высота строки НЕ увеличивается")
    print()
    print("   2. Колонки G, H, I (данные складов):")
    print("      - Текст переносится для многострочных данных")
    print("      - Выравнивание по центру")
    print()
    print("💡 Теперь длинные названия складов не будут смещать другие данные!")

if __name__ == "__main__":
    try:
        apply_fixed_formatting()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
