@echo off
echo 🚀 Starting Stock Tracker Sync...
echo ================================

cd "C:\Users\miros\Downloads\Stock Tracker\Stock-Tracker"

echo 📅 Starting sync at %date% %time%

"C:/Users/miros/Downloads/Stock Tracker/Stock-Tracker/.venv/Scripts/python.exe" run_full_sync.py

if %ERRORLEVEL% EQU 0 (
    echo ✅ Sync completed successfully!
) else (
    echo ❌ Sync failed with error code %ERRORLEVEL%
)

echo 📅 Completed at %date% %time%
echo ================================