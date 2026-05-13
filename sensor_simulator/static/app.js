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
    let detail = data?.detail;
    if (Array.isArray(detail)) {
      detail = detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const loc = Array.isArray(item.loc) ? item.loc.join(".") : "campo";
            const msg = item.msg || JSON.stringify(item);
            return `${loc}: ${msg}`;
          }
          return String(item);
        })
        .join(" | ");
    } else if (detail && typeof detail === "object") {
      detail = JSON.stringify(detail);
    }
    throw new Error(detail || "Falha na requisicao");
  }
  return data;
}

function updateResult(data) {
  resultBox.textContent = fmtJson(data);
}

// --- Tab Navigation ---
function setupTabs() {
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const tabName = button.getAttribute("data-tab");

      // Deactivate all
      tabButtons.forEach((btn) => btn.classList.remove("active"));
      tabContents.forEach((content) => content.classList.remove("active"));

      // Activate selected
      button.classList.add("active");
      document.getElementById(`tab-${tabName}`)?.classList.add("active");
    });
  });
}

function updateResultBox(tabId, data) {
  const resultBox = document.getElementById(tabId);
  if (resultBox) {
    resultBox.textContent = fmtJson(data);
  }
}

// --- Dynamic Alerta Items ---
function addAlertaItem(container, values = {}) {
  const alertaNum = container.children.length + 1;
  const item = document.createElement("div");
  item.className = "alerta-item";
  item.innerHTML = `
    <h4 style="margin: 0 0 12px; font-size: 14px;">Alerta #${alertaNum}</h4>
    <div class="form-group">
      <label>Região:</label>
      <input type="text" class="alerta-regiao" value="${values.regiao || ""}" placeholder="Ex: Zona Norte" />
    </div>
    <div class="form-group">
      <label>Descrição:</label>
      <input type="text" class="alerta-descricao" value="${values.descricao || ""}" placeholder="Ex: Risco de alagamento" />
    </div>
    <div class="form-group">
      <label>Severidade:</label>
      <select class="alerta-severidade">
        <option value="normal" ${values.severidade === "normal" ? "selected" : ""}>Normal</option>
        <option value="atencao" ${values.severidade === "atencao" ? "selected" : ""}>Atenção</option>
        <option value="critico" ${values.severidade === "critico" ? "selected" : ""}>Crítico</option>
      </select>
    </div>
    <button type="button" class="btn btn-remove">Remover Alerta</button>
  `;

  const removeBtn = item.querySelector(".btn-remove");
  removeBtn.addEventListener("click", () => item.remove());

  container.appendChild(item);
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
    estado_bomba: "Estado da Bomba",
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
    sub.textContent = `${sensor.sensor_id} • ${sensor.kind === "water" ? "Nivel" : sensor.kind === "bomba" ? "Bomba de Drenagem" : "Meteorologica"}`;

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
      { value: "bateria", label: sensor.kind === "bomba" ? "Gerador de Emergencia" : "Bateria emergencia" },
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
    batteryLabel.textContent = sensor.kind === "bomba" ? "Gerador de Emergencia" : "Bateria";
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
    bmsLabel.textContent = sensor.kind === "bomba" ? "Rotacao" : "BMS";
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

      let control;
      if (field === "estado_bomba") {
        control = document.createElement("select");
        [
          { value: "1", label: "Ligada" },
          { value: "0", label: "Desligada" },
        ].forEach((opt) => {
          const option = document.createElement("option");
          option.value = opt.value;
          option.textContent = opt.label;
          control.appendChild(option);
        });
        control.value = String(value);
        control.addEventListener("change", async () => {
          try {
            await updateSensorFields(sensor.sensor_id, { [field]: Number(control.value) });
            await refreshSensors();
          } catch (error) {
            updateResult({ ok: false, error: error.message });
            await refreshSensors();
          }
        });
      } else {
        control = document.createElement("input");
        control.type = "number";
        control.value = value;
        control.min = range.min;
        control.max = range.max;
        control.step = range.step;
        control.addEventListener("change", async () => {
          try {
            await updateSensorFields(sensor.sensor_id, { [field]: Number(control.value) });
            await refreshSensors();
          } catch (error) {
            updateResult({ ok: false, error: error.message });
            await refreshSensors();
          }
        });
      }

      const unitTag = document.createElement("small");
      unitTag.textContent = unit;

      row.appendChild(label);
      row.appendChild(control);
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

// --- Form Handlers for Simulations ---

// Previsão de Chuva
document.getElementById("form-previsao")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const payload = {
    regiao: formData.get("regiao") || "Jardim Romano",
    nivel: parseInt(formData.get("nivel")),
    descricao: formData.get("descricao"),
    precipitacao_mm: parseFloat(formData.get("precipitacao_mm")),
  };

  try {
    const data = await api("/api/previsoes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    updateResultBox("previsao-result", data);
  } catch (error) {
    updateResultBox("previsao-result", { ok: false, error: error.message });
  }
});

// Situação Defesa Civil
document.getElementById("btn-add-alerta")?.addEventListener("click", (e) => {
  e.preventDefault();
  const container = document.getElementById("alertas-list");
  const maxAlertas = 5;
  if (container.children.length < maxAlertas) {
    addAlertaItem(container);
  } else {
    alert("Máximo de 5 alertas atingido");
  }
});

document.getElementById("form-defesa-civil")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);

  const alertasContainer = document.getElementById("alertas-list");
  const alertasItems = alertasContainer.querySelectorAll(".alerta-item");
  const alertas_ativos = Array.from(alertasItems).map((item) => ({
    regiao: item.querySelector(".alerta-regiao").value,
    descricao: item.querySelector(".alerta-descricao").value,
    severidade: item.querySelector(".alerta-severidade").value,
  }));

  const payload = {
    status: formData.get("status"),
    alertas_ativos,
  };

  try {
    const data = await api("/api/defesa-civil", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    updateResultBox("defesa-civil-result", data);
  } catch (error) {
    updateResultBox("defesa-civil-result", { ok: false, error: error.message });
  }
});

// Alertas Defesa Civil
document.getElementById("form-alertas")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(e.target);
  const payload = {
    titulo: formData.get("titulo"),
    descricao: formData.get("descricao"),
    regiao: formData.get("regiao"),
    valido_ate: formData.get("valido_ate"),
  };

  try {
    const data = await api("/api/alertas", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    updateResultBox("alertas-result", data);
  } catch (error) {
    updateResultBox("alertas-result", { ok: false, error: error.message });
  }
});

(async function init() {
  try {
    setupTabs();
    
    // Initialize Defesa Civil alertas list with one empty item
    const alertasContainer = document.getElementById("alertas-list");
    if (alertasContainer) {
      addAlertaItem(alertasContainer);
    }

    await refreshSensors();
    await refreshAutoStatus();
    setInterval(refreshAutoStatus, 5000);
  } catch (error) {
    updateResult({ ok: false, error: error.message });
  }
})();
