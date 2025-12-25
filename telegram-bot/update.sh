#!/bin/bash

# Quick update script for production bot
# Updates only the code without touching credentials

set -e

BOT_DIR="/opt/stock-tracker-bot"
BACKUP_DIR="/opt/stock-tracker-bot.backup.$(date +%Y%m%d_%H%M%S)"

echo "=== Quick Update Script ==="
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: This script must be run as root" 
   exit 1
fi

echo "[1/5] Stopping bot service..."
systemctl stop stock-tracker-bot
echo "✓ Service stopped"

echo ""
echo "[2/5] Creating backup..."
cp -r $BOT_DIR $BACKUP_DIR
echo "✓ Backup created: $BACKUP_DIR"

echo ""
echo "[3/5] Updating code..."
# Assume new code is in /tmp/telegram-bot-update/
if [ -d "/tmp/telegram-bot-update/app" ]; then
    rm -rf $BOT_DIR/app
    cp -r /tmp/telegram-bot-update/app $BOT_DIR/
    
    if [ -f "/tmp/telegram-bot-update/requirements.txt" ]; then
        cp /tmp/telegram-bot-update/requirements.txt $BOT_DIR/
        echo "Installing new dependencies..."
        cd $BOT_DIR
        sudo -u stock-bot venv/bin/pip install -r requirements.txt
    fi
    
    chown -R stock-bot:stock-bot $BOT_DIR/app
    echo "✓ Code updated"
else
    echo "ERROR: No code found in /tmp/telegram-bot-update/"
    echo "Please upload new code there first"
    exit 1
fi

echo ""
echo "[4/5] Testing new code..."
cd $BOT_DIR
if sudo -u stock-bot venv/bin/python -c "from app.config import settings; print('Test: OK')"; then
    echo "✓ Code test passed"
else
    echo "ERROR: Code test failed!"
    echo "Rolling back..."
    systemctl stop stock-tracker-bot
    rm -rf $BOT_DIR
    mv $BACKUP_DIR $BOT_DIR
    systemctl start stock-tracker-bot
    echo "Rollback complete. Old version is running."
    exit 1
fi

echo ""
echo "[5/5] Starting bot service..."
systemctl start stock-tracker-bot
sleep 3

if systemctl is-active --quiet stock-tracker-bot; then
    echo "✓ Service started successfully"
    echo ""
    echo "=== Update Complete ==="
    echo ""
    echo "Backup location: $BACKUP_DIR"
    echo "Check logs: journalctl -u stock-tracker-bot -f"
else
    echo "ERROR: Service failed to start!"
    echo "Check logs: journalctl -u stock-tracker-bot -n 50"
    echo ""
    echo "To rollback, run:"
    echo "  systemctl stop stock-tracker-bot"
    echo "  rm -rf $BOT_DIR"
    echo "  mv $BACKUP_DIR $BOT_DIR"
    echo "  systemctl start stock-tracker-bot"
    exit 1
fi
