# Backup configurations
$backupDir = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item docker-compose.yml $backupDir\
Copy-Item -Recurse monitoring $backupDir\
Copy-Item .env.example $backupDir\
Write-Host "Backup created: $backupDir"
