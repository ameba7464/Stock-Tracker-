#!/bin/bash
# Automatic system maintenance script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Stock Tracker Maintenance ===${NC}\n"

# Function to run with status
run_task() {
    local TASK_NAME=$1
    shift
    
    echo -e "${YELLOW}➜ $TASK_NAME${NC}"
    if "$@" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✅ Done${NC}"
        return 0
    else
        echo -e "${RED}  ❌ Failed${NC}"
        return 1
    fi
}

# 1. Pull latest Docker images
echo -e "${CYAN}1. Updating Docker Images${NC}"
run_task "Pull monitoring images" docker-compose pull prometheus grafana alertmanager
run_task "Pull exporter images" docker-compose pull postgres-exporter redis-exporter node-exporter cadvisor

# 2. Clean up old Docker resources
echo -e "\n${CYAN}2. Cleaning Up Docker${NC}"
run_task "Remove unused containers" docker container prune -f
run_task "Remove unused images" docker image prune -f
run_task "Remove unused volumes" docker volume prune -f
run_task "Remove unused networks" docker network prune -f

# 3. Backup configurations
echo -e "\n${CYAN}3. Backing Up Configurations${NC}"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
run_task "Backup docker-compose.yml" cp docker-compose.yml "$BACKUP_DIR/"
run_task "Backup monitoring configs" cp -r monitoring "$BACKUP_DIR/"
run_task "Backup .env.example" cp .env.example "$BACKUP_DIR/"
echo -e "${GREEN}  Backup saved to: $BACKUP_DIR${NC}"

# 4. Restart unhealthy services
echo -e "\n${CYAN}4. Checking Service Health${NC}"
UNHEALTHY=$(docker ps --filter health=unhealthy --format '{{.Names}}' | wc -l)
if [ "$UNHEALTHY" -gt 0 ]; then
    echo -e "${YELLOW}  Found $UNHEALTHY unhealthy services${NC}"
    docker ps --filter health=unhealthy --format '{{.Names}}' | while read SERVICE; do
        run_task "Restart $SERVICE" docker-compose restart "$SERVICE"
    done
else
    echo -e "${GREEN}  ✅ All services healthy${NC}"
fi

# 5. Check disk usage
echo -e "\n${CYAN}5. Disk Usage Check${NC}"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${RED}  ⚠️  Disk usage is high: ${DISK_USAGE}%${NC}"
    echo -e "${YELLOW}  Consider cleaning up old logs and backups${NC}"
else
    echo -e "${GREEN}  ✅ Disk usage OK: ${DISK_USAGE}%${NC}"
fi

# 6. Verify monitoring targets
echo -e "\n${CYAN}6. Monitoring Targets Check${NC}"
UP_TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets | map(select(.health == "up")) | length' 2>/dev/null || echo "0")
TOTAL_TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets | length' 2>/dev/null || echo "0")
if [ "$UP_TARGETS" -gt 0 ]; then
    echo -e "${GREEN}  ✅ $UP_TARGETS/$TOTAL_TARGETS targets UP${NC}"
else
    echo -e "${RED}  ❌ Could not check targets${NC}"
fi

# 7. Summary
echo -e "\n${CYAN}=== Maintenance Summary ===${NC}"
echo -e "Date: $(date)"
echo -e "Docker images: ${GREEN}Updated${NC}"
echo -e "Cleanup: ${GREEN}Done${NC}"
echo -e "Backup: ${GREEN}$BACKUP_DIR${NC}"
echo -e "Services: ${GREEN}Checked${NC}"
echo -e "\n${CYAN}Next Steps:${NC}"
echo -e "  1. Check logs: docker-compose logs -f --tail=50"
echo -e "  2. View status: ./scripts/monitoring_status.sh"
echo -e "  3. Access Grafana: http://localhost:3000"

echo -e "\n${GREEN}✅ Maintenance completed successfully!${NC}"
