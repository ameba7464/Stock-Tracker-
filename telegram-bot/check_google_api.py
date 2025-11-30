"""Проверка настроек Google API и credentials."""
import json
from pathlib import Path

def check_credentials():
    """Проверка файла credentials.json"""
    print("🔍 Проверка credentials.json")
    print("=" * 60)
    
    cred_path = Path("credentials.json")
    
    if not cred_path.exists():
        print("❌ Файл credentials.json НЕ НАЙДЕН!")
        return False
    
    print("✅ Файл credentials.json найден")
    
    try:
        with open(cred_path, 'r') as f:
            creds = json.load(f)
        
        required_fields = [
            'type', 'project_id', 'private_key_id', 'private_key',
            'client_email', 'client_id', 'auth_uri', 'token_uri'
        ]
        
        missing = []
        for field in required_fields:
            if field not in creds:
                missing.append(field)
        
        if missing:
            print(f"❌ Отсутствуют поля: {', '.join(missing)}")
            return False
        
        print("✅ Все необходимые поля присутствуют")
        print(f"\n📧 Service Account Email: {creds['client_email']}")
        print(f"🆔 Project ID: {creds['project_id']}")
        
        return True
        
    except json.JSONDecodeError:
        print("❌ Ошибка чтения JSON файла")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def print_instructions():
    """Инструкции по включению API"""
    print("\n" + "=" * 60)
    print("📋 ИНСТРУКЦИЯ ПО ВКЛЮЧЕНИЮ API")
    print("=" * 60)
    print("""
1. Откройте Google Cloud Console:
   https://console.cloud.google.com/

2. Убедитесь что выбран проект: stocktr-479319

3. Перейдите в "APIs & Services" → "Library"
   https://console.cloud.google.com/apis/library

4. ВКЛЮЧИТЕ следующие API (если не включены):

   а) Google Sheets API:
      - Найдите "Google Sheets API"
      - Нажмите на него
      - Нажмите "ENABLE" (если не включен)
   
   б) Google Drive API:
      - Найдите "Google Drive API"
      - Нажмите на него
      - Нажмите "ENABLE" (если не включен)

5. Проверьте включенные API:
   https://console.cloud.google.com/apis/dashboard?project=stocktr-479319
   
   Должны быть активны:
   ✅ Google Sheets API
   ✅ Google Drive API

6. После включения подождите 1-2 минуты и перезапустите бота

""")


if __name__ == "__main__":
    print("\n🔧 ДИАГНОСТИКА GOOGLE API НАСТРОЕК")
    print("=" * 60)
    
    if check_credentials():
        print("\n✅ Credentials файл в порядке")
        print_instructions()
        print("\n💡 СЛЕДУЮЩИЕ ШАГИ:")
        print("1. Включите API по инструкции выше")
        print("2. Подождите 1-2 минуты")
        print("3. Перезапустите бота: python -m app.main")
    else:
        print("\n❌ Проблема с credentials.json")
        print("Проверьте что файл правильный и находится в папке telegram-bot/")
