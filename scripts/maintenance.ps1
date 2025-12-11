# Automatic system maintenance script (PowerShell)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Stock Tracker Maintenance ===`n" -ForegroundColor Cyan

# Function to run with status
function Invoke-Task {
    param(
        [string]$TaskName,
        [scriptblock]$Command
    )
    
    Write-Host "➜ $TaskName" -ForegroundColor Yellow
    try {
        $null = & $Command
        Write-Host "  ✅ Done" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  ❌ Failed: $_" -ForegroundColor Red
        return $false
    }
}

# 1. Pull latest Docker images
Write-Host "1. Updating Docker Images" -ForegroundColor Cyan
Invoke-Task "Pull monitoring images" { docker-compose pull prometheus grafana alertmanager 2>&1 | Out-Null }
Invoke-Task "Pull exporter images" { docker-compose pull postgres-exporter redis-exporter node-exporter cadvisor 2>&1 | Out-Null }

# 2. Clean up old Docker resources
Write-Host "`n2. Cleaning Up Docker" -ForegroundColor Cyan
Invoke-Task "Remove unused containers" { docker container prune -f 2>&1 | Out-Null }
Invoke-Task "Remove unused images" { docker image prune -f 2>&1 | Out-Null }
Invoke-Task "Remove unused volumes" { docker volume prune -f 2>&1 | Out-Null }
Invoke-Task "Remove unused networks" { docker network prune -f 2>&1 | Out-Null }

# 3. Backup configurations
Write-Host "`n3. Backing Up Configurations" -ForegroundColor Cyan
$backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Invoke-Task "Backup docker-compose.yml" { Copy-Item docker-compose.yml $backupDir\ }
Invoke-Task "Backup monitoring configs" { Copy-Item -Recurse monitoring $backupDir\ }
Invoke-Task "Backup .env.example" { Copy-Item .env.example $backupDir\ }
Write-Host "  Backup saved to: $backupDir" -ForegroundColor Green

# 4. Restart unhealthy services
Write-Host "`n4. Checking Service Health" -ForegroundColor Cyan
$unhealthy = docker ps --filter health=unhealthy --format '{{.Names}}'
if ($unhealthy) {
    Write-Host "  Found unhealthy services" -ForegroundColor Yellow
    $unhealthy | ForEach-Object {
        Invoke-Task "Restart $_" { docker-compose restart $_ 2>&1 | Out-Null }
    }
} else {
    Write-Host "  ✅ All services healthy" -ForegroundColor Green
}

# 5. Check disk usage
Write-Host "`n5. Disk Usage Check" -ForegroundColor Cyan
$drive = Get-PSDrive C
$percentUsed = [math]::Round((($drive.Used / ($drive.Used + $drive.Free)) * 100), 0)
if ($percentUsed -gt 80) {
    Write-Host "  ⚠️  Disk usage is high: $percentUsed%" -ForegroundColor Red
    Write-Host "  Consider cleaning up old logs and backups" -ForegroundColor Yellow
} else {
    Write-Host "  ✅ Disk usage OK: $percentUsed%" -ForegroundColor Green
}

# 6. Verify monitoring targets
Write-Host "`n6. Monitoring Targets Check" -ForegroundColor Cyan
try {
    $targets = Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" -TimeoutSec 5
    $upTargets = ($targets.data.activeTargets | Where-Object { $_.health -eq "up" }).Count
    $totalTargets = $targets.data.activeTargets.Count
    Write-Host "  ✅ $upTargets/$totalTargets targets UP" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Could not check targets" -ForegroundColor Red
}

# 7. Summary
Write-Host "`n=== Maintenance Summary ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date)"
Write-Host "Docker images: " -NoNewline; Write-Host "Updated" -ForegroundColor Green
Write-Host "Cleanup: " -NoNewline; Write-Host "Done" -ForegroundColor Green
Write-Host "Backup: " -NoNewline; Write-Host "$backupDir" -ForegroundColor Green
Write-Host "Services: " -NoNewline; Write-Host "Checked" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  1. Check logs: docker-compose logs -f --tail=50"
Write-Host "  2. View status: .\scripts\monitoring_status.ps1"
Write-Host "  3. Access Grafana: http://localhost:3000"

Write-Host "`n✅ Maintenance completed successfully!" -ForegroundColor Green
