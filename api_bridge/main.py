"""
API Bridge HTTP → AMQP
Recebe leituras de sensores via POST HTTPS e publica no RabbitMQ.

Fase 1: Fila aberta — qualquer sensor com o endereço consegue publicar.
Fase 2 (futura): Autenticação por token/API key para sensores registrados.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import pika
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

# --- Modelos ---
class Localizacao(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    descricao: Optional[str] = None


class LeituraSensor(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=100)
    tipo_sensor: str = Field(..., pattern=r"^(nivel_agua|vazao|pluviometro|pressao|temperatura)$")
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


# --- Conexão RabbitMQ ---
_connection: Optional[pika.BlockingConnection] = None
_channel = None


def get_channel():
    global _connection, _channel
    if _connection is None or _connection.is_closed:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        params = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VHOST,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
        _connection = pika.BlockingConnection(params)
        _channel = _connection.channel()
        logger.info("Conexão AMQP estabelecida com %s:%s%s", RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_VHOST)
    if _channel is None or _channel.is_closed:
        _channel = _connection.channel()
    return _channel


def close_connection():
    global _connection, _channel
    if _connection and not _connection.is_closed:
        _connection.close()
        logger.info("Conexão AMQP fechada")
    _connection = None
    _channel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Bridge iniciando...")
    try:
        get_channel()
        logger.info("Conexão AMQP pronta")
    except Exception as e:
        logger.warning("Não foi possível conectar ao RabbitMQ no startup: %s", e)
    yield
    close_connection()
    logger.info("API Bridge encerrada")


# --- App FastAPI ---
app = FastAPI(
    title="Sensores API Bridge",
    description="API HTTP para publicação de leituras de sensores no RabbitMQ",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    try:
        ch = get_channel()
        if ch.is_open:
            return {"status": "healthy", "broker": "connected"}
    except Exception:
        pass
    return {"status": "degraded", "broker": "disconnected"}


@app.post("/api/v1/leituras", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
def publicar_leitura(leitura: LeituraSensor):
    """
    Publica uma leitura de sensor na fila RabbitMQ.

    Qualquer sensor com o endereço pode publicar (fase 1 - fila aberta).
    """
    if not leitura.timestamp:
        leitura.timestamp = datetime.now(timezone.utc).isoformat()

    routing_key = f"sensor.{leitura.tipo_sensor}.{leitura.sensor_id}"
    body = leitura.model_dump_json()

    try:
        channel = get_channel()
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistente
                content_type="application/json",
            ),
        )
    except Exception as e:
        logger.error("Erro ao publicar: %s", e)
        close_connection()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker indisponível. Tente novamente.",
        )

    logger.info("Publicado: %s → %s", routing_key, leitura.valor)
    return PublishResponse(ok=True, message="Leitura publicada", routing_key=routing_key)


@app.post("/api/v1/leituras/batch", status_code=status.HTTP_201_CREATED)
def publicar_leituras_batch(leituras: list[LeituraSensor]):
    """
    Publica múltiplas leituras de uma vez (batch).
    Limite: 100 leituras por request.
    """
    if len(leituras) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 100 leituras por batch",
        )

    resultados = []
    try:
        channel = get_channel()
        for leitura in leituras:
            if not leitura.timestamp:
                leitura.timestamp = datetime.now(timezone.utc).isoformat()
            routing_key = f"sensor.{leitura.tipo_sensor}.{leitura.sensor_id}"
            channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=leitura.model_dump_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            resultados.append({"routing_key": routing_key, "ok": True})
    except Exception as e:
        logger.error("Erro ao publicar batch: %s", e)
        close_connection()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Broker indisponível. Tente novamente.",
        )

    logger.info("Batch publicado: %d leituras", len(resultados))
    return {"ok": True, "total": len(resultados), "leituras": resultados}
