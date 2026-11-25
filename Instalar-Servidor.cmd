@echo off
setlocal
cd /d "%~dp0"
title Milenio - instalar en el servidor del taller
echo Este asistente prepara la computadora central donde se guardan las ordenes.
echo Para entrar desde otro equipo o celular, abre la direccion de tu taller.
if exist "%LOCALAPPDATA%\MilenioServer\private\current.json" (
    echo Ya hay una instalacion en este equipo. Para actualizarla, sigue
    echo infra\DESPLIEGUE-Y-RECUPERACION.md durante una pausa del taller.
    pause
    exit /b 1
)
if not exist ".runtime\wheels\" (
    echo Extrae el ZIP completo de instalacion y vuelve a abrir este archivo.
    pause
    exit /b 1
)
echo Necesitas Python 3.12 de 64 bits y el ZIP extraido en una carpeta local.
choice /C SN /N /M "Instalar en esta computadora como servidor central? [S/N] "
if errorlevel 2 exit /b 0
if not errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Server.ps1" -Offline
if errorlevel 1 (
    echo La instalacion se detuvo. Revisa el mensaje anterior antes de continuar.
    pause
    exit /b 1
)
pause
