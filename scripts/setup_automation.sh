#!/bin/bash
# Setup automated tasks (cron jobs) for Stock Tracker

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}=== Setting up automated tasks ===${NC}\n"

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${YELLOW}Project directory: $PROJECT_DIR${NC}\n"

# Create cron jobs
echo -e "${CYAN}Creating cron jobs...${NC}"

# Backup existing crontab
crontab -l > /tmp/crontab.backup 2>/dev/null || true

# Create new cron jobs
cat > /tmp/stock-tracker-cron << EOF
# Stock Tracker Automated Tasks
# Generated on $(date)

# Daily maintenance at 3 AM
0 3 * * * cd $PROJECT_DIR && ./scripts/maintenance.sh >> logs/maintenance.log 2>&1

# Health check every 6 hours
0 */6 * * * cd $PROJECT_DIR && ./scripts/monitoring_status.sh >> logs/health_check.log 2>&1

# Docker cleanup weekly (Sunday at 2 AM)
0 2 * * 0 docker system prune -af --volumes >> $PROJECT_DIR/logs/docker_cleanup.log 2>&1

# Backup configurations daily at 1 AM
0 1 * * * cd $PROJECT_DIR && tar -czf backups/daily_backup_\$(date +\%Y\%m\%d).tar.gz monitoring/ docker-compose.yml .env.example

# Remove old backups (keep last 7 days)
0 4 * * * find $PROJECT_DIR/backups -name "daily_backup_*.tar.gz" -mtime +7 -delete

# Check disk usage and alert if > 80%
0 */4 * * * df -h / | awk 'NR==2 {if (substr(\$5,1,length(\$5)-1) > 80) print "⚠️ Disk usage warning: " \$5}' >> $PROJECT_DIR/logs/disk_check.log 2>&1

EOF

# Install cron jobs
echo -e "${YELLOW}Installing cron jobs...${NC}"
crontab /tmp/stock-tracker-cron

# Verify installation
echo -e "\n${CYAN}Installed cron jobs:${NC}"
crontab -l | grep -A 20 "Stock Tracker"

# Create log directory if not exists
mkdir -p "$PROJECT_DIR/logs"

echo -e "\n${GREEN}✅ Automated tasks configured successfully!${NC}"
echo -e "\n${CYAN}Scheduled tasks:${NC}"
echo -e "  • Daily maintenance:    3:00 AM"
echo -e "  • Health checks:        Every 6 hours"
echo -e "  • Docker cleanup:       Sunday 2:00 AM"
echo -e "  • Configuration backup: 1:00 AM"
echo -e "  • Old backup cleanup:   4:00 AM"
echo -e "  • Disk usage check:     Every 4 hours"

echo -e "\n${CYAN}Logs location:${NC}"
echo -e "  $PROJECT_DIR/logs/"

echo -e "\n${CYAN}Useful commands:${NC}"
echo -e "  View cron jobs:   crontab -l"
echo -e "  Edit cron jobs:   crontab -e"
echo -e "  Remove cron jobs: crontab -r"
echo -e "  View logs:        tail -f logs/*.log"
