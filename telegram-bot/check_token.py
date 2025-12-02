"""Проверка и обновление OAuth токена."""
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = 'token.json'

def check_token():
    try:
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        
        print('📊 Информация о токене:')
        client_id = data.get('client_id', 'N/A')
        print(f'   Client ID: {client_id[:40]}...' if client_id else '   Client ID: N/A')
        print(f'   Refresh token: {"Есть" if data.get("refresh_token") else "Нет"}')
        print(f'   Scopes: {data.get("scopes", [])}')
        
        # Проверяем валидность
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        print(f'   Valid: {creds.valid}')
        print(f'   Expired: {creds.expired}')
        
        if creds.expired and creds.refresh_token:
            print('\n🔄 Обновляем токен...')
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
            print('✅ Токен обновлён!')
        elif creds.valid:
            print('\n✅ Токен валиден!')
        else:
            print('\n❌ Токен невалиден и не может быть обновлён')
            print('   Запустите: python get_oauth_token.py')
            
    except FileNotFoundError:
        print('❌ Файл token.json не найден')
        print('   Запустите: python get_oauth_token.py')
    except Exception as e:
        print(f'❌ Ошибка: {e}')

if __name__ == '__main__':
    check_token()
