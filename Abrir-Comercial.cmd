@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Abrir-Milenio.ps1" -Mode live -Port 8770 -NoBrowser
if errorlevel 1 (pause & exit /b 1)
start "" "http://127.0.0.1:8770/commercial/"
