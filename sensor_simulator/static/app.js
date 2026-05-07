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
          const payload = {
            sensor_id: sensor.sensor_id,
            fields: { [field]: Number(input.value) },
          };
          await api("/api/sensors/update", {
            method: "POST",
            body: JSON.stringify(payload),
          });
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
