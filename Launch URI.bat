@echo off
REM One-click URI startup. Double-click this file.
REM
REM Starts the backend (if it is not already running) and then opens
REM the URI desktop app - no terminal typing required. All the actual
REM logic lives in scripts\launch_uri.ps1 (which reuses the existing
REM scripts\uri_server_ctl.ps1 backend controller); this file only
REM exists so double-clicking it does not first ask "Run with
REM PowerShell?" or open the script in a text editor.
REM
REM Live UX Repair: launch_uri.ps1 now runs fully hidden and detached
REM (via -WindowStyle Hidden + "start", not waited-on) so a successful
REM launch never leaves a visible console window - this .bat's own
REM window closes within a fraction of a second regardless of how long
REM the backend health check takes. A real failure still surfaces:
REM launch_uri.ps1's own Show-FailureAndExit shows a Windows message
REM box independently of console visibility (already verified working
REM in docs/plans/UI_HYBRID_LAUNCH_MOBILE_READINESS_REPORT.md), so this
REM .bat no longer needs to wait for or relay an exit code itself.
REM
REM -ExecutionPolicy Bypass applies to this one invocation only - it
REM does not change any system-wide PowerShell execution policy.
setlocal
set "SCRIPT_DIR=%~dp0"
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%SCRIPT_DIR%scripts\launch_uri.ps1"
endlocal
exit /b 0
