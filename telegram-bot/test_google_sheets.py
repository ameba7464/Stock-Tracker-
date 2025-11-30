"""Тест прямого подключения к Google Sheets API."""
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API библиотеки не установлены!")
    print("Установите: pip install google-auth google-api-python-client")
    sys.exit(1)


def test_google_sheets_api():
    """Тестирование подключения к Google Sheets API."""
    print("🔍 Тест Google Sheets API")
    print("=" * 60)
    
    # Проверка credentials
    cred_path = Path("credentials.json")
    if not cred_path.exists():
        print("❌ credentials.json не найден!")
        return False
    
    print("✅ credentials.json найден")
    
    try:
        # Создаем credentials
        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]
        
        credentials = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=SCOPES
        )
        
        print("✅ Credentials загружены")
        
        # Создаем сервис
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Sheets API service создан")
        
        # Пробуем создать тестовую таблицу
        print("\n🧪 Попытка создать тестовую таблицу...")
        
        spreadsheet = {
            'properties': {
                'title': 'TEST - Stock Tracker API Test'
            }
        }
        
        result = service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()
        
        sheet_id = result.get('spreadsheetId')
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        
        print(f"\n✅ УСПЕХ! Таблица создана!")
        print(f"📊 ID: {sheet_id}")
        print(f"🔗 URL: {sheet_url}")
        
        # Удаляем тестовую таблицу
        print("\n🗑️ Удаляем тестовую таблицу...")
        drive_service = build('drive', 'v3', credentials=credentials)
        drive_service.files().delete(fileId=sheet_id).execute()
        print("✅ Тестовая таблица удалена")
        
        print("\n" + "=" * 60)
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("Google Sheets API работает корректно")
        print("=" * 60)
        
        return True
        
    except HttpError as e:
        print(f"\n❌ HTTP Ошибка: {e}")
        print(f"Статус: {e.status_code}")
        print(f"Причина: {e.error_details}")
        
        if e.status_code == 403:
            print("\n⚠️ ПРОБЛЕМА: API не включен или нет прав")
            print("\nЧто проверить:")
            print("1. Google Sheets API включен в проекте:")
            print("   https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=stocktr-479319")
            print("\n2. Google Drive API включен в проекте:")
            print("   https://console.cloud.google.com/apis/library/drive.googleapis.com?project=stocktr-479319")
            print("\n3. Service Account существует и активен:")
            print("   https://console.cloud.google.com/iam-admin/serviceaccounts?project=stocktr-479319")
        
        return False
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_google_sheets_api()
    sys.exit(0 if success else 1)
