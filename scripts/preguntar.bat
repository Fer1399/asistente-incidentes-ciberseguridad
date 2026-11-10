@echo off
REM Consola para preguntar al asistente sin la extension.
REM El backend tiene que estar en marcha (scripts\iniciar.bat en otra ventana).
REM   scripts\preguntar.bat                    conversacion interactiva
REM   scripts\preguntar.bat "tu pregunta"      una sola pregunta
setlocal
chcp 65001 >nul
REM Carpeta desde la que se lanza: las rutas relativas de los adjuntos se resuelven desde aqui
set "PREGUNTAR_ORIGEN=%CD%"
set "REPO=%~dp0.."
cd /d "%REPO%\backend"
".venv\Scripts\python.exe" preguntar.py %*
