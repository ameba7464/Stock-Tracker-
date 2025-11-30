# PostgreSQL Setup Guide для Windows

## Шаг 1: Скачивание PostgreSQL

1. Перейдите на официальный сайт: https://www.postgresql.org/download/windows/
2. Нажмите "Download the installer"
3. Выберите последнюю версию для Windows x86-64 (например, PostgreSQL 16.x)
4. Скачайте установщик (примерно 350 MB)

## Шаг 2: Установка PostgreSQL

1. Запустите скачанный установщик `postgresql-16.x-windows-x64.exe`
2. Нажмите "Next" на экране приветствия
3. **Installation Directory**: оставьте по умолчанию `C:\Program Files\PostgreSQL\16`
4. **Select Components**: оставьте все отмеченным:
   - ✅ PostgreSQL Server
   - ✅ pgAdmin 4 (графический интерфейс)
   - ✅ Stack Builder
   - ✅ Command Line Tools
5. **Data Directory**: оставьте по умолчанию `C:\Program Files\PostgreSQL\16\data`
6. **Password**: установите пароль для суперпользователя `postgres`
   - **ВАЖНО**: запомните этот пароль, он понадобится для подключения!
   - Рекомендуем: `postgres` (для локальной разработки)
7. **Port**: оставьте `5432` (порт по умолчанию)
8. **Locale**: выберите `Russian, Russia` или оставьте `Default locale`
9. Нажмите "Next" и дождитесь завершения установки

## Шаг 3: Проверка установки

Откройте новое окно PowerShell и выполните:

```powershell
psql --version
```

Должно показать что-то вроде: `psql (PostgreSQL) 16.x`

## Шаг 4: Создание базы данных для Stock Tracker

Откройте PowerShell и выполните:

```powershell
# Подключаемся к PostgreSQL (введите пароль, который установили)
psql -U postgres

# В psql консоли выполните:
CREATE DATABASE stock_tracker;
CREATE USER stock_user WITH PASSWORD 'stock_password';
GRANT ALL PRIVILEGES ON DATABASE stock_tracker TO stock_user;
\q
```

## Шаг 5: Обновление .env файла

Теперь нужно обновить DATABASE_URL в файле `.env`:

```env
DATABASE_URL=postgresql://stock_user:stock_password@localhost:5432/stock_tracker
```

## Альтернатива: Использовать пользователя postgres

Если не хотите создавать нового пользователя, можно использовать суперпользователя:

```env
DATABASE_URL=postgresql://postgres:ВАШ_ПАРОЛЬ@localhost:5432/stock_tracker
```

И создать только базу данных:

```powershell
psql -U postgres -c "CREATE DATABASE stock_tracker;"
```

## Проверка подключения

После настройки проверьте подключение:

```powershell
psql -U stock_user -d stock_tracker
# или
psql -U postgres -d stock_tracker
```

Если подключение успешно, вы увидите приглашение `stock_tracker=#`

## Графический интерфейс (опционально)

PostgreSQL устанавливает pgAdmin 4 - графический инструмент для управления БД:

1. Запустите pgAdmin 4 из меню Пуск
2. Введите мастер-пароль (любой)
3. В дереве слева: Servers → PostgreSQL 16 → (введите пароль postgres)
4. Вы увидите созданную базу данных `stock_tracker`

---

После выполнения всех шагов возвращайтесь, и мы запустим сервер!
