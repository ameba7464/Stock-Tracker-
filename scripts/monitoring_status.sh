#!/bin/bash
# Quick monitoring status check script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== Stock Tracker Monitoring Status ===${NC}\n"

# Function to check service
check_service() {
    local NAME=$1
    local URL=$2
    
    if curl -sf "$URL" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $NAME is UP${NC}"
        return 0
    else
        echo -e "${RED}❌ $NAME is DOWN${NC}"
        return 1
    fi
}

# Check Docker services
echo -e "${CYAN}Docker Services:${NC}"
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep stock-tracker

echo -e "\n${CYAN}Service Health Checks:${NC}"

# Check each monitoring service
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Alertmanager" "http://localhost:9093/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"
check_service "API" "http://localhost:8000/health"
check_service "API Metrics" "http://localhost:8000/metrics"

echo -e "\n${CYAN}Prometheus Targets:${NC}"
TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets[] | "\(.labels.job)\t\(.health)"' 2>/dev/null)
if [ -n "$TARGETS" ]; then
    echo "$TARGETS" | awk -F'\t' '{printf "%-30s %s\n", $1, ($2=="up" ? "✅ UP" : "❌ DOWN")}'
else
    echo -e "${RED}❌ Could not fetch targets${NC}"
fi

echo -e "\n${CYAN}Recent Alerts:${NC}"
ALERTS=$(curl -s http://localhost:9093/api/v2/alerts 2>/dev/null | jq -r '.[] | select(.status.state=="active") | "\(.labels.alertname)\t\(.labels.severity)"' 2>/dev/null)
if [ -n "$ALERTS" ]; then
    echo "$ALERTS" | awk -F'\t' '{printf "%-30s %s\n", $1, $2}'
else
    echo -e "${GREEN}✅ No active alerts${NC}"
fi

echo -e "\n${CYAN}Disk Usage (Docker Volumes):${NC}"
docker system df -v | grep stock-tracker | awk '{printf "%-40s %10s\n", $1, $2}'

echo -e "\n${CYAN}Quick Links:${NC}"
echo "  Prometheus:    http://localhost:9090"
echo "  Alertmanager:  http://localhost:9093"
echo "  Grafana:       http://localhost:3000 (admin / StockTrackerMonitoring2024!)"
echo "  API Docs:      http://localhost:8000/docs"
echo "  Flower:        http://localhost:5555"

echo -e "\n${CYAN}Useful Commands:${NC}"
echo "  View logs:         docker logs stock-tracker-prometheus --tail 50"
echo "  Restart service:   docker-compose restart prometheus"
echo "  Check config:      docker-compose config"
echo "  Update services:   docker-compose pull && docker-compose up -d"
