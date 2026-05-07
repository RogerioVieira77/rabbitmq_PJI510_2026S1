let sensors = [];

const grid = document.getElementById("sensor-grid");
const resultBox = document.getElementById("send-result");
const autoStatus = document.getElementById("auto-status");

function fmtJson(data) {
  return JSON.stringify(data, null, 2);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Falha na requisicao");
  }
  return data;
}

function updateResult(data) {
  resultBox.textContent = fmtJson(data);
}

async function updateSensorFields(sensorId, fields) {
  return api("/api/sensors/update", {
    method: "POST",
    body: JSON.stringify({ sensor_id: sensorId, fields }),
  });
}

function toLabel(fieldName) {
  const map = {
    nivel_agua: "Nivel de agua",
    vento_direcao: "Direcao do vento",
    vento_velocidade: "Velocidade do vento",
    pluviometro: "Pluviometro",
    temperatura: "Temperatura",
    umidade: "Umidade",
    pressao: "Pressao atmosferica",
  };
  return map[fieldName] || fieldName;
}

async function refreshSensors() {
  const data = await api("/api/sensors");
  sensors = data.sensors;
  renderSensors();
}

async function refreshAutoStatus() {
  const data = await api("/api/auto");
  if (data.enabled) {
    autoStatus.textContent = `ativo (${data.interval_seconds}s)`;
    autoStatus.classList.add("active");
  } else {
    autoStatus.textContent = "desativado";
    autoStatus.classList.remove("active");
  }
}

function renderSensors() {
  grid.innerHTML = "";

  sensors.forEach((sensor) => {
    const card = document.createElement("article");
    card.className = "card";

    const title = document.createElement("h3");
    title.textContent = sensor.label;

    const sub = document.createElement("small");
    sub.textContent = `${sensor.sensor_id} • ${sensor.kind === "water" ? "Nivel" : "Meteorologica"}`;

    const statusBadge = document.createElement("span");
    statusBadge.className = `sensor-state ${sensor.ativo ? "on" : "off"}`;
    statusBadge.textContent = sensor.ativo ? "Ligado" : "Desligado";

    if (!sensor.ativo) {
      card.classList.add("card-off");
    }

    const opsWrap = document.createElement("div");
    opsWrap.className = "ops";

    const activeRow = document.createElement("div");
    activeRow.className = "field";
    const activeLabel = document.createElement("label");
    activeLabel.textContent = "Estado";
    const activeSelect = document.createElement("select");
    [
      { value: "ligado", label: "Ligado" },
      { value: "desligado", label: "Desligado" },
    ].forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      activeSelect.appendChild(option);
    });
    activeSelect.value = sensor.ativo ? "ligado" : "desligado";
    activeSelect.addEventListener("change", async () => {
      try {
        await updateSensorFields(sensor.sensor_id, { ativo: activeSelect.value === "ligado" });
        await refreshSensors();
      } catch (error) {
        updateResult({ ok: false, error: error.message });
        await refreshSensors();
      }
    });
    const activeInfo = document.createElement("small");
    activeInfo.textContent = "envio";
    activeRow.appendChild(activeLabel);
    activeRow.appendChild(activeSelect);
    activeRow.appendChild(activeInfo);
    opsWrap.appendChild(activeRow);

    const sourceRow = document.createElement("div");
    sourceRow.className = "field";
    const sourceLabel = document.createElement("label");
    sourceLabel.textContent = "Alimentacao";
    const sourceSelect = document.createElement("select");
    [
      { value: "rede", label: "Rede eletrica" },
      { value: "bateria", label: "Bateria emergencia" },
    ].forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      sourceSelect.appendChild(option);
    });
    sourceSelect.value = sensor.fonte_alimentacao;
    sourceSelect.addEventListener("change", async () => {
      try {
        await updateSensorFields(sensor.sensor_id, { fonte_alimentacao: sourceSelect.value });
        await refreshSensors();
      } catch (error) {
        updateResult({ ok: false, error: error.message });
        await refreshSensors();
      }
    });
    const sourceInfo = document.createElement("small");
    sourceInfo.textContent = sensor.fonte_alimentacao;
    sourceRow.appendChild(sourceLabel);
    sourceRow.appendChild(sourceSelect);
    sourceRow.appendChild(sourceInfo);
    opsWrap.appendChild(sourceRow);

    const batteryRow = document.createElement("div");
    batteryRow.className = "field";
    const batteryLabel = document.createElement("label");
    batteryLabel.textContent = "Bateria";
    const batteryInput = document.createElement("input");
    batteryInput.type = "number";
    batteryInput.min = 0;
    batteryInput.max = 100;
    batteryInput.step = 1;
    batteryInput.value = sensor.bateria_pct;
    batteryInput.addEventListener("change", async () => {
      try {
        await updateSensorFields(sensor.sensor_id, { bateria_pct: Number(batteryInput.value) });
        await refreshSensors();
      } catch (error) {
        updateResult({ ok: false, error: error.message });
        await refreshSensors();
      }
    });
    const batteryInfo = document.createElement("small");
    batteryInfo.textContent = "%";
    batteryRow.appendChild(batteryLabel);
    batteryRow.appendChild(batteryInput);
    batteryRow.appendChild(batteryInfo);
    opsWrap.appendChild(batteryRow);

    const bmsRow = document.createElement("div");
    bmsRow.className = "field";
    const bmsLabel = document.createElement("label");
    bmsLabel.textContent = "BMS";
    const bmsSelect = document.createElement("select");
    ["normal", "alerta", "critico"].forEach((level) => {
      const option = document.createElement("option");
      option.value = level;
      option.textContent = level;
      bmsSelect.appendChild(option);
    });
    bmsSelect.value = sensor.bms_nivel;
    bmsSelect.addEventListener("change", async () => {
      try {
        await updateSensorFields(sensor.sensor_id, { bms_nivel: bmsSelect.value });
        await refreshSensors();
      } catch (error) {
        updateResult({ ok: false, error: error.message });
        await refreshSensors();
      }
    });
    const bmsInfo = document.createElement("small");
    bmsInfo.textContent = "nivel";
    bmsRow.appendChild(bmsLabel);
    bmsRow.appendChild(bmsSelect);
    bmsRow.appendChild(bmsInfo);
    opsWrap.appendChild(bmsRow);

    const fieldsWrap = document.createElement("div");
    fieldsWrap.className = "fields";

    Object.entries(sensor.values).forEach(([field, value]) => {
      const range = sensor.ranges[field];
      const unit = sensor.units[field];

      const row = document.createElement("div");
      row.className = "field";

      const label = document.createElement("label");
      label.textContent = toLabel(field);

      const input = document.createElement("input");
      input.type = "number";
      input.value = value;
      input.min = range.min;
      input.max = range.max;
      input.step = range.step;

      input.addEventListener("change", async () => {
        try {
          await updateSensorFields(sensor.sensor_id, { [field]: Number(input.value) });
          await refreshSensors();
        } catch (error) {
          updateResult({ ok: false, error: error.message });
          await refreshSensors();
        }
      });

      const unitTag = document.createElement("small");
      unitTag.textContent = unit;

      row.appendChild(label);
      row.appendChild(input);
      row.appendChild(unitTag);
      fieldsWrap.appendChild(row);
    });

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const btnRandom = document.createElement("button");
    btnRandom.className = "btn";
    btnRandom.textContent = "Randomizar";
    btnRandom.addEventListener("click", async () => {
      try {
        await api("/api/sensors/randomize", {
          method: "POST",
          body: JSON.stringify({ sensor_id: sensor.sensor_id }),
        });
        await refreshSensors();
      } catch (error) {
        updateResult({ ok: false, error: error.message });
      }
    });

    const btnSend = document.createElement("button");
    btnSend.className = "btn btn-primary";
    btnSend.textContent = "Enviar";
    btnSend.disabled = !sensor.ativo;
    btnSend.addEventListener("click", async () => {
      try {
        const data = await api("/api/sensors/send", {
          method: "POST",
          body: JSON.stringify({ sensor_id: sensor.sensor_id }),
        });
        updateResult(data);
      } catch (error) {
        updateResult({ ok: false, error: error.message });
      }
    });

    actions.appendChild(btnRandom);
    actions.appendChild(btnSend);

    card.appendChild(title);
    card.appendChild(sub);
    card.appendChild(statusBadge);
    card.appendChild(opsWrap);
    card.appendChild(fieldsWrap);
    card.appendChild(actions);
    grid.appendChild(card);
  });
}

document.getElementById("btn-random-all").addEventListener("click", async () => {
  try {
    await api("/api/sensors/randomize", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await refreshSensors();
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
});

document.getElementById("btn-send-all").addEventListener("click", async () => {
  try {
    const data = await api("/api/sensors/send", {
      method: "POST",
      body: JSON.stringify({}),
    });
    updateResult(data);
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
});

document.getElementById("btn-auto-start").addEventListener("click", async () => {
  const intervalInput = document.getElementById("interval-seconds");
  const interval = Number(intervalInput.value || 10);
  try {
    const data = await api("/api/auto/start", {
      method: "POST",
      body: JSON.stringify({ interval_seconds: interval }),
    });
    updateResult(data);
    await refreshAutoStatus();
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
});

document.getElementById("btn-auto-stop").addEventListener("click", async () => {
  try {
    const data = await api("/api/auto/stop", { method: "POST", body: JSON.stringify({}) });
    updateResult(data);
    await refreshAutoStatus();
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
});

(async function init() {
  try {
    await refreshSensors();
    await refreshAutoStatus();
    setInterval(refreshAutoStatus, 5000);
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
})();
