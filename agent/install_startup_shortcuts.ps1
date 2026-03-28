$startupDir = [Environment]::GetFolderPath("Startup")
$projectRoot = Split-Path -Parent $PSScriptRoot

$backendShortcut = Join-Path $startupDir "AIAnomalySystemBackend.lnk"
$agentShortcut = Join-Path $startupDir "AIAnomalySystemAgent.lnk"

$shell = New-Object -ComObject WScript.Shell

$backend = $shell.CreateShortcut($backendShortcut)
$backend.TargetPath = "C:\Windows\System32\cmd.exe"
$backend.Arguments = "/c `"$projectRoot\agent\start_backend.cmd`""
$backend.WorkingDirectory = $projectRoot
$backend.WindowStyle = 7
$backend.Save()

$agent = $shell.CreateShortcut($agentShortcut)
$agent.TargetPath = "C:\Windows\System32\cmd.exe"
$agent.Arguments = "/c `"$projectRoot\agent\start_agent.cmd`""
$agent.WorkingDirectory = $projectRoot
$agent.WindowStyle = 7
$agent.Save()

Write-Host "Startup shortcuts installed in $startupDir"
