const API_BASE = "";

const statusEl = document.getElementById("status");
const modeEl = document.getElementById("mode-value");
const cpuEl = document.getElementById("cpu-value");
const cpuRangeEl = document.getElementById("cpu-range-value");
const ramEl = document.getElementById("ram-value");
const diskEl = document.getElementById("disk-value");
const anomalyEl = document.getElementById("anomaly-value");
const reasonEl = document.getElementById("reason-value");
const predictionEl = document.getElementById("prediction-value");
const timestampEl = document.getElementById("timestamp-value");
const jsonOutputEl = document.getElementById("json-output");
const historyEl = document.getElementById("history");
const autoRefreshEl = document.getElementById("auto-refresh");
const healthScoreEl = document.getElementById("health-score");
const healthCaptionEl = document.getElementById("health-caption");
const lastRefreshEl = document.getElementById("last-refresh");
const cpuBarEl = document.getElementById("cpu-bar");
const ramBarEl = document.getElementById("ram-bar");
const diskBarEl = document.getElementById("disk-bar");
const emailEnabledEl = document.getElementById("email-enabled-value");
const emailStatusEl = document.getElementById("email-status-value");

const chartCanvas = document.getElementById("chart");
const chartContext = chartCanvas ? chartCanvas.getContext("2d") : null;
let tick = 0;
let refreshTimer = null;
let currentRefreshInterval = 300000;
const chartState = {
  labels: [],
  cpu: [],
  ram: [],
  disk: []
};
const tabId = sessionStorage.getItem("tabId") || `tab-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const pageRole = new URLSearchParams(window.location.search).get("role");
const criticalChannel = "BroadcastChannel" in window ? new BroadcastChannel("ai-anomaly-critical") : null;
let closeProtectionEnabled = false;
let lastBrowserVoiceAt = 0;

sessionStorage.setItem("tabId", tabId);

let chart = null;

function renderFallbackChart() {
  if (!chartCanvas || !chartContext) {
    return;
  }

  const width = chartCanvas.clientWidth || 900;
  const height = chartCanvas.clientHeight || 460;
  if (chartCanvas.width !== width || chartCanvas.height !== height) {
    chartCanvas.width = width;
    chartCanvas.height = height;
  }

  chartContext.clearRect(0, 0, width, height);

  const padding = { top: 24, right: 24, bottom: 42, left: 48 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const maxValue = 100;

  chartContext.fillStyle = "#fffdf7";
  chartContext.fillRect(0, 0, width, height);

  chartContext.strokeStyle = "rgba(22, 34, 43, 0.08)";
  chartContext.lineWidth = 1;
  for (let index = 0; index <= 5; index += 1) {
    const y = padding.top + (plotHeight / 5) * index;
    chartContext.beginPath();
    chartContext.moveTo(padding.left, y);
    chartContext.lineTo(width - padding.right, y);
    chartContext.stroke();
  }

  chartContext.fillStyle = "#62727f";
  chartContext.font = "12px Trebuchet MS";
  chartContext.textAlign = "right";
  for (let index = 0; index <= 5; index += 1) {
    const value = maxValue - index * 20;
    const y = padding.top + (plotHeight / 5) * index + 4;
    chartContext.fillText(`${value}%`, padding.left - 8, y);
  }

  const drawSeries = (values, color) => {
    if (!values.length) {
      return;
    }

    chartContext.beginPath();
    chartContext.strokeStyle = color;
    chartContext.lineWidth = 3;
    values.forEach((value, index) => {
      const x = padding.left + (plotWidth / Math.max(values.length - 1, 1)) * index;
      const y = padding.top + plotHeight - (value / maxValue) * plotHeight;
      if (index === 0) {
        chartContext.moveTo(x, y);
      } else {
        chartContext.lineTo(x, y);
      }
    });
    chartContext.stroke();

    values.forEach((value, index) => {
      const x = padding.left + (plotWidth / Math.max(values.length - 1, 1)) * index;
      const y = padding.top + plotHeight - (value / maxValue) * plotHeight;
      chartContext.beginPath();
      chartContext.fillStyle = color;
      chartContext.arc(x, y, 3, 0, Math.PI * 2);
      chartContext.fill();
    });
  };

  drawSeries(chartState.cpu, "#ef4444");
  drawSeries(chartState.ram, "#2563eb");
  drawSeries(chartState.disk, "#0d8f72");

  chartContext.textAlign = "center";
  chartContext.fillStyle = "#62727f";
  const labelsToDraw = chartState.labels;
  labelsToDraw.forEach((label, index) => {
    const x = padding.left + (plotWidth / Math.max(labelsToDraw.length - 1, 1)) * index;
    chartContext.fillText(label, x, height - 14);
  });
}

function syncChartRender() {
  if (!chartCanvas || !chartContext) {
    return;
  }

  if (chart) {
    chart.data.labels = [...chartState.labels];
    chart.data.datasets[0].data = [...chartState.cpu];
    chart.data.datasets[1].data = [...chartState.ram];
    chart.data.datasets[2].data = [...chartState.disk];
    chart.update();
    return;
  }

  renderFallbackChart();
}

function setChartStateFromTelemetry(records) {
  if (!Array.isArray(records) || !records.length) {
    return;
  }

  const latestRecords = records.slice(-12);
  chartState.labels = latestRecords.map((record) => formatTime(record.timestamp));
  chartState.cpu = latestRecords.map((record) => record.data.cpu);
  chartState.ram = latestRecords.map((record) => record.data.ram);
  chartState.disk = latestRecords.map((record) => record.data.disk);
  syncChartRender();
}

if (chartContext && window.Chart) {
const cpuGradient = chartContext.createLinearGradient(0, 0, 0, 360);
cpuGradient.addColorStop(0, "rgba(239, 68, 68, 0.36)");
cpuGradient.addColorStop(1, "rgba(239, 68, 68, 0.02)");

const ramGradient = chartContext.createLinearGradient(0, 0, 0, 360);
ramGradient.addColorStop(0, "rgba(37, 99, 235, 0.28)");
ramGradient.addColorStop(1, "rgba(37, 99, 235, 0.02)");

const diskGradient = chartContext.createLinearGradient(0, 0, 0, 360);
diskGradient.addColorStop(0, "rgba(13, 143, 114, 0.28)");
diskGradient.addColorStop(1, "rgba(13, 143, 114, 0.02)");

chart = new Chart(chartContext, {
  type: "line",
  data: {
    labels: [],
    datasets: [
      {
        label: "CPU",
        data: [],
        borderColor: "#ef4444",
        backgroundColor: cpuGradient,
        tension: 0.38,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3
      },
      {
        label: "RAM",
        data: [],
        borderColor: "#2563eb",
        backgroundColor: ramGradient,
        tension: 0.38,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3
      },
      {
        label: "Disk",
        data: [],
        borderColor: "#0d8f72",
        backgroundColor: diskGradient,
        tension: 0.38,
        fill: true,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false
    },
    plugins: {
      legend: {
        labels: {
          usePointStyle: true,
          boxWidth: 10,
          color: "#16222b",
          font: {
            weight: "700"
          }
        }
      },
      tooltip: {
        backgroundColor: "rgba(16, 32, 41, 0.92)",
        titleColor: "#ffffff",
        bodyColor: "#e5eef5",
        padding: 12,
        displayColors: true
      }
    },
    scales: {
      x: {
        grid: {
          display: false
        },
        ticks: {
          color: "#62727f"
        }
      },
      y: {
        beginAtZero: true,
        max: 100,
        grid: {
          color: "rgba(22, 34, 43, 0.08)"
        },
        ticks: {
          color: "#62727f",
          callback: (value) => `${value}%`
        }
      }
    }
  }
});
}

async function requestJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function updateChart(result) {
  if (!chartCanvas || !chartContext) {
    return;
  }

  const pointLabel = formatTime(result.timestamp);
  const lastLabel = chartState.labels[chartState.labels.length - 1];

  if (lastLabel === pointLabel) {
    chartState.cpu[chartState.cpu.length - 1] = result.data.cpu;
    chartState.ram[chartState.ram.length - 1] = result.data.ram;
    chartState.disk[chartState.disk.length - 1] = result.data.disk;
    syncChartRender();
    return;
  }

  chartState.labels.push(formatTime(result.timestamp));
  chartState.cpu.push(result.data.cpu);
  chartState.ram.push(result.data.ram);
  chartState.disk.push(result.data.disk);

  if (chartState.labels.length > 12) {
    chartState.labels.shift();
    chartState.cpu.shift();
    chartState.ram.shift();
    chartState.disk.shift();
  }

  syncChartRender();
}

function updateMeters(result) {
  if (cpuBarEl) cpuBarEl.style.width = `${result.data.cpu}%`;
  if (ramBarEl) ramBarEl.style.width = `${result.data.ram}%`;
  if (diskBarEl) diskBarEl.style.width = `${result.data.disk}%`;
}

function updateHealth(result) {
  if (!healthScoreEl || !healthCaptionEl) {
    return;
  }

  healthScoreEl.textContent = `${result.health_score}/100`;

  if (result.health_score >= 70) {
    healthCaptionEl.textContent = "Healthy operating window";
  } else if (result.health_score >= 45) {
    healthCaptionEl.textContent = "Moderate resource pressure";
  } else {
    healthCaptionEl.textContent = "High instability risk detected";
  }
}

function enableCloseProtection() {
  closeProtectionEnabled = true;
}

function disableCloseProtection() {
  closeProtectionEnabled = false;
}

function attemptCloseCurrentTab() {
  window.close();
}

function speakBrowserAlert(message) {
  if (!("speechSynthesis" in window)) {
    return;
  }

  const now = Date.now();
  if (now - lastBrowserVoiceAt < 3000) {
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(message);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.volume = 1;
  lastBrowserVoiceAt = now;
  window.speechSynthesis.speak(utterance);
}

function playBrowserBeep(times = 2) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    return;
  }

  const audioContext = new AudioContextClass();

  for (let index = 0; index < times; index += 1) {
    const startAt = audioContext.currentTime + index * 0.35;
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(920, startAt);
    gainNode.gain.setValueAtTime(0.0001, startAt);
    gainNode.gain.exponentialRampToValueAtTime(0.22, startAt + 0.02);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.22);

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    oscillator.start(startAt);
    oscillator.stop(startAt + 0.24);
  }

  setTimeout(() => {
    audioContext.close().catch(() => {});
  }, times * 400);
}

function showHighLoadPopup(result) {
  alert(
    [
      "High Load Warning",
      "",
      `CPU: ${result.data.cpu}%`,
      `RAM: ${result.data.ram}%`,
      `Disk: ${result.data.disk}%`
    ].join("\n")
  );
}

function handleCriticalEvent(result) {
  enableCloseProtection();

  if (pageRole !== "important") {
    window.open("/page/prediction?role=important", "_blank", "noopener");
  }

  if (criticalChannel) {
    criticalChannel.postMessage({
      type: "critical-overload",
      sourceTabId: tabId
    });
  }

  alert(
    "Critical overload detected. Keep this tab open and review the important prediction tab that was opened."
  );
}

function updateDashboard(result) {
  if (cpuEl) cpuEl.textContent = `${result.data.cpu}%`;
  if (cpuRangeEl && result.cpu_expected_range) cpuRangeEl.textContent = result.cpu_expected_range.label;
  if (ramEl) ramEl.textContent = `${result.data.ram}%`;
  if (diskEl) diskEl.textContent = `${result.data.disk}%`;
  if (anomalyEl) {
    anomalyEl.textContent = result.anomaly ? "Detected" : "Normal";
    anomalyEl.className = `pill ${result.anomaly ? "anomaly-yes" : "anomaly-no"}`;
  }
  if (reasonEl) reasonEl.textContent = result.reason;
  if (predictionEl) predictionEl.textContent = result.prediction;
  if (timestampEl) timestampEl.textContent = new Date(result.timestamp).toLocaleString();
  if (modeEl) modeEl.textContent = result.mode;
  if (lastRefreshEl) lastRefreshEl.textContent = formatTime(result.timestamp);
  if (emailEnabledEl) {
    emailEnabledEl.textContent = result.email_alerts_enabled ? "Enabled" : "Not Configured";
    emailEnabledEl.className = `pill ${result.email_alerts_enabled ? "anomaly-no" : "anomaly-yes"}`;
  }
  if (emailStatusEl) emailStatusEl.textContent = result.email_alert_status || "No alert sent";

  if (statusEl) {
    statusEl.textContent = result.anomaly ? "Anomaly detected" : "System operating normally";
    statusEl.className = result.anomaly ? "status-alert" : "status-ok";
  }

  if (jsonOutputEl) jsonOutputEl.textContent = JSON.stringify(result, null, 2);
  updateMeters(result);
  updateHealth(result);
  updateChart(result);

  if (result.critical) {
    handleCriticalEvent(result);
  } else {
    disableCloseProtection();
  }
}

function applyImmediateModeState(mode) {
  if (modeEl) {
    modeEl.textContent = mode;
  }

  if (cpuRangeEl) {
    cpuRangeEl.textContent = mode === "high" ? "70% - 100%" : "0% - 60%";
  }

  if (statusEl) {
    statusEl.textContent = mode === "high" ? "High load mode activated" : "System operating normally";
    statusEl.className = mode === "high" ? "status-alert" : "status-ok";
  }

  if (reasonEl) {
    reasonEl.textContent =
      mode === "high"
        ? "High load mode is active. Monitoring is now using the high processing CPU range."
        : "System activity is within the normal operating range";
  }

  if (predictionEl) {
    predictionEl.textContent =
      mode === "high" ? "Monitoring high-load thresholds with real system data" : "Low risk: System is stable";
  }
}

function updateHistory(records) {
  if (!historyEl) {
    return;
  }

  if (!records.length) {
    historyEl.innerHTML = '<li class="muted">No anomalies recorded yet.</li>';
    return;
  }

  historyEl.innerHTML = records
    .map(
      (record) => `
        <li>
          <strong>${record.prediction}</strong><br>
          CPU: ${record.data.cpu}% | RAM: ${record.data.ram}% | Disk: ${record.data.disk}%<br>
          Reason: ${record.reason}<br>
          Time: ${record.timestamp ? new Date(record.timestamp).toLocaleString() : "Recent"}
        </li>
      `
    )
    .join("");
}

async function refreshDashboard() {
  try {
    if (chartCanvas && chartState.labels.length === 0) {
      const telemetryHistory = await requestJson("/telemetry-history");
      setChartStateFromTelemetry(telemetryHistory);
    }

    const result = await requestJson("/monitor");
    currentRefreshInterval = (result.refresh_interval_seconds || 300) * 1000;
    syncAutoRefresh();
    updateDashboard(result);

    const history = await requestJson("/history");
    updateHistory(history);
    return result;
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = "Backend connection failed";
      statusEl.className = "status-alert";
    }
    if (reasonEl) reasonEl.textContent = error.message;
    if (predictionEl) predictionEl.textContent = "Start the server and try again.";
    if (jsonOutputEl) jsonOutputEl.textContent = error.message;
    return null;
  }
}

async function setMode(mode) {
  try {
    applyImmediateModeState(mode);
    await requestJson(`/set-mode/${mode}`);
    await refreshDashboard();
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = "Could not switch mode";
      statusEl.className = "status-alert";
    }
  }
}

function syncAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }

  if (autoRefreshEl && autoRefreshEl.checked) {
    refreshTimer = setInterval(refreshDashboard, currentRefreshInterval);
  }
}

window.addEventListener("beforeunload", (event) => {
  if (!closeProtectionEnabled) {
    return;
  }

  event.preventDefault();
  event.returnValue = "";
});

if (criticalChannel) {
  criticalChannel.onmessage = (event) => {
    if (event.data?.type !== "critical-overload") {
      return;
    }

    if (event.data.sourceTabId === tabId || pageRole === "important") {
      enableCloseProtection();
      return;
    }

    enableCloseProtection();
    const shouldClose = window.confirm(
      "Critical overload detected. This tab is not essential right now. Close this tab?"
    );

    if (shouldClose) {
      attemptCloseCurrentTab();
    }
  };
}

const normalBtn = document.getElementById("normal-btn");
const highBtn = document.getElementById("high-btn");
const refreshBtn = document.getElementById("refresh-btn");

if (normalBtn) normalBtn.addEventListener("click", () => setMode("normal"));
if (highBtn) highBtn.addEventListener("click", () => setMode("high"));
if (refreshBtn) refreshBtn.addEventListener("click", refreshDashboard);
if (autoRefreshEl) autoRefreshEl.addEventListener("change", syncAutoRefresh);

syncAutoRefresh();
if (
  statusEl ||
  cpuEl ||
  anomalyEl ||
  reasonEl ||
  predictionEl ||
  historyEl ||
  chart
) {
  refreshDashboard();
}

if (chartCanvas && !window.Chart) {
  window.addEventListener("resize", renderFallbackChart);
  renderFallbackChart();
}
