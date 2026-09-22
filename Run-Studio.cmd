@echo off
setlocal
set "ROOT=%~dp0"
set "MPLBACKEND=Agg"
cd /d "%ROOT%"
if "%~1"=="" if exist "%ROOT%artifacts\workbench-v2\DOSSIER.html" (
  start "" "%ROOT%artifacts\workbench-v2\DOSSIER.html"
  exit /b 0
)
if exist "%ROOT%.venv\Scripts\python.exe" (
  "%ROOT%.venv\Scripts\python.exe" -m milenio studio %*
) else (
  py -3.12 -m milenio studio %*
)
exit /b %ERRORLEVEL%
