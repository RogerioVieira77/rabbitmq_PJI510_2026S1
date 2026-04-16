# Teste com Postman — API de Sensores PJI510

## 1. Health Check

- **Método**: `GET`
- **URL**: `https://sensores-pji510.unicomunitaria.com.br/health`
- Clique **Send**
- Resposta esperada (200):
```json
{"status": "healthy", "broker": "connected"}
```

---

## 2. Publicar uma leitura (single)

- **Método**: `POST`
- **URL**: `https://sensores-pji510.unicomunitaria.com.br/api/v1/leituras`
- Aba **Headers**: adicione `Content-Type` = `application/json`
- Aba **Body** → selecione **raw** → **JSON**, cole:

```json
{
  "sensor_id": "sensor_nivel_001",
  "tipo_sensor": "nivel_agua",
  "valor": 2.45,
  "unidade": "m",
  "status": "normal"
}
```

- Clique **Send**
- Resposta esperada (201):
```json
{
  "ok": true,
  "message": "Leitura publicada",
  "routing_key": "sensor.nivel_agua.sensor_nivel_001"
}
```

---

## 3. Publicar em batch

- **Método**: `POST`
- **URL**: `https://sensores-pji510.unicomunitaria.com.br/api/v1/leituras/batch`
- **Headers**: `Content-Type` = `application/json`
- **Body** → **raw** → **JSON**:

```json
[
  {
    "sensor_id": "sensor_nivel_002",
    "tipo_sensor": "nivel_agua",
    "valor": 1.85,
    "unidade": "m"
  },
  {
    "sensor_id": "sensor_chuva_001",
    "tipo_sensor": "pluviometro",
    "valor": 12.3,
    "unidade": "mm/h"
  },
  {
    "sensor_id": "sensor_temp_001",
    "tipo_sensor": "temperatura",
    "valor": 23.5,
    "unidade": "C",
    "status": "alerta",
    "bateria_pct": 72
  }
]
```

- Resposta esperada (201):
```json
{
  "ok": true,
  "total": 3,
  "leituras": [
    {"routing_key": "sensor.nivel_agua.sensor_nivel_002", "ok": true},
    {"routing_key": "sensor.pluviometro.sensor_chuva_001", "ok": true},
    {"routing_key": "sensor.temperatura.sensor_temp_001", "ok": true}
  ]
}
```

---

## 4. Testar validação (erro proposital)

- **POST** para `/api/v1/leituras` com tipo inválido:

```json
{
  "sensor_id": "sensor_001",
  "tipo_sensor": "umidade",
  "valor": 80,
  "unidade": "%"
}
```

- Resposta esperada (422 — Unprocessable Entity) com mensagem indicando que `tipo_sensor` deve ser um dos valores aceitos.

---

## 5. Documentação Swagger

Acesse no navegador: `https://sensores-pji510.unicomunitaria.com.br/docs`

Lá você pode testar todos os endpoints diretamente pelo "Try it out" sem precisar do Postman.

---

## Tipos de sensor aceitos

| tipo_sensor | Descrição |
|---|---|
| `nivel_agua` | Nível da água (m) |
| `vazao` | Vazão (m³/s) |
| `pluviometro` | Precipitação (mm/h) |
| `pressao` | Pressão (kPa) |
| `temperatura` | Temperatura (°C) |

## Campos opcionais

| Campo | Tipo | Descrição |
|---|---|---|
| `timestamp` | string ISO 8601 | Preenchido automaticamente se omitido |
| `status` | `normal`, `alerta`, `critico`, `erro` | Default: `normal` |
| `bateria_pct` | int 0-100 | Nível de bateria do sensor |
| `localizacao` | objeto | `latitude`, `longitude`, `descricao` |
