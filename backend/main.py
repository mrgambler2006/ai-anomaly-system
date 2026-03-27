from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_generator import generate_data
from .database import get_history, save_anomaly
from .model import detect_anomaly

app = FastAPI()

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

mode = "normal"


def get_reason(data):
    if data["cpu"] > 85 and data["ram"] > 80:
        return "Heavy application causing high CPU and RAM usage"
    if data["cpu"] > 85:
        return "Too many processes running"
    if data["ram"] > 80:
        return "Memory overload"
    return "Normal"


def predict_failure(data):
    if data["cpu"] > 90:
        return "High risk: System may crash soon"
    if data["cpu"] > 80:
        return "Medium risk: System slowing down"
    return "Low risk"


@app.get("/")
def home():
    return FileResponse(frontend_dir / "index.html")


@app.get("/set-mode/{new_mode}")
def set_mode(new_mode: str):
    global mode
    if new_mode not in {"normal", "high"}:
        return {"error": "Mode must be normal or high"}

    mode = new_mode
    return {"mode": mode}


@app.get("/monitor")
def monitor():
    data = generate_data(mode)
    anomaly = detect_anomaly(data)
    health_score = max(0, 100 - round((data["cpu"] + data["ram"] + data["disk"]) / 3))

    result = {
        "data": data,
        "anomaly": anomaly,
        "reason": get_reason(data),
        "prediction": predict_failure(data),
        "mode": mode,
        "health_score": health_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if anomaly:
        save_anomaly(result)

    return result


@app.get("/history")
def history():
    return get_history()
