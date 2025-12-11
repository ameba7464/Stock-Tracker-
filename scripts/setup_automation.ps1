# Setup automated tasks (Windows Task Scheduler) for Stock Tracker

$ErrorActionPreference = "Stop"

Write-Host "`n=== Setting up automated tasks ===" -ForegroundColor Cyan

$projectDir = Split-Path -Parent $PSScriptRoot

Write-Host "`nProject directory: $projectDir`n" -ForegroundColor Yellow

# Function to create scheduled task
function New-StockTrackerTask {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Schedule,
        [string]$Description
    )
    
    Write-Host "Creating task: $TaskName" -ForegroundColor Yellow
    
    # Delete if exists
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    $action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    
    $trigger = switch ($Schedule) {
        "Daily3AM" { New-ScheduledTaskTrigger -Daily -At 3am }
        "Every6Hours" { 
            $t = New-ScheduledTaskTrigger -Daily -At 12am
            $t.Repetition = (New-ScheduledTaskTrigger -Once -At 12am -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration ([TimeSpan]::MaxValue)).Repetition
            $t
        }
        "WeeklySunday2AM" { New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2am }
        "Daily1AM" { New-ScheduledTaskTrigger -Daily -At 1am }
        "Daily4AM" { New-ScheduledTaskTrigger -Daily -At 4am }
        "Every4Hours" {
            $t = New-ScheduledTaskTrigger -Daily -At 12am
            $t.Repetition = (New-ScheduledTaskTrigger -Once -At 12am -RepetitionInterval (New-TimeSpan -Hours 4) -RepetitionDuration ([TimeSpan]::MaxValue)).Repetition
            $t
        }
    }
    
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description $Description
    
    Write-Host "  ✅ Created" -ForegroundColor Green
}

# Create tasks
Write-Host "`nCreating scheduled tasks...`n" -ForegroundColor Cyan

New-StockTrackerTask `
    -TaskName "StockTracker_DailyMaintenance" `
    -ScriptPath "$projectDir\scripts\maintenance.ps1" `
    -Schedule "Daily3AM" `
    -Description "Daily maintenance: Docker cleanup, backup, health check"

New-StockTrackerTask `
    -TaskName "StockTracker_HealthCheck" `
    -ScriptPath "$projectDir\scripts\monitoring_status.ps1" `
    -Schedule "Every6Hours" `
    -Description "Check monitoring system health every 6 hours"

New-StockTrackerTask `
    -TaskName "StockTracker_DockerCleanup" `
    -ScriptPath "$projectDir\scripts\docker_cleanup.ps1" `
    -Schedule "WeeklySunday2AM" `
    -Description "Weekly Docker cleanup: remove unused containers, images, volumes"

New-StockTrackerTask `
    -TaskName "StockTracker_ConfigBackup" `
    -ScriptPath "$projectDir\scripts\backup_configs.ps1" `
    -Schedule "Daily1AM" `
    -Description "Backup monitoring configurations daily"

# Create backup script if not exists
$backupScript = @'
# Backup configurations
$backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item docker-compose.yml $backupDir\
Copy-Item -Recurse monitoring $backupDir\
Copy-Item .env.example $backupDir\
Write-Host "Backup created: $backupDir"
'@
Set-Content -Path "$projectDir\scripts\backup_configs.ps1" -Value $backupScript

# Create cleanup script
$cleanupScript = @'
# Docker cleanup
docker system prune -af --volumes
Write-Host "Docker cleanup completed"
'@
Set-Content -Path "$projectDir\scripts\docker_cleanup.ps1" -Value $cleanupScript

# List created tasks
Write-Host "`n=== Created Tasks ===" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -like "StockTracker_*" } | Format-Table TaskName, State, @{Name="NextRun";Expression={$_.NextRunTime}}

Write-Host "`n✅ Automated tasks configured successfully!" -ForegroundColor Green

Write-Host "`nScheduled tasks:" -ForegroundColor Cyan
Write-Host "  • Daily maintenance:    3:00 AM"
Write-Host "  • Health checks:        Every 6 hours"
Write-Host "  • Docker cleanup:       Sunday 2:00 AM"
Write-Host "  • Configuration backup: 1:00 AM"

Write-Host "`nUseful commands:" -ForegroundColor Cyan
Write-Host "  View tasks:   Get-ScheduledTask | Where-Object { `$_.TaskName -like 'StockTracker_*' }"
Write-Host "  Run task:     Start-ScheduledTask -TaskName 'StockTracker_HealthCheck'"
Write-Host "  Remove task:  Unregister-ScheduledTask -TaskName 'StockTracker_HealthCheck'"
Write-Host "  View history: Get-ScheduledTaskInfo -TaskName 'StockTracker_HealthCheck'"
