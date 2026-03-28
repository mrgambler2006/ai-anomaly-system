# ai-anomaly-system

## Background Monitoring Agent

To keep monitoring CPU, RAM, and Disk even after the website is closed, run the background agent on the Windows system.

Install dependency:

```powershell
pip install psutil
pip install pyttsx3
```

Start the backend:

```powershell
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.main:app --reload
```

Then start the background agent:

```powershell
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" agent\monitor_agent.py --server-url http://127.0.0.1:8000 --interval 10
```

If the backend is not already running and the server URL points to `127.0.0.1` or `localhost`, the agent now tries to start the local FastAPI backend automatically before retrying telemetry.

Or launch it hidden in the background:

```powershell
powershell -ExecutionPolicy Bypass -File agent\start_agent.ps1
```

Register both the backend and background agent to start automatically when you sign in:

```powershell
powershell -ExecutionPolicy Bypass -File agent\register_startup_task.ps1
```

If Windows blocks scheduled tasks, install user-level startup shortcuts instead:

```powershell
powershell -ExecutionPolicy Bypass -File agent\install_startup_shortcuts.ps1
```

What it does:
- collects real CPU, RAM, and Disk data from the system
- sends telemetry to the backend even if the website is closed
- shows local Windows popup alerts for anomaly or critical states
- speaks overload and critical voice warnings when risk is 70% or higher
- lets the website display the latest system status from the agent
- agent checks the system every 10 seconds
- popup cooldown is 10 seconds by default

## Email Alerts

You can enable email notifications for anomaly and critical events.

Set these environment variables before starting the backend:

```powershell
$env:ALERT_EMAIL_SMTP_HOST="smtp.gmail.com"
$env:ALERT_EMAIL_SMTP_PORT="587"
$env:ALERT_EMAIL_USERNAME="your_email@gmail.com"
$env:ALERT_EMAIL_PASSWORD="your_app_password"
$env:ALERT_EMAIL_FROM="your_email@gmail.com"
$env:ALERT_EMAIL_TO="your_email@gmail.com"
$env:ALERT_EMAIL_USE_TLS="true"
$env:ALERT_EMAIL_COOLDOWN_SECONDS="900"
```

Then start the app normally:

```powershell
& "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn backend.main:app --reload
```

Notes:
- Use an app password for Gmail, not your normal password.
- Alerts send only for anomaly or critical states.
- Cooldown prevents repeated spam emails.

## MongoDB

MongoDB is supported for both anomaly history and telemetry snapshot storage.

1. Create a repo-root `.env` file from `.env.example`.
2. Set `MONGODB_URI` to your MongoDB server or Atlas connection string.
3. Start the backend normally.

Example:

```powershell
Copy-Item .env.example .env
```

You can verify the backend database connection here:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/database-status | Select-Object -Expand Content
```

To rewrite older MongoDB records into the new clean app format, run:

```powershell
& .\.venv\Scripts\python.exe -m backend.migrate_mongodb_records
```
