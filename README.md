# Project Title
## AI-Powered Explainable Anomaly Detection System
*An intelligent system monitoring platform that detects anomalies in real time and explains why they happen.*

## Problem Statement
Modern system monitoring dashboards usually show raw CPU, RAM, and disk values, but they often fail to answer the critical operational questions:

- Is this behavior normal or abnormal?
- Why is the anomaly happening?
- How urgently should the user respond?

Because of this, teams spend time interpreting graphs manually instead of acting quickly. Traditional monitoring can detect load, but it rarely provides **machine learning insight plus explanation**, which is essential for faster decision-making.

## Solution Overview
This project builds a smart monitoring system that combines **real-time telemetry**, **machine learning-based anomaly detection**, and **explainable insights** in a single dashboard.

The platform continuously monitors system metrics, sends them through an anomaly detection pipeline, generates a reason for suspicious behavior, and displays the result through a polished multi-page frontend with charts, alerts, and status views.

### Execution Flow
1. The backend collects or receives live system metrics.
2. The ML model evaluates the telemetry for abnormal behavior.
3. The explanation engine generates the reason behind the anomaly.
4. The frontend presents insights, alerts, charts, and system status in real time.

## Key Features
- Real-time monitoring of CPU, RAM, and disk usage
- Machine learning-based anomaly detection using scikit-learn
- Explainable AI output that gives the reason behind anomalies
- Dynamic dashboard with live charts and visual insights
- Alert system with popup and optional voice notification
- Multi-page professional UI with smooth animations
- Background monitoring agent for continuous telemetry collection
- Optional MongoDB integration for history and telemetry storage

## Tech Stack Used
- **Backend:** FastAPI, Python
- **Machine Learning:** scikit-learn
- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **System Monitoring:** psutil
- **Database:** MongoDB (optional)

## Why This Project Is Unique
- It combines **anomaly detection + explainability**, which makes the output more useful than a standard monitoring dashboard.
- It focuses on **actionable intelligence**, not just raw numbers.
- It is designed as a **demo-ready SaaS-style platform** with strong visual presentation for hackathons.
- It includes both **backend intelligence** and **frontend user experience**, making it a complete product prototype rather than a single-model demo.

## Demo Flow
- Launch the backend and monitoring agent.
- Open the homepage to introduce the product and navigation flow.
- Visit the real-time monitoring page to show live CPU, RAM, and disk metrics.
- Trigger higher system load to demonstrate anomaly detection.
- Open the anomaly and explanation pages to show the detected issue and reason.
- Present the visualization page to showcase live chart-based monitoring.

## How to Run the Project
### 1. Install dependencies
```powershell
pip install -r requirements.txt
pip install psutil pyttsx3
```

### 2. Start the backend server
```powershell
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Start the background monitoring agent
```powershell
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" agent\monitor_agent.py --server-url http://127.0.0.1:8000 --interval 10
```

### 4. Open the application
```text
http://127.0.0.1:8000/
```

### Optional: Run the monitoring agent in the background
```powershell
powershell -ExecutionPolicy Bypass -File agent\start_agent.ps1
```

### Optional: Start the backend and agent on login
```powershell
powershell -ExecutionPolicy Bypass -File agent\register_startup_task.ps1
```

If scheduled tasks are blocked:

```powershell
powershell -ExecutionPolicy Bypass -File agent\install_startup_shortcuts.ps1
```

### Optional: Enable MongoDB
Add the following values to `.env`:

```env
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DB_NAME=server_monitor
MONGODB_COLLECTION_NAME=anomalies
MONGODB_SNAPSHOT_COLLECTION_NAME=snapshots
MONGODB_CURRENT_COLLECTION_NAME=current_status
```

Verify database connectivity:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/database-status | Select-Object -Expand Content
```

## Project Structure
```text
agent/      Background monitoring and alert agent
backend/    FastAPI API, ML logic, explanation flow, database integration
frontend/   Dashboard pages, charts, UI animations, monitoring views
```

## Future Improvements
- Add Docker support for easier deployment
- Introduce authentication and multi-user dashboards
- Add deeper process-level anomaly detection
- Support cloud deployment and remote server monitoring
- Expand explainability with richer root-cause analysis
- Add alert delivery through email, mobile, and webhook channels

## Impact
This project transforms raw machine metrics into **clear, explainable, and actionable intelligence**. It helps users understand not only when something is wrong, but also why it is wrong, making the system more practical, more trustworthy, and more valuable in real-world monitoring scenarios.
