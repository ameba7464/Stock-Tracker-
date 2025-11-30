"""Тест создания файла в папке через Drive API."""
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Создаем credentials
credentials = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
)

# Создаем Drive service
service = build('drive', 'v3', credentials=credentials)

# Метаданные файла
file_metadata = {
    'name': 'Test Sheet from Bot',
    'mimeType': 'application/vnd.google-apps.spreadsheet',
    'parents': ['1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA']  # ID вашей папки
}

try:
    # Создаём файл
    file = service.files().create(
        body=file_metadata,
        fields='id, webViewLink'
    ).execute()
    
    print(f"✅ Таблица создана!")
    print(f"📄 ID: {file.get('id')}")
    print(f"🔗 URL: {file.get('webViewLink')}")
    
    # Настраиваем доступ
    permission = {
        'type': 'anyone',
        'role': 'writer'
    }
    service.permissions().create(
        fileId=file.get('id'),
        body=permission
    ).execute()
    
    print("✅ Доступ настроен для всех по ссылке")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
