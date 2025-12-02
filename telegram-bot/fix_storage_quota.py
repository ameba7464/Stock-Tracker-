"""
Скрипт для диагностики и исправления проблемы с квотой хранилища Service Account.

Ошибка: APIError: [403]: The user's Drive storage quota has been exceeded.

ПРИЧИНА: 
Когда Service Account создаёт файлы, они принадлежат ему (не пользователю папки).
У Service Account есть своя квота хранилища (15 ГБ), которая может переполниться.

РЕШЕНИЕ:
1. Удалить старые файлы, созданные Service Account
2. Или передать владение файлами другому аккаунту
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os

# Путь к credentials
CREDENTIALS_PATH = 'credentials.json'

def get_drive_service():
    """Создаёт сервис Google Drive API."""
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=credentials)

def check_storage_quota():
    """Проверяет использование квоты хранилища Service Account."""
    print("🔍 Проверка квоты хранилища Service Account...")
    print("-" * 60)
    
    service = get_drive_service()
    
    try:
        # Получаем информацию о хранилище
        about = service.about().get(fields="storageQuota, user").execute()
        
        user = about.get('user', {})
        quota = about.get('storageQuota', {})
        
        print(f"📧 Email Service Account: {user.get('emailAddress', 'N/A')}")
        print()
        
        # Квота в байтах
        limit = int(quota.get('limit', 0))
        usage = int(quota.get('usage', 0))
        usage_in_drive = int(quota.get('usageInDrive', 0))
        usage_in_trash = int(quota.get('usageInDriveTrash', 0))
        
        # Конвертируем в человекочитаемый формат
        def format_bytes(bytes_val):
            if bytes_val >= 1024 ** 3:
                return f"{bytes_val / (1024 ** 3):.2f} ГБ"
            elif bytes_val >= 1024 ** 2:
                return f"{bytes_val / (1024 ** 2):.2f} МБ"
            elif bytes_val >= 1024:
                return f"{bytes_val / 1024:.2f} КБ"
            return f"{bytes_val} байт"
        
        print("📊 ИСПОЛЬЗОВАНИЕ КВОТЫ:")
        print(f"   Лимит:           {format_bytes(limit)}")
        print(f"   Использовано:    {format_bytes(usage)}")
        print(f"   В Drive:         {format_bytes(usage_in_drive)}")
        print(f"   В корзине:       {format_bytes(usage_in_trash)}")
        
        if limit > 0:
            usage_percent = (usage / limit) * 100
            print(f"   Процент:         {usage_percent:.1f}%")
            
            if usage_percent >= 100:
                print()
                print("❌ КВОТА ПРЕВЫШЕНА! Необходимо освободить место.")
                return False
            elif usage_percent >= 90:
                print()
                print("⚠️ ВНИМАНИЕ! Квота почти заполнена!")
        
        print()
        return True
        
    except HttpError as e:
        print(f"❌ Ошибка API: {e}")
        return False

def list_files_owned_by_service_account():
    """Выводит список файлов, принадлежащих Service Account."""
    print("\n📁 Файлы, созданные Service Account:")
    print("-" * 60)
    
    service = get_drive_service()
    
    try:
        # Получаем все файлы
        results = service.files().list(
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, size, createdTime, trashed)",
            orderBy="createdTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print("   Нет файлов.")
            return []
        
        total_size = 0
        spreadsheets = []
        
        for f in files:
            size = int(f.get('size', 0))
            total_size += size
            
            mime = f.get('mimeType', '')
            is_spreadsheet = 'spreadsheet' in mime
            trashed = f.get('trashed', False)
            status = "🗑️ " if trashed else ""
            
            if is_spreadsheet:
                spreadsheets.append(f)
            
            print(f"   {status}{f['name'][:50]:<50} | {f.get('createdTime', '')[:10]}")
        
        print("-" * 60)
        print(f"   Всего файлов: {len(files)}")
        print(f"   Таблиц: {len(spreadsheets)}")
        
        return files
        
    except HttpError as e:
        print(f"❌ Ошибка API: {e}")
        return []

def empty_trash():
    """Очищает корзину Service Account."""
    print("\n🗑️ Очистка корзины...")
    
    service = get_drive_service()
    
    try:
        service.files().emptyTrash().execute()
        print("✅ Корзина очищена!")
        return True
    except HttpError as e:
        print(f"❌ Ошибка при очистке корзины: {e}")
        return False

def delete_old_spreadsheets(keep_count=10):
    """Удаляет старые таблицы, оставляя последние N."""
    print(f"\n🗑️ Удаление старых таблиц (оставляем последние {keep_count})...")
    
    service = get_drive_service()
    
    try:
        # Получаем все Google Sheets
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
            pageSize=1000,
            fields="files(id, name, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        if len(files) <= keep_count:
            print(f"   Всего таблиц: {len(files)}, удаление не требуется.")
            return 0
        
        # Файлы для удаления (все кроме последних keep_count)
        to_delete = files[keep_count:]
        
        print(f"   Будет удалено: {len(to_delete)} таблиц")
        
        deleted = 0
        for f in to_delete:
            try:
                service.files().delete(fileId=f['id']).execute()
                print(f"   ✓ Удалено: {f['name'][:50]}")
                deleted += 1
            except HttpError as e:
                print(f"   ✗ Ошибка удаления {f['name']}: {e}")
        
        print(f"\n✅ Удалено файлов: {deleted}")
        return deleted
        
    except HttpError as e:
        print(f"❌ Ошибка API: {e}")
        return 0

def transfer_ownership(file_id: str, new_owner_email: str):
    """Передаёт владение файлом другому пользователю."""
    print(f"\n🔄 Передача владения файлом {file_id}...")
    
    service = get_drive_service()
    
    try:
        permission = {
            'type': 'user',
            'role': 'owner',
            'emailAddress': new_owner_email
        }
        
        service.permissions().create(
            fileId=file_id,
            body=permission,
            transferOwnership=True
        ).execute()
        
        print(f"✅ Владение передано: {new_owner_email}")
        return True
        
    except HttpError as e:
        print(f"❌ Ошибка передачи владения: {e}")
        return False

def main():
    """Главная функция диагностики и исправления."""
    print("=" * 60)
    print("🔧 ДИАГНОСТИКА ПРОБЛЕМЫ С КВОТОЙ GOOGLE DRIVE")
    print("=" * 60)
    
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"❌ Файл {CREDENTIALS_PATH} не найден!")
        return
    
    # 1. Проверяем квоту
    quota_ok = check_storage_quota()
    
    # 2. Показываем файлы
    files = list_files_owned_by_service_account()
    
    if not quota_ok or len(files) > 0:
        print("\n" + "=" * 60)
        print("💡 РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:")
        print("=" * 60)
        
        if not quota_ok:
            print("""
1. ОЧИСТИТЬ КОРЗИНУ:
   - Запустите: python fix_storage_quota.py --empty-trash

2. УДАЛИТЬ СТАРЫЕ ТАБЛИЦЫ:
   - Запустите: python fix_storage_quota.py --delete-old 10
   - Оставит только 10 последних таблиц

3. ЛУЧШЕЕ РЕШЕНИЕ - НАСТРОИТЬ OAuth:
   - Service Account создаёт файлы от своего имени
   - OAuth создаёт файлы от имени пользователя
   - Запустите: python get_oauth_token.py
            """)
        else:
            print("   ✅ Квота в норме, проблема может быть в другом.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--empty-trash":
            empty_trash()
            check_storage_quota()
        elif sys.argv[1] == "--delete-old":
            keep = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            delete_old_spreadsheets(keep)
            empty_trash()
            check_storage_quota()
        elif sys.argv[1] == "--list":
            list_files_owned_by_service_account()
        else:
            print("Использование:")
            print("  python fix_storage_quota.py              - Диагностика")
            print("  python fix_storage_quota.py --list       - Список файлов")
            print("  python fix_storage_quota.py --empty-trash - Очистить корзину")
            print("  python fix_storage_quota.py --delete-old N - Удалить старые, оставить N")
    else:
        main()
