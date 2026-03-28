from math import sqrt


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _std(values, mean_value):
    if len(values) < 2:
        return 1.0
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return max(sqrt(variance), 1.0)


def analyze_system(data, history, mode="normal"):
    cpu = data["cpu"]
    ram = data["ram"]
    disk = data["disk"]

    history = history[-20:]
    has_baseline = len(history) >= 5
    cpu_history = [item["data"]["cpu"] for item in history] if history else [45]
    ram_history = [item["data"]["ram"] for item in history] if history else [50]
    disk_history = [item["data"]["disk"] for item in history] if history else [40]

    cpu_mean = _mean(cpu_history)
    ram_mean = _mean(ram_history)
    disk_mean = _mean(disk_history)

    cpu_std = _std(cpu_history, cpu_mean)
    ram_std = _std(ram_history, ram_mean)
    disk_std = _std(disk_history, disk_mean)

    cpu_z = abs(cpu - cpu_mean) / cpu_std
    ram_z = abs(ram - ram_mean) / ram_std
    disk_z = abs(disk - disk_mean) / disk_std

    if mode == "high":
        overload_limits = ((cpu, 70), (ram, 65), (disk, 70))
        critical_limits = ((cpu, 85), (ram, 88), (disk, 92))
        anomaly_score_limit = 2.2
    else:
        overload_limits = ((cpu, 80), (ram, 78), (disk, 82))
        critical_limits = ((cpu, 92), (ram, 93), (disk, 96))
        anomaly_score_limit = 3.1

    overload_metrics = sum(1 for value, limit in overload_limits if value >= limit)
    critical_metrics = sum(1 for value, limit in critical_limits if value >= limit)

    score = (cpu / 100) * 1.35 + (ram / 100) * 1.1 + (disk / 100) * 0.85
    if has_baseline:
        score += (
            min(cpu_z, 4) * 0.55
            + min(ram_z, 4) * 0.45
            + min(disk_z, 4) * 0.35
        )
    score += overload_metrics * 0.75 + critical_metrics * 1.2
    score = round(score, 2)

    anomaly = score >= anomaly_score_limit or critical_metrics >= 1 or overload_metrics >= 1
    critical = critical_metrics >= 1 or (
        (mode == "high" and cpu >= 85 and ram >= 88)
        or (mode != "high" and cpu >= 92 and ram >= 93)
    )
    overloaded = overload_metrics >= 1

    if mode == "high" and cpu >= 70 and ram < 88 and critical_metrics == 0:
        reason = "CPU is in the high load range because too many processes are running"
    elif critical:
        reason = "CPU and RAM are simultaneously overloaded, indicating a likely crash condition"
    elif has_baseline and cpu_z >= 2.2:
        reason = "CPU usage deviated sharply from recent behavior"
    elif has_baseline and ram_z >= 2.2:
        reason = "RAM usage deviated sharply from recent behavior"
    elif has_baseline and disk_z >= 2.0:
        reason = "Disk usage spiked beyond its recent operating profile"
    elif overload_metrics >= 2:
        reason = "Multiple core resources are overloaded at the same time"
    else:
        reason = "System activity is within the recent operating baseline"

    if critical:
        prediction = "High risk: System may crash soon"
    elif anomaly:
        prediction = "Medium risk: System may become unstable"
    else:
        prediction = "Low risk: System is stable"

    return {
        "anomaly": anomaly,
        "critical": critical,
        "overloaded": overloaded,
        "overload_metrics": overload_metrics,
        "score": score,
        "reason": reason,
        "prediction": prediction,
    }
