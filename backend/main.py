from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .alerts import email_alerts_enabled, send_email_alert
from .database import (
    get_database_status,
    get_history,
    get_latest_snapshot,
    get_recent_snapshots,
    latest_snapshot_is_fresh,
    save_anomaly,
    save_snapshot,
)
from .model import analyze_system

app = FastAPI()

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

mode = "normal"


class TelemetryPayload(BaseModel):
    cpu: float = Field(ge=0, le=100)
    ram: float = Field(ge=0, le=100)
    disk: float = Field(ge=0, le=100)
    hostname: str = "local-system"
    source: str = "agent"


def resolve_system_status(cpu_value, agent_connected=True):
    if not agent_connected:
        return "Agent offline"
    if cpu_value >= 50:
        return "Anomaly detected"
    return "System operating normally"


def resolve_current_mode(cpu_value):
    if cpu_value >= 50:
        return "high"
    return "low"


def current_cpu_range():
    if mode == "high":
        return {
            "label": "50% - 100%",
            "min": 50,
            "max": 100,
            "category": "high-load",
        }

    return {
        "label": "0% - 50%",
        "min": 0,
        "max": 50,
        "category": "normal",
    }


def build_result(data, source="background-agent", hostname="local-system"):
    recent_history = get_recent_snapshots()
    analysis = analyze_system(data, recent_history, mode=mode)
    current_mode = resolve_current_mode(data["cpu"])

    health_score = max(0, 100 - round((data["cpu"] + data["ram"] + data["disk"]) / 3))
    risk_percent = max(0, min(100, round(analysis["score"] * 20)))

    result = {
        "data": data,
        "anomaly": analysis["anomaly"],
        "critical": analysis["critical"],
        "overloaded": analysis["overloaded"],
        "overload_metrics": analysis["overload_metrics"],
        "reason": analysis["reason"],
        "prediction": analysis["prediction"],
        "anomaly_score": analysis["score"],
        "risk_percent": risk_percent,
        "mode": current_mode,
        "cpu_expected_range": {
            "label": "50% - 100%" if current_mode == "high" else "0% - 50%",
            "min": 50 if current_mode == "high" else 0,
            "max": 100 if current_mode == "high" else 50,
            "category": "high-load" if current_mode == "high" else "low-load",
        },
        "health_score": health_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "refresh_interval_seconds": 10,
        "email_alerts_enabled": email_alerts_enabled(),
        "source": source,
        "hostname": hostname,
        "agent_connected": True,
        "system_status": resolve_system_status(data["cpu"], agent_connected=True),
    }

    save_snapshot(result)
    if result["anomaly"]:
        save_anomaly(result)
        alert_result = send_email_alert(result)
        result["email_alert_status"] = alert_result["reason"]
    else:
        result["email_alert_status"] = "No alert sent"

    return result


@app.get("/")
def home():
    return FileResponse(frontend_dir / "index.html")


@app.get("/page/{page_name}")
def page(page_name: str):
    allowed_pages = {
        "monitoring",
        "anomaly",
        "explanation",
        "prediction",
        "visualization",
    }
    if page_name not in allowed_pages:
        return FileResponse(frontend_dir / "index.html")

    return FileResponse(frontend_dir / f"{page_name}.html")


@app.get("/set-mode/{new_mode}")
def set_mode(new_mode: str):
    global mode
    if new_mode not in {"normal", "high"}:
        return {"error": "Mode must be normal or high"}

    mode = new_mode
    return {"mode": mode, "cpu_expected_range": current_cpu_range()}


@app.get("/monitor")
def monitor():
    if latest_snapshot_is_fresh():
        latest = get_latest_snapshot()
        if latest:
            return latest

    latest = get_latest_snapshot()
    if latest:
        latest_copy = dict(latest)
        latest_copy["source"] = "background-agent"
        latest_copy["agent_connected"] = False
        latest_copy["system_status"] = resolve_system_status(
            latest_copy.get("data", {}).get("cpu", 0),
            agent_connected=False,
        )
        latest_copy["reason"] = "Background agent is currently offline. Showing last known system snapshot."
        latest_copy["prediction"] = "Agent offline: showing last known status"
        return latest_copy

    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "data": {"cpu": 0, "ram": 0, "disk": 0},
        "anomaly": False,
        "critical": False,
        "overloaded": False,
        "overload_metrics": 0,
        "reason": "Background agent is not connected yet. Start the monitor agent to collect real system data.",
        "prediction": "Waiting for background agent",
        "anomaly_score": 0.0,
        "risk_percent": 0,
        "mode": mode,
        "cpu_expected_range": current_cpu_range(),
        "health_score": 0,
        "timestamp": timestamp,
        "refresh_interval_seconds": 10,
        "email_alerts_enabled": email_alerts_enabled(),
        "email_alert_status": "No alert sent",
        "source": "agent-unavailable",
        "hostname": "unknown",
        "agent_connected": False,
        "system_status": "Waiting for live data",
    }


@app.post("/agent/telemetry")
def receive_agent_telemetry(payload: TelemetryPayload):
    data = {
        "cpu": round(payload.cpu, 2),
        "ram": round(payload.ram, 2),
        "disk": round(payload.disk, 2),
    }
    result = build_result(data, source="background-agent", hostname=payload.hostname)
    return result


@app.get("/agent/status")
def agent_status():
    latest = get_latest_snapshot()
    if not latest:
        return {"connected": False, "message": "No agent data received yet"}

    return {
        "connected": latest_snapshot_is_fresh(),
        "latest": latest,
    }


@app.get("/history")
def history():
    return get_history()


@app.get("/telemetry-history")
def telemetry_history():
    return get_recent_snapshots(limit=12)


@app.get("/database-status")
def database_status():
    return get_database_status()
