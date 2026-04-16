#!/usr/bin/env bash
# =============================================
# Smoke test pós-deploy - RabbitMQ PJI510
# Uso: bash scripts/healthcheck.sh
# =============================================
set -uo pipefail

APP_NAME="rabbitmq-pji510"
MGMT_URL="http://127.0.0.1:8093"
AMQP_PORT="5672"
VHOST="%2Fpji510"  # URL-encoded /pji510

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC} — $desc"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}❌ FAIL${NC} — $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "========================================"
echo " Smoke Test — RabbitMQ PJI510"
echo " $(date -Iseconds)"
echo "========================================"
echo ""

# 1. Container rodando
docker inspect --format='{{.State.Status}}' "$APP_NAME" 2>/dev/null | grep -q running
check "Container $APP_NAME está running" $?

# 2. Healthcheck healthy
docker inspect --format='{{.State.Health.Status}}' "$APP_NAME" 2>/dev/null | grep -q healthy
check "Healthcheck reporta healthy" $?

# 3. Porta AMQP respondendo
timeout 5 bash -c "echo > /dev/tcp/127.0.0.1/$AMQP_PORT" 2>/dev/null
check "Porta AMQP ($AMQP_PORT) respondendo" $?

# 4. Management UI respondendo
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$MGMT_URL/api/overview" -u admin:admin 2>/dev/null || echo "000")
[ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]
check "Management UI ($MGMT_URL) respondendo (HTTP $HTTP_CODE)" $?

# 5. VHost /pji510 existe
VHOSTS=$(docker exec "$APP_NAME" rabbitmqctl list_vhosts --formatter json 2>/dev/null || true)
echo "$VHOSTS" | grep -q pji510
check "VHost /pji510 existe" $?

# 6. Exchange sensores.exchange existe
EXCHANGES=$(docker exec "$APP_NAME" rabbitmqctl list_exchanges -p /pji510 --formatter json 2>/dev/null || true)
echo "$EXCHANGES" | grep -q sensores.exchange
check "Exchange sensores.exchange existe" $?

# 7. Queue sensores.leituras existe
QUEUES=$(docker exec "$APP_NAME" rabbitmqctl list_queues -p /pji510 --formatter json 2>/dev/null || true)
echo "$QUEUES" | grep -q sensores.leituras
check "Queue sensores.leituras existe" $?

# 8. Queue DLQ existe
echo "$QUEUES" | grep -q sensores.leituras.dlq
check "Queue sensores.leituras.dlq (DLQ) existe" $?

echo ""
echo "========================================"
echo " Resultado: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
echo "========================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
