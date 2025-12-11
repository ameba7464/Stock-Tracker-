# Скрипт проверки системы мониторинга Stock Tracker (Windows PowerShell)

Write-Host "🔍 Проверка системы мониторинга Stock Tracker" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Function to check service
function Test-Service {
    param(
        [string]$ServiceName,
        [string]$Url
    )
    
    Write-Host "Проверка $ServiceName... " -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ OK" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "✗ FAIL" -ForegroundColor Red
        return $false
    }
}

# Check Docker containers
Write-Host "📦 Проверка Docker контейнеров:" -ForegroundColor Yellow
Write-Host "--------------------------------"

$containers = @(
    "stock-tracker-api",
    "stock-tracker-prometheus",
    "stock-tracker-grafana",
    "stock-tracker-alertmanager",
    "stock-tracker-postgres-exporter",
    "stock-tracker-redis-exporter",
    "stock-tracker-node-exporter",
    "stock-tracker-cadvisor"
)

$allRunning = $true
foreach ($container in $containers) {
    $running = docker ps --format "{{.Names}}" | Select-String -Pattern "^$container$" -Quiet
    if ($running) {
        Write-Host "  ✓ $container" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ $container (не запущен)" -ForegroundColor Red
        $allRunning = $false
    }
}

Write-Host ""

# Check HTTP endpoints
Write-Host "🌐 Проверка HTTP endpoints:" -ForegroundColor Yellow
Write-Host "--------------------------------"

Test-Service "API Health" "http://localhost:8000/api/v1/health/" | Out-Null
Test-Service "API Metrics" "http://localhost:8000/metrics" | Out-Null
Test-Service "Prometheus" "http://localhost:9090/-/healthy" | Out-Null
Test-Service "Grafana" "http://localhost:3000/api/health" | Out-Null
Test-Service "Alertmanager" "http://localhost:9093/-/healthy" | Out-Null
Test-Service "PostgreSQL Exporter" "http://localhost:9187/metrics" | Out-Null
Test-Service "Redis Exporter" "http://localhost:9121/metrics" | Out-Null
Test-Service "Node Exporter" "http://localhost:9100/metrics" | Out-Null
Test-Service "cAdvisor" "http://localhost:8080/healthz" | Out-Null

Write-Host ""

# Check Prometheus targets
Write-Host "🎯 Проверка Prometheus targets:" -ForegroundColor Yellow
Write-Host "--------------------------------"

try {
    $targetsResponse = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -Method Get
    
    if ($targetsResponse.status -eq "success") {
        Write-Host "✓ Prometheus targets доступны" -ForegroundColor Green
        
        $targets = @("stock-tracker-api", "postgresql", "redis", "node-exporter", "cadvisor")
        
        foreach ($target in $targets) {
            $targetData = $targetsResponse.data.activeTargets | Where-Object { $_.labels.job -eq $target }
            
            if ($targetData) {
                if ($targetData.health -eq "up") {
                    Write-Host "  ✓ $target (UP)" -ForegroundColor Green
                }
                else {
                    Write-Host "  ⚠ $target (DOWN)" -ForegroundColor Yellow
                }
            }
            else {
                Write-Host "  ✗ $target (не найден)" -ForegroundColor Red
            }
        }
    }
}
catch {
    Write-Host "✗ Не удалось получить targets" -ForegroundColor Red
}

Write-Host ""

# Check metrics
Write-Host "📊 Проверка метрик API:" -ForegroundColor Yellow
Write-Host "--------------------------------"

try {
    $metricsResponse = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -Method Get -UseBasicParsing
    $metricsText = $metricsResponse.Content
    
    $metricsToCheck = @(
        "http_requests_total",
        "http_request_duration_seconds",
        "system_cpu_usage_percent",
        "system_memory_usage_bytes",
        "celery_tasks_total"
    )
    
    foreach ($metric in $metricsToCheck) {
        if ($metricsText -match "^$metric") {
            Write-Host "  ✓ $metric" -ForegroundColor Green
        }
        else {
            Write-Host "  ✗ $metric" -ForegroundColor Red
        }
    }
}
catch {
    Write-Host "✗ Не удалось получить метрики" -ForegroundColor Red
}

Write-Host ""

# Check Grafana datasources
Write-Host "📈 Проверка Grafana datasources:" -ForegroundColor Yellow
Write-Host "--------------------------------"

try {
    $credentials = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin"))
    $headers = @{ Authorization = "Basic $credentials" }
    
    $grafanaDs = Invoke-RestMethod -Uri "http://localhost:3000/api/datasources" -Method Get -Headers $headers
    
    if ($grafanaDs | Where-Object { $_.name -eq "Prometheus" }) {
        Write-Host "✓ Prometheus datasource настроен" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ Prometheus datasource не найден" -ForegroundColor Yellow
        Write-Host "  Войдите в Grafana и проверьте Configuration → Data Sources"
    }
}
catch {
    Write-Host "⚠ Не удалось проверить Grafana datasources" -ForegroundColor Yellow
}

Write-Host ""

# Check alert rules
Write-Host "🚨 Проверка Alert Rules:" -ForegroundColor Yellow
Write-Host "--------------------------------"

try {
    $rulesResponse = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/rules" -Method Get
    
    if ($rulesResponse.status -eq "success") {
        $ruleGroups = $rulesResponse.data.groups.Count
        Write-Host "✓ Alert rules загружены ($ruleGroups groups)" -ForegroundColor Green
        
        $importantAlerts = @("APIDown", "PostgreSQLDown", "HighErrorRate", "HighLatency")
        
        foreach ($alert in $importantAlerts) {
            $found = $false
            foreach ($group in $rulesResponse.data.groups) {
                if ($group.rules | Where-Object { $_.name -eq $alert }) {
                    $found = $true
                    break
                }
            }
            
            if ($found) {
                Write-Host "  ✓ $alert" -ForegroundColor Green
            }
            else {
                Write-Host "  ⚠ $alert (не найден)" -ForegroundColor Yellow
            }
        }
    }
}
catch {
    Write-Host "✗ Не удалось получить alert rules" -ForegroundColor Red
}

Write-Host ""

# Check environment variables
Write-Host "⚙️  Проверка переменных окружения:" -ForegroundColor Yellow
Write-Host "--------------------------------"

try {
    $envVars = docker-compose exec -T alertmanager env 2>$null
    
    if ($envVars -match "TELEGRAM_BOT_TOKEN") {
        Write-Host "✓ TELEGRAM_BOT_TOKEN установлен" -ForegroundColor Green
    }
    else {
        Write-Host "✗ TELEGRAM_BOT_TOKEN не установлен" -ForegroundColor Red
        Write-Host "  Добавьте в .env: TELEGRAM_BOT_TOKEN=your_token"
    }
    
    if ($envVars -match "TELEGRAM_ALERT_CHAT_ID") {
        Write-Host "✓ TELEGRAM_ALERT_CHAT_ID установлен" -ForegroundColor Green
    }
    else {
        Write-Host "✗ TELEGRAM_ALERT_CHAT_ID не установлен" -ForegroundColor Red
        Write-Host "  Добавьте в .env: TELEGRAM_ALERT_CHAT_ID=your_chat_id"
    }
}
catch {
    Write-Host "⚠ Не удалось проверить переменные окружения" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "📋 Сводка:" -ForegroundColor Yellow
Write-Host "--------------------------------"

if ($allRunning) {
    Write-Host "✓ Все контейнеры запущены" -ForegroundColor Green
}
else {
    Write-Host "✗ Некоторые контейнеры не запущены" -ForegroundColor Red
    Write-Host "  Запустите: docker-compose up -d"
}

Write-Host ""
Write-Host "🔗 Полезные ссылки:" -ForegroundColor Cyan
Write-Host "  Grafana:      http://localhost:3000"
Write-Host "  Prometheus:   http://localhost:9090"
Write-Host "  Alertmanager: http://localhost:9093"
Write-Host "  API Metrics:  http://localhost:8000/metrics"
Write-Host ""

# Test Telegram notification
$reply = Read-Host "Отправить тестовое уведомление в Telegram? (y/n)"

if ($reply -eq 'y' -or $reply -eq 'Y') {
    Write-Host "Отправка тестового сообщения..."
    
    # Load .env file
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)$') {
                $key = $matches[1]
                $value = $matches[2]
                Set-Variable -Name $key -Value $value -Scope Script
            }
        }
        
        if ($TELEGRAM_BOT_TOKEN -and $TELEGRAM_ALERT_CHAT_ID) {
            $message = @"
<b>✅ Stock Tracker Monitoring</b>

Тестовое уведомление от системы мониторинга.

<i>Если вы получили это сообщение, уведомления настроены правильно!</i>
"@
            
            $body = @{
                chat_id = $TELEGRAM_ALERT_CHAT_ID
                parse_mode = "HTML"
                text = $message
            }
            
            try {
                $response = Invoke-RestMethod `
                    -Uri "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" `
                    -Method Post `
                    -Body $body
                
                if ($response.ok) {
                    Write-Host "✓ Сообщение отправлено успешно!" -ForegroundColor Green
                    Write-Host "  Проверьте Telegram: @Enotiz"
                }
            }
            catch {
                Write-Host "✗ Ошибка отправки" -ForegroundColor Red
                Write-Host $_.Exception.Message
            }
        }
        else {
            Write-Host "⚠ TELEGRAM_BOT_TOKEN или TELEGRAM_ALERT_CHAT_ID не установлены" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "⚠ Файл .env не найден" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ Проверка завершена!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Документация:" -ForegroundColor Cyan
Write-Host "  MONITORING_QUICKSTART.md - быстрый старт"
Write-Host "  docs/MONITORING_GUIDE.md - полное руководство"
