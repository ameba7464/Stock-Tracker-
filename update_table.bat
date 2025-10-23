@echo off
REM Скрипт для обновления таблицы Stock Tracker
REM Получает свежие данные из Wildberries API и обновляет Google Sheets

echo.
echo ================================================
echo       STOCK TRACKER - ОБНОВЛЕНИЕ ТАБЛИЦЫ
echo ================================================
echo.

REM Переходим в директорию проекта
cd /d "%~dp0"

echo 📋 Проверяем окружение...

REM Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден. Установите Python и добавьте его в PATH
    pause
    exit /b 1
)

REM Проверяем наличие файлов конфигурации
if not exist "config\service-account.json" (
    echo ❌ Файл service-account.json не найден в папке config\
    echo    Скопируйте файл сервисного аккаунта Google в config\service-account.json
    pause
    exit /b 1
)

if not exist ".env" (
    echo ❌ Файл .env не найден
    echo    Создайте файл .env с настройками API ключей
    pause
    exit /b 1
)

echo ✅ Окружение готово
echo.

echo 🔄 Запускаем обновление таблицы...
echo    - Подключение к Wildberries API
echo    - Получение данных об остатках и заказах
echo    - Расчет показателей оборачиваемости
echo    - Обновление Google Sheets
echo.

REM Запускаем обновление через основной модуль
python -m src.stock_tracker.main --update-table

if %errorlevel% equ 0 (
    echo.
    echo ✅ ОБНОВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!
    echo 📊 Данные в Google Sheets обновлены
) else (
    echo.
    echo ❌ ОШИБКА ПРИ ОБНОВЛЕНИИ!
    echo 📝 Проверьте логи для получения подробной информации
    echo.
    echo 💡 Частые проблемы:
    echo    - Проверьте настройку GOOGLE_SHEET_ID в .env файле
    echo    - Убедитесь что service-account.json находится в папке config\
    echo    - Проверьте что API ключ Wildberries корректный
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul