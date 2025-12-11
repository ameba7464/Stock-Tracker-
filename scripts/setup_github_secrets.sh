#!/bin/bash
# Setup GitHub Secrets for CI/CD

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== GitHub Secrets Setup for Stock Tracker Monitoring ===${NC}\n"

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) is not installed${NC}"
    echo -e "${YELLOW}Install it from: https://cli.github.com/${NC}"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Not authenticated with GitHub${NC}"
    echo -e "${CYAN}Running: gh auth login${NC}"
    gh auth login
fi

echo -e "${GREEN}✅ GitHub CLI is authenticated${NC}\n"

# Get repository info
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo -e "${CYAN}Repository: ${REPO}${NC}\n"

# Function to set secret
set_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3
    
    echo -e "${YELLOW}Setting secret: ${SECRET_NAME}${NC}"
    echo -e "Description: ${DESCRIPTION}"
    
    if [ -z "$SECRET_VALUE" ]; then
        read -sp "Enter value for ${SECRET_NAME}: " SECRET_VALUE
        echo
    fi
    
    echo "$SECRET_VALUE" | gh secret set "$SECRET_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${SECRET_NAME} set successfully${NC}\n"
    else
        echo -e "${RED}❌ Failed to set ${SECRET_NAME}${NC}\n"
    fi
}

# Set monitoring secrets
echo -e "${CYAN}=== Setting Monitoring Secrets ===${NC}\n"

set_secret "TELEGRAM_BOT_TOKEN" "" "Telegram bot token for alerts (from @BotFather)"
set_secret "TELEGRAM_ALERT_CHAT_ID" "1651759646" "Your Telegram chat ID for receiving alerts"
set_secret "GRAFANA_PASSWORD" "" "Grafana admin password"

# Set deployment secrets
echo -e "${CYAN}=== Setting Deployment Secrets ===${NC}\n"

set_secret "PRODUCTION_HOST" "" "Production server IP or hostname"
set_secret "PRODUCTION_USER" "" "SSH user for production server"
set_secret "SSH_PRIVATE_KEY" "" "SSH private key for production server"
set_secret "SSH_PORT" "22" "SSH port (default: 22)"

echo -e "${CYAN}=== Verifying Secrets ===${NC}\n"

SECRETS=$(gh secret list)
echo "$SECRETS"

echo -e "\n${GREEN}✅ All secrets have been set up!${NC}"
echo -e "\n${CYAN}Next steps:${NC}"
echo -e "1. Push changes to trigger CI/CD: ${YELLOW}git push origin main${NC}"
echo -e "2. Check workflow status: ${YELLOW}gh run list${NC}"
echo -e "3. View monitoring: ${YELLOW}http://${PRODUCTION_HOST}:3000${NC}"
echo -e "\n${CYAN}Useful commands:${NC}"
echo -e "  gh secret list                    # List all secrets"
echo -e "  gh secret set SECRET_NAME         # Update a secret"
echo -e "  gh secret remove SECRET_NAME      # Remove a secret"
echo -e "  gh run watch                      # Watch latest workflow run"
