# RABBITMQ_PJI510_2026S1 - Fila para publicação de Dados dos Sensores de monitoramento de um reservatório

## Objetivo do Sistema

Criação de uma fila RabbitMQ para publicação dos dados de leitura de sensores de monitoramento de um reservatório de água. Esse reservatório é usado como uma área de contingência para a prevenção de enchentes em uma área de risco.

Os dados dos sensores serão consumidos por uma aplicação chamada **"Alerta Romano"** que será responsável por processar esses dados e acionar os mecanismos de alerta à população.

Este documento traz uma descrição macro do sistema cobrindo a idealização inicial, as decisões de infraestrutura e o planejamento de implementação.

---

## Contexto de Infraestrutura

### Servidor de Homologação

| Propriedade       | Valor                                    |
|-------------------|------------------------------------------|
| Hostname          | `srv1312297`                             |
| IP Público        | `191.101.234.42`                         |
| SO                | Ubuntu 24.04.4 LTS                       |
| Domínio           | `*.unicomunitaria.com.br`               |
| TLS               | Let's Encrypt wildcard                   |
| Diretório base    | `/opt/unicomunitaria/docker/rabbitmq_PJI510_2026S1` |

### Aplicações coexistentes no servidor

| Aplicação               | Portas ocupadas (127.0.0.1)         |
|--------------------------|-------------------------------------|
| sistema-de-enderecos     | 8082 (API)                          |
| sistema-de-cadastros     | 8081 (frontend)                     |
| polidrama                | 8091 (backend), 8092 (frontend), 15432 (postgres) |
| sistema-de-condominios   | 8000 (backend), 3000 (frontend), 5434 (postgres), 6380 (redis) |
| app001                   | 8081 (conflito conhecido)           |

### Portas disponíveis para o RabbitMQ

| Serviço                  | Porta Host (127.0.0.1)  | Porta Interna | Justificativa                          |
|--------------------------|-------------------------|---------------|----------------------------------------|
| AMQP (protocolo de fila) | **5672**                | 5672          | Porta padrão AMQP, fora da faixa 8081-8099, sem conflito |
| Management UI            | **8093**                | 15672         | Próxima porta livre na faixa reservada 8081-8099 |

> **Nota:** A porta AMQP 5672 não será exposta externamente (UFW bloqueia). O Management UI será acessível publicamente via NGINX reverse proxy com HTTPS.

---

## 1 - Publicação de Dados dos Sensores (Producer)

### 1.1 - Detalhamento

Os sensores de monitoramento do reservatório publicam leituras periódicas na fila RabbitMQ. Cada mensagem contém os dados de uma leitura individual.

**Estrutura da mensagem (payload JSON):**

```json
{
  "sensor_id": "SENSOR-RES-001",
  "tipo_sensor": "nivel_agua",
  "valor": 3.72,
  "unidade": "metros",
  "timestamp": "2026-04-15T14:30:00Z",
  "localizacao": {
    "latitude": -23.5505,
    "longitude": -46.6333,
    "descricao": "Reservatório Norte - Ponto A"
  },
  "status": "normal",
  "bateria_pct": 87
}
```

**Tipos de sensores suportados:**

| Tipo              | Unidade  | Descrição                                    |
|-------------------|----------|----------------------------------------------|
| `nivel_agua`      | metros   | Nível da água no reservatório                |
| `vazao`           | m³/s     | Vazão de entrada/saída do reservatório       |
| `pluviometro`     | mm/h     | Índice pluviométrico na região               |
| `pressao`         | kPa      | Pressão na tubulação                         |
| `temperatura`     | °C       | Temperatura da água                          |

**Topologia RabbitMQ:**

| Componente     | Nome                            | Tipo             |
|----------------|---------------------------------|------------------|
| Exchange       | `sensores.exchange`             | `topic`          |
| Queue          | `sensores.leituras`             | durable          |
| Routing Key    | `sensor.<tipo>.<sensor_id>`     | pattern          |
| Dead Letter Ex | `sensores.dlx`                  | `fanout`         |
| Dead Letter Q  | `sensores.leituras.dlq`         | durable          |
| VHost          | `/pji510`                       | isolado          |

**Exemplo de routing keys:**
- `sensor.nivel_agua.SENSOR-RES-001`
- `sensor.vazao.SENSOR-RES-002`
- `sensor.pluviometro.SENSOR-RES-003`

> O exchange `topic` permite que o "Alerta Romano" consuma todas as leituras (`sensor.#`) ou filtre por tipo (`sensor.nivel_agua.*`).

---

## 2 - Consumo de Dados (Consumer - Alerta Romano)

### 2.1 - Detalhamento

A aplicação **"Alerta Romano"** se conecta à queue `sensores.leituras` e processa as mensagens para:
- Armazenar o histórico de leituras
- Avaliar regras de alerta (nível crítico, vazão anormal, etc.)
- Disparar notificações quando limiares forem ultrapassados

**Binding da queue:**
- `sensores.leituras` vinculada ao `sensores.exchange` com routing key `sensor.#` (recebe todas as leituras)

**Política de consumo:**
- Prefetch count: `10` (para balancear throughput e memória)
- Acknowledgment: manual (`ack` após processamento bem-sucedido)
- Rejeição: `nack` com requeue para falhas transitórias; envio para DLQ para falhas persistentes (após 3 tentativas)

---

### Funcionalidades Transversais

🔹 **Autenticação no broker** — Usuário e senha dedicados por aplicação (producer e consumer separados)
🔹 **VHost isolado** (`/pji510`) — Separação lógica das demais aplicações que possam usar o broker futuramente
🔹 **Dead Letter Queue** — Mensagens que falharem 3x são redirecionadas para `sensores.leituras.dlq` para análise
🔹 **Management UI** — Painel web para monitoramento de filas, conexões e throughput
🔹 **Healthcheck** — Verificação automática de saúde do broker via Docker
🔹 **Persistência** — Mensagens e configurações armazenadas em volume Docker nomeado
🔹 **Logs centralizados** — Logs do broker acessíveis via `docker compose logs`

---

### Tecnologias

| Camada              | Tecnologia                                |
|---------------------|-------------------------------------------|
| Message Broker      | RabbitMQ 3.13 (com plugin Management)     |
| Protocolo           | AMQP 0-9-1                                |
| Container Runtime   | Docker + Docker Compose                   |
| Reverse Proxy       | NGINX (host) com TLS wildcard             |
| Monitoramento       | RabbitMQ Management UI + healthcheck      |
| Producers           | Sensores IoT (protocolo AMQP ou HTTP→AMQP bridge) |
| Consumer            | Alerta Romano (aplicação externa)         |
| DevOps              | GitHub Actions (CI/CD), UFW (firewall)    |

---

## 3. Modelo de Deploy (Docker Compose)

Arquivo: `docker-compose.yml`

```yaml
services:
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: rabbitmq-pji510
    hostname: rabbitmq-pji510
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-admin}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
      RABBITMQ_DEFAULT_VHOST: /pji510
    ports:
      - "127.0.0.1:5672:5672"
      - "127.0.0.1:8093:15672"
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
      - ./config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
      - ./config/definitions.json:/etc/rabbitmq/definitions.json:ro
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running", "-q"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 30s

volumes:
  rabbitmq_data:
```

### Variáveis de ambiente (`.env.example`)

```env
RABBITMQ_USER=admin
RABBITMQ_PASS=TROCAR_ANTES_DO_DEPLOY
```

> **IMPORTANTE:** O arquivo `.env` com a senha real **NÃO deve ser versionado**. Apenas `.env.example` vai para o repositório.

---

## 4. Configuração NGINX

Subdomínio: `rabbitmq-pji510.unicomunitaria.com.br`
Arquivo: `/etc/nginx/sites-available/rabbitmq-pji510.hml.conf`

```nginx
server {
    listen 80;
    server_name rabbitmq-pji510.unicomunitaria.com.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name rabbitmq-pji510.unicomunitaria.com.br;

    ssl_certificate     /etc/letsencrypt/live/unicomunitaria.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/unicomunitaria.com.br/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8093;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Segurança e Hardening

### 5.1 Regras de Firewall (UFW)

```bash
# A porta AMQP NÃO é aberta externamente
sudo ufw deny 5672/tcp comment "RabbitMQ AMQP - bloqueado externamente"

# O Management UI NÃO é aberto diretamente (acesso via NGINX 443)
sudo ufw deny 8093/tcp comment "RabbitMQ Management - bloqueado externamente"
```

> O acesso externo ao broker AMQP só deve ocorrer via VPN ou túnel SSH, nunca diretamente.

### 5.2 Credenciais

| Usuário              | Permissão         | VHost     | Uso                          |
|----------------------|-------------------|-----------|------------------------------|
| `admin`              | administrator     | `/pji510` | Administração e Management UI |
| `sensor_producer`    | write             | `/pji510` | Publicação dos sensores      |
| `alerta_consumer`    | read              | `/pji510` | Consumo pelo Alerta Romano   |

> Cada aplicação conecta com credencial própria e permissão mínima (princípio do menor privilégio).

### 5.3 Políticas de Fila

| Política          | Valor        | Justificativa                                |
|-------------------|--------------|----------------------------------------------|
| `x-max-length`    | 100.000      | Limite de mensagens para proteger a memória  |
| `x-message-ttl`   | 86.400.000ms | Mensagens expiram em 24h se não consumidas   |
| `x-dead-letter-exchange` | `sensores.dlx` | Mensagens rejeitadas vão para DLQ  |
| `durable`         | true         | Mensagens sobrevivem a restart do broker     |

---

## 6. Planejamento da Implementação

### Fase 0 — Planejamento e Setup (1–2 semanas)

- [x] Análise do servidor e portas disponíveis
- [x] Definição da topologia de filas (exchange, queues, routing keys)
- [x] Definição de credenciais e políticas de segurança
- [ ] Revisão e aprovação deste plano pelo time
- [ ] Criação do repositório Git (se ainda não existir como repo independente)
- [ ] Configuração do `.env.example` e `docker-compose.yml`

### Fase 1 — MVP (2–3 semanas)

Objetivo: Broker funcional com fila de sensores operacional em homologação

**Módulos Prioritários:**

1. Setup do Docker Compose com RabbitMQ + Management UI
2. Criação do VHost `/pji510` com exchange e queue configurados via `definitions.json`
3. Configuração do NGINX reverse proxy para o Management UI
4. Criação dos usuários (admin, sensor_producer, alerta_consumer)
5. Script de teste de publicação (producer de teste em Python)
6. Script de teste de consumo (consumer de teste em Python)
7. Validação do healthcheck e smoke test

**Critério de sucesso:**

- Broker operacional e acessível via Management UI em `https://rabbitmq-pji510.unicomunitaria.com.br`
- Mensagem de teste publicada e consumida com sucesso na fila `sensores.leituras`
- Nenhuma porta exposta externamente além de 80/443 via NGINX
- Coexistência comprovada com as demais aplicações do servidor (sem conflito de portas ou recursos)

### Fase 2 — Integração com Producers (2–3 semanas)

- Definição do protocolo de comunicação com os sensores reais (AMQP direto ou bridge HTTP→AMQP)
- Implementação do adapter/producer para os sensores IoT
- Testes de carga com volume simulado de leituras
- Monitoramento de uso de memória e disco no servidor compartilhado

### Fase 3 — Integração com Alerta Romano (2–3 semanas)

- Conexão da aplicação "Alerta Romano" como consumer na fila `sensores.leituras`
- Implementação do tratamento de erros e Dead Letter Queue
- Testes de resiliência (restart do broker, mensagens corrompidas, falha de rede)
- Validação do fluxo completo: sensor → broker → alerta

### Fase 4 — Produção e Observabilidade (2–3 semanas)

- Definição de limites de recursos no Docker Compose (`mem_limit`, `cpus`)
- Implementação de alertas de monitoramento (queue depth, consumer lag, disk usage)
- Documentação operacional (runbook de incidentes)
- Pipeline CI/CD via GitHub Actions para deploy automatizado
- Preparação para migração para ambiente de produção (se aplicável)

---

## 7. Estrutura de Arquivos do Projeto

```
rabbitmq_PJI510_2026S1/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
├── config/
│   ├── rabbitmq.conf
│   └── definitions.json        # exchanges, queues, bindings, users
├── scripts/
│   ├── test_producer.py         # producer de teste
│   ├── test_consumer.py         # consumer de teste
│   └── healthcheck.sh           # smoke test pós-deploy
├── docs/
│   ├── 001 - Plano de desenvolvimento.md
│   ├── 002 - Software Requirements Specification - SRS.md
│   ├── 003 - Pesquisa e Desenvolvimento - PRD.md
│   ├── 004 - DevSpecs.md
│   └── 005 - Backlog Tecnico.md
└── nginx/
    └── rabbitmq-pji510.hml.conf
```

---

## 8. Resumo Final

**`Funcionalidades chave:`**

- Broker RabbitMQ com fila dedicada para dados de sensores de monitoramento de reservatório
- Exchange `topic` para roteamento flexível por tipo de sensor
- Dead Letter Queue para tratamento de falhas
- VHost isolado (`/pji510`) para separação lógica no servidor compartilhado
- Management UI acessível via HTTPS com NGINX reverse proxy
- Credenciais segregadas por papel (admin, producer, consumer)

**`Referências essenciais:`**

- [RabbitMQ Documentation](https://www.rabbitmq.com/docs)
- [RabbitMQ Docker Official Image](https://hub.docker.com/_/rabbitmq)
- [AMQP 0-9-1 Protocol](https://www.rabbitmq.com/tutorials/amqp-concepts)
- Modelo de deploy: `deploy_models/MODELO - Deploy APP - HOM.md`
- Checklist de aplicação: `deploy_models/Template - Checklist por Aplicacao.md`

**`Fluxo do Plano de desenvolvimento:`**

```
Sensores IoT ──AMQP──▸ Exchange (topic) ──routing──▸ Queue (sensores.leituras) ──▸ Alerta Romano
                        sensores.exchange              │
                                                       ├── nack (3x) ──▸ DLQ (sensores.leituras.dlq)
                                                       └── ack ──▸ processado
```
