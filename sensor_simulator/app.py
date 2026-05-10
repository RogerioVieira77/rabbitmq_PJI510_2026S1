import asyncio
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

API_BRIDGE_URL = os.getenv("API_BRIDGE_URL", "http://api_bridge:8000")
SEND_TIMEOUT_SECONDS = 8

SENSOR_STATE: dict[str, dict[str, Any]] = {
    "SENSOR-RES-001": {
        "sensor_id": "SENSOR-RES-001",
        "kind": "water",
        "label": "Sensor de Nivel 1 (Piscinao - Norte)",
        "ativo": True,
        "fonte_alimentacao": "rede",
        "bateria_pct": 96,
        "bms_nivel": "normal",
        "values": {"nivel_agua": 2.35},
        "ranges": {"nivel_agua": {"min": 0.0, "max": 8.0, "step": 0.01}},
        "units": {"nivel_agua": "m"},
        "location": {
            "latitude": -23.477448639552904,
            "longitude": -46.38281519942896,
            "descricao": "Piscinao Romano - Norte",
        },
    },
    "SENSOR-RES-002": {
        "sensor_id": "SENSOR-RES-002",
        "kind": "water",
        "label": "Sensor de Nivel 2 (Piscinao - Sul)",
        "ativo": True,
        "fonte_alimentacao": "rede",
        "bateria_pct": 94,
        "bms_nivel": "normal",
        "values": {"nivel_agua": 2.72},
        "ranges": {"nivel_agua": {"min": 0.0, "max": 8.0, "step": 0.01}},
        "units": {"nivel_agua": "m"},
        "location": {
            "latitude": -23.477509826705106,
            "longitude": -46.38297628605139,
            "descricao": "Piscinao Romano - Sul",
        },
    },
    "ESTACAO-MET-001": {
        "sensor_id": "ESTACAO-MET-001",
        "kind": "weather",
        "label": "Estacao Meteorologica 1 (CEU Tres Pontes)",
        "ativo": True,
        "fonte_alimentacao": "rede",
        "bateria_pct": 92,
        "bms_nivel": "normal",
        "values": {
            "vento_direcao": 180,
            "vento_velocidade": 12.0,
            "pluviometro": 0.0,
            "temperatura": 24.2,
            "umidade": 71.0,
            "pressao": 1012.3,
        },
        "ranges": {
            "vento_direcao": {"min": 0, "max": 359, "step": 1},
            "vento_velocidade": {"min": 0.0, "max": 180.0, "step": 0.1},
            "pluviometro": {"min": 0.0, "max": 300.0, "step": 0.1},
            "temperatura": {"min": -40.0, "max": 60.0, "step": 0.1},
            "umidade": {"min": 10.0, "max": 99.0, "step": 0.1},
            "pressao": {"min": 800.0, "max": 1100.0, "step": 0.1},
        },
        "units": {
            "vento_direcao": "graus",
            "vento_velocidade": "km/h",
            "pluviometro": "mm",
            "temperatura": "C",
            "umidade": "%",
            "pressao": "hPa",
        },
        "location": {
            "latitude": -23.47887049933471,
            "longitude": -46.381250238234415,
            "descricao": "CEU Tres Pontes",
        },
    },
    "ESTACAO-MET-002": {
        "sensor_id": "ESTACAO-MET-002",
        "kind": "weather",
        "label": "Estacao Meteorologica 2 (Piscinao Romano)",
        "ativo": True,
        "fonte_alimentacao": "rede",
        "bateria_pct": 90,
        "bms_nivel": "normal",
        "values": {
            "vento_direcao": 122,
            "vento_velocidade": 9.2,
            "pluviometro": 1.2,
            "temperatura": 22.9,
            "umidade": 74.5,
            "pressao": 1010.7,
        },
        "ranges": {
            "vento_direcao": {"min": 0, "max": 359, "step": 1},
            "vento_velocidade": {"min": 0.0, "max": 180.0, "step": 0.1},
            "pluviometro": {"min": 0.0, "max": 300.0, "step": 0.1},
            "temperatura": {"min": -40.0, "max": 60.0, "step": 0.1},
            "umidade": {"min": 10.0, "max": 99.0, "step": 0.1},
            "pressao": {"min": 800.0, "max": 1100.0, "step": 0.1},
        },
        "units": {
            "vento_direcao": "graus",
            "vento_velocidade": "km/h",
            "pluviometro": "mm",
            "temperatura": "C",
            "umidade": "%",
            "pressao": "hPa",
        },
        "location": {
            "latitude": -23.477472724522762,
            "longitude": -46.38292473607622,
            "descricao": "Piscinao Romano",
        },
    },
}

AUTO_STATE: dict[str, Any] = {"enabled": False, "interval_seconds": 10}
AUTO_TASK: Optional[asyncio.Task] = None

app = FastAPI(title="PJI510 Sensor Simulator", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


class UpdateSensorRequest(BaseModel):
    sensor_id: str
    fields: dict[str, Any]


class RandomizeRequest(BaseModel):
    sensor_id: Optional[str] = None


class SendRequest(BaseModel):
    sensor_id: Optional[str] = None


class AutoStartRequest(BaseModel):
    interval_seconds: int = Field(default=10, ge=1, le=3600)


def _safe_state() -> dict[str, dict[str, Any]]:
    return SENSOR_STATE


def _bms_from_battery_pct(bateria_pct: int) -> str:
    if bateria_pct <= 15:
        return "critico"
    if bateria_pct <= 30:
        return "alerta"
    return "normal"


def _clamp(field_name: str, value: float, sensor: dict[str, Any]) -> float:
    field_range = sensor["ranges"].get(field_name)
    if field_range is None:
        raise HTTPException(status_code=400, detail=f"Campo invalido para o sensor: {field_name}")
    min_value = float(field_range["min"])
    max_value = float(field_range["max"])
    step = float(field_range["step"])
    clamped = max(min_value, min(max_value, value))
    decimals = 0 if step >= 1 else 1 if step >= 0.1 else 2
    return round(clamped, decimals)


def _randomize_sensor(sensor: dict[str, Any]) -> None:
    if sensor["fonte_alimentacao"] == "bateria":
        sensor["bateria_pct"] = max(0, int(sensor["bateria_pct"]) - random.randint(1, 8))
    else:
        sensor["bateria_pct"] = min(100, int(sensor["bateria_pct"]) + random.randint(0, 2))
    sensor["bms_nivel"] = _bms_from_battery_pct(int(sensor["bateria_pct"]))

    if sensor["kind"] == "water":
        sensor["values"]["nivel_agua"] = round(random.uniform(0.0, 8.0), 2)
        return

    sensor["values"]["vento_direcao"] = random.randint(0, 359)
    sensor["values"]["vento_velocidade"] = round(random.uniform(0.0, 180.0), 1)
    sensor["values"]["pluviometro"] = round(random.uniform(0.0, 300.0), 1)
    sensor["values"]["temperatura"] = round(random.uniform(-40.0, 60.0), 1)
    sensor["values"]["umidade"] = round(random.uniform(10.0, 99.0), 1)
    sensor["values"]["pressao"] = round(random.uniform(800.0, 1100.0), 1)


def _status_for(tipo_sensor: str, valor: float) -> str:
    if tipo_sensor == "nivel_agua":
        if valor >= 6.5:
            return "critico"
        if valor >= 5.5:
            return "alerta"
        return "normal"
    if tipo_sensor == "pluviometro":
        if valor >= 120:
            return "critico"
        if valor >= 80:
            return "alerta"
        return "normal"
    if tipo_sensor == "vento_velocidade":
        if valor >= 120:
            return "critico"
        if valor >= 90:
            return "alerta"
        return "normal"
    if tipo_sensor == "temperatura":
        if valor <= -20 or valor >= 50:
            return "critico"
        if valor <= -5 or valor >= 40:
            return "alerta"
        return "normal"
    if tipo_sensor == "umidade":
        if valor <= 15 or valor >= 98:
            return "critico"
        if valor <= 20 or valor >= 95:
            return "alerta"
        return "normal"
    if tipo_sensor == "pressao":
        if valor <= 830 or valor >= 1085:
            return "critico"
        if valor <= 850 or valor >= 1065:
            return "alerta"
        return "normal"
    return "normal"


def _build_payloads(sensor: dict[str, Any]) -> list[dict[str, Any]]:
    sensor_id = sensor["sensor_id"]
    location = sensor["location"]
    values = sensor["values"]

    if sensor["kind"] == "water":
        value = float(values["nivel_agua"])
        return [
            {
                "sensor_id": sensor_id,
                "tipo_sensor": "nivel_agua",
                "valor": value,
                "unidade": "m",
                "status": _status_for("nivel_agua", value),
                "localizacao": location,
                "bateria_pct": int(sensor["bateria_pct"]),
                "ativo": bool(sensor["ativo"]),
                "fonte_alimentacao": sensor["fonte_alimentacao"],
                "bms_nivel": sensor["bms_nivel"],
            }
        ]

    payloads = []
    for tipo_sensor in (
        "vento_direcao",
        "vento_velocidade",
        "pluviometro",
        "temperatura",
        "umidade",
        "pressao",
    ):
        value = float(values[tipo_sensor])
        payloads.append(
            {
                "sensor_id": sensor_id,
                "tipo_sensor": tipo_sensor,
                "valor": value,
                "unidade": sensor["units"][tipo_sensor],
                "status": _status_for(tipo_sensor, value),
                "localizacao": location,
                "bateria_pct": int(sensor["bateria_pct"]),
                "ativo": bool(sensor["ativo"]),
                "fonte_alimentacao": sensor["fonte_alimentacao"],
                "bms_nivel": sensor["bms_nivel"],
            }
        )
    return payloads


async def _send_payload(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{API_BRIDGE_URL}/api/v1/leituras", json=payload)
    response_data: Any = None
    try:
        response_data = response.json()
    except Exception:
        response_data = response.text

    return {
        "sensor_id": payload["sensor_id"],
        "tipo_sensor": payload["tipo_sensor"],
        "status_code": response.status_code,
        "ok": response.status_code == 201,
        "response": response_data,
    }


async def _send_sensor(sensor: dict[str, Any]) -> list[dict[str, Any]]:
    if not bool(sensor.get("ativo", True)):
        return [
            {
                "sensor_id": sensor["sensor_id"],
                "tipo_sensor": "*",
                "status_code": 409,
                "ok": False,
                "response": {
                    "ok": False,
                    "message": "Sensor desligado. Envio bloqueado.",
                },
            }
        ]

    payloads = _build_payloads(sensor)
    tasks = [_send_payload(payload) for payload in payloads]
    return await asyncio.gather(*tasks)


async def _auto_loop() -> None:
    while AUTO_STATE["enabled"]:
        for sensor in SENSOR_STATE.values():
            try:
                _randomize_sensor(sensor)
                await _send_sensor(sensor)
            except Exception:
                pass
        await asyncio.sleep(AUTO_STATE["interval_seconds"])


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(Path("static/index.html"))


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sensors")
async def get_sensors() -> dict[str, Any]:
    return {"sensors": list(_safe_state().values())}


@app.post("/api/sensors/randomize")
async def randomize_sensors(body: RandomizeRequest) -> dict[str, Any]:
    if body.sensor_id:
        sensor = SENSOR_STATE.get(body.sensor_id)
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor nao encontrado")
        _randomize_sensor(sensor)
    else:
        for sensor in SENSOR_STATE.values():
            _randomize_sensor(sensor)

    return {"ok": True, "sensors": list(_safe_state().values())}


@app.post("/api/sensors/update")
async def update_sensor(body: UpdateSensorRequest) -> dict[str, Any]:
    sensor = SENSOR_STATE.get(body.sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor nao encontrado")

    for field_name, value in body.fields.items():
        if field_name in sensor["values"]:
            sensor["values"][field_name] = _clamp(field_name, float(value), sensor)
            continue

        if field_name == "ativo":
            sensor["ativo"] = bool(value)
            continue

        if field_name == "fonte_alimentacao":
            if value not in ("rede", "bateria"):
                raise HTTPException(status_code=400, detail="fonte_alimentacao deve ser 'rede' ou 'bateria'")
            sensor["fonte_alimentacao"] = value
            if value == "rede":
                sensor["bms_nivel"] = "normal"
            else:
                sensor["bms_nivel"] = _bms_from_battery_pct(int(sensor["bateria_pct"]))
            continue

        if field_name == "bateria_pct":
            pct = int(value)
            if pct < 0 or pct > 100:
                raise HTTPException(status_code=400, detail="bateria_pct deve estar entre 0 e 100")
            sensor["bateria_pct"] = pct
            sensor["bms_nivel"] = _bms_from_battery_pct(pct)
            continue

        if field_name == "bms_nivel":
            if value not in ("normal", "alerta", "critico"):
                raise HTTPException(status_code=400, detail="bms_nivel deve ser normal, alerta ou critico")
            sensor["bms_nivel"] = value
            continue

        raise HTTPException(status_code=400, detail=f"Campo invalido: {field_name}")

    return {"ok": True, "sensor": sensor}


@app.post("/api/sensors/send")
async def send_sensors(body: SendRequest) -> dict[str, Any]:
    if body.sensor_id:
        sensor = SENSOR_STATE.get(body.sensor_id)
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor nao encontrado")
        result = await _send_sensor(sensor)
        return {"ok": all(item["ok"] for item in result), "results": result}

    all_results: list[dict[str, Any]] = []
    for sensor in SENSOR_STATE.values():
        sensor_results = await _send_sensor(sensor)
        all_results.extend(sensor_results)

    return {"ok": all(item["ok"] for item in all_results), "results": all_results}


@app.get("/api/auto")
async def auto_status() -> dict[str, Any]:
    return AUTO_STATE


@app.post("/api/auto/start")
async def auto_start(body: AutoStartRequest) -> dict[str, Any]:
    global AUTO_TASK
    AUTO_STATE["interval_seconds"] = body.interval_seconds
    if AUTO_STATE["enabled"]:
        return {"ok": True, "message": "Envio automatico ja estava ativo", "auto": AUTO_STATE}

    AUTO_STATE["enabled"] = True
    AUTO_TASK = asyncio.create_task(_auto_loop())
    return {"ok": True, "message": "Envio automatico iniciado", "auto": AUTO_STATE}


@app.post("/api/auto/stop")
async def auto_stop() -> dict[str, Any]:
    AUTO_STATE["enabled"] = False
    return {"ok": True, "message": "Envio automatico desativado", "auto": AUTO_STATE}


# --- Endpoints para Simulações Independentes ---

class PrevisaoChuvaRequest(BaseModel):
    regiao: str = Field(default="Jardim Romano", min_length=1, max_length=100)
    nivel: int = Field(..., ge=1, le=5)
    descricao: str = Field(..., min_length=1, max_length=200)
    precipitacao_mm: float = Field(..., ge=0, le=300)


class AlertaDefesaCivilItem(BaseModel):
    regiao: str = Field(..., min_length=1, max_length=100)
    descricao: str = Field(..., min_length=1, max_length=200)
    severidade: str = Field(..., pattern=r"^(normal|atencao|critico)$")


class SituacaoDefesaCivilRequest(BaseModel):
    status: str = Field(..., pattern=r"^(verde|amarelo|laranja|vermelho)$")
    alertas_ativos: list[AlertaDefesaCivilItem] = Field(default_factory=list, max_length=5)


class AlertaDefesaCivilRequest(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=100)
    descricao: str = Field(..., min_length=1, max_length=500)
    regiao: str = Field(default="Jardim Romano", min_length=1, max_length=100)
    valido_ate: str = Field(...)  # ISO 8601 datetime string


@app.post("/api/previsoes")
async def send_previsao_chuva(body: PrevisaoChuvaRequest) -> dict[str, Any]:
    """Publica uma previsão de chuva no API Bridge."""
    payload = body.model_dump()
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{API_BRIDGE_URL}/api/v1/previsoes", json=payload)
    
    try:
        response_data = response.json()
    except Exception:
        response_data = response.text
    
    return {
        "ok": response.status_code == 201,
        "status_code": response.status_code,
        "response": response_data,
    }


@app.post("/api/defesa-civil")
async def send_situacao_defesa_civil(body: SituacaoDefesaCivilRequest) -> dict[str, Any]:
    """Publica a situação da Defesa Civil no API Bridge."""
    payload = body.model_dump()
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{API_BRIDGE_URL}/api/v1/defesa-civil", json=payload)
    
    try:
        response_data = response.json()
    except Exception:
        response_data = response.text
    
    return {
        "ok": response.status_code == 201,
        "status_code": response.status_code,
        "response": response_data,
    }


@app.post("/api/alertas")
async def send_alerta_defesa_civil(body: AlertaDefesaCivilRequest) -> dict[str, Any]:
    """Publica um alerta específico da Defesa Civil no API Bridge."""
    payload = body.model_dump()
    async with httpx.AsyncClient(timeout=SEND_TIMEOUT_SECONDS) as client:
        response = await client.post(f"{API_BRIDGE_URL}/api/v1/alertas", json=payload)
    
    try:
        response_data = response.json()
    except Exception:
        response_data = response.text
    
    return {
        "ok": response.status_code == 201,
        "status_code": response.status_code,
        "response": response_data,
    }
