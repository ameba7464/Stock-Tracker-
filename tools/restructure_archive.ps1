<#
Скрипт полуавтоматической реструктуризации: переносит вспомогательные скрипты в `archive/`.
Безопасен: использует `git mv` если доступен, иначе `Move-Item`.
Запускать из каталога `Stock-Tracker` (где лежат скрипты).
#>

param(
    [switch]$DryRun,
    [switch]$IncludeV2,
    [switch]$MoveUpdateProducts
)

Write-Host "=== ARCHIVE RESTRUCTURE START ===" -ForegroundColor Cyan

function Ensure-Folder($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

$archiveRoot = "archive"
$folders = @("analysis","checks","debug","fixes","verification","tests","demo","legacy","misc")
foreach ($f in $folders) { Ensure-Folder (Join-Path $archiveRoot $f) }

function Move-IfMatch {
    param(
        [string]$Pattern,
        [string]$Target
    )
    Get-ChildItem -File -Name $Pattern -ErrorAction SilentlyContinue | ForEach-Object {
        $src = $_
        $destFolder = Join-Path $archiveRoot $Target
        $dest = Join-Path $destFolder $src
        if ($DryRun) {
            Write-Host "[DRY] $src -> $archiveRoot/$Target/" -ForegroundColor Yellow
        } else {
            Write-Host "[MOVE] $src -> $archiveRoot/$Target/" -ForegroundColor Green
            try {
                git mv $src $dest 2>$null
                if ($LASTEXITCODE -ne 0) { Move-Item $src $dest -Force }
            } catch { Write-Warning "Failed move $src" }
        }
    }
}

# 1 Analysis
Move-IfMatch "analyze_*.py" "analysis"
Move-IfMatch "compare_*.py" "analysis"
Move-IfMatch "final_comparison*.py" "legacy"

# 2 Checks
Move-IfMatch "check_*.py" "checks"

# 3 Debug / Diagnose
Move-IfMatch "debug_*.py" "debug"
Move-IfMatch "diagnose_*.py" "debug"

# 4 Fixes
Move-IfMatch "fix_*.py" "fixes"
Move-IfMatch "quick_fix_warehouse_data.py" "fixes"
Move-IfMatch "prepare_order_fix.py" "fixes"
Move-IfMatch "restore_warehouse_data.py" "fixes"
Move-IfMatch "clean_warehouse_data.py" "fixes"
if ($MoveUpdateProducts) { Move-IfMatch "update_products.py" "fixes" }

# 5 Verification
Move-IfMatch "verify_*.py" "verification"
Move-IfMatch "final_verification*.py" "verification"

# 6 Demo
Move-IfMatch "simulate_correct_table.py" "demo"
Move-IfMatch "simple_table_analyzer.py" "demo"
Move-IfMatch "show_analysis_summary.py" "demo"
Move-IfMatch "show_expected_changes.py" "demo"

# 7 Non-standard tests
Move-IfMatch "test_problematic_articles.py" "tests"
Move-IfMatch "test_warehouse_normalization.py" "tests"
Move-IfMatch "run_all_tests.py" "tests"

# 8 Versioned *_v2 (optional)
if ($IncludeV2) { Move-IfMatch "*_v2.py" "legacy" }

Write-Host "=== ARCHIVE RESTRUCTURE COMPLETE ===" -ForegroundColor Cyan
if ($DryRun) { Write-Host "DRY-RUN: Ничего не перенесено. Запустите без -DryRun для применения." -ForegroundColor Yellow }
else { Write-Host "Проверьте git status и выполните commit." -ForegroundColor Green }
