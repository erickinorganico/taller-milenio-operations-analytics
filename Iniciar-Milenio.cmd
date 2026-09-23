@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Web.ps1"
if errorlevel 1 exit /b 1
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\run_web.py" --mode live %*
exit /b %ERRORLEVEL%
