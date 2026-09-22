@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup.ps1"
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -m milenio demo --output artifacts/demo
if errorlevel 1 (
  echo Si la salida ya existe, use --output con una nueva carpeta para conservar evidencia.
  pause
  exit /b 1
)
echo Reporte: artifacts\demo\reports\informe_ejecutivo.html
pause
