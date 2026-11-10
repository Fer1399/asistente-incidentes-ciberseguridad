<#
.SYNOPSIS
    Instala el backend del Asistente de Incidentes en Windows 11.

.DESCRIPTION
    1. Comprueba Python (3.11 o superior), Ollama y Tesseract.
    2. Crea el entorno virtual en backend\.venv e instala las dependencias.
       Si existe la carpeta wheels\ (preparada con preparar-offline.ps1) instala sin internet.
    3. Elige el modelo de chat según la GPU del equipo y crea backend\.env.
    4. Descarga los modelos en Ollama (salvo -SinModelos).

.PARAMETER ModeloChat
    Modelo de chat a usar. Si no se indica, se elige automáticamente:
    - GPU NVIDIA con 12 GB de VRAM o más -> qwen2.5:14b
    - resto de equipos (GPU pequeña, integrada o solo CPU) -> qwen2.5:7b

.PARAMETER SinVision
    No descarga el modelo de visión. Las capturas se leerán solo con OCR.

.PARAMETER SinModelos
    No descarga ningún modelo (útil si los copias desde otro equipo).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1 -ModeloChat qwen2.5:7b -SinVision
#>
param(
    [string]$ModeloChat,
    [switch]$SinVision,
    [switch]$SinModelos
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path $PSScriptRoot -Parent
$Backend = Join-Path $Repo "backend"
$Venv = Join-Path $Backend ".venv"
$Wheels = Join-Path $Repo "wheels"

$ModeloVision = "qwen2.5vl:7b"
$EmbedModel = "bge-m3"

function Paso($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Ok($texto)   { Write-Host "    [OK] $texto" -ForegroundColor Green }
function Aviso($texto){ Write-Host "    [AVISO] $texto" -ForegroundColor Yellow }
function Fallo($texto){ Write-Host "    [ERROR] $texto" -ForegroundColor Red; exit 1 }

Write-Host "Asistente de Incidentes - instalación" -ForegroundColor White

# 1. Python ---------------------------------------------------------------
# Se busca, por orden, Python 3.12 y 3.11 de 64 bits. Versiones más nuevas pueden no
# tener aún paquetes compilados (numpy, chromadb...) y pip intentaría compilarlos.
Paso "Comprobando Python"
$Python = $null
$Candidatos = @(
    @{ Exe = "py";     Args = @("-3.12") },
    @{ Exe = "py";     Args = @("-3.11") },
    @{ Exe = "python"; Args = @() }
)
$Comprobacion = "import sys, struct; print('%d.%d %d' % (sys.version_info[0], sys.version_info[1], struct.calcsize('P') * 8))"
foreach ($c in $Candidatos) {
    if (-not (Get-Command $c.Exe -ErrorAction SilentlyContinue)) { continue }
    $ArgsVersion = $c.Args + @("-c", $Comprobacion)
    $salida = & $c.Exe @ArgsVersion 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $salida) { continue }
    $version, $bits = "$salida".Trim().Split(" ")
    if ($bits -ne "64") { Aviso "Python $version de $bits bits ignorado: hace falta 64 bits."; continue }
    if ($version -notin @("3.11", "3.12")) { Aviso "Python $version ignorado: usa 3.12."; continue }
    $Python = $c; break
}
if (-not $Python) {
    Fallo "No encuentro Python 3.12 de 64 bits. Instálalo con: winget install -e --id Python.Python.3.12  (luego cierra y abre PowerShell)"
}
Ok "Python $version (64 bits)"

# 2. Entorno virtual y dependencias --------------------------------------
Paso "Preparando el entorno virtual (backend\.venv)"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
if (Test-Path $VenvPython) {
    $versionVenv = & $VenvPython -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
    if ($versionVenv -ne $version) {
        Aviso "El entorno existente usa Python $versionVenv; se vuelve a crear con $version."
        Remove-Item -Recurse -Force $Venv
    }
}
if (-not (Test-Path $VenvPython)) {
    $ArgsVenv = $Python.Args + @("-m", "venv", $Venv)
    & $Python.Exe @ArgsVenv
    if ($LASTEXITCODE -ne 0) { Fallo "No se pudo crear el entorno virtual." }
}
Ok "Entorno listo"

Paso "Instalando dependencias"
$Requisitos = Join-Path $Backend "requirements.txt"
# --only-binary: nunca compilar desde código fuente (en Windows falla sin compilador de C)
if (Test-Path $Wheels) {
    Write-Host "    Usando paquetes locales de wheels\ (sin internet)"
    & $VenvPython -m pip install --no-index --find-links $Wheels --only-binary=:all: -r $Requisitos
} else {
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install --only-binary=:all: -r $Requisitos
}
if ($LASTEXITCODE -ne 0) { Fallo "Falló la instalación de dependencias. Copia el error completo y consulta docs\01-instalacion.md (Problemas frecuentes)." }
Ok "Dependencias instaladas"

# 3. Modelo de chat y configuración --------------------------------------
Paso "Eligiendo el modelo de chat"
if ($ModeloChat) {
    Ok "Modelo indicado: $ModeloChat"
} else {
    $vramMb = 0
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        $lecturas = & nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>$null
        if ($LASTEXITCODE -eq 0 -and $lecturas) {
            $vramMb = ($lecturas | ForEach-Object { [int]("$_".Trim()) } | Measure-Object -Maximum).Maximum
        }
    }
    if ($vramMb -ge 12000) {
        $ModeloChat = "qwen2.5:14b"
        Ok "GPU NVIDIA con $([math]::Round($vramMb / 1024)) GB: $ModeloChat"
    } else {
        $ModeloChat = "qwen2.5:7b"
        if ($vramMb -gt 0) { Ok "GPU NVIDIA con $([math]::Round($vramMb / 1024)) GB: $ModeloChat" }
        else { Ok "Sin GPU NVIDIA detectada (se usará la CPU): $ModeloChat" }
        Aviso "Sin GPU dedicada las respuestas pueden tardar uno o varios minutos. Considera -SinVision."
    }
}

Paso "Creando backend\.env"
$EnvFile = Join-Path $Backend ".env"
if (Test-Path $EnvFile) {
    Aviso ".env ya existe: no lo toco. Para cambiar de modelo, edita CHAT_MODEL en backend\.env."
} else {
    $contenido = Get-Content (Join-Path $Backend ".env.example") -Raw -Encoding UTF8
    $contenido = $contenido -replace "(?m)^CHAT_MODEL=.*$", "CHAT_MODEL=$ModeloChat"
    if ($SinVision) { $contenido = $contenido -replace "(?m)^VISION_ACTIVA=.*$", "VISION_ACTIVA=false" }
    [System.IO.File]::WriteAllText($EnvFile, $contenido, (New-Object System.Text.UTF8Encoding $false))
    Ok ".env creado con CHAT_MODEL=$ModeloChat"
}
New-Item -ItemType Directory -Force -Path (Join-Path $Repo "data") | Out-Null

# 4. Tesseract (OCR) ------------------------------------------------------
Paso "Comprobando Tesseract (OCR)"
$TesseractDefecto = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if ((Get-Command tesseract -ErrorAction SilentlyContinue) -or (Test-Path $TesseractDefecto)) {
    Ok "Tesseract encontrado"
} else {
    Aviso "Tesseract no está instalado. Sin él no se leerán PDFs escaneados ni capturas en modo OCR."
    Aviso "Instálalo con: winget install -e --id UB-Mannheim.TesseractOCR  (marca el idioma Spanish)"
}

# 5. Ollama y modelos -------------------------------------------------------
Paso "Comprobando Ollama"
# Si se acaba de instalar, el PATH de esta consola aún no lo incluye: se busca en sus carpetas habituales.
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    foreach ($dir in @("$env:LOCALAPPDATA\Programs\Ollama", "$env:ProgramFiles\Ollama")) {
        if (Test-Path (Join-Path $dir "ollama.exe")) { $env:Path += ";$dir"; break }
    }
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Fallo "No encuentro Ollama. Instálalo con: winget install -e --id Ollama.Ollama  y vuelve a ejecutar este script."
}
Ok (& ollama --version)

if ($SinModelos) {
    Aviso "Se omite la descarga de modelos (-SinModelos)."
} else {
    $ADescargar = @($ModeloChat, $EmbedModel)
    if (-not $SinVision) { $ADescargar += $ModeloVision }
    foreach ($modelo in $ADescargar) {
        Paso "Descargando modelo $modelo"
        & ollama pull $modelo
        if ($LASTEXITCODE -ne 0) { Aviso "No se pudo descargar $modelo. ¿Está Ollama en marcha y hay conexión?" }
        else { Ok $modelo }
    }
}

Write-Host "`nInstalación terminada." -ForegroundColor Green
Write-Host "Arranca el backend con scripts\iniciar.bat y abre http://127.0.0.1:8000/health"
