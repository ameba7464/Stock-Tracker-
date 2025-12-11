# Emergency recovery script for monitoring system (PowerShell)

$ErrorActionPreference = "Continue"

Write-Host "`n=== EMERGENCY RECOVERY MODE ===`n" -ForegroundColor Red

# 1. Stop all services
Write-Host "1. Stopping all services..." -ForegroundColor Cyan
docker-compose down
Start-Sleep -Seconds 2

# 2. Clean up problematic containers
Write-Host "`n2. Cleaning up..." -ForegroundColor Cyan
docker container prune -f
docker network prune -f

# 3. Restart PostgreSQL and Redis first
Write-Host "`n3. Starting database services..." -ForegroundColor Cyan
docker-compose up -d postgres redis
Write-Host "Waiting 10 seconds for databases..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 4. Start API and workers
Write-Host "`n4. Starting application services..." -ForegroundColor Cyan
docker-compose up -d api worker beat

# 5. Start monitoring stack
Write-Host "`n5. Starting monitoring stack..." -ForegroundColor Cyan
docker-compose up -d prometheus grafana alertmanager
docker-compose up -d postgres-exporter redis-exporter node-exporter cadvisor

# 6. Wait and check
Write-Host "`n6. Waiting for services to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# 7. Health check
Write-Host "`n7. Health Check:" -ForegroundColor Cyan
$services = @{
    "Prometheus" = "http://localhost:9090/-/healthy"
    "Grafana" = "http://localhost:3000/api/health"
    "Alertmanager" = "http://localhost:9093/-/healthy"
}

foreach ($service in $services.GetEnumerator()) {
    try {
        $response = Invoke-WebRequest -Uri $service.Value -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ $($service.Key) is UP" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ $($service.Key) is DOWN" -ForegroundColor Red
    }
}

# 8. Show status
Write-Host "`n8. Current Status:" -ForegroundColor Cyan
docker ps --format 'table {{.Names}}\t{{.Status}}'

Write-Host "`n=== Recovery process completed ===" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Check logs: docker-compose logs -f"
Write-Host "2. Run status check: .\scripts\monitoring_status.ps1"
Write-Host "3. If still issues, check individual logs:"
Write-Host "   docker logs stock-tracker-prometheus --tail 50"
Write-Host "   docker logs stock-tracker-grafana --tail 50"
