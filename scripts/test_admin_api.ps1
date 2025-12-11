# 🧪 Примеры API запросов для тестирования админ-панели

## Настройка

Сначала получите токен доступа:

```powershell
# Вход и получение токена
$loginData = @{
    email = "admin@example.com"
    password = "ваш_пароль"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginData

$token = $response.access_token
Write-Host "✅ Токен получен: $token" -ForegroundColor Green

# Сохраните для использования в других запросах
$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
}
```

## 📊 Получить статистику

```powershell
$stats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/stats" `
    -Headers $headers

Write-Host "Всего пользователей: $($stats.total_users)"
Write-Host "Активных: $($stats.active_users)"
Write-Host "Админов: $($stats.admin_users)"
Write-Host "Тенантов: $($stats.total_tenants)"
Write-Host ""
Write-Host "Распределение по тарифам:"
Write-Host "  Free: $($stats.free_plan_count)"
Write-Host "  Starter: $($stats.starter_plan_count)"
Write-Host "  Pro: $($stats.pro_plan_count)"
Write-Host "  Enterprise: $($stats.enterprise_plan_count)"
```

## 👥 Получить список пользователей

### Базовый запрос (первая страница)

```powershell
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?page=1&page_size=20" `
    -Headers $headers

Write-Host "Найдено пользователей: $($users.total)"
Write-Host "Страница: $($users.page) из $($users.total_pages)"
Write-Host ""

foreach ($user in $users.users) {
    Write-Host "📧 $($user.email) - $($user.tenant_name) [$($user.plan_type)]" -ForegroundColor Cyan
}
```

### С поиском

```powershell
$search = "test"
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?search=$search" `
    -Headers $headers

Write-Host "Результаты поиска '$search': $($users.total) пользователей"
```

### С фильтром по тарифу

```powershell
$plan = "pro"
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?plan_filter=$plan" `
    -Headers $headers

Write-Host "Пользователей на тарифе '$plan': $($users.total)"
```

### Только активные

```powershell
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?active_only=true" `
    -Headers $headers

Write-Host "Активных пользователей: $($users.total)"
```

### Комбинация фильтров

```powershell
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?plan_filter=pro&active_only=true&page=1&page_size=10" `
    -Headers $headers

Write-Host "Активных пользователей на Pro: $($users.total)"
```

## 🔍 Получить детали конкретного пользователя

```powershell
# Замените на реальный UUID пользователя
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$user = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId" `
    -Headers $headers

Write-Host "=== Информация о пользователе ==="
Write-Host "Email: $($user.email)"
Write-Host "Имя: $($user.full_name)"
Write-Host "Роль: $($user.role)"
Write-Host "Активен: $($user.is_active)"
Write-Host "Админ: $($user.is_admin)"
Write-Host ""
Write-Host "=== Организация ==="
Write-Host "Название: $($user.tenant_name)"
Write-Host "Маркетплейс: $($user.marketplace_type)"
Write-Host ""
Write-Host "=== Подписка ==="
Write-Host "Тариф: $($user.plan_type)"
Write-Host "Статус: $($user.subscription_status)"
Write-Host "Квота: $($user.quota_used) / $($user.quota_limit)"
```

## ✏️ Изменить права пользователя

### Выдать права администратора

```powershell
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$updateData = @{
    is_admin = $true
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId/access" `
    -Method PATCH `
    -Headers $headers `
    -Body $updateData

Write-Host "✅ Права администратора выданы!" -ForegroundColor Green
```

### Деактивировать пользователя

```powershell
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$updateData = @{
    is_active = $false
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId/access" `
    -Method PATCH `
    -Headers $headers `
    -Body $updateData

Write-Host "✅ Пользователь деактивирован!" -ForegroundColor Yellow
```

### Изменить тариф

```powershell
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$updateData = @{
    plan_type = "pro"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId/access" `
    -Method PATCH `
    -Headers $headers `
    -Body $updateData

Write-Host "✅ Тариф изменен на Pro!" -ForegroundColor Green
```

### Изменить несколько параметров сразу

```powershell
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$updateData = @{
    is_active = $true
    is_admin = $true
    plan_type = "enterprise"
} | ConvertTo-Json

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId/access" `
    -Method PATCH `
    -Headers $headers `
    -Body $updateData

Write-Host "✅ Все параметры обновлены!" -ForegroundColor Green
```

## 🗑️ Удалить пользователя (мягкое удаление)

```powershell
$userId = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$userId" `
    -Method DELETE `
    -Headers $headers

Write-Host "✅ Пользователь деактивирован!" -ForegroundColor Red
```

## 📈 Скрипт для массового обновления

### Активировать всех пользователей на Free тарифе

```powershell
# Получить всех пользователей на Free
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?plan_filter=free&page_size=100" `
    -Headers $headers

Write-Host "Найдено $($users.total) пользователей на Free тарифе"

foreach ($user in $users.users) {
    if (-not $user.is_active) {
        Write-Host "Активирую пользователя: $($user.email)" -ForegroundColor Yellow
        
        $updateData = @{
            is_active = $true
        } | ConvertTo-Json
        
        try {
            Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$($user.id)/access" `
                -Method PATCH `
                -Headers $headers `
                -Body $updateData | Out-Null
            
            Write-Host "  ✅ Активирован" -ForegroundColor Green
        } catch {
            Write-Host "  ❌ Ошибка: $_" -ForegroundColor Red
        }
    }
}
```

### Повысить тариф для всех активных пользователей

```powershell
# Получить всех активных пользователей на Starter
$users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?plan_filter=starter&active_only=true" `
    -Headers $headers

Write-Host "Повышаю тариф для $($users.total) пользователей"

foreach ($user in $users.users) {
    Write-Host "Обновляю: $($user.email)" -ForegroundColor Yellow
    
    $updateData = @{
        plan_type = "pro"
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$($user.id)/access" `
            -Method PATCH `
            -Headers $headers `
            -Body $updateData | Out-Null
        
        Write-Host "  ✅ Повышен до Pro" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Ошибка: $_" -ForegroundColor Red
    }
}
```

## 📊 Аналитический скрипт

```powershell
# Собрать полную статистику

Write-Host "=== Сбор статистики ===" -ForegroundColor Cyan
Write-Host ""

# Общая статистика
$stats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/stats" `
    -Headers $headers

Write-Host "📊 Общая статистика:"
Write-Host "  Всего пользователей: $($stats.total_users)"
Write-Host "  Активных: $($stats.active_users) ($([math]::Round($stats.active_users / $stats.total_users * 100, 2))%)"
Write-Host "  Админов: $($stats.admin_users)"
Write-Host "  Тенантов: $($stats.total_tenants)"
Write-Host ""

Write-Host "💳 Распределение по тарифам:"
Write-Host "  Free: $($stats.free_plan_count) ($([math]::Round($stats.free_plan_count / $stats.total_users * 100, 2))%)"
Write-Host "  Starter: $($stats.starter_plan_count) ($([math]::Round($stats.starter_plan_count / $stats.total_users * 100, 2))%)"
Write-Host "  Pro: $($stats.pro_plan_count) ($([math]::Round($stats.pro_plan_count / $stats.total_users * 100, 2))%)"
Write-Host "  Enterprise: $($stats.enterprise_plan_count) ($([math]::Round($stats.enterprise_plan_count / $stats.total_users * 100, 2))%)"
Write-Host ""

# Последние зарегистрированные
$recent = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?page=1&page_size=5" `
    -Headers $headers

Write-Host "🆕 Последние 5 регистраций:"
foreach ($user in $recent.users) {
    $date = [DateTime]::Parse($user.created_at).ToString("dd.MM.yyyy HH:mm")
    Write-Host "  $date - $($user.email) [$($user.plan_type)]"
}
```

## 🔐 Тест безопасности

```powershell
Write-Host "=== Тест безопасности ===" -ForegroundColor Yellow
Write-Host ""

# Попытка доступа без токена
Write-Host "1. Проверка: Доступ без токена..."
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/stats"
    Write-Host "  ❌ ОШИБКА: Доступ получен без токена!" -ForegroundColor Red
} catch {
    Write-Host "  ✅ OK: Доступ запрещен (401)" -ForegroundColor Green
}

# Попытка с неправильным токеном
Write-Host "2. Проверка: Доступ с неправильным токеном..."
$badHeaders = @{Authorization = "Bearer invalid_token_12345"}
try {
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/stats" -Headers $badHeaders
    Write-Host "  ❌ ОШИБКА: Доступ получен с неправильным токеном!" -ForegroundColor Red
} catch {
    Write-Host "  ✅ OK: Доступ запрещен (401)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Тесты безопасности завершены!"
```

## 💡 Полезные функции

### Функция для красивого вывода пользователя

```powershell
function Show-User {
    param([string]$UserId)
    
    $user = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users/$UserId" `
        -Headers $headers
    
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║          Информация о пользователе     ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📧 Email:           $($user.email)"
    Write-Host "👤 Имя:             $($user.full_name)"
    Write-Host "🏢 Организация:     $($user.tenant_name)"
    Write-Host "💼 Роль:            $($user.role)"
    Write-Host "✅ Активен:         $($user.is_active)"
    Write-Host "🛡️  Админ:           $($user.is_admin)"
    Write-Host "💳 Тариф:           $($user.plan_type)"
    Write-Host "📊 Квота:           $($user.quota_used) / $($user.quota_limit)"
    Write-Host ""
}

# Использование
Show-User -UserId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

### Функция для экспорта пользователей в CSV

```powershell
function Export-Users {
    param([string]$OutputFile = "users_export.csv")
    
    $allUsers = @()
    $page = 1
    
    do {
        $users = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/users?page=$page&page_size=100" `
            -Headers $headers
        
        $allUsers += $users.users
        $page++
        Write-Host "Загружено страниц: $page из $($users.total_pages)..." -ForegroundColor Yellow
        
    } while ($page -le $users.total_pages)
    
    $allUsers | Export-Csv -Path $OutputFile -NoTypeInformation -Encoding UTF8
    Write-Host "✅ Экспортировано $($allUsers.Count) пользователей в $OutputFile" -ForegroundColor Green
}

# Использование
Export-Users -OutputFile "my_users.csv"
```

---

**Совет:** Сохраните этот файл как `test_admin_api.ps1` и запускайте для тестирования!
