import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage


_last_sent_at = {
    "anomaly": None,
    "critical": None,
}


def _get_env(name, default=""):
    return os.getenv(name, default).strip()


def email_alerts_enabled():
    required = [
        "ALERT_EMAIL_SMTP_HOST",
        "ALERT_EMAIL_SMTP_PORT",
        "ALERT_EMAIL_FROM",
        "ALERT_EMAIL_TO",
    ]
    return all(_get_env(name) for name in required)


def _cooldown_seconds():
    raw = _get_env("ALERT_EMAIL_COOLDOWN_SECONDS", "900")
    try:
        return max(60, int(raw))
    except ValueError:
        return 900


def _should_send(level):
    last_sent = _last_sent_at.get(level)
    if last_sent is None:
        return True

    now = datetime.now(timezone.utc)
    return now - last_sent >= timedelta(seconds=_cooldown_seconds())


def _build_subject(result):
    level = "CRITICAL" if result["critical"] else "ANOMALY"
    return f"[{level}] AI Anomaly System Alert"


def _build_body(result):
    data = result["data"]
    return (
        "AI Anomaly System Alert\n\n"
        f"Timestamp: {result['timestamp']}\n"
        f"Mode: {result['mode']}\n"
        f"Anomaly: {result['anomaly']}\n"
        f"Critical: {result['critical']}\n"
        f"Prediction: {result['prediction']}\n"
        f"Reason: {result['reason']}\n"
        f"Anomaly Score: {result['anomaly_score']}\n"
        f"Health Score: {result['health_score']}\n\n"
        "System Metrics\n"
        f"CPU: {data['cpu']}%\n"
        f"RAM: {data['ram']}%\n"
        f"Disk: {data['disk']}%\n"
    )


def send_email_alert(result):
    if not email_alerts_enabled():
        return {"sent": False, "reason": "Email alerts are not configured"}

    level = "critical" if result["critical"] else "anomaly"
    if not _should_send(level):
        return {"sent": False, "reason": f"{level.title()} alert is in cooldown"}

    host = _get_env("ALERT_EMAIL_SMTP_HOST")
    port = int(_get_env("ALERT_EMAIL_SMTP_PORT", "587"))
    username = _get_env("ALERT_EMAIL_USERNAME")
    password = _get_env("ALERT_EMAIL_PASSWORD")
    from_email = _get_env("ALERT_EMAIL_FROM")
    to_email = _get_env("ALERT_EMAIL_TO")
    use_tls = _get_env("ALERT_EMAIL_USE_TLS", "true").lower() != "false"

    message = EmailMessage()
    message["Subject"] = _build_subject(result)
    message["From"] = from_email
    message["To"] = to_email
    message.set_content(_build_body(result))

    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except Exception as exc:
        return {"sent": False, "reason": f"Email send failed: {exc}"}

    _last_sent_at[level] = datetime.now(timezone.utc)
    return {"sent": True, "reason": f"{level.title()} email alert sent"}
