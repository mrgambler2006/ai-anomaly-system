$python = "C:\Users\lenovo\AppData\Local\Programs\Python\Python311\python.exe"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendArgs = "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
$agentArgs = "agent\monitor_agent.py --server-url http://127.0.0.1:8000 --interval 60 --popup-cooldown 900"

$backendAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument $backendArgs `
    -WorkingDirectory $projectRoot

$agentAction = New-ScheduledTaskAction `
    -Execute $python `
    -Argument $agentArgs `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask `
    -TaskName "AIAnomalySystemBackend" `
    -Action $backendAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts the AI anomaly system backend when the user logs on." `
    -Force | Out-Null

Register-ScheduledTask `
    -TaskName "AIAnomalySystemAgent" `
    -Action $agentAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Starts the AI anomaly background monitor when the user logs on." `
    -Force | Out-Null

Write-Host "Startup tasks registered successfully."
