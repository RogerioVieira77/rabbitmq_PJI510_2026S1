#!/usr/bin/env python3
"""
Producer de teste - Publica mensagens simulando leituras de sensores.
Uso: python3 scripts/test_producer.py
Requer: pip install pika
"""

import json
import random
import time
from datetime import datetime, timezone

import pika

RABBITMQ_HOST = "127.0.0.1"
RABBITMQ_PORT = 5672
RABBITMQ_VHOST = "/pji510"
RABBITMQ_USER = "sensor_producer"
RABBITMQ_PASS = "sensor_pass_temp"  # Trocar pela senha real

EXCHANGE = "sensores.exchange"

SENSORES = [
    {"sensor_id": "SENSOR-RES-001", "tipo": "nivel_agua", "unidade": "metros", "min": 0.5, "max": 8.0},
    {"sensor_id": "SENSOR-RES-002", "tipo": "vazao", "unidade": "m3/s", "min": 0.1, "max": 15.0},
    {"sensor_id": "SENSOR-RES-003", "tipo": "pluviometro", "unidade": "mm/h", "min": 0.0, "max": 120.0},
    {"sensor_id": "SENSOR-RES-004", "tipo": "pressao", "unidade": "kPa", "min": 80.0, "max": 250.0},
    {"sensor_id": "SENSOR-RES-005", "tipo": "temperatura", "unidade": "C", "min": 10.0, "max": 35.0},
]


def gerar_leitura(sensor: dict) -> dict:
    valor = round(random.uniform(sensor["min"], sensor["max"]), 2)
    status = "normal"
    if sensor["tipo"] == "nivel_agua" and valor > 6.5:
        status = "alerta"
    elif sensor["tipo"] == "pluviometro" and valor > 80.0:
        status = "alerta"

    return {
        "sensor_id": sensor["sensor_id"],
        "tipo_sensor": sensor["tipo"],
        "valor": valor,
        "unidade": sensor["unidade"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "localizacao": {
            "latitude": -23.5505,
            "longitude": -46.6333,
            "descricao": "Reservatório Norte - Ponto A",
        },
        "status": status,
        "bateria_pct": random.randint(20, 100),
    }


def main():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
    )

    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    print(f"Conectado ao RabbitMQ em {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    print(f"Publicando no exchange '{EXCHANGE}' (vhost: {RABBITMQ_VHOST})")
    print("Ctrl+C para parar.\n")

    try:
        count = 0
        while True:
            sensor = random.choice(SENSORES)
            leitura = gerar_leitura(sensor)
            routing_key = f"sensor.{sensor['tipo']}.{sensor['sensor_id']}"

            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(leitura),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistente
                    content_type="application/json",
                ),
            )

            count += 1
            status_icon = "⚠️" if leitura["status"] == "alerta" else "✅"
            print(
                f"[{count}] {status_icon} {routing_key} → "
                f"{leitura['valor']} {leitura['unidade']} ({leitura['status']})"
            )

            time.sleep(2)  # simula intervalo entre leituras

    except KeyboardInterrupt:
        print(f"\nParado. Total de mensagens publicadas: {count}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
