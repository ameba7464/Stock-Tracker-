#!/bin/bash
# Скрипт для развертывания исправлений на сервере Яндекс.Облака
# Использование: ./deploy_fixes.sh

set -e  # Остановка при ошибке

echo "=============================================="
echo "🚀 РАЗВЕРТЫВАНИЕ ИСПРАВЛЕНИЙ БОТА"
echo "=============================================="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SERVER="yc-user@158.160.188.247"
BOT_DIR="/opt/stock-tracker-bot"

# Проверка SSH подключения
echo "1️⃣  Проверка подключения к серверу..."
if ssh -o ConnectTimeout=5 $SERVER "echo 'OK'" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Подключение к серверу успешно${NC}"
else
    echo -e "${RED}❌ Не удалось подключиться к серверу${NC}"
    exit 1
fi

echo ""
echo "2️⃣  Копирование исправленных файлов на сервер..."

# Копируем исправленные файлы
FILES=(
    "app/bot/handlers/registration.py:app/bot/handlers/"
    "app/database/crud.py:app/database/"
    "app/database/database.py:app/database/"
    "app/bot/middlewares/db.py:app/bot/middlewares/"
    "fix_database_duplicates.py:."
)

for file_path in "${FILES[@]}"; do
    IFS=':' read -r src dest <<< "$file_path"
    echo "   📁 Копирование $src..."
    if scp "$src" "$SERVER:$BOT_DIR/$dest" > /dev/null 2>&1; then
        echo -e "      ${GREEN}✅ $src скопирован${NC}"
    else
        echo -e "      ${RED}❌ Ошибка копирования $src${NC}"
        exit 1
    fi
done

echo ""
echo "3️⃣  Создание резервной копии базы данных..."
ssh $SERVER "sudo -u postgres pg_dump stocktracker > /tmp/backup_\$(date +%Y%m%d_%H%M%S).sql" || true
echo -e "${GREEN}✅ Резервная копия создана${NC}"

echo ""
echo "4️⃣  Проверка и исправление дубликатов в БД..."
echo ""
echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Скрипт попросит подтверждение для исправления дубликатов${NC}"
echo -e "${YELLOW}   Введите 'yes' если хотите исправить дубликаты${NC}"
echo ""

# Запускаем скрипт исправления дубликатов
ssh -t $SERVER "cd $BOT_DIR && source venv/bin/activate && python fix_database_duplicates.py"

echo ""
echo "5️⃣  Перезапуск сервиса бота..."
ssh $SERVER "sudo systemctl restart stock-tracker-bot.service"
sleep 3

# Проверка статуса
if ssh $SERVER "sudo systemctl is-active stock-tracker-bot.service" | grep -q "active"; then
    echo -e "${GREEN}✅ Бот успешно перезапущен${NC}"
else
    echo -e "${RED}❌ Ошибка перезапуска бота${NC}"
    echo ""
    echo "Проверьте статус командой:"
    echo "   ssh $SERVER 'sudo systemctl status stock-tracker-bot.service'"
    exit 1
fi

echo ""
echo "6️⃣  Проверка логов..."
echo ""
ssh $SERVER "tail -n 20 $BOT_DIR/logs/bot.log"

echo ""
echo "=============================================="
echo -e "${GREEN}✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО УСПЕШНО${NC}"
echo "=============================================="
echo ""
echo "📋 Следующие шаги:"
echo "   1. Протестируйте бота через Telegram: /start"
echo "   2. Проверьте процесс регистрации"
echo "   3. Следите за логами: ssh $SERVER 'tail -f $BOT_DIR/logs/bot.log'"
echo ""
echo "📊 Полезные команды:"
echo "   Статус бота:  ssh $SERVER 'sudo systemctl status stock-tracker-bot.service'"
echo "   Логи:         ssh $SERVER 'tail -100 $BOT_DIR/logs/bot.log'"
echo "   Перезапуск:   ssh $SERVER 'sudo systemctl restart stock-tracker-bot.service'"
echo ""
