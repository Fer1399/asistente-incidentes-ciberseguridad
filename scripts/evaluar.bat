@echo off
REM Batería de evaluación del asistente (el backend tiene que estar en marcha).
REM   scripts\evaluar.bat                      todos los casos
REM   scripts\evaluar.bat ransomware-servidor  uno o varios casos
REM   scripts\evaluar.bat --modelo qwen2.5:7b  con otro modelo
setlocal
chcp 65001 >nul
cd /d "%~dp0..\backend"
".venv\Scripts\python.exe" evaluacion\evaluar.py %*
