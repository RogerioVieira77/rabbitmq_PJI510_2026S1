"""
API Bridge HTTP → AMQP
Recebe leituras de sensores via POST HTTPS e publica no RabbitMQ.

Fase 1: Fila aberta — qualquer sensor com o endereço consegue publicar.
Fase 2 (futura): Autenticação por token/API key para sensores registrados.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import aio_pika
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger("api_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Configuração via variáveis de ambiente ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/pji510")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "sensor_producer")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "")
EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "sensores.exchange")
STARTUP_RETRIES = int(os.getenv("STARTUP_RETRIES", "5"))
STARTUP_RETRY_DELAY = float(os.getenv("STARTUP_RETRY_DELAY", "3"))

# --- Modelos ---
class Localizacao(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    descricao: Optional[str] = None


class LeituraSensor(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=100)
    tipo_sensor: str = Field(
        ...,
        pattern=r"^(nivel_agua|pluviometro|pressao|temperatura|umidade|vento_direcao|vento_velocidade)$",
    )
    valor: float
    unidade: str = Field(..., min_length=1, max_length=20)
    timestamp: Optional[str] = None
    localizacao: Optional[Localizacao] = None
    status: Optional[str] = Field(default="normal", pattern=r"^(normal|alerta|critico|erro)$")
    bateria_pct: Optional[int] = Field(default=None, ge=0, le=100)


class PublishResponse(BaseModel):
    ok: bool
    message: str
    routing_key: str


# --- Conexão RabbitMQ (robust = reconexão automática) ---
_connection: Optional[aio_pika.abc.AbstractRobustConnection] = None


async def _publish_messages(messages: list[tuple[str, bytes]]) -> None:
    """Publica uma lista de (routing_key, body) usando um único canal."""
    if _connection is None or _connection.is_closed:
        raise RuntimeError("Sem conexão AMQP disponível")
    channel = await _connection.channel()
    try:
        exchange = await channel.get_exchange(EXCHANGE_NAME, ensure=False)
        for routing_key, body in messages:
            await exchange.publish(
                aio_pika.Message(
                    body=body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )
    finally:
        await channel.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _connection
    logger.info("API Bridge iniciando...")

    last_error: Optional[Exception] = None
    for attempt in range(1, STARTUP_RETRIES + 1):
        try:
            _connection = await aio_pika.connect_robust(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                virtualhost=RABBITMQ_VHOST,
                login=RABBITMQ_USER,
                password=RABBITMQ_PASS,
            )
            logger.info(
                "Conexão AMQP estabelecida com %s:%d%s",
                RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST,
            )
            break
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Tentativa %d/%d de conectar ao RabbitMQ falhou: %s",
                attempt, STARTUP_RETRIES, exc,
            )
            if attempt < STARTUP_RETRIES:
                await asyncio.sleep(STARTUP_RETRY_DELAY)
    else:
        logger.error(
            "Não foi possível conectar ao RabbitMQ após %d tentativas: %s",
            STARTUP_RETRIES, last_error,
        )
        sys.exit(1)

    yield

    if _connection and not _connection.is_closed:
        await _connection.close()
    logger.info("API Bridge encerrada")


# --- App FastAPI ---
app = FastAPI(
    title="Sensores API Bridge",
    description="API HTTP para publicação de leituras de sensores no RabbitMQ",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    if _connection and not _connection.is_closed:
        return {"status": "healthy", "broker": "connected"}
    return {"status": "degraded", "broker": "disconnected"}


@app.post("/api/v1/leituras", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publicar_leitura(leitura: LeituraSensor):
    """
    Publica uma leitura de sensor na fila RabbitMQ.

    Qualquer sensor com o endereço pode publicar (fase 1 - fila aberta).
    """
    if not leitura.timestamp:
        leitura.timestamp = datetime.now(timezone.utc).isoformat()

    routing_key = f"sensor.{leitura.tipo_sensor}.{leitura.sensor_id}"

    try:
        await _publish_messages([(routing_key, leitura.model_dump_json().encode())])
    except Exception as exc:
        logger.error("Erro ao publicar: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker indisponível. Tente novamente.",
        )

    logger.info("Publicado: %s → %s", routing_key, leitura.valor)
    return PublishResponse(ok=True, message="Leitura publicada", routing_key=routing_key)


@app.post("/api/v1/leituras/batch", status_code=status.HTTP_201_CREATED)
async def publicar_leituras_batch(leituras: list[LeituraSensor]):
    """
    Publica múltiplas leituras de uma vez (batch).
    Limite: 100 leituras por request.
    """
    if len(leituras) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 100 leituras por batch",
        )

    for leitura in leituras:
        if not leitura.timestamp:
            leitura.timestamp = datetime.now(timezone.utc).isoformat()

    messages = [
        (f"sensor.{l.tipo_sensor}.{l.sensor_id}", l.model_dump_json().encode())
        for l in leituras
    ]

    try:
        await _publish_messages(messages)
    except Exception as exc:
        logger.error("Erro ao publicar batch: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker indisponível. Tente novamente.",
        )

    resultados = [{"routing_key": rk, "ok": True} for rk, _ in messages]
    logger.info("Batch publicado: %d leituras", len(resultados))
    return {"ok": True, "total": len(resultados), "leituras": resultados}
