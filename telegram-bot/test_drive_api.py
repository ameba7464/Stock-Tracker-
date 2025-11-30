"""Тест создания файла через Drive API."""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

def test_drive_api():
    """Тест создания файла через Drive API."""
    print("🔍 Тест Google Drive API")
    print("=" * 60)
    
    try:
        # Загружаем credentials
        print("1️⃣ Загрузка credentials...")
        credentials = service_account.Credentials.from_service_account_file(
            'credentials.json',
            scopes=SCOPES
        )
        print("✅ Credentials загружены")
        print(f"   Service Account: {credentials.service_account_email}")
        
        # Создаем Drive service
        print("\n2️⃣ Создание Drive service...")
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service создан")
        
        # Пробуем создать файл (Google Sheet через Drive API)
        print("\n3️⃣ Попытка создать Google Sheet через Drive API...")
        file_metadata = {
            'name': 'Test Sheet from Drive API',
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        
        file = drive_service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        print("✅ Файл создан успешно!")
        print(f"   ID: {file.get('id')}")
        print(f"   Имя: {file.get('name')}")
        print(f"   Ссылка: {file.get('webViewLink')}")
        
        # Удаляем тестовый файл
        print("\n4️⃣ Удаление тестового файла...")
        drive_service.files().delete(fileId=file.get('id')).execute()
        print("✅ Тестовый файл удален")
        
        print("\n" + "=" * 60)
        print("🎉 ВСЁ РАБОТАЕТ! Drive API настроен правильно")
        
    except HttpError as e:
        print(f"\n❌ HTTP Ошибка: {e}")
        print(f"Статус: {e.status_code}")
        print(f"Причина: {e.error_details}")
        
        print("\n⚠️ ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("1. Drive API не включен")
        print("   https://console.cloud.google.com/apis/library/drive.googleapis.com?project=stocktr-479319")
        print("\n2. Service Account не имеет прав")
        print("   Проверьте права в IAM:")
        print("   https://console.cloud.google.com/iam-admin/iam?project=stocktr-479319")
        print("\n3. Попробуйте добавить роль 'Service Usage Consumer':")
        print("   - Откройте IAM")
        print("   - Найдите stocktr@stocktr-479319.iam.gserviceaccount.com")
        print("   - Добавьте роль: Service Usage Consumer")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_drive_api()
