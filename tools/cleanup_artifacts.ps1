<#
Скрипт очистки временных артефактов и генерируемых данных.
Удаляет логи, JSON отладочные файлы, временные CSV/TSV.
ВНИМАНИЕ: Удаляет файлы навсегда!
#>

param(
    [switch]$DryRun,
    [switch]$KeepLogs
)

Write-Host "=== CLEANUP ARTIFACTS START ===" -ForegroundColor Cyan

$artifactsToDelete = @()

# Лог файлы
if (-not $KeepLogs) {
    $artifactsToDelete += "sync_debug.log"
    $artifactsToDelete += "temp_log.txt"
    $artifactsToDelete += "fbs_sync_test.log"
}

# Debug JSON
$artifactsToDelete += "api_structure_debug.json"
$artifactsToDelete += "api_v2_structure_debug.json"
$artifactsToDelete += "warehouse_structure_debug.json"
$artifactsToDelete += "wb_critical_analysis.json"
$artifactsToDelete += "wb_discrepancy_analysis_report.json"
$artifactsToDelete += "excel_analysis_detailed_report.json"
$artifactsToDelete += "real_wb_test_data.json"
$artifactsToDelete += "all_tests_report.json"
$artifactsToDelete += "github_actions_test_report.json"
$artifactsToDelete += "validation_report.json"
$artifactsToDelete += "final_validation_report.json"

# Временные текстовые отчёты
$artifactsToDelete += "analysis_output.txt"
$artifactsToDelete += "comparison_result.txt"
$artifactsToDelete += "comparison_result_utf8.txt"
$artifactsToDelete += "api_warehouse_check.txt"

# CSV/TSV выгрузки с датами
$artifactsToDelete += "comparison_report.csv"
$artifactsToDelete += "Stock Tracker - Stock Tracker (1).csv"
$artifactsToDelete += "Stock Tracker - Stock Tracker (2).tsv"
$artifactsToDelete += "Stock Tracker - Stock Tracker (9).csv"

# Excel выгрузки (если нет используемых)
# $artifactsToDelete += "10-11-2025 История остатков с 04-11-2025 по 10-11-2025.xlsx"

$deletedCount = 0
$skippedCount = 0

foreach ($file in $artifactsToDelete) {
    if (Test-Path $file) {
        if ($DryRun) {
            Write-Host "[DRY] DELETE: $file" -ForegroundColor Yellow
            $deletedCount++
        } else {
            try {
                Remove-Item $file -Force
                Write-Host "[DELETE] $file" -ForegroundColor Red
                $deletedCount++
            } catch {
                Write-Warning "Failed to delete ${file}"
            }
        }
    } else {
        $skippedCount++
    }
}

Write-Host "`n=== CLEANUP COMPLETE ===" -ForegroundColor Cyan
Write-Host "Deleted: $deletedCount files" -ForegroundColor Green
Write-Host "Skipped (not found): $skippedCount files" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "`nDRY-RUN: Ничего не удалено. Запустите без -DryRun для применения." -ForegroundColor Yellow
}
