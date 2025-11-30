"""Тест создания файла НАПРЯМУЮ в папке через Drive API."""
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

FOLDER_ID = "1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA"

def test_create_directly_in_folder():
    """Тест создания файла напрямую в указанной папке."""
    print("🔍 Тест создания Google Sheet НАПРЯМУЮ в папке")
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
        print(f"   Service Account: {credentials.service_account_email}")
        
        # Создаем только Drive service
        print("\n2️⃣ Создание Drive service...")
        drive_service = build('drive', 'v3', credentials=credentials)
        print("✅ Drive service создан")
        
        # Создаем Google Sheet НАПРЯМУЮ в папке через Drive API
        print(f"\n3️⃣ Создание Google Sheet в папке {FOLDER_ID}...")
        file_metadata = {
            'name': 'Test Sheet - Direct Creation',
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [FOLDER_ID]  # Указываем папку сразу при создании
        }
        
        file = drive_service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink, parents'
        ).execute()
        
        print("✅ Файл создан успешно!")
        print(f"   ID: {file.get('id')}")
        print(f"   Имя: {file.get('name')}")
        print(f"   Родители: {file.get('parents')}")
        print(f"   Ссылка: {file.get('webViewLink')}")
        
        # Даем публичный доступ
        print("\n4️⃣ Настройка прав доступа...")
        permission = {
            'type': 'anyone',
            'role': 'writer'
        }
        
        drive_service.permissions().create(
            fileId=file.get('id'),
            body=permission
        ).execute()
        
        print("✅ Права доступа настроены (anyone can write)")
        
        print("\n" + "=" * 60)
        print("🎉 УСПЕХ! Таблица создана напрямую в папке")
        print(f"🔗 Ссылка: {file.get('webViewLink')}")
        print("\n✨ Проверьте папку в вашем Google Drive!")
        print("=" * 60)
        
        # Спрашиваем, удалить ли тестовый файл
        print("\nУдалить тестовый файл? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == 'y':
                drive_service.files().delete(fileId=file.get('id')).execute()
                print("✅ Тестовый файл удален")
        except:
            pass
        
    except HttpError as e:
        print(f"\n❌ HTTP Ошибка: {e}")
        print(f"Статус: {e.status_code}")
        print(f"Причина: {e.error_details}")
        
        if e.status_code == 403:
            print("\n⚠️ ОШИБКА 403 - НЕТ ПРАВ:")
            print("\n📋 ПРОВЕРЬТЕ:")
            print("1. Откройте папку в Google Drive:")
            print("   https://drive.google.com/drive/folders/1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA")
            print("\n2. Нажмите правой кнопкой → 'Открыть доступ'")
            print("\n3. Добавьте адрес:")
            print("   stocktr@stocktr-479319.iam.gserviceaccount.com")
            print("\n4. Выберите роль: 'Редактор'")
            print("\n5. ВАЖНО: Снимите галочку 'Уведомить пользователей' (если есть)")
            print("\n6. Нажмите 'Готово' или 'Отправить'")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_create_directly_in_folder()
