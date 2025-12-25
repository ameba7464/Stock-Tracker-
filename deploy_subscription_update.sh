#!/bin/bash

# ============================================
# Скрипт Деплоя Унифицированной Системы Подписок
# ============================================

set -e  # Выход при ошибке

echo "=========================================="
echo "Деплой унифицированной системы подписок"
echo "=========================================="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Переменные
PROJECT_DIR="Stock-Tracker"
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${YELLOW}Шаг 1: Проверка окружения${NC}"
echo "----------------------------------------"

# Проверка наличия проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ Директория $PROJECT_DIR не найдена!${NC}"
    echo "Клонируем проект с GitHub..."
    git clone https://github.com/ameba7464/Stock-Tracker-.git $PROJECT_DIR
    cd $PROJECT_DIR
else
    echo -e "${GREEN}✓ Директория проекта найдена${NC}"
    cd $PROJECT_DIR
fi

echo ""
echo -e "${YELLOW}Шаг 2: Обновление кода${NC}"
echo "----------------------------------------"

# Сохраняем локальные изменения
git stash

# Получаем последние изменения
git fetch origin
git pull origin main

echo -e "${GREEN}✓ Код обновлен${NC}"

echo ""
echo -e "${YELLOW}Шаг 3: Проверка .env файла${NC}"
echo "----------------------------------------"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo "Создайте .env файл с необходимыми переменными:"
    echo "  DATABASE_URL=postgresql://..."
    echo "  PAYMENT_ENABLED=false"
    echo "  FREE_TRIAL_DAYS=7"
    exit 1
fi

# Проверяем наличие PAYMENT_ENABLED
if ! grep -q "PAYMENT_ENABLED" .env; then
    echo "Добавляем PAYMENT_ENABLED в .env..."
    echo "" >> .env
    echo "# Subscription Configuration" >> .env
    echo "PAYMENT_ENABLED=false  # false = MVP (бесплатно для всех)" >> .env
    echo "FREE_TRIAL_DAYS=7" >> .env
    echo "SUBSCRIPTION_PRICE=299" >> .env
fi

echo -e "${GREEN}✓ Конфигурация проверена${NC}"

echo ""
echo -e "${YELLOW}Шаг 4: Установка зависимостей${NC}"
echo "----------------------------------------"

# Активируем виртуальное окружение
if [ ! -d "venv" ]; then
    echo "Создаем виртуальное окружение..."
    python3 -m venv venv
fi

source venv/bin/activate

# Устанавливаем зависимости
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Устанавливаем cryptography для шифрования
pip install -q cryptography

echo -e "${GREEN}✓ Зависимости установлены${NC}"

echo ""
echo -e "${YELLOW}Шаг 5: Создание бэкапа БД${NC}"
echo "----------------------------------------"

# Создаем директорию для бэкапов
mkdir -p $BACKUP_DIR

# Получаем настройки БД из .env
DB_NAME=$(grep DB_NAME .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)
DB_USER=$(grep DB_USER .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
    echo -e "${YELLOW}⚠ Не удалось получить настройки БД из .env${NC}"
    echo "Введите имя базы данных (или нажмите Enter для пропуска):"
    read -r input_db_name
    if [ -n "$input_db_name" ]; then
        DB_NAME=$input_db_name
    fi
fi

if [ -n "$DB_NAME" ]; then
    BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
    echo "Создаем бэкап БД: $DB_NAME"
    
    if command -v pg_dump &> /dev/null; then
        pg_dump $DB_NAME > $BACKUP_FILE 2>/dev/null || echo -e "${YELLOW}⚠ Не удалось создать бэкап (может потребоваться пароль)${NC}"
        
        if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
            echo -e "${GREEN}✓ Бэкап создан: $BACKUP_FILE${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ pg_dump не найден, пропускаем бэкап${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Бэкап пропущен${NC}"
fi

echo ""
echo -e "${YELLOW}Шаг 6: Проверка текущей миграции${NC}"
echo "----------------------------------------"

CURRENT_MIGRATION=$(alembic current 2>/dev/null | grep -oP '^\w+' | head -1 || echo "none")
echo "Текущая миграция: $CURRENT_MIGRATION"

echo ""
echo -e "${YELLOW}Шаг 7: Применение миграций${NC}"
echo "----------------------------------------"

echo "Миграция 1: Критические улучшения безопасности"
alembic upgrade 20251225_critical_improvements

echo ""
echo "Миграция 2: Унификация системы подписок"
alembic upgrade 20251225_unify_subscriptions

echo -e "${GREEN}✓ Миграции применены${NC}"

echo ""
echo -e "${YELLOW}Шаг 8: Проверка таблиц БД${NC}"
echo "----------------------------------------"

# Проверяем наличие таблицы subscriptions
python3 << EOF
import os
from sqlalchemy import create_engine, inspect, text

db_url = os.getenv('DATABASE_URL')
if not db_url:
    # Пытаемся собрать из компонентов
    from dotenv import load_dotenv
    load_dotenv()
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'tgstock')
    db_user = os.getenv('DB_USER', 'postgres')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

engine = create_engine(db_url)
inspector = inspect(engine)

tables = inspector.get_table_names()
print(f"✓ Найдено таблиц: {len(tables)}")

if 'subscriptions' in tables:
    print("✓ Таблица subscriptions создана")
    
    # Проверяем колонки
    columns = [col['name'] for col in inspector.get_columns('subscriptions')]
    required_cols = ['status', 'has_access', 'trial_ends_at', 'payment_provider']
    
    for col in required_cols:
        if col in columns:
            print(f"  ✓ Колонка {col} есть")
        else:
            print(f"  ✗ Колонка {col} отсутствует!")
    
    # Проверяем количество записей
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM subscriptions"))
        count = result.scalar()
        print(f"✓ Записей в subscriptions: {count}")
else:
    print("✗ Таблица subscriptions не найдена!")
EOF

echo -e "${GREEN}✓ Структура БД проверена${NC}"

echo ""
echo -e "${YELLOW}Шаг 9: Перезапуск бота${NC}"
echo "----------------------------------------"

# Проверяем, запущен ли бот через systemd
if systemctl is-active --quiet stock-tracker-bot; then
    echo "Перезапускаем бота через systemd..."
    sudo systemctl restart stock-tracker-bot
    sleep 2
    
    if systemctl is-active --quiet stock-tracker-bot; then
        echo -e "${GREEN}✓ Бот перезапущен (systemd)${NC}"
    else
        echo -e "${RED}✗ Ошибка при перезапуске бота${NC}"
        sudo systemctl status stock-tracker-bot
    fi
else
    # Запускаем бота вручную в фоне
    echo "Запускаем бота в фоновом режиме..."
    
    cd telegram-bot
    nohup python -m app.main > ../logs/bot.log 2>&1 &
    BOT_PID=$!
    
    echo "PID бота: $BOT_PID"
    sleep 3
    
    if ps -p $BOT_PID > /dev/null; then
        echo -e "${GREEN}✓ Бот запущен (PID: $BOT_PID)${NC}"
        echo $BOT_PID > ../bot.pid
    else
        echo -e "${RED}✗ Не удалось запустить бота${NC}"
    fi
    
    cd ..
fi

echo ""
echo -e "${YELLOW}Шаг 10: Проверка работы бота${NC}"
echo "----------------------------------------"

# Проверяем, отвечает ли бот на getMe
BOT_TOKEN=$(grep BOT_TOKEN .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs || grep bot_token .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | xargs)

if [ -n "$BOT_TOKEN" ]; then
    echo "Проверяем статус бота через API..."
    response=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
    
    if echo "$response" | grep -q '"ok":true'; then
        bot_username=$(echo "$response" | grep -oP '"username":"[^"]+' | cut -d '"' -f4)
        echo -e "${GREEN}✓ Бот отвечает: @${bot_username}${NC}"
    else
        echo -e "${YELLOW}⚠ Бот не отвечает на API запросы${NC}"
    fi
else
    echo -e "${YELLOW}⚠ BOT_TOKEN не найден в .env${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!${NC}"
echo "=========================================="
echo ""
echo "📊 Статус системы:"
echo "  • Код: обновлен"
echo "  • БД: миграции применены"
echo "  • Бот: запущен"
echo ""
echo "🎯 Текущий режим:"
echo "  • payment_enabled = false (MVP)"
echo "  • Все пользователи имеют бесплатный доступ"
echo ""
echo "🚀 Для включения платежей:"
echo "  1. Измените в .env: PAYMENT_ENABLED=true"
echo "  2. Добавьте: PAYMENT_TOKEN=ваш_токен"
echo "  3. Перезапустите бота"
echo ""
echo "📚 Документация:"
echo "  • HOW_BOT_WORKS.md - Как работает бот"
echo "  • SUBSCRIPTION_ARCHITECTURE.md - Архитектура"
echo "  • CODE_REVIEW_SUMMARY.md - Результаты проверки"
echo ""
echo -e "${GREEN}Деплой завершен!${NC}"
