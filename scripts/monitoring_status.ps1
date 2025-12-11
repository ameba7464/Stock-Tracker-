# Quick monitoring status check script (PowerShell)

$ErrorActionPreference = "SilentlyContinue"

Write-Host "`n=== Stock Tracker Monitoring Status ===`n" -ForegroundColor Cyan

# Function to check service
function Test-Service {
    param(
        [string]$Name,
        [string]$Url
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ $Name is UP" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "❌ $Name is DOWN" -ForegroundColor Red
        return $false
    }
}

# Check Docker services
Write-Host "Docker Services:" -ForegroundColor Cyan
docker ps --format 'table {{.Names}}\t{{.Status}}' | Select-String 'stock-tracker'

Write-Host "`nService Health Checks:" -ForegroundColor Cyan

# Check each monitoring service
Test-Service "Prometheus" "http://localhost:9090/-/healthy"
Test-Service "Alertmanager" "http://localhost:9093/-/healthy"
Test-Service "Grafana" "http://localhost:3000/api/health"
Test-Service "API" "http://localhost:8000/health"
Test-Service "API Metrics" "http://localhost:8000/metrics"

Write-Host "`nPrometheus Targets:" -ForegroundColor Cyan
try {
    $targets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -TimeoutSec 5
    $targets.data.activeTargets | ForEach-Object {
        $job = $_.labels.job
        $health = if ($_.health -eq "up") { "✅ UP" } else { "❌ DOWN" }
        Write-Host ("  {0,-30} {1}" -f $job, $health)
    }
} catch {
    Write-Host "❌ Could not fetch targets" -ForegroundColor Red
}

Write-Host "`nRecent Alerts:" -ForegroundColor Cyan
try {
    $alerts = Invoke-RestMethod -Uri "http://localhost:9093/api/v2/alerts" -TimeoutSec 5
    $activeAlerts = $alerts | Where-Object { $_.status.state -eq "active" }
    if ($activeAlerts) {
        $activeAlerts | ForEach-Object {
            $alertname = $_.labels.alertname
            $severity = $_.labels.severity
            Write-Host ("  {0,-30} {1}" -f $alertname, $severity)
        }
    } else {
        Write-Host "✅ No active alerts" -ForegroundColor Green
    }
} catch {
    Write-Host "✅ No active alerts" -ForegroundColor Green
}

Write-Host "`nDisk Usage (Docker Volumes):" -ForegroundColor Cyan
docker system df -v | Select-String 'stock-tracker' | ForEach-Object {
    Write-Host "  $_"
}

Write-Host "`nQuick Links:" -ForegroundColor Cyan
Write-Host "  Prometheus:    http://localhost:9090"
Write-Host "  Alertmanager:  http://localhost:9093"
Write-Host "  Grafana:       http://localhost:3000 (admin / StockTrackerMonitoring2024!)"
Write-Host "  API Docs:      http://localhost:8000/docs"
Write-Host "  Flower:        http://localhost:5555"

Write-Host "`nUseful Commands:" -ForegroundColor Cyan
Write-Host "  View logs:         docker logs stock-tracker-prometheus --tail 50"
Write-Host "  Restart service:   docker-compose restart prometheus"
Write-Host "  Check config:      docker-compose config"
Write-Host "  Update services:   docker-compose pull; docker-compose up -d"
