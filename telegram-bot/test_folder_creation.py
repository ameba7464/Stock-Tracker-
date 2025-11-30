"""Тест создания файла в указанной папке Drive."""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

FOLDER_ID = "1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA"

def test_create_in_folder():
    """Тест создания файла в указанной папке."""
    print("🔍 Тест создания Google Sheet в папке")
    print("=" * 60)
    print(f"📁 Папка ID: {FOLDER_ID}")
    print()
    
    try:
        # Загружаем credentials
        print("1️⃣ Загрузка credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        print("✅ Credentials загружены")
        
        # Создаем services
        print("\n2️⃣ Создание services...")
        sheets_service = build('sheets', 'v4', credentials=credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Services созданы")
        
        # Создаем таблицу
        print("\n3️⃣ Создание Google Sheet...")
        spreadsheet = {
            'properties': {
                'title': 'Test Sheet - Telegram Bot'
            }
        }
        
        sheet = sheets_service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()
        
        sheet_id = sheet.get('spreadsheetId')
        print(f"✅ Таблица создана: {sheet_id}")
        
        # Перемещаем в папку
        print(f"\n4️⃣ Перемещение в папку {FOLDER_ID}...")
        
        # Получаем текущих родителей
        file = drive_service.files().get(
            fileId=sheet_id,
            fields='parents'
        ).execute()
        previous_parents = ",".join(file.get('parents', []))
        
        # Перемещаем
        drive_service.files().update(
            fileId=sheet_id,
            addParents=FOLDER_ID,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        
        print("✅ Файл перемещен в папку")
        
        # Даем публичный доступ
        print("\n5️⃣ Настройка прав доступа...")
        permission = {
            'type': 'anyone',
            'role': 'writer'
        }
        
        drive_service.permissions().create(
            fileId=sheet_id,
            body=permission
        ).execute()
        
        print("✅ Права доступа настроены")
        
        # Получаем ссылку
        file_info = drive_service.files().get(
            fileId=sheet_id,
            fields='webViewLink'
        ).execute()
        
        print("\n" + "=" * 60)
        print("🎉 УСПЕХ! Таблица создана")
        print(f"📊 ID: {sheet_id}")
        print(f"🔗 Ссылка: {file_info.get('webViewLink')}")
        print("\n✨ Проверьте папку в вашем Google Drive!")
        print("=" * 60)
        
        # Спрашиваем, удалить ли тестовый файл
        print("\nУдалить тестовый файл? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == 'y':
                drive_service.files().delete(fileId=sheet_id).execute()
                print("✅ Тестовый файл удален")
        except:
            pass
        
    except HttpError as e:
        print(f"\n❌ HTTP Ошибка: {e}")
        print(f"Статус: {e.status_code}")
        print(f"Причина: {e.error_details}")
        
        if e.status_code == 403:
            print("\n⚠️ ОШИБКА 403:")
            print("1. Убедитесь что вы предоставили доступ к папке для:")
            print(f"   stocktr@stocktr-479319.iam.gserviceaccount.com")
            print("\n2. Роль должна быть: Редактор (Editor)")
            print("\n3. Проверьте что ID папки правильный:")
            print(f"   {FOLDER_ID}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_create_in_folder()
