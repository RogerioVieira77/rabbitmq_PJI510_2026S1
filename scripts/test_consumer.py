#!/usr/bin/env python3
"""
Consumer de teste - Consome mensagens da fila de leituras de sensores.
Uso: python3 scripts/test_consumer.py
Requer: pip install pika
"""

import json
import sys

import pika

RABBITMQ_HOST = "127.0.0.1"
RABBITMQ_PORT = 5672
RABBITMQ_VHOST = "/pji510"
RABBITMQ_USER = "alerta_consumer"
RABBITMQ_PASS = "consumer_pass_temp"  # Trocar pela senha real

QUEUE = "sensores.leituras"
PREFETCH = 10


def callback(ch, method, properties, body):
    try:
        leitura = json.loads(body)
        status_icon = "⚠️" if leitura.get("status") == "alerta" else "✅"
        print(
            f"{status_icon} [{method.routing_key}] "
            f"Sensor: {leitura['sensor_id']} | "
            f"Tipo: {leitura['tipo_sensor']} | "
            f"Valor: {leitura['valor']} {leitura['unidade']} | "
            f"Status: {leitura['status']} | "
            f"Timestamp: {leitura['timestamp']}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except json.JSONDecodeError as e:
        print(f"ERRO: Mensagem inválida (não é JSON): {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except KeyError as e:
        print(f"ERRO: Campo obrigatório ausente: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"ERRO inesperado: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


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

    channel.basic_qos(prefetch_count=PREFETCH)
    channel.basic_consume(queue=QUEUE, on_message_callback=callback, auto_ack=False)

    print(f"Conectado ao RabbitMQ em {RABBITMQ_HOST}:{RABBITMQ_PORT}")
    print(f"Consumindo da fila '{QUEUE}' (vhost: {RABBITMQ_VHOST})")
    print(f"Prefetch: {PREFETCH}")
    print("Aguardando mensagens... Ctrl+C para parar.\n")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nParado.")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
