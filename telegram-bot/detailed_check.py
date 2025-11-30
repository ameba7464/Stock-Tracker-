"""Детальная проверка прав Google Service Account."""
import json
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API библиотеки не установлены!")
    exit(1)


def check_detailed():
    """Детальная проверка прав и API."""
    print("🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА GOOGLE API")
    print("=" * 70)
    
    # 1. Проверка credentials файла
    print("\n1️⃣ Проверка credentials.json")
    cred_path = Path("credentials.json")
    
    if not cred_path.exists():
        print("❌ Файл не найден!")
        return
    
    with open(cred_path) as f:
        creds_data = json.load(f)
    
    print(f"✅ Файл найден")
    print(f"   Project ID: {creds_data.get('project_id')}")
    print(f"   Service Account: {creds_data.get('client_email')}")
    print(f"   Client ID: {creds_data.get('client_id')}")
    
    # 2. Проверка scopes
    print("\n2️⃣ Проверка scopes (разрешений)")
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    try:
        credentials = service_account.Credentials.from_service_account_file(
            str(cred_path),
            scopes=SCOPES
        )
        print("✅ Credentials созданы с scopes:")
        for scope in SCOPES:
            print(f"   • {scope}")
    except Exception as e:
        print(f"❌ Ошибка создания credentials: {e}")
        return
    
    # 3. Проверка Google Sheets API
    print("\n3️⃣ Проверка Google Sheets API")
    try:
        sheets_service = build('sheets', 'v4', credentials=credentials)
        print("✅ Sheets service создан")
        
        # Пробуем минимальный запрос
        print("   Попытка создать таблицу...")
        result = sheets_service.spreadsheets().create(
            body={'properties': {'title': 'Test'}},
            fields='spreadsheetId'
        ).execute()
        
        sheet_id = result.get('spreadsheetId')
        print(f"✅ УСПЕХ! Таблица создана: {sheet_id}")
        
        # Удаляем
        drive_service = build('drive', 'v3', credentials=credentials)
        drive_service.files().delete(fileId=sheet_id).execute()
        print("✅ Тестовая таблица удалена")
        
    except HttpError as e:
        print(f"❌ HTTP Ошибка: {e.status_code}")
        print(f"   Детали: {e.error_details}")
        
        if e.status_code == 403:
            print("\n⚠️ ОШИБКА 403 - НЕТ ПРАВ")
            print("\n📋 ЧТО ПРОВЕРИТЬ:")
            print("\n   A) Убедитесь что включены ОБА API:")
            print("      ✓ Google Sheets API")
            print("      ✓ Google Drive API")
            print("\n   B) Проверьте в консоли:")
            print(f"      https://console.cloud.google.com/apis/dashboard?project={creds_data.get('project_id')}")
            print("\n   C) Если API включены только что - подождите 2-3 минуты")
            print("\n   D) Проверьте Service Account:")
            print(f"      https://console.cloud.google.com/iam-admin/serviceaccounts?project={creds_data.get('project_id')}")
            print("\n   E) Попробуйте дать Service Account роль 'Editor':")
            print(f"      1. Откройте: https://console.cloud.google.com/iam-admin/iam?project={creds_data.get('project_id')}")
            print(f"      2. Нажмите 'Grant Access'")
            print(f"      3. В поле 'New principals' вставьте: {creds_data.get('client_email')}")
            print(f"      4. В 'Role' выберите: Editor")
            print(f"      5. Нажмите 'Save'")
        
        return
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    # 4. Проверка Google Drive API
    print("\n4️⃣ Проверка Google Drive API")
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service создан")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return
    
    print("\n" + "=" * 70)
    print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
    print("=" * 70)


if __name__ == "__main__":
    check_detailed()
