# rabbitmq_PJI510_2026S1

Fila RabbitMQ para publicação de dados de sensores de monitoramento de um reservatório de água, voltada à prevenção de enchentes em área de risco.

## Stack

- **Broker:** RabbitMQ 3.13 (Management Alpine)
- **Protocolo:** AMQP 0-9-1
- **Deploy:** Docker Compose
- **Proxy:** NGINX + TLS (wildcard Let's Encrypt)

## Quick Start

```bash
# 1. Configure as credenciais
cp .env.example .env
# Edite .env com senhas seguras

# 2. Bootstrap completo (sobe broker + configura usuários)
make bootstrap

# 3. Verificar saúde
make health

# 4. Smoke test pós-deploy
make smoke-test
```

## Portas

| Serviço       | Porta Host        | Acesso Externo                                     |
|---------------|-------------------|-----------------------------------------------------|
| AMQP          | `127.0.0.1:5672`  | Apenas local (bloqueado no UFW)                     |
| Management UI | `127.0.0.1:8093`  | Via NGINX: `https://rabbitmq-pji510.unicomunitaria.com.br` |

## Topologia

```
Sensores IoT ──AMQP──▸ sensores.exchange (topic) ──▸ sensores.leituras ──▸ Alerta Romano
                                                      └── nack (3x) ──▸ sensores.leituras.dlq
```

## Comandos Úteis

```bash
make up              # Sobe o broker
make down            # Para o broker
make logs            # Mostra logs
make status          # Status dos containers
make health          # Verifica saúde
make test-producer   # Executa producer de teste (requer: pip install pika)
make test-consumer   # Executa consumer de teste (requer: pip install pika)
make smoke-test      # Smoke test completo
make help            # Lista todos os comandos
```

## Documentação

- [001 - Plano de Desenvolvimento](docs/001%20-%20Plano%20de%20desenvolvimento%20-%20MODELO.md)
- [002 - SRS](docs/002%20-%20Software%20Requirements%20Specification%20-%20SRS%20-%20MODELO.md)
- [003 - PRD](docs/003%20-%20Pesquisa%20e%20Desenvolvimento%20-%20PRD%20-%20MODELO.md)
- [004 - DevSpecs](docs/004%20-%20DevSpecs%20-%20MODELO.md)
- [005 - Backlog Técnico](docs/005%20-%20Backlog%20Tecnico%20-%20MODELO.md)