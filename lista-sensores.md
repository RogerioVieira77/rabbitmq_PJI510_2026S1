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

## Bombas de Drenagem

| ID | Label | Localização | Métrica | Valores |
|---|---|---|---|---|
| `BOMBA-DRE-001` | Bomba de Drenagem 1 (Piscinao Romano) | Piscinao Romano | `estado_bomba` | `1.0` = Ligada · `0.0` = Desligada |
| `BOMBA-DRE-002` | Bomba de Drenagem 2 (Piscinao Romano) | Piscinao Romano | `estado_bomba` | `1.0` = Ligada · `0.0` = Desligada |
| `BOMBA-DRE-003` | Bomba de Drenagem 3 (Piscinao Romano) | Piscinao Romano | `estado_bomba` | `1.0` = Ligada · `0.0` = Desligada |
| `BOMBA-DRE-004` | Bomba de Drenagem 4 (Piscinao Romano) | Piscinao Romano | `estado_bomba` | `1.0` = Ligada · `0.0` = Desligada |
| `BOMBA-DRE-005` | Bomba de Drenagem 5 (Piscinao Romano) | Piscinao Romano | `estado_bomba` | `1.0` = Ligada · `0.0` = Desligada |

**Coordenadas:**

- `BOMBA-DRE-001`: latitude `-23.477310`, longitude `-46.382610`
- `BOMBA-DRE-002`: latitude `-23.477380`, longitude `-46.382680`
- `BOMBA-DRE-003`: latitude `-23.477450`, longitude `-46.382760`
- `BOMBA-DRE-004`: latitude `-23.477520`, longitude `-46.382830`
- `BOMBA-DRE-005`: latitude `-23.477590`, longitude `-46.382910`

### Métrica das Bombas de Drenagem

| Tipo (`tipo_sensor`) | Unidade | Valores | Descrição |
|---|---|---|---|
| `estado_bomba` | bool | `1.0` / `0.0` | Estado operacional da bomba (1 = ligada, 0 = desligada) |

> Cada envio de uma bomba gera **1 mensagem** no RabbitMQ com o estado atual.

---

## Routing Keys (RabbitMQ)

Formato: `sensor.<tipo_sensor>.<sensor_id>`

Exemplos:

- `sensor.nivel_agua.SENSOR-RES-001`
- `sensor.nivel_agua.SENSOR-RES-002`
- `sensor.temperatura.ESTACAO-MET-001`
- `sensor.pluviometro.ESTACAO-MET-002`
- `sensor.estado_bomba.BOMBA-DRE-001`
- `sensor.estado_bomba.BOMBA-DRE-002`
- `sensor.estado_bomba.BOMBA-DRE-003`
- `sensor.estado_bomba.BOMBA-DRE-004`
- `sensor.estado_bomba.BOMBA-DRE-005`

Exchange: `sensores.exchange` (topic)  
Vhost: `/pji510`
