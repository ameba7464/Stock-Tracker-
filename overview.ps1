# Complete System Overview Script

Write-Host @"

╔══════════════════════════════════════════════════════════════════════╗
║         STOCK TRACKER - PRODUCTION MONITORING SYSTEM                 ║
║              Complete System Overview & Control Center               ║
╚══════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

# Quick Links
Write-Host "🌐 DASHBOARDS:" -ForegroundColor Yellow
Write-Host "  Prometheus:   http://localhost:9090" -ForegroundColor Gray
Write-Host "  Alertmanager: http://localhost:9093" -ForegroundColor Gray
Write-Host "  Grafana:      http://localhost:3000 (admin / StockTrackerMonitoring2024!)" -ForegroundColor Gray
Write-Host "  API Docs:     http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  Flower:       http://localhost:5555" -ForegroundColor Gray

# Quick Actions Menu
Write-Host "`n🛠️  QUICK ACTIONS:" -ForegroundColor Yellow
Write-Host "  1. Check Status          - .\scripts\monitoring_status.ps1" -ForegroundColor Gray
Write-Host "  2. Quick Update          - .\scripts\quick_update.ps1" -ForegroundColor Gray
Write-Host "  3. Run Maintenance       - .\scripts\maintenance.ps1" -ForegroundColor Gray
Write-Host "  4. Emergency Recovery    - .\scripts\emergency_recovery.ps1" -ForegroundColor Gray
Write-Host "  5. Setup Automation      - .\scripts\setup_automation.ps1" -ForegroundColor Gray
Write-Host "  6. Setup GitHub Secrets  - .\scripts\setup_github_secrets.ps1" -ForegroundColor Gray

# Documentation
Write-Host "`n📚 DOCUMENTATION:" -ForegroundColor Yellow
Write-Host "  Quick Start:    MONITORING_QUICKSTART.md" -ForegroundColor Gray
Write-Host "  Full Guide:     docs/MONITORING_GUIDE.md" -ForegroundColor Gray
Write-Host "  Docker Secrets: monitoring/DOCKER_SECRETS_SETUP.md" -ForegroundColor Gray
Write-Host "  CI/CD Guide:    docs/CI_CD_DEPLOYMENT_GUIDE.md" -ForegroundColor Gray
Write-Host "  Summary:        AUTOMATION_SUMMARY.md" -ForegroundColor Gray

# GitHub Actions
Write-Host "`n🚀 CI/CD PIPELINES:" -ForegroundColor Yellow
Write-Host "  View workflows: gh workflow list" -ForegroundColor Gray
Write-Host "  View runs:      gh run list --limit 10" -ForegroundColor Gray
Write-Host "  Watch run:      gh run watch" -ForegroundColor Gray
Write-Host "  Actions URL:    https://github.com/ameba7464/Stock-Tracker-/actions" -ForegroundColor Gray

# System Status
Write-Host "`n📊 CURRENT STATUS:" -ForegroundColor Yellow

# Docker containers count
$containers = docker ps --format '{{.Names}}' | Select-String 'stock-tracker' | Measure-Object
Write-Host "  Running containers: $($containers.Count)" -ForegroundColor Gray

# Prometheus targets
try {
    $targets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -TimeoutSec 5 -ErrorAction Stop
    $upTargets = ($targets.data.activeTargets | Where-Object { $_.health -eq "up" }).Count
    $totalTargets = $targets.data.activeTargets.Count
    Write-Host "  Prometheus targets: $upTargets/$totalTargets UP" -ForegroundColor Gray
} catch {
    Write-Host "  Prometheus targets: Not available" -ForegroundColor Gray
}

# Active alerts
try {
    $alerts = Invoke-RestMethod -Uri "http://localhost:9093/api/v2/alerts" -TimeoutSec 5 -ErrorAction Stop
    $activeAlerts = ($alerts | Where-Object { $_.status.state -eq "active" }).Count
    if ($activeAlerts -gt 0) {
        Write-Host "  Active alerts: $activeAlerts ⚠️" -ForegroundColor Red
    } else {
        Write-Host "  Active alerts: 0 ✅" -ForegroundColor Green
    }
} catch {
    Write-Host "  Active alerts: Not available" -ForegroundColor Gray
}

# Disk usage
$drive = Get-PSDrive C -ErrorAction SilentlyContinue
if ($drive) {
    $percentUsed = [math]::Round((($drive.Used / ($drive.Used + $drive.Free)) * 100), 0)
    $color = if ($percentUsed -gt 80) { "Red" } elseif ($percentUsed -gt 60) { "Yellow" } else { "Green" }
    Write-Host "  Disk usage: $percentUsed%" -ForegroundColor $color
}

# Scheduled tasks
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -like "StockTracker_*" }
Write-Host "  Scheduled tasks: $($tasks.Count)" -ForegroundColor Gray

Write-Host "`n💡 TIP:" -ForegroundColor Cyan
Write-Host "  Run this script anytime: " -NoNewline; Write-Host ".\overview.ps1" -ForegroundColor Yellow

Write-Host "`n" -NoNewline
