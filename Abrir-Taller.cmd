@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Abrir-Milenio.ps1" -Mode live %*
if errorlevel 1 pause
