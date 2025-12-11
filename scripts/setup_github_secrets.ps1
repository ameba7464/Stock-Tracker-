# Setup GitHub Secrets for CI/CD (PowerShell version)

$ErrorActionPreference = "Stop"

Write-Host "`n=== GitHub Secrets Setup for Stock Tracker Monitoring ===`n" -ForegroundColor Cyan

# Check if gh CLI is installed
try {
    $ghVersion = gh --version
    Write-Host "✅ GitHub CLI is installed" -ForegroundColor Green
} catch {
    Write-Host "❌ GitHub CLI (gh) is not installed" -ForegroundColor Red
    Write-Host "Install it from: https://cli.github.com/" -ForegroundColor Yellow
    exit 1
}

# Check if authenticated
try {
    gh auth status 2>&1 | Out-Null
    Write-Host "✅ GitHub CLI is authenticated`n" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Not authenticated with GitHub" -ForegroundColor Yellow
    Write-Host "Running: gh auth login`n" -ForegroundColor Cyan
    gh auth login
}

# Get repository info
$repo = gh repo view --json nameWithOwner -q .nameWithOwner
Write-Host "Repository: $repo`n" -ForegroundColor Cyan

# Function to set secret
function Set-GitHubSecret {
    param(
        [string]$SecretName,
        [string]$SecretValue,
        [string]$Description
    )
    
    Write-Host "Setting secret: $SecretName" -ForegroundColor Yellow
    Write-Host "Description: $Description"
    
    if ([string]::IsNullOrEmpty($SecretValue)) {
        $SecretValue = Read-Host -Prompt "Enter value for $SecretName" -AsSecureString
        $SecretValue = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecretValue)
        )
    }
    
    $SecretValue | gh secret set $SecretName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $SecretName set successfully`n" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to set $SecretName`n" -ForegroundColor Red
    }
}

# Set monitoring secrets
Write-Host "=== Setting Monitoring Secrets ===`n" -ForegroundColor Cyan

Set-GitHubSecret -SecretName "TELEGRAM_BOT_TOKEN" -SecretValue "8558236991:AAHFu2krkBMIWFKF6W_MkIYoIFbfw-d1kms" -Description "Telegram bot token for alerts"
Set-GitHubSecret -SecretName "TELEGRAM_ALERT_CHAT_ID" -SecretValue "1651759646" -Description "Your Telegram chat ID"
Set-GitHubSecret -SecretName "GRAFANA_PASSWORD" -SecretValue "StockTrackerMonitoring2024!" -Description "Grafana admin password"

# Set deployment secrets
Write-Host "=== Setting Deployment Secrets ===`n" -ForegroundColor Cyan

Set-GitHubSecret -SecretName "PRODUCTION_HOST" -SecretValue "" -Description "Production server IP or hostname"
Set-GitHubSecret -SecretName "PRODUCTION_USER" -SecretValue "" -Description "SSH user for production server"
Set-GitHubSecret -SecretName "SSH_PRIVATE_KEY" -SecretValue "" -Description "SSH private key for production server"
Set-GitHubSecret -SecretName "SSH_PORT" -SecretValue "22" -Description "SSH port (default: 22)"

Write-Host "=== Verifying Secrets ===`n" -ForegroundColor Cyan

gh secret list

Write-Host "`n✅ All secrets have been set up!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Cyan
Write-Host "1. Push changes to trigger CI/CD: " -NoNewline
Write-Host "git push origin main" -ForegroundColor Yellow
Write-Host "2. Check workflow status: " -NoNewline
Write-Host "gh run list" -ForegroundColor Yellow
Write-Host "3. View monitoring: " -NoNewline
Write-Host "http://`$PRODUCTION_HOST:3000" -ForegroundColor Yellow

Write-Host "`nUseful commands:" -ForegroundColor Cyan
Write-Host "  gh secret list                    # List all secrets"
Write-Host "  gh secret set SECRET_NAME         # Update a secret"
Write-Host "  gh secret remove SECRET_NAME      # Remove a secret"
Write-Host "  gh run watch                      # Watch latest workflow run"
