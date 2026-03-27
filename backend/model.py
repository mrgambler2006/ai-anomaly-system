def detect_anomaly(data):
    cpu = data["cpu"]
    ram = data["ram"]
    disk = data["disk"]

    risk_score = 0

    if cpu >= 85:
        risk_score += 2
    elif cpu >= 75:
        risk_score += 1

    if ram >= 80:
        risk_score += 2
    elif ram >= 70:
        risk_score += 1

    if disk >= 85:
        risk_score += 2
    elif disk >= 75:
        risk_score += 1

    return risk_score >= 3
