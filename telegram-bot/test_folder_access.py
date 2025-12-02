"""Тест доступа к папке Google Drive."""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CREDENTIALS_PATH = 'credentials.json'
FOLDER_ID = '1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA'  # Из .env

def test_folder_access():
    """Проверяет доступ Service Account к папке."""
    print("🔍 Проверка доступа к папке Google Drive...")
    print("-" * 60)
    
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    service = build('drive', 'v3', credentials=credentials)
    
    try:
        # Получаем информацию о папке
        folder = service.files().get(
            fileId=FOLDER_ID,
            fields="id, name, owners, permissions, capabilities"
        ).execute()
        
        print(f"✅ Папка найдена!")
        print(f"   Название: {folder.get('name')}")
        print(f"   ID: {folder.get('id')}")
        
        # Владельцы
        owners = folder.get('owners', [])
        print(f"\n👤 Владелец папки:")
        for owner in owners:
            print(f"   {owner.get('emailAddress')}")
        
        # Права доступа
        caps = folder.get('capabilities', {})
        print(f"\n🔐 Права Service Account:")
        print(f"   Может редактировать: {caps.get('canEdit', False)}")
        print(f"   Может добавлять файлы: {caps.get('canAddChildren', False)}")
        print(f"   Может удалять: {caps.get('canDelete', False)}")
        
        # Пробуем создать тестовый файл
        print(f"\n📝 Попытка создать тестовый файл в папке...")
        
        file_metadata = {
            'name': 'TEST_DELETE_ME',
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [FOLDER_ID]
        }
        
        test_file = service.files().create(
            body=file_metadata,
            fields='id, name, owners'
        ).execute()
        
        print(f"✅ Файл создан успешно!")
        print(f"   ID: {test_file.get('id')}")
        
        # Кто владелец созданного файла?
        file_owners = test_file.get('owners', [])
        print(f"\n👤 Владелец созданного файла:")
        for owner in file_owners:
            print(f"   {owner.get('emailAddress')}")
        
        # Удаляем тестовый файл
        service.files().delete(fileId=test_file.get('id')).execute()
        print(f"\n🗑️ Тестовый файл удалён")
        
        return True
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else []
        print(f"\n❌ Ошибка: {e.resp.status}")
        print(f"   {e._get_reason()}")
        
        if e.resp.status == 404:
            print("\n💡 Папка не найдена или Service Account не имеет к ней доступа.")
            print("   Убедитесь что папка расшарена на: stocktr@stocktr-479319.iam.gserviceaccount.com")
        elif e.resp.status == 403:
            print("\n💡 Нет прав доступа.")
            if "storage quota" in str(e).lower():
                print("   Проблема с квотой хранилища!")
            else:
                print("   Проверьте права доступа к папке.")
        
        return False

if __name__ == "__main__":
    test_folder_access()
