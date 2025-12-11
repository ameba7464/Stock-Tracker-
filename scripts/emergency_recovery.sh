#!/bin/bash
# Emergency recovery script for monitoring system

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${RED}=== EMERGENCY RECOVERY MODE ===${NC}\n"

# 1. Stop all services
echo -e "${CYAN}1. Stopping all services...${NC}"
docker-compose down
sleep 2

# 2. Clean up problematic containers
echo -e "\n${CYAN}2. Cleaning up...${NC}"
docker container prune -f
docker network prune -f

# 3. Restart PostgreSQL and Redis first
echo -e "\n${CYAN}3. Starting database services...${NC}"
docker-compose up -d postgres redis
echo -e "${YELLOW}Waiting 10 seconds for databases...${NC}"
sleep 10

# 4. Start API and workers
echo -e "\n${CYAN}4. Starting application services...${NC}"
docker-compose up -d api worker beat

# 5. Start monitoring stack
echo -e "\n${CYAN}5. Starting monitoring stack...${NC}"
docker-compose up -d prometheus grafana alertmanager
docker-compose up -d postgres-exporter redis-exporter node-exporter cadvisor

# 6. Wait and check
echo -e "\n${CYAN}6. Waiting for services to initialize...${NC}"
sleep 15

# 7. Health check
echo -e "\n${CYAN}7. Health Check:${NC}"
services=("prometheus:9090" "grafana:3000" "alertmanager:9093")
for service_port in "${services[@]}"; do
    service="${service_port%%:*}"
    port="${service_port##*:}"
    if curl -sf "http://localhost:$port/-/healthy" > /dev/null 2>&1 || \
       curl -sf "http://localhost:$port/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service is UP${NC}"
    else
        echo -e "${RED}❌ $service is DOWN${NC}"
    fi
done

# 8. Show status
echo -e "\n${CYAN}8. Current Status:${NC}"
docker ps --format 'table {{.Names}}\t{{.Status}}'

echo -e "\n${GREEN}=== Recovery process completed ===${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Check logs: docker-compose logs -f"
echo -e "2. Run status check: ./scripts/monitoring_status.sh"
echo -e "3. If still issues, check individual logs:"
echo -e "   docker logs stock-tracker-prometheus --tail 50"
echo -e "   docker logs stock-tracker-grafana --tail 50"
