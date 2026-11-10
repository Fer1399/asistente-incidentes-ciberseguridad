<#
.SYNOPSIS
    Descarga todos los paquetes de Python en la carpeta wheels\ para instalar
    el backend en un equipo sin internet.

.DESCRIPTION
    Ejecútalo en un equipo CON internet y con la MISMA versión de Python que el
    equipo de destino. Después copia el repositorio completo (con wheels\) por USB
    y ejecuta allí scripts\instalar.ps1: detectará wheels\ y no usará la red.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\preparar-offline.ps1
#>
$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Wheels = Join-Path $Repo "wheels"
$Requisitos = Join-Path $Repo "backend\requirements.txt"

New-Item -ItemType Directory -Force -Path $Wheels | Out-Null
Write-Host "Descargando paquetes en $Wheels ..." -ForegroundColor Cyan
py -3.12 -m pip download --only-binary=:all: -r $Requisitos -d $Wheels
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] Falló la descarga." -ForegroundColor Red; exit 1 }

Write-Host "`nListo. Copia también los modelos de Ollama:" -ForegroundColor Green
Write-Host "  $env:USERPROFILE\.ollama\models  ->  misma ruta en el otro equipo"
