@echo off
setlocal
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File ".\scripts\run_avatar_motion_lab_probe.ps1"
endlocal
