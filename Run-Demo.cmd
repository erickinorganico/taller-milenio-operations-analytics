@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup.ps1"
if not exist ".venv\Scripts\python.exe" exit /b 1
set "MILENIO_OUTPUT=artifacts\run-%RANDOM%-%RANDOM%"
".venv\Scripts\python.exe" -m milenio demo --output "%MILENIO_OUTPUT%"
if errorlevel 1 (
  echo Si la salida ya existe, use --output con una nueva carpeta para conservar evidencia.
  pause
  exit /b 1
)
echo Reporte: %MILENIO_OUTPUT%\reports\informe_ejecutivo.html
pause
