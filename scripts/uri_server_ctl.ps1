<#
.SYNOPSIS
    Install/start/stop/restart/status control for the URI API server as
    a persistent Windows Scheduled Task.

.DESCRIPTION
    Wraps scripts/run_uri_server.py in a per-user Scheduled Task (Task
    Scheduler is built into Windows - no extra software installed) so
    the server survives closing the terminal that started it and comes
    back automatically the next time this user logs on, including
    after a PC reboot. Runs only while this user is logged on (no
    stored credentials needed for "run whether logged on or not"), and
    is configured to restart itself if the process ever exits
    unexpectedly.

    This script only manages the PROCESS lifecycle - it contains no
    Brain reasoning, orchestration, or business logic of its own. The
    task's action is always exactly `python.exe scripts/run_uri_server.py`,
    the same command used for a manual foreground run.

.PARAMETER Action
    install   - registers the scheduled task (run once).
    uninstall - removes the scheduled task.
    start     - starts the task now.
    stop      - stops the running task/process.
    restart   - stop then start.
    status    - shows the task's state plus a live GET /health check.

.EXAMPLE
    powershell -File scripts\uri_server_ctl.ps1 -Action install
    powershell -File scripts\uri_server_ctl.ps1 -Action status
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("install", "uninstall", "start", "stop", "restart", "status")]
    [string]$Action,

    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$TaskName = "URIServer"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LauncherScript = Join-Path $RepoRoot "scripts\run_uri_server.py"
$LogDir = Join-Path $RepoRoot "uri_workspace\logs"
$LogFile = Join-Path $LogDir "uri_server.log"

function Install-UriServerTask {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

    # cmd.exe wraps the real launch purely so stdout/stderr can be
    # redirected to a log file - Task Scheduler itself has no built-in
    # output-redirection option. The launcher/orchestrator underneath
    # is unchanged either way.
    $cmdArgument = (
        "/c `"`"$PythonExe`" `"$LauncherScript`" --port $Port " +
        ">> `"$LogFile`" 2>&1`""
    )

    $taskAction = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument $cmdArgument `
        -WorkingDirectory $RepoRoot

    $taskTrigger = New-ScheduledTaskTrigger -AtLogOn

    $taskSettings = New-ScheduledTaskSettingsSet `
        -Hidden `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -MultipleInstances IgnoreNew

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Settings $taskSettings `
        -Description ("URI API server (uri_core.app.server) - local/LAN " +
            "development server, restarts on failure, runs at this " +
            "user's logon (including after reboot).") `
        -Force | Out-Null

    Write-Output "Installed scheduled task '$TaskName' (runs at logon as $env:USERNAME)."
    Write-Output "Log file: $LogFile"
}

function Uninstall-UriServerTask {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed scheduled task '$TaskName' (if it existed)."
}

function Start-UriServerTask {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "Start requested."
}

function Stop-UriServerTask {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    # Stop-ScheduledTask only stops the direct child (cmd.exe) - the
    # real uvicorn process is cmd's child, so it is targeted
    # separately by matching its command line, never by a bare
    # process-name kill that could hit an unrelated python.exe.
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*run_uri_server.py*" } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    Write-Output "Stop requested."
}

function Show-UriServerStatus {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

    if ($null -eq $task) {
        Write-Output "Scheduled task '$TaskName' is not installed."
    }
    else {
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Output "Task state:      $($task.State)"
        Write-Output "Last run time:   $($info.LastRunTime)"
        Write-Output "Last run result: $($info.LastTaskResult) (0 = success)"
        Write-Output "Next run time:   $($info.NextRunTime)"
    }

    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 3
        Write-Output "Health check:    reachable, status=$($health.status)"
    }
    catch {
        Write-Output "Health check:    NOT reachable ($($_.Exception.Message))"
    }
}

switch ($Action) {
    "install" { Install-UriServerTask }
    "uninstall" { Uninstall-UriServerTask }
    "start" { Start-UriServerTask }
    "stop" { Stop-UriServerTask }
    "restart" { Stop-UriServerTask; Start-Sleep -Seconds 2; Start-UriServerTask }
    "status" { Show-UriServerStatus }
}
