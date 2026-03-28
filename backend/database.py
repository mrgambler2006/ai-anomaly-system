from collections import deque
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
except ModuleNotFoundError:
    ASCENDING = DESCENDING = MongoClient = None


_anomaly_history = deque(maxlen=50)
_telemetry_history = deque(maxlen=240)
_latest_snapshot = None
_RETENTION_HOURS = 24


def _load_env_file():
    locked_keys = set(os.environ)
    candidate_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]

    for env_path in candidate_paths:
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in locked_keys:
                os.environ[key] = value
                locked_keys.add(key)


def _normalized_now():
    return datetime.now(timezone.utc)


def _cutoff_time():
    return _normalized_now() - timedelta(hours=_RETENTION_HOURS)


def _parse_timestamp(timestamp):
    if not timestamp:
        return _normalized_now()

    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return _normalized_now()

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _snapshot_document(data):
    document = _storage_document(data)
    document["document_type"] = "telemetry_snapshot"
    return document


def _anomaly_document(data):
    document = _storage_document(data)
    document["document_type"] = "anomaly_event"
    return document


def _storage_document(data):
    document = dict(data)
    recorded_at = _parse_timestamp(data.get("timestamp"))
    metrics = data.get("data", {})
    cpu = round(metrics.get("cpu", 0), 2)
    ram = round(metrics.get("ram", 0), 2)
    disk = round(metrics.get("disk", 0), 2)

    document["recorded_at"] = recorded_at
    document["cpu"] = cpu
    document["ram"] = ram
    document["disk"] = disk
    document["display_metrics"] = f"CPU: {cpu}% | RAM: {ram}% | Disk: {disk}%"
    document["display_time"] = recorded_at.astimezone().strftime("%m/%d/%Y, %I:%M:%S %p")
    document["display_summary"] = (
        f"{data.get('prediction', 'Unknown status')}\n"
        f"CPU: {cpu}% | RAM: {ram}% | Disk: {disk}%\n"
        f"Reason: {data.get('reason', 'No reason available')}\n"
        f"Time: {document['display_time']}"
    )
    return document


def _public_document(document):
    if not document:
        return None

    clean_document = dict(document)
    clean_document.pop("_id", None)
    clean_document.pop("document_type", None)
    clean_document.pop("recorded_at", None)
    return clean_document


def _build_mongo_state():
    if MongoClient is None:
        return {
            "client": None,
            "anomaly_collection": None,
            "current_snapshot_collection": None,
            "snapshot_collection": None,
            "enabled": False,
            "error": "pymongo is not installed",
        }

    mongodb_uri = os.getenv("MONGODB_URI", "").strip()
    mongodb_db_name = os.getenv("MONGODB_DB_NAME", "server_monitor")
    anomaly_collection_name = os.getenv("MONGODB_COLLECTION_NAME", "anomalies")
    snapshot_collection_name = os.getenv("MONGODB_SNAPSHOT_COLLECTION_NAME", "snapshots")
    current_snapshot_collection_name = os.getenv("MONGODB_CURRENT_COLLECTION_NAME", "current_status")

    if not mongodb_uri:
        return {
            "client": None,
            "anomaly_collection": None,
            "current_snapshot_collection": None,
            "snapshot_collection": None,
            "enabled": False,
            "error": "MONGODB_URI is not configured",
        }

    if " " in mongodb_uri:
        return {
            "client": None,
            "anomaly_collection": None,
            "current_snapshot_collection": None,
            "snapshot_collection": None,
            "enabled": False,
            "error": "MONGODB_URI contains spaces. Remove spaces from the connection string.",
        }

    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[mongodb_db_name]
        anomaly_collection = db[anomaly_collection_name]
        snapshot_collection = db[snapshot_collection_name]
        current_snapshot_collection = db[current_snapshot_collection_name]

        if ASCENDING is not None:
            anomaly_collection.create_index([("recorded_at", ASCENDING)], expireAfterSeconds=_RETENTION_HOURS * 3600)
            snapshot_collection.create_index([("recorded_at", ASCENDING)], expireAfterSeconds=_RETENTION_HOURS * 3600)
            anomaly_collection.create_index([("document_type", ASCENDING), ("recorded_at", DESCENDING)])
            snapshot_collection.create_index([("document_type", ASCENDING), ("recorded_at", DESCENDING)])
            current_snapshot_collection.create_index([("document_type", ASCENDING), ("recorded_at", DESCENDING)])

        return {
            "client": client,
            "anomaly_collection": anomaly_collection,
            "current_snapshot_collection": current_snapshot_collection,
            "snapshot_collection": snapshot_collection,
            "enabled": True,
            "error": None,
        }
    except Exception as exc:
        return {
            "client": None,
            "anomaly_collection": None,
            "current_snapshot_collection": None,
            "snapshot_collection": None,
            "enabled": False,
            "error": str(exc),
        }


_load_env_file()
mongo_state = _build_mongo_state()
anomaly_collection = mongo_state["anomaly_collection"]
current_snapshot_collection = mongo_state["current_snapshot_collection"]
snapshot_collection = mongo_state["snapshot_collection"]


def save_snapshot(data):
    global _latest_snapshot
    _telemetry_history.append(data)
    _latest_snapshot = data
    snapshot_document = _snapshot_document(data)
    if snapshot_collection is not None:
        snapshot_collection.insert_one(snapshot_document)
    if current_snapshot_collection is not None:
        latest_document = dict(snapshot_document)
        latest_document["_id"] = "latest"
        latest_document["document_type"] = "latest_snapshot"
        current_snapshot_collection.replace_one({"_id": "latest"}, latest_document, upsert=True)


def get_latest_snapshot():
    if current_snapshot_collection is not None:
        latest = current_snapshot_collection.find_one({"_id": "latest"})
        if latest:
            return _public_document(latest)

    if snapshot_collection is not None:
        latest = snapshot_collection.find_one(
            {
                "document_type": "telemetry_snapshot",
                "recorded_at": {"$gte": _cutoff_time()},
            },
            sort=[("recorded_at", DESCENDING)],
        )
        if latest:
            return _public_document(latest)
    return _latest_snapshot


def get_recent_snapshots(limit=30):
    if snapshot_collection is not None:
        cursor = (
            snapshot_collection.find(
                {
                    "document_type": "telemetry_snapshot",
                    "recorded_at": {"$gte": _cutoff_time()},
                }
            )
            .sort("recorded_at", DESCENDING)
            .limit(max(limit, 0))
        )
        items = [_public_document(item) for item in cursor]
        items.reverse()
        return items

    items = list(_telemetry_history)
    if limit <= 0:
        return items
    return items[-limit:]


def latest_snapshot_is_fresh(max_age_seconds=600):
    latest = get_latest_snapshot()
    if not latest:
        return False

    try:
        snapshot_time = datetime.fromisoformat(latest["timestamp"])
    except (KeyError, ValueError):
        return False

    if snapshot_time.tzinfo is None:
        snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)
    else:
        snapshot_time = snapshot_time.astimezone(timezone.utc)

    age = (_normalized_now() - snapshot_time).total_seconds()
    return age <= max_age_seconds


def save_anomaly(data):
    if anomaly_collection is not None:
        anomaly_collection.insert_one(_anomaly_document(data))
    else:
        _anomaly_history.appendleft(data)


def get_history():
    if anomaly_collection is not None:
        cursor = anomaly_collection.find(
            {
                "document_type": "anomaly_event",
                "recorded_at": {"$gte": _cutoff_time()},
            }
        ).sort("recorded_at", DESCENDING)
        return [_public_document(item) for item in cursor]

    return list(_anomaly_history)


def get_database_status():
    return {
        "mongodb_enabled": mongo_state["enabled"],
        "mongodb_error": mongo_state["error"],
        "database_name": os.getenv("MONGODB_DB_NAME", "server_monitor"),
        "anomaly_collection": os.getenv("MONGODB_COLLECTION_NAME", "anomalies"),
        "snapshot_collection": os.getenv("MONGODB_SNAPSHOT_COLLECTION_NAME", "snapshots"),
        "current_snapshot_collection": os.getenv("MONGODB_CURRENT_COLLECTION_NAME", "current_status"),
        "retention_hours": _RETENTION_HOURS,
    }
