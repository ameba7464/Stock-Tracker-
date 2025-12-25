# ============================================
# PowerShell Скрипт Деплоя для Windows
# ============================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Деплой унифицированной системы подписок" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$SERVER = "yc-user@158.160.188.247"
$PROJECT_DIR = "Stock-Tracker"

Write-Host "Шаг 1: Загрузка скрипта на сервер" -ForegroundColor Yellow
Write-Host "----------------------------------------"

# Копируем скрипт на сервер
scp deploy_subscription_update.sh "${SERVER}:~/"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Скрипт загружен на сервер" -ForegroundColor Green
} else {
    Write-Host "✗ Ошибка при загрузке скрипта" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Шаг 2: Клонирование/обновление проекта" -ForegroundColor Yellow
Write-Host "----------------------------------------"

# Проверяем есть ли проект на сервере
$projectExists = ssh $SERVER "test -d $PROJECT_DIR && echo 'exists' || echo 'not_exists'"

if ($projectExists -match "not_exists") {
    Write-Host "Клонируем проект..." -ForegroundColor Cyan
    ssh $SERVER "git clone https://github.com/ameba7464/Stock-Tracker-.git $PROJECT_DIR"
} else {
    Write-Host "Обновляем проект..." -ForegroundColor Cyan
    ssh $SERVER "cd $PROJECT_DIR && git stash && git pull origin main"
}

Write-Host "✓ Проект обновлен" -ForegroundColor Green

Write-Host ""
Write-Host "Шаг 3: Запуск деплоя на сервере" -ForegroundColor Yellow
Write-Host "----------------------------------------"

# Делаем скрипт исполняемым и запускаем
ssh $SERVER "chmod +x deploy_subscription_update.sh && ./deploy_subscription_update.sh"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Проверьте работу бота:" -ForegroundColor Cyan
    Write-Host "  ssh $SERVER" -ForegroundColor White
    Write-Host "  cd $PROJECT_DIR" -ForegroundColor White
    Write-Host "  tail -f logs/bot.log" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ Ошибка при деплое" -ForegroundColor Red
    Write-Host "Проверьте логи на сервере:" -ForegroundColor Yellow
    Write-Host "  ssh $SERVER" -ForegroundColor White
    Write-Host "  cat deploy_subscription_update.log" -ForegroundColor White
}
