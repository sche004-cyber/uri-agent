<#
.SYNOPSIS
    One-click startup for URI on Windows: brings up the backend API
    server (if it isn't already running) and then opens the Windows
    desktop app, in that order, without requiring the user to type any
    command themselves.

.DESCRIPTION
    This script is pure process orchestration - it contains no Brain
    reasoning, orchestration, or business logic of its own. It only
    ever starts two things that already exist unmodified:
      1. The backend, via the existing, previously-accepted
         scripts/uri_server_ctl.ps1 (a persistent per-user Scheduled
         Task wrapping scripts/run_uri_server.py). Reused as-is, not
         reimplemented - this script adds only what that one doesn't
         already do: deciding whether starting it is even necessary,
         waiting for it to actually become reachable, and reporting
         clearly if it never does.
      2. The already-built Windows desktop app
         (build\windows\x64\runner\Release\uri_ui.exe). This script
         does not build it - see README note in the repo root's
         "Launch URI.bat" / this milestone's report for when a rebuild
         is needed.

    Safe to run repeatedly: if the backend is already reachable, it is
    left alone (no restart, no duplicate task start - Task Scheduler's
    own MultipleInstances=IgnoreNew setting, already configured by
    uri_server_ctl.ps1, makes a second Start-ScheduledTask call while
    one is running a no-op regardless). If the desktop app is already
    running, this script brings its window forward instead of opening
    a second instance.

.PARAMETER Port
    Backend port to check/start on (default 8000, matching both
    scripts/run_uri_server.py's default and uri_ui's own compiled-in
    default backend address).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\launch_uri.ps1
#>

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CtlScript = Join-Path $PSScriptRoot "uri_server_ctl.ps1"
$ExePath = Join-Path $RepoRoot "uri_ui\build\windows\x64\runner\Release\uri_ui.exe"
$HealthUrl = "http://127.0.0.1:$Port/health"
$ProcessName = "uri_ui"

# How long to wait for the backend to become reachable after asking
# Task Scheduler to start it, before giving up and reporting failure.
# uvicorn + this app's own startup services (model provider discovery,
# etc.) are not instant, but any real hang is a genuine problem the
# user should be told about promptly rather than waiting indefinitely.
$HealthPollSeconds = 30
$HealthPollIntervalSeconds = 1

function Write-Step($Message) {
    Write-Output "==> $Message"
}

function Test-BackendHealthy {
    try {
        Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2 -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Show-FailureAndExit([string]$Message) {
    Write-Output ""
    Write-Output "FAILED: $Message"
    Write-Output ""
    # A double-clicked .bat has no console the user is already watching -
    # a message box guarantees the failure is actually seen, not just
    # flashed on screen for a fraction of a second.
    try {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.MessageBox]::Show(
            $Message,
            "URI failed to start",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    }
    catch {
        # Headless/CI environment with no Windows Forms available - the
        # console message above is the fallback, not a silent failure.
    }
    exit 1
}

# ---------------------------------------------------------------
# 1. Backend: start only if not already reachable.
# ---------------------------------------------------------------

if (Test-BackendHealthy) {
    Write-Step "Backend already running at $HealthUrl - reusing it."
}
else {
    Write-Step "Backend not reachable - starting it."

    $task = Get-ScheduledTask -TaskName "URIServer" -ErrorAction SilentlyContinue
    if ($null -eq $task) {
        Write-Step "First run on this machine - installing the backend's Scheduled Task."
        & $CtlScript -Action install -Port $Port
    }

    # Safe even if a previous instance is still starting up: Task
    # Scheduler's MultipleInstances=IgnoreNew (set at install time)
    # makes this a no-op rather than a second process if one is
    # already running.
    & $CtlScript -Action start -Port $Port | Out-Null

    Write-Step "Waiting for the backend to become reachable (up to $HealthPollSeconds s)..."
    $elapsed = 0
    $healthy = $false
    while ($elapsed -lt $HealthPollSeconds) {
        Start-Sleep -Seconds $HealthPollIntervalSeconds
        $elapsed += $HealthPollIntervalSeconds
        if (Test-BackendHealthy) {
            $healthy = $true
            break
        }
    }

    if (-not $healthy) {
        Show-FailureAndExit (
            "The URI backend did not become reachable at $HealthUrl within " +
            "$HealthPollSeconds seconds. Check the log at " +
            "uri_workspace\logs\uri_server.log, or run " +
            "'powershell -File scripts\uri_server_ctl.ps1 -Action status' " +
            "for the Scheduled Task's own state."
        )
    }

    Write-Step "Backend is up."
}

# ---------------------------------------------------------------
# 2. Desktop app: don't open a second window if one is already open.
# ---------------------------------------------------------------

$existing = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Step "URI desktop app is already running - bringing it to the front."
    try {
        Add-Type -Name Win32ShowWindow -Namespace Native -MemberDefinition @"
            [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
            [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
"@
        foreach ($proc in $existing) {
            if ($proc.MainWindowHandle -ne [IntPtr]::Zero) {
                [Native.Win32ShowWindow]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null # SW_RESTORE
                [Native.Win32ShowWindow]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
            }
        }
    }
    catch {
        # Focusing is a convenience, not a correctness requirement - the
        # app is already open and usable either way.
    }
    exit 0
}

if (-not (Test-Path $ExePath)) {
    Show-FailureAndExit (
        "The URI desktop app has not been built yet (expected at " +
        "$ExePath). From uri_ui\, run: flutter build windows --release"
    )
}

Write-Step "Starting the URI desktop app."
Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath)
Write-Step "Done."
exit 0
