# PowerShell script to setup Windows Task Scheduler for Stock Tracker
# Runs automatically every day at 2 AM (can be customized)

$taskName = "Stock Tracker Auto Sync"
$scriptPath = "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker\auto_sync.bat"
$workingDir = "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Stock Tracker - Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Old task removed." -ForegroundColor Green
}

# Create the action
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $workingDir

# Create the trigger (daily at 2 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 2am

# Create task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew

# Create the principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the scheduled task
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Automatically synchronizes Stock Tracker data with Wildberries API and updates Google Sheets daily at 2 AM"

Write-Host ""
Write-Host "Task created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Task Details:" -ForegroundColor Cyan
Write-Host "  Name: $taskName" -ForegroundColor White
Write-Host "  Schedule: Daily at 2:00 AM" -ForegroundColor White
Write-Host "  Script: $scriptPath" -ForegroundColor White
Write-Host ""
Write-Host "To modify schedule:" -ForegroundColor Yellow
Write-Host "  1. Open Task Scheduler (taskschd.msc)" -ForegroundColor White
Write-Host "  2. Find 'Stock Tracker Auto Sync'" -ForegroundColor White
Write-Host "  3. Right-click -> Properties -> Triggers" -ForegroundColor White
Write-Host ""
Write-Host "To test now:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host ""
Write-Host "To disable:" -ForegroundColor Yellow
Write-Host "  Disable-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
