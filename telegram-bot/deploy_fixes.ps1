# PowerShell скрипт для развертывания исправлений на сервере Яндекс.Облака
# Использование: .\deploy_fixes.ps1

$ErrorActionPreference = "Stop"

Write-Host "=============================================="
Write-Host "🚀 РАЗВЕРТЫВАНИЕ ИСПРАВЛЕНИЙ БОТА" -ForegroundColor Cyan
Write-Host "=============================================="
Write-Host ""

$SERVER = "yc-user@158.160.188.247"
$BOT_DIR = "/opt/stock-tracker-bot"

# Проверка SSH подключения
Write-Host "1️⃣  Проверка подключения к серверу..." -ForegroundColor Yellow
try {
    $result = ssh -o ConnectTimeout=5 $SERVER "echo 'OK'" 2>&1
    Write-Host "✅ Подключение к серверу успешно" -ForegroundColor Green
} catch {
    Write-Host "❌ Не удалось подключиться к серверу" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "2️⃣  Копирование исправленных файлов на сервер..." -ForegroundColor Yellow

# Копируем исправленные файлы
$files = @(
    @{src="app/bot/handlers/registration.py"; dest="app/bot/handlers/"},
    @{src="app/database/crud.py"; dest="app/database/"},
    @{src="app/database/database.py"; dest="app/database/"},
    @{src="app/bot/middlewares/db.py"; dest="app/bot/middlewares/"},
    @{src="fix_database_duplicates.py"; dest="."}
)

foreach ($file in $files) {
    Write-Host "   📁 Копирование $($file.src)..." -ForegroundColor Gray
    try {
        scp $file.src "${SERVER}:${BOT_DIR}/$($file.dest)" 2>&1 | Out-Null
        Write-Host "      ✅ $($file.src) скопирован" -ForegroundColor Green
    } catch {
        Write-Host "      ❌ Ошибка копирования $($file.src)" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "3️⃣  Создание резервной копии базы данных..." -ForegroundColor Yellow
try {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    ssh $SERVER "sudo -u postgres pg_dump stocktracker > /tmp/backup_$timestamp.sql" 2>&1 | Out-Null
    Write-Host "✅ Резервная копия создана: backup_$timestamp.sql" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Не удалось создать резервную копию (продолжаем...)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "4️⃣  Проверка и исправление дубликатов в БД..." -ForegroundColor Yellow
Write-Host ""
Write-Host "⚠️  ВНИМАНИЕ: Скрипт попросит подтверждение для исправления дубликатов" -ForegroundColor Yellow
Write-Host "   Введите 'yes' если хотите исправить дубликаты" -ForegroundColor Yellow
Write-Host ""

# Запускаем скрипт исправления дубликатов
ssh -t $SERVER "cd $BOT_DIR && source venv/bin/activate && python fix_database_duplicates.py"

Write-Host ""
Write-Host "5️⃣  Перезапуск сервиса бота..." -ForegroundColor Yellow
ssh $SERVER "sudo systemctl restart stock-tracker-bot.service"
Start-Sleep -Seconds 3

# Проверка статуса
$status = ssh $SERVER "sudo systemctl is-active stock-tracker-bot.service" 2>&1
if ($status -match "active") {
    Write-Host "✅ Бот успешно перезапущен" -ForegroundColor Green
} else {
    Write-Host "❌ Ошибка перезапуска бота" -ForegroundColor Red
    Write-Host ""
    Write-Host "Проверьте статус командой:"
    Write-Host "   ssh $SERVER 'sudo systemctl status stock-tracker-bot.service'"
    exit 1
}

Write-Host ""
Write-Host "6️⃣  Проверка логов..." -ForegroundColor Yellow
Write-Host ""
ssh $SERVER "tail -n 20 $BOT_DIR/logs/bot.log"

Write-Host ""
Write-Host "=============================================="
Write-Host "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО" -ForegroundColor Green
Write-Host "=============================================="
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "   1. Протестируйте бота через Telegram: /start"
Write-Host "   2. Проверьте процесс регистрации"
Write-Host "   3. Следите за логами: ssh $SERVER 'tail -f $BOT_DIR/logs/bot.log'"
Write-Host ""
Write-Host "📊 Полезные команды:" -ForegroundColor Cyan
Write-Host "   Статус бота:  ssh $SERVER 'sudo systemctl status stock-tracker-bot.service'"
Write-Host "   Логи:         ssh $SERVER 'tail -100 $BOT_DIR/logs/bot.log'"
Write-Host "   Перезапуск:   ssh $SERVER 'sudo systemctl restart stock-tracker-bot.service'"
Write-Host ""
