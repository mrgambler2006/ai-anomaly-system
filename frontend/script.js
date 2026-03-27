const API_BASE = "";

const statusEl = document.getElementById("status");
const modeEl = document.getElementById("mode-value");
const cpuEl = document.getElementById("cpu-value");
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

const chartCanvas = document.getElementById("chart");
const chartContext = chartCanvas ? chartCanvas.getContext("2d") : null;
let tick = 0;
let refreshTimer = null;

let chart = null;

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
  if (!chart) {
    return;
  }

  tick += 1;
  chart.data.labels.push(formatTime(result.timestamp));
  chart.data.datasets[0].data.push(result.data.cpu);
  chart.data.datasets[1].data.push(result.data.ram);
  chart.data.datasets[2].data.push(result.data.disk);

  if (chart.data.labels.length > 12) {
    chart.data.labels.shift();
    chart.data.datasets.forEach((dataset) => dataset.data.shift());
  }

  chart.update();
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

function updateDashboard(result) {
  if (cpuEl) cpuEl.textContent = `${result.data.cpu}%`;
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

  if (statusEl) {
    statusEl.textContent = result.anomaly ? "Anomaly detected" : "System operating normally";
    statusEl.className = result.anomaly ? "status-alert" : "status-ok";
  }

  if (jsonOutputEl) jsonOutputEl.textContent = JSON.stringify(result, null, 2);
  updateMeters(result);
  updateHealth(result);
  updateChart(result);
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
    const result = await requestJson("/monitor");
    updateDashboard(result);

    const history = await requestJson("/history");
    updateHistory(history);
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = "Backend connection failed";
      statusEl.className = "status-alert";
    }
    if (reasonEl) reasonEl.textContent = error.message;
    if (predictionEl) predictionEl.textContent = "Start the server and try again.";
    if (jsonOutputEl) jsonOutputEl.textContent = error.message;
  }
}

async function setMode(mode) {
  try {
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
    refreshTimer = setInterval(refreshDashboard, 2000);
  }
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
