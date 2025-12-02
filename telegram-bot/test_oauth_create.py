"""Тест создания файла через OAuth."""
import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = 'token.json'
FOLDER_ID = '1NkBvCFyFpXRg8Opno6-_Cf8mTeT7OHRA'

def test_oauth_create():
    print('🔍 Тест создания файла через OAuth...')
    print('-' * 60)
    
    try:
        # Загружаем credentials
        creds = Credentials.from_authorized_user_file(TOKEN_FILE)
        
        if creds.expired and creds.refresh_token:
            print('🔄 Обновляем токен...')
            creds.refresh(Request())
        
        # Создаём клиент gspread
        client = gspread.authorize(creds)
        
        print(f'📁 Создаём таблицу в папке: {FOLDER_ID}')
        
        # Создаём таблицу в папке
        spreadsheet = client.create('TEST_OAUTH_DELETE_ME', folder_id=FOLDER_ID)
        
        print(f'✅ Таблица создана!')
        print(f'   ID: {spreadsheet.id}')
        print(f'   URL: {spreadsheet.url}')
        
        # Проверяем владельца
        # Даём доступ по ссылке
        spreadsheet.share('', perm_type='anyone', role='reader')
        print(f'   Доступ: любой по ссылке')
        
        # Удаляем тестовую таблицу
        print(f'\n🗑️ Удаляем тестовую таблицу...')
        client.del_spreadsheet(spreadsheet.id)
        print(f'✅ Тестовая таблица удалена')
        
        print('\n' + '=' * 60)
        print('🎉 OAUTH РАБОТАЕТ! Можно создавать таблицы!')
        print('=' * 60)
        
        return True
        
    except Exception as e:
        print(f'\n❌ Ошибка: {e}')
        
        if 'quota' in str(e).lower():
            print('\n💡 Проблема с квотой сохраняется.')
            print('   Возможно OAuth настроен на другой аккаунт.')
        
        return False

if __name__ == '__main__':
    test_oauth_create()
