# Быстрая настройка PostgreSQL для Stock Tracker

## Проблема
PostgreSQL установлен и работает, но мы не знаем пароль пользователя `postgres`.

## Решение 1: Сброс пароля (РЕКОМЕНДУЕТСЯ)

**Выполните в PowerShell от имени Администратора:**

```powershell
# 1. Остановите службу
Stop-Service -Name "postgresql-x64-17"

# 2. Создайте временный файл для сброса пароля
$resetScript = @"
ALTER USER postgres WITH PASSWORD 'postgres';
"@
$resetScript | Out-File -FilePath "C:\temp_reset.sql" -Encoding UTF8

# 3. Запустите PostgreSQL с файлом сброса (одной строкой)
& "C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" -D "C:\Program Files\PostgreSQL\17\data" start

# 4. Подождите 5 секунд
Start-Sleep -Seconds 5

# 5. Выполните сброс пароля
$env:PGPASSWORD=""; & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d postgres -f "C:\temp_reset.sql"

# 6. Удалите временный файл
Remove-Item "C:\temp_reset.sql"

# 7. Запустите службу обратно
Start-Service -Name "postgresql-x64-17"
```

## Решение 2: Изменить метод аутентификации на trust (временно)

**Выполните в PowerShell от имени Администратора:**

```powershell
# 1. Остановите службу
Stop-Service -Name "postgresql-x64-17"

# 2. Создайте резервную копию pg_hba.conf
Copy-Item "C:\Program Files\PostgreSQL\17\data\pg_hba.conf" "C:\Program Files\PostgreSQL\17\data\pg_hba.conf.backup"

# 3. Измените метод аутентификации на trust
(Get-Content "C:\Program Files\PostgreSQL\17\data\pg_hba.conf") -replace 'scram-sha-256', 'trust' | Set-Content "C:\Program Files\PostgreSQL\17\data\pg_hba.conf"

# 4. Запустите службу
Start-Service -Name "postgresql-x64-17"

# 5. Измените пароль
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# 6. Верните оригинальный pg_hba.conf
Stop-Service -Name "postgresql-x64-17"
Copy-Item "C:\Program Files\PostgreSQL\17\data\pg_hba.conf.backup" "C:\Program Files\PostgreSQL\17\data\pg_hba.conf" -Force
Start-Service -Name "postgresql-x64-17"
```

## Решение 3: Простой способ (если помните пароль)

Если вы помните пароль, просто создайте базу данных:

```powershell
$env:PGPASSWORD="ВАШ_ПАРОЛЬ"
& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -U postgres stock_tracker
```

## После сброса пароля

Создайте базу данных для Stock Tracker:

```powershell
# Установите пароль (который мы установили выше)
$env:PGPASSWORD="postgres"

# Создайте базу данных
& "C:\Program Files\PostgreSQL\17\bin\createdb.exe" -U postgres stock_tracker

# Проверьте, что база создана
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -l
```

## Обновите .env файл

После создания базы данных обновите файл `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stock_tracker
```

---

**ВАЖНО**: Выполните одно из решений от имени Администратора, затем дайте знать, и я обновлю конфигурацию!
