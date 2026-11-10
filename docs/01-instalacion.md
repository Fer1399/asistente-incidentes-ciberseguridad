# 01 · Instalación en Windows 11

Esta guía deja funcionando, en un equipo, el **backend** del asistente, los **modelos de IA
locales** y la **extensión de Chrome**.

Una vez instalado, todo funciona **sin conexión a internet**. La red solo hace falta para
descargar los programas y los modelos la primera vez (o se pueden llevar en un USB: ver
[Instalación sin internet](#instalación-sin-internet)).

En los comandos, `<carpeta-del-proyecto>` es la carpeta donde descargues el repositorio,
por ejemplo `Documentos\asistente-incidentes-ciberseguridad`.

---

## Requisitos

| | Mínimo | Recomendado |
|---|---|---|
| Sistema | Windows 10 u 11 de 64 bits | Windows 11 |
| RAM | 16 GB | 32 GB |
| GPU | No imprescindible: sin ella el modelo funciona en la CPU, pero más lento | NVIDIA con 12 GB de VRAM o más |
| Disco libre | 15 GB | 25 GB |
| Navegador | Google Chrome 116 o posterior | |

### Modelos que se instalan

El instalador elige el modelo de chat según la GPU del equipo:

| Equipo | Modelo de chat | Respuesta típica |
|---|---|---|
| GPU NVIDIA con 12 GB de VRAM o más | `qwen2.5:14b` (≈ 9 GB) | 10-30 segundos |
| GPU más pequeña, integrada o sin GPU | `qwen2.5:7b` (≈ 4,7 GB) | Desde segundos (con GPU) hasta varios minutos (solo CPU) |

Además, siempre:

| Modelo | Para qué | Tamaño aprox. |
|---|---|---|
| `bge-m3` | Embeddings: convertir los textos en vectores para la búsqueda (RAG) | 1,2 GB |
| `qwen2.5vl:7b` | Visión: describir capturas de pantalla (opcional, `-SinVision` para omitirlo) | 6 GB |

Los tamaños son aproximados. Los nombres se pueden cambiar en `backend\.env` si en el
catálogo de Ollama aparecen versiones más nuevas.

---

## Paso 1 · Instalar los programas

Abre **PowerShell como administrador** y ejecuta:

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Ollama.Ollama
winget install -e --id UB-Mannheim.TesseractOCR
winget install -e --id Git.Git
```

| Programa | Para qué |
|---|---|
| **Python 3.12** | Ejecuta el backend. Usa la 3.12 (o 3.11) de 64 bits: con versiones más nuevas algunos paquetes aún no están disponibles. |
| **Ollama** | Ejecuta los modelos de IA en local. Tras instalarlo queda un icono en la bandeja del sistema. |
| **Tesseract** | OCR para PDFs escaneados y capturas. Durante la instalación, en *Additional language data*, marca **Spanish**. |
| **Git** | Para descargar el repositorio (opcional si lo descargas como zip). |

**Cierra PowerShell y abre una ventana nueva** para que se actualice el `PATH`, y comprueba:

```powershell
py -0p              # debe aparecer una línea con 3.12
ollama --version
tesseract --version
```

Si instalaste Tesseract sin el idioma español, descarga `spa.traineddata` del repositorio
`tesseract-ocr/tessdata` y cópialo en `C:\Program Files\Tesseract-OCR\tessdata\`.

---

## Paso 2 · Descargar el proyecto

**Con Git:**

```powershell
cd $HOME\Documents
git clone https://github.com/Fer1399/asistente-incidentes-ciberseguridad.git
cd asistente-incidentes-ciberseguridad
```

**Sin Git:** en la página del repositorio, *Code* → *Download ZIP*, descomprímelo y entra
en la carpeta con `cd <carpeta-del-proyecto>`.

Todos los comandos siguientes se ejecutan **dentro de la carpeta del proyecto**.

---

## Paso 3 · Ejecutar el instalador

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
```

El script:

1. Busca Python 3.12 (o 3.11) de 64 bits.
2. Crea el entorno virtual en `backend\.venv` e instala las dependencias.
3. Detecta la GPU y elige el modelo de chat.
4. Crea `backend\.env` con la configuración.
5. Comprueba Tesseract y Ollama.
6. Descarga los modelos con `ollama pull` (puede tardar un buen rato).

Debe terminar con **`Instalación terminada.`** en verde.

| Opción | Para qué sirve |
|---|---|
| `-ModeloChat qwen2.5:7b` | Elegir el modelo de chat en lugar de la detección automática |
| `-SinVision` | No descargar el modelo de visión; las capturas se leerán solo con OCR (recomendable sin GPU) |
| `-SinModelos` | No descargar modelos (si ya están en Ollama o los copias de otro equipo) |

> `-ExecutionPolicy Bypass` solo afecta a esa ejecución: no cambia la configuración de
> seguridad de Windows.

---

## Paso 4 · Arrancar el backend

```powershell
scripts\iniciar.bat
```

Si Ollama no está en marcha, el script lo arranca. Verás:

```
Asistente de Incidentes -> http://127.0.0.1:8000
...
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Deja esa ventana abierta** mientras uses el asistente. Para pararlo, `Ctrl+C`. La primera
vez indexa los playbooks incluidos (unos segundos con GPU, algo más sin ella).

---

## Paso 5 · Comprobar que todo funciona

Abre <http://127.0.0.1:8000/health>. Lo importante:

| Campo | Debe salir | Si no |
|---|---|---|
| `"listo"` | `true` | Revisa los dos campos siguientes |
| `"ollama"` → `"ok"` | `true` | Abre Ollama desde el menú Inicio |
| `"modelos"` → `"instalado"` | `true` en `chat` y `embeddings` | `ollama pull <nombre-del-modelo>` |
| `"ocr"` → `"tesseract"` | `true` | Opcional; necesario para PDFs escaneados y capturas |
| `"conocimiento"` → `"indexados"` | `8` (7 playbooks y la referencia MITRE) | Espera unos segundos y recarga |

---

## Paso 6 · Cargar la extensión en Chrome

1. Abre `chrome://extensions` y activa **Modo de desarrollador** (arriba a la derecha).
2. Pulsa **Cargar descomprimida** y elige la carpeta **`extension`** de dentro del proyecto
   (no la raíz del proyecto).
3. En el menú de extensiones (icono de puzle), fija *Asistente de Incidentes* con la chincheta.
4. Pulsa el icono: se abre el panel lateral. Arriba a la derecha debe poner **Conectado**.

Uso de cada pestaña: [08 · La extensión de Chrome](08-extension.md).

---

## Uso diario

1. `scripts\iniciar.bat` (y dejar la ventana abierta).
2. Abrir el panel con el icono de la extensión.

Para apagarlo: `Ctrl+C` en la ventana del backend. Ollama se puede cerrar desde su icono
de la bandeja del sistema.

---

## Actualizar a una versión nueva

1. Para el backend (`Ctrl+C`).
2. Con Git: `git pull`. Con zip: descomprime la versión nueva **encima** de la carpeta del
   proyecto. Tus datos están en `data\` y tu configuración en `backend\.env`: no se
   sobrescriben.
3. Si la versión nueva lo indica, vuelve a ejecutar `scripts\instalar.ps1` (es seguro
   repetirlo).
4. `scripts\iniciar.bat`.
5. En `chrome://extensions`, pulsa **recargar** en la tarjeta de la extensión.

---

## Instalación sin internet

Para instalar en un equipo sin conexión, prepara los paquetes en otro equipo que sí la tenga:

1. **En el equipo con internet**, con la misma versión de Python que tendrá el de destino:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\preparar-offline.ps1
   ```
   Se crea la carpeta `wheels\` con todos los paquetes de Python.
2. Descarga allí también los modelos (`ollama pull` de cada uno) y copia en un USB:
   - La carpeta completa del proyecto (incluida `wheels\`).
   - La carpeta de modelos de Ollama: `%USERPROFILE%\.ollama\models`.
   - Los instaladores de Python, Ollama y Tesseract.
3. **En el equipo sin internet**: instala los programas, copia la carpeta de modelos en
   `%USERPROFILE%\.ollama\models` y ejecuta:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1 -SinModelos
   ```
   El instalador detecta `wheels\` y no usa la red.

---

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `py -0p` no muestra la 3.12 | Python 3.12 no instalado | `winget install -e --id Python.Python.3.12` y abre una consola nueva |
| `metadata-generation-failed` al instalar `numpy` u otro paquete | Se usó una versión de Python sin paquetes compilados (muy nueva o de 32 bits) | Instala Python 3.12 de 64 bits y repite `instalar.ps1`: rehace el entorno |
| `No module named 'uvicorn'` al arrancar | La instalación de dependencias no terminó | Repite `instalar.ps1` y revisa el primer error que aparezca |
| `No encuentro Ollama` en el instalador | Ollama recién instalado y `PATH` sin actualizar | Abre una consola nueva; si persiste, cierra sesión en Windows y vuelve a entrar |
| `El argumento 'scripts\instalar.ps1' ... no existe` | La consola no está en la carpeta del proyecto | `cd <carpeta-del-proyecto>` antes de ejecutar el script |
| `git` no se reconoce | Git no instalado o consola abierta antes de instalarlo | `winget install -e --id Git.Git` y abre una consola nueva, o descarga el zip |
| `"ollama": {"ok": false}` en `/health` | Ollama no está en marcha | Ábrelo desde el menú Inicio o ejecuta `ollama serve` |
| `"instalado": false` en un modelo | El modelo no se descargó | `ollama pull <nombre-del-modelo>` |
| `ValueError: OLLAMA_URL ... apunta fuera de este equipo` | `.env` con una dirección no local | Usa `http://127.0.0.1:11434` |
| La página `/health` no carga (conexión rechazada) | El backend no está en marcha | `scripts\iniciar.bat` y deja la ventana abierta |
| Respuestas muy lentas | El modelo funciona en la CPU | Normal sin GPU. Desactiva la visión en Ajustes o usa un modelo más pequeño (`qwen2.5:3b`) |
| *Falta el archivo de manifiesto* al cargar la extensión | Se eligió la raíz del proyecto | Elige la carpeta `extension` |
| Error de permisos al ejecutar `.ps1` | Política de ejecución de PowerShell | Ejecuta con `powershell -ExecutionPolicy Bypass -File ...` |
