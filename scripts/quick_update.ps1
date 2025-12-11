# Quick Update Script - Pull and restart monitoring services

$ErrorActionPreference = "Continue"

Write-Host "`n=== Quick Monitoring Update ===`n" -ForegroundColor Cyan

# 1. Pull latest images
Write-Host "1. Pulling latest images..." -ForegroundColor Yellow
$services = @("prometheus", "grafana", "alertmanager", "postgres-exporter", "redis-exporter", "node-exporter", "cadvisor")

foreach ($service in $services) {
    Write-Host "  Pulling $service..." -NoNewline
    docker-compose pull $service 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ⚠️" -ForegroundColor Yellow
    }
}

# 2. Restart services
Write-Host "`n2. Restarting monitoring services..." -ForegroundColor Yellow
docker-compose up -d --force-recreate prometheus grafana alertmanager postgres-exporter redis-exporter node-exporter cadvisor

# 3. Wait for initialization
Write-Host "`n3. Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 4. Quick health check
Write-Host "`n4. Health Check:" -ForegroundColor Yellow
$checks = @{
    "Prometheus" = "http://localhost:9090/-/healthy"
    "Grafana" = "http://localhost:3000/api/health"
    "Alertmanager" = "http://localhost:9093/-/healthy"
}

foreach ($check in $checks.GetEnumerator()) {
    try {
        $response = Invoke-WebRequest -Uri $check.Value -TimeoutSec 5 -UseBasicParsing
        Write-Host "  $($check.Key): " -NoNewline
        Write-Host "✅ UP" -ForegroundColor Green
    } catch {
        Write-Host "  $($check.Key): " -NoNewline
        Write-Host "❌ DOWN" -ForegroundColor Red
    }
}

Write-Host "`n✅ Update completed!" -ForegroundColor Green
Write-Host "`nView dashboards:"
Write-Host "  Prometheus:   http://localhost:9090"
Write-Host "  Grafana:      http://localhost:3000"
Write-Host "  Alertmanager: http://localhost:9093"
