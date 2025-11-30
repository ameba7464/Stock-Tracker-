"""Скрипт для получения OAuth токена Google."""
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes для доступа
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def get_oauth_token():
    """Получение OAuth токена через браузер."""
    creds = None
    token_file = 'token.json'
    credentials_file = 'oauth_credentials.json'
    
    # Проверяем наличие oauth_credentials.json
    if not os.path.exists(credentials_file):
        print("❌ Файл oauth_credentials.json не найден!")
        print("\n📋 Следуйте инструкциям в OAUTH_SETUP_GUIDE.md")
        print("\n1. Создайте OAuth Client ID в Google Cloud Console")
        print("2. Скачайте JSON файл")
        print("3. Сохраните его как 'oauth_credentials.json' в текущей папке")
        return
    
    # Проверяем существующий токен
    if os.path.exists(token_file):
        print("✅ Найден существующий токен")
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # Если токена нет или он истёк
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Обновление токена...")
            creds.refresh(Request())
        else:
            print("🌐 Открываю браузер для авторизации...")
            print("\n⚠️ Если увидите предупреждение безопасности:")
            print("   Нажмите 'Advanced' → 'Go to Stock Tracker Bot (unsafe)'")
            print("   Это нормально для приложений в режиме тестирования\n")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Сохраняем токен
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        
        print("\n✅ Токен успешно получен и сохранён!")
        print(f"📄 Файл: {os.path.abspath(token_file)}")
    else:
        print("✅ Токен валиден")
    
    # Показываем информацию о токене
    print("\n📊 Информация о токене:")
    token_data = json.loads(creds.to_json())
    print(f"   Client ID: {token_data.get('client_id', 'N/A')[:30]}...")
    print(f"   Есть refresh_token: {'Да' if token_data.get('refresh_token') else 'Нет'}")
    print(f"   Scopes: {', '.join(token_data.get('scopes', []))}")
    
    print("\n✅ Готово! Теперь бот может создавать таблицы в вашем Google Drive")
    print("🔐 Токен будет автоматически обновляться при необходимости")

if __name__ == '__main__':
    try:
        get_oauth_token()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\n💡 Убедитесь что:")
        print("   1. Файл oauth_credentials.json существует")
        print("   2. OAuth consent screen настроен")
        print("   3. Ваш email добавлен в Test users")
