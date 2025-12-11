#!/bin/bash
# Скрипт проверки системы мониторинга Stock Tracker

echo "🔍 Проверка системы мониторинга Stock Tracker"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service
check_service() {
    local service=$1
    local url=$2
    
    echo -n "Проверка $service... "
    
    if curl -s -f -o /dev/null "$url"; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        return 1
    fi
}

# Check Docker containers
echo "📦 Проверка Docker контейнеров:"
echo "--------------------------------"

containers=(
    "stock-tracker-api"
    "stock-tracker-prometheus"
    "stock-tracker-grafana"
    "stock-tracker-alertmanager"
    "stock-tracker-postgres-exporter"
    "stock-tracker-redis-exporter"
    "stock-tracker-node-exporter"
    "stock-tracker-cadvisor"
)

all_running=true
for container in "${containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo -e "  ${GREEN}✓${NC} $container"
    else
        echo -e "  ${RED}✗${NC} $container (не запущен)"
        all_running=false
    fi
done

echo ""

# Check HTTP endpoints
echo "🌐 Проверка HTTP endpoints:"
echo "--------------------------------"

check_service "API Health" "http://localhost:8000/api/v1/health/"
check_service "API Metrics" "http://localhost:8000/metrics"
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"
check_service "Alertmanager" "http://localhost:9093/-/healthy"
check_service "PostgreSQL Exporter" "http://localhost:9187/metrics"
check_service "Redis Exporter" "http://localhost:9121/metrics"
check_service "Node Exporter" "http://localhost:9100/metrics"
check_service "cAdvisor" "http://localhost:8080/healthz"

echo ""

# Check Prometheus targets
echo "🎯 Проверка Prometheus targets:"
echo "--------------------------------"

targets_response=$(curl -s http://localhost:9090/api/v1/targets)

if echo "$targets_response" | grep -q '"status":"success"'; then
    echo -e "${GREEN}✓ Prometheus targets доступны${NC}"
    
    # Check individual targets
    targets=(
        "stock-tracker-api"
        "postgresql"
        "redis"
        "node-exporter"
        "cadvisor"
    )
    
    for target in "${targets[@]}"; do
        if echo "$targets_response" | grep -q "\"job\":\"$target\""; then
            # Check if target is up
            if echo "$targets_response" | grep "\"job\":\"$target\"" | grep -q '"health":"up"'; then
                echo -e "  ${GREEN}✓${NC} $target (UP)"
            else
                echo -e "  ${YELLOW}⚠${NC} $target (DOWN)"
            fi
        else
            echo -e "  ${RED}✗${NC} $target (не найден)"
        fi
    done
else
    echo -e "${RED}✗ Не удалось получить targets${NC}"
fi

echo ""

# Check metrics
echo "📊 Проверка метрик API:"
echo "--------------------------------"

metrics_response=$(curl -s http://localhost:8000/metrics)

metrics_to_check=(
    "http_requests_total"
    "http_request_duration_seconds"
    "system_cpu_usage_percent"
    "system_memory_usage_bytes"
    "celery_tasks_total"
)

for metric in "${metrics_to_check[@]}"; do
    if echo "$metrics_response" | grep -q "^$metric"; then
        echo -e "  ${GREEN}✓${NC} $metric"
    else
        echo -e "  ${RED}✗${NC} $metric"
    fi
done

echo ""

# Check Grafana datasources
echo "📈 Проверка Grafana datasources:"
echo "--------------------------------"

grafana_ds=$(curl -s -u admin:admin http://localhost:3000/api/datasources 2>/dev/null)

if echo "$grafana_ds" | grep -q "Prometheus"; then
    echo -e "${GREEN}✓ Prometheus datasource настроен${NC}"
else
    echo -e "${YELLOW}⚠ Prometheus datasource не найден${NC}"
    echo "  Войдите в Grafana и проверьте Configuration → Data Sources"
fi

echo ""

# Check alert rules
echo "🚨 Проверка Alert Rules:"
echo "--------------------------------"

rules_response=$(curl -s http://localhost:9090/api/v1/rules)

if echo "$rules_response" | grep -q '"status":"success"'; then
    rule_groups=$(echo "$rules_response" | grep -o '"name":"[^"]*"' | wc -l)
    echo -e "${GREEN}✓ Alert rules загружены ($rule_groups groups)${NC}"
    
    # Check for some important alerts
    important_alerts=(
        "APIDown"
        "PostgreSQLDown"
        "HighErrorRate"
        "HighLatency"
    )
    
    for alert in "${important_alerts[@]}"; do
        if echo "$rules_response" | grep -q "\"$alert\""; then
            echo -e "  ${GREEN}✓${NC} $alert"
        else
            echo -e "  ${YELLOW}⚠${NC} $alert (не найден)"
        fi
    done
else
    echo -e "${RED}✗ Не удалось получить alert rules${NC}"
fi

echo ""

# Check environment variables
echo "⚙️  Проверка переменных окружения:"
echo "--------------------------------"

if docker-compose exec -T alertmanager env 2>/dev/null | grep -q "TELEGRAM_BOT_TOKEN"; then
    echo -e "${GREEN}✓ TELEGRAM_BOT_TOKEN установлен${NC}"
else
    echo -e "${RED}✗ TELEGRAM_BOT_TOKEN не установлен${NC}"
    echo "  Добавьте в .env: TELEGRAM_BOT_TOKEN=your_token"
fi

if docker-compose exec -T alertmanager env 2>/dev/null | grep -q "TELEGRAM_ALERT_CHAT_ID"; then
    echo -e "${GREEN}✓ TELEGRAM_ALERT_CHAT_ID установлен${NC}"
else
    echo -e "${RED}✗ TELEGRAM_ALERT_CHAT_ID не установлен${NC}"
    echo "  Добавьте в .env: TELEGRAM_ALERT_CHAT_ID=your_chat_id"
fi

echo ""

# Summary
echo "📋 Сводка:"
echo "--------------------------------"

if [ "$all_running" = true ]; then
    echo -e "${GREEN}✓ Все контейнеры запущены${NC}"
else
    echo -e "${RED}✗ Некоторые контейнеры не запущены${NC}"
    echo "  Запустите: docker-compose up -d"
fi

echo ""
echo "🔗 Полезные ссылки:"
echo "  Grafana:      http://localhost:3000"
echo "  Prometheus:   http://localhost:9090"
echo "  Alertmanager: http://localhost:9093"
echo "  API Metrics:  http://localhost:8000/metrics"
echo ""

# Test Telegram notification (optional)
read -p "Отправить тестовое уведомление в Telegram? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Отправка тестового сообщения..."
    
    # Get token and chat_id from .env
    source .env 2>/dev/null
    
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_ALERT_CHAT_ID" ]; then
        response=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_ALERT_CHAT_ID}" \
            -d "parse_mode=HTML" \
            -d "text=<b>✅ Stock Tracker Monitoring</b>%0A%0AТестовое уведомление от системы мониторинга.%0A%0A<i>Если вы получили это сообщение, уведомления настроены правильно!</i>")
        
        if echo "$response" | grep -q '"ok":true'; then
            echo -e "${GREEN}✓ Сообщение отправлено успешно!${NC}"
            echo "  Проверьте Telegram: @Enotiz"
        else
            echo -e "${RED}✗ Ошибка отправки${NC}"
            echo "$response"
        fi
    else
        echo -e "${YELLOW}⚠ TELEGRAM_BOT_TOKEN или TELEGRAM_ALERT_CHAT_ID не установлены${NC}"
    fi
fi

echo ""
echo "✅ Проверка завершена!"
echo ""
echo "📚 Документация:"
echo "  MONITORING_QUICKSTART.md - быстрый старт"
echo "  docs/MONITORING_GUIDE.md - полное руководство"
