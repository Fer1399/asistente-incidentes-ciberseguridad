@echo off
REM Arranca el backend del Asistente de Incidentes.
REM Si Ollama no esta en marcha, lo arranca minimizado.
setlocal
chcp 65001 >nul
title Asistente de Incidentes - backend

set "REPO=%~dp0.."
cd /d "%REPO%\backend"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] No existe el entorno de Python.
    echo Ejecuta primero:  powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import uvicorn, fastapi, chromadb" 2>nul
if errorlevel 1 (
    echo [ERROR] Faltan dependencias: la instalacion no termino bien.
    echo Vuelve a ejecutar:  powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
    pause
    exit /b 1
)

where ollama >nul 2>&1
if errorlevel 1 (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Ollama"
    if exist "%ProgramFiles%\Ollama\ollama.exe" set "PATH=%PATH%;%ProgramFiles%\Ollama"
)

curl -s -o nul http://127.0.0.1:11434/api/version
if errorlevel 1 (
    echo Ollama no responde. Arrancandolo...
    start "Ollama" /min ollama serve
    timeout /t 4 /nobreak >nul
)

".venv\Scripts\python.exe" run.py
pause
