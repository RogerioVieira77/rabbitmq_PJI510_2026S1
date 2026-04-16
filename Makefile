# =============================================
# RabbitMQ PJI510 - Makefile
# =============================================

.PHONY: help bootstrap up down logs status health test-producer test-consumer setup-users clean

APP_NAME   = rabbitmq-pji510
COMPOSE    = docker compose

help: ## Mostra este help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Setup completo: copia .env, sobe o broker, aguarda healthy e configura usuários
	@echo "==> Verificando .env..."
	@test -f .env || (cp .env.example .env && echo "ATENÇÃO: .env criado a partir do .env.example. Edite as senhas antes de continuar." && exit 1)
	@echo "==> Subindo o broker..."
	$(COMPOSE) up -d --build
	@echo "==> Aguardando healthcheck..."
	@timeout 60 bash -c 'until docker inspect --format="{{.State.Health.Status}}" $(APP_NAME) 2>/dev/null | grep -q healthy; do sleep 2; done'
	@echo "==> Broker healthy!"
	@$(MAKE) setup-users
	@echo "==> Bootstrap concluído."

up: ## Sobe o broker
	$(COMPOSE) up -d

down: ## Para o broker
	$(COMPOSE) down

logs: ## Mostra os logs do broker
	$(COMPOSE) logs -f --tail=50 rabbitmq

status: ## Mostra status dos containers
	$(COMPOSE) ps

health: ## Verifica saúde do broker
	@docker exec $(APP_NAME) rabbitmq-diagnostics check_running -q && echo "OK: Broker running" || echo "FAIL: Broker not running"
	@docker exec $(APP_NAME) rabbitmq-diagnostics check_port_connectivity -q && echo "OK: Ports OK" || echo "FAIL: Port issues"

setup-users: ## Cria usuários producer e consumer via rabbitmqctl
	@echo "==> Criando usuário sensor_producer..."
	@docker exec $(APP_NAME) rabbitmqctl add_user sensor_producer $$(grep SENSOR_PRODUCER_PASS .env 2>/dev/null | cut -d= -f2 || echo "sensor_pass_temp") 2>/dev/null || true
	@docker exec $(APP_NAME) rabbitmqctl set_permissions -p /pji510 sensor_producer "" "sensores\..*" "" 2>/dev/null || true
	@echo "==> Criando usuário alerta_consumer..."
	@docker exec $(APP_NAME) rabbitmqctl add_user alerta_consumer $$(grep ALERTA_CONSUMER_PASS .env 2>/dev/null | cut -d= -f2 || echo "consumer_pass_temp") 2>/dev/null || true
	@docker exec $(APP_NAME) rabbitmqctl set_permissions -p /pji510 alerta_consumer "" "" "sensores\..*" 2>/dev/null || true
	@echo "==> Usuários configurados."

test-producer: ## Executa o script de teste do producer
	python3 scripts/test_producer.py

test-consumer: ## Executa o script de teste do consumer
	python3 scripts/test_consumer.py

smoke-test: ## Executa smoke test completo pós-deploy
	bash scripts/healthcheck.sh

clean: ## Remove containers e volumes (DESTRUTIVO)
	@echo "ATENÇÃO: Isso vai remover todos os dados do RabbitMQ!"
	@read -p "Tem certeza? (y/N) " confirm && [ "$$confirm" = "y" ] && $(COMPOSE) down -v || echo "Cancelado."
