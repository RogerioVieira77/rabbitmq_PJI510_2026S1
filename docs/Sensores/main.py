import network
import time
import random
from machine import Pin, time_pulse_us
import ujson
import urequests

# Configurações da API
API_URL = "https://sensores-pji510.unicomunitaria.com.br/api/v1/leituras"
HEADERS = {'Content-Type': 'application/json'}

# Configuração de Hardware (Sensores HC-SR04)
TRIG1 = Pin(5, Pin.OUT)
ECHO1 = Pin(18, Pin.IN)
TRIG2 = Pin(17, Pin.OUT)
ECHO2 = Pin(16, Pin.IN)

# Parâmetros do sistema
altura_total_cm = 400
tolerancia_cm = 1
MM_POR_PULSO = 2
chuva_mm = 0
contador_medicoes = 0
nivel_anterior_m = None
offset_chuva_cm = 0

# Conexão WiFi
print("Conectando ao WiFi", end="")
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('Wokwi-GUEST', '')
while not sta_if.isconnected():
    print(".", end="")
    time.sleep(0.1)
print(" Conectado!")

def medir_distancia(trig, echo):
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1)
    return duracao / 58  # Cálculo de distância em cm

def enviar_para_api(tipo, valor, unidade):
    payload = {
        "sensor_id": "sensor_nivel_001",
        "tipo_sensor": tipo,
        "valor": round(valor, 2),
        "unidade": unidade
    }

    print(f"\n[INFO] Enviando dados de {tipo}...")
    print(f"[DADOS]: {ujson.dumps(payload)}")
    
    try:
        response = urequests.post(API_URL, json=payload, headers=HEADERS)
        print(f"[STATUS RESPOSTA]: {response.status_code}")
        
        # Error Handler
        if response.status_code != 201:
            print(f"[RESPOSTA SERVIDOR]: {response.text}")
            
        response.close()
    except Exception as e:
        print(f"[ERRO]: Falha na comunicação: {e}")

while True:
    contador_medicoes += 1
    
    # A cada 10 medições, reduz o offset equivalente a 2 pulsos do pluviômetro
    if contador_medicoes % 10 == 0:
        perda_cm = 2 * (MM_POR_PULSO / 10) 
        offset_chuva_cm = max(0, offset_chuva_cm - perda_cm)
    
    # Medição de Nível (Média de dois sensores para precisão)
    dist1 = medir_distancia(TRIG1, ECHO1)
    time.sleep_ms(50)
    dist2 = medir_distancia(TRIG2, ECHO2)
    distancia_media = (dist1 + dist2) / 2
    
    # Cálculo do nível com o offset da chuva
    nivel_cm = max(0, altura_total_cm - distancia_media + offset_chuva_cm)
    nivel_m = nivel_cm / 100 
    
    # Envio do nível se houver mudança relevante
    if nivel_anterior_m is None or abs(nivel_m - nivel_anterior_m) > (tolerancia_cm / 100):
        enviar_para_api("nivel_agua", nivel_m, "m")
        nivel_anterior_m = nivel_m

    # Simulação de Pluviômetro a cada 6 ciclos
    if contador_medicoes % 6 == 0:
        intensidade = random.choice(["fraca", "media", "forte", "sem_chuva"])
        novos_pulsos = {"fraca": 1, "media": random.randint(2, 4), "forte": random.randint(5, 10)}.get(intensidade, 0)
        
        chuva_mm += novos_pulsos * MM_POR_PULSO
        # A cada chuva, o nível do tanque também sobe 
        offset_chuva_cm += novos_pulsos * MM_POR_PULSO / 10   # converte mm para cm
        
        if chuva_mm > 0:
            enviar_para_api("pluviometro", chuva_mm, "mm/h")

        # Reset aleatório da chuva para simular fim de precipitação
        if novos_pulsos > 0 and random.random() < 0.2:
            chuva_mm = 0
            print("Chuva cessou. Acumulador resetado.")

    time.sleep(1)