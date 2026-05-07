# Lista de Sensores - PJI510 2026/S1

Cenario oficial: localidade unica Jardim Romano, com monitoramento do Piscinao Romano para a aplicacao Alerta Romano.

## Sensores de Nível de Água

| ID | Label | Localização | Métrica | Faixa |
|---|---|---|---|---|
| `SENSOR-RES-001` | Sensor de Nivel 1 (Piscinao - Norte) | Piscinao Romano | `nivel_agua` | 0-8 m |
| `SENSOR-RES-002` | Sensor de Nivel 2 (Piscinao - Sul) | Piscinao Romano | `nivel_agua` | 0-8 m |

**Coordenadas:**

- `SENSOR-RES-001`: latitude `-23.477448639552904`, longitude `-46.38281519942896`
- `SENSOR-RES-002`: latitude `-23.477509826705106`, longitude `-46.38297628605139`

---

## Estações Meteorológicas

| ID | Label | Localização |
|---|---|---|
| `ESTACAO-MET-001` | Estacao Meteorologica 1 (CEU Tres Pontes) | CEU Tres Pontes |
| `ESTACAO-MET-002` | Estacao Meteorologica 2 (Piscinao Romano) | Piscinao Romano |

**Coordenadas:**

- `ESTACAO-MET-001`: latitude `-23.47887049933471`, longitude `-46.381250238234415`
- `ESTACAO-MET-002`: latitude `-23.477472724522762`, longitude `-46.38292473607622`

### Métricas das Estações Meteorológicas

| Tipo (`tipo_sensor`) | Unidade | Faixa |
|---|---|---|
| `vento_direcao` | graus | 0 – 359 |
| `vento_velocidade` | km/h | 0 – 180 |
| `pluviometro` | mm | 0 – 300 |
| `temperatura` | °C | −40 – 60 |
| `umidade` | % | 10 – 99 |
| `pressao` | hPa | 800 – 1100 |

> Cada envio de uma estacao meteorologica gera **6 mensagens separadas** no RabbitMQ, uma por tipo de metrica.

---

## Routing Keys (RabbitMQ)

Formato: `sensores.<tipo_sensor>.<sensor_id>`

Exemplos:

- `sensores.nivel_agua.SENSOR-RES-001`
- `sensores.nivel_agua.SENSOR-RES-002`
- `sensores.temperatura.ESTACAO-MET-001`
- `sensores.pluviometro.ESTACAO-MET-002`

Exchange: `sensores.exchange` (topic)  
Vhost: `/pji510`
