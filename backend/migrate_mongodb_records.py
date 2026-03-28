from datetime import datetime, timezone

from .database import (
    _anomaly_document,
    _parse_timestamp,
    _public_document,
    _snapshot_document,
    anomaly_collection,
    current_snapshot_collection,
    get_database_status,
    snapshot_collection,
)


def _normalize_existing_document(document, builder):
    clean = _public_document(document) or {}

    if "data" not in clean:
        cpu = float(clean.get("cpu", 0) or 0)
        ram = float(clean.get("ram", 0) or 0)
        disk = float(clean.get("disk", 0) or 0)
        clean["data"] = {
            "cpu": round(cpu, 2),
            "ram": round(ram, 2),
            "disk": round(disk, 2),
        }

    clean.setdefault("timestamp", _parse_timestamp(document.get("timestamp")).isoformat())
    clean.setdefault("prediction", "Unknown status")
    clean.setdefault("reason", "No reason available")
    clean.setdefault("source", "background-agent")
    clean.setdefault("hostname", "unknown")
    clean.setdefault("anomaly", False)
    clean.setdefault("critical", False)
    clean.setdefault("overloaded", False)
    clean.setdefault("overload_metrics", 0)
    clean.setdefault("anomaly_score", 0.0)
    clean.setdefault("risk_percent", 0)
    clean.setdefault("mode", "normal")
    clean.setdefault("cpu_expected_range", {"label": "0% - 60%", "min": 0, "max": 60, "category": "normal"})
    clean.setdefault("health_score", 0)
    clean.setdefault("refresh_interval_seconds", 10)
    clean.setdefault("email_alerts_enabled", False)
    clean.setdefault("email_alert_status", "No alert sent")

    rebuilt = builder(clean)
    rebuilt["_id"] = document["_id"]
    return rebuilt


def _migrate_collection(collection, builder, label):
    if collection is None:
        print(f"{label}: skipped because MongoDB is not connected.")
        return

    migrated = 0
    cursor = collection.find({})
    for document in cursor:
        rebuilt = _normalize_existing_document(document, builder)
        collection.replace_one({"_id": document["_id"]}, rebuilt)
        migrated += 1

    print(f"{label}: migrated {migrated} records.")


def main():
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"Migration started at {started_at}")
    status = get_database_status()
    if not status["mongodb_enabled"]:
        print(f"MongoDB connection error: {status['mongodb_error']}")
    _migrate_collection(snapshot_collection, _snapshot_document, "snapshots")
    _migrate_collection(anomaly_collection, _anomaly_document, "anomalies")
    if snapshot_collection is not None and current_snapshot_collection is not None:
        latest_snapshot = snapshot_collection.find_one({"document_type": "telemetry_snapshot"}, sort=[("recorded_at", -1)])
        if latest_snapshot:
            latest_snapshot["document_type"] = "latest_snapshot"
            latest_snapshot["_id"] = "latest"
            current_snapshot_collection.replace_one({"_id": "latest"}, latest_snapshot, upsert=True)
            print("current_status: updated latest real-time document.")
    finished_at = datetime.now(timezone.utc).isoformat()
    print(f"Migration finished at {finished_at}")


if __name__ == "__main__":
    main()
