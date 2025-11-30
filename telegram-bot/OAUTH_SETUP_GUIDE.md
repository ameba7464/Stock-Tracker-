# Настройка OAuth для создания Google Sheets

## Шаг 1: Создание OAuth Client ID

1. Откройте Google Cloud Console:
   https://console.cloud.google.com/apis/credentials?project=stocktr-479319

2. Нажмите **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

3. Если попросит настроить OAuth consent screen:
   - Нажмите **"CONFIGURE CONSENT SCREEN"**
   - Выберите **"External"** (или "Internal" если у вас Google Workspace)
   - Нажмите **"CREATE"**
   
   Заполните обязательные поля:
   - **App name**:  Stock Tracker Bot
   - **User support email**: ваш email
   - **Developer contact**: ваш email
   - Нажмите **"SAVE AND CONTINUE"**
   
   На странице **Scopes**:
   - Нажмите **"ADD OR REMOVE SCOPES"**
   - Найдите и добавьте:
     - `https://www.googleapis.com/auth/spreadsheets`
     - `https://www.googleapis.com/auth/drive.file`
   - Нажмите **"UPDATE"**
   - Нажмите **"SAVE AND CONTINUE"**
   
   На странице **Test users**:
   - Нажмите **"+ ADD USERS"**
   - Добавьте свой Google email
   - Нажмите **"SAVE AND CONTINUE"**
   
   Нажмите **"BACK TO DASHBOARD"**

4. Вернитесь в **Credentials** и снова нажмите **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**

5. Выберите:
   - **Application type**: Desktop app
   - **Name**: Stock Tracker Bot Desktop

6. Нажмите **"CREATE"**

7. **ВАЖНО**: Скачайте JSON файл (кнопка Download JSON)
   - Сохраните его как `oauth_credentials.json` в папку `telegram-bot/`

## Шаг 2: Получение токена

После создания файла `oauth_credentials.json`, запустите скрипт авторизации:

```bash
python get_oauth_token.py
```

Скрипт откроет браузер для авторизации. После успешной авторизации токен будет сохранён автоматически.

## Готово!

После этих шагов бот сможет создавать таблицы в вашем Google Drive от вашего имени.
