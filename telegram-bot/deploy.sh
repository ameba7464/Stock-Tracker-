#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Stock Tracker Bot - Deploy to Server${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Проверка root прав
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root${NC}" 
   exit 1
fi

# Переменные
BOT_USER="stock-bot"
BOT_DIR="/opt/stock-tracker-bot"
LOG_DIR="/var/log/stock-tracker-bot"
SERVICE_NAME="stock-tracker-bot"

echo -e "${YELLOW}[1/8] Creating user and directories...${NC}"
# Создание пользователя
if ! id "$BOT_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d $BOT_DIR $BOT_USER
    echo -e "${GREEN}✓ User $BOT_USER created${NC}"
else
    echo -e "${GREEN}✓ User $BOT_USER already exists${NC}"
fi

# Создание директорий
mkdir -p $BOT_DIR
mkdir -p $LOG_DIR
mkdir -p $BOT_DIR/logs
echo -e "${GREEN}✓ Directories created${NC}"

echo -e "\n${YELLOW}[2/8] Installing system dependencies...${NC}"
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip postgresql-client curl
echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "\n${YELLOW}[3/8] Copying files...${NC}"
# Копирование файлов (запустить из директории с ботом)
if [ -d "app" ]; then
    cp -r app $BOT_DIR/
    cp requirements.txt $BOT_DIR/
    cp credentials.json $BOT_DIR/ 2>/dev/null || echo "credentials.json not found, will need to add manually"
    cp token.json $BOT_DIR/ 2>/dev/null || echo "token.json not found (OAuth - optional)"
    cp .env $BOT_DIR/
    echo -e "${GREEN}✓ Files copied${NC}"
else
    echo -e "${RED}[ERROR] Run this script from telegram-bot directory${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[4/8] Creating Python virtual environment...${NC}"
cd $BOT_DIR
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo -e "${GREEN}✓ Virtual environment created${NC}"

echo -e "\n${YELLOW}[5/8] Setting permissions...${NC}"
chown -R $BOT_USER:$BOT_USER $BOT_DIR
chown -R $BOT_USER:$BOT_USER $LOG_DIR
chmod 600 $BOT_DIR/.env
chmod 600 $BOT_DIR/credentials.json 2>/dev/null
chmod 600 $BOT_DIR/token.json 2>/dev/null
echo -e "${GREEN}✓ Permissions set${NC}"

echo -e "\n${YELLOW}[6/8] Testing database connection...${NC}"
cd $BOT_DIR
su - $BOT_USER -c "cd $BOT_DIR && source venv/bin/activate && python -c 'import asyncio; from app.database.database import init_db; asyncio.run(init_db()); print(\"Database connection: OK\")'"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}[WARNING] Database connection failed. Check .env settings${NC}"
fi

echo -e "\n${YELLOW}[7/8] Installing systemd service...${NC}"
# Копирование service file
if [ -f "../stock-tracker-bot.service" ]; then
    cp ../stock-tracker-bot.service /etc/systemd/system/
else
    cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=Stock Tracker Telegram Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=stock-bot
Group=stock-bot
WorkingDirectory=/opt/stock-tracker-bot
Environment="PYTHONUNBUFFERED=1"
Environment="PYTHONUTF8=1"
Environment="TZ=Europe/Moscow"
EnvironmentFile=/opt/stock-tracker-bot/.env
ExecStart=/opt/stock-tracker-bot/venv/bin/python -m app.main
Restart=always
RestartSec=10
StandardOutput=append:/var/log/stock-tracker-bot/bot.log
StandardError=append:/var/log/stock-tracker-bot/error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/stock-tracker-bot /opt/stock-tracker-bot/logs

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable $SERVICE_NAME
echo -e "${GREEN}✓ Systemd service installed${NC}"

echo -e "\n${YELLOW}[8/8] Starting bot service...${NC}"
systemctl start $SERVICE_NAME
sleep 3

# Проверка статуса
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Bot service started successfully!${NC}"
else
    echo -e "${RED}[ERROR] Bot service failed to start${NC}"
    echo -e "${YELLOW}Check logs: journalctl -u $SERVICE_NAME -n 50${NC}"
    exit 1
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${YELLOW}Useful commands:${NC}"
echo -e "  Status:  ${GREEN}systemctl status $SERVICE_NAME${NC}"
echo -e "  Logs:    ${GREEN}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  Restart: ${GREEN}systemctl restart $SERVICE_NAME${NC}"
echo -e "  Stop:    ${GREEN}systemctl stop $SERVICE_NAME${NC}"
echo -e "\n${YELLOW}Log files:${NC}"
echo -e "  Bot log:   ${GREEN}tail -f $LOG_DIR/bot.log${NC}"
echo -e "  Error log: ${GREEN}tail -f $LOG_DIR/error.log${NC}"
echo -e ""
