# 06 · Correos, logs y capturas de pantalla

El asistente puede analizar los artefactos de un incidente: un correo sospechoso, un log,
un PDF o una captura de pantalla. Cada fichero se analiza **antes** de llegar al modelo:
se extraen sus indicadores de compromiso (IOCs), se generan alertas automáticas y se
convierte en texto que el modelo puede leer.

---

## Formatos admitidos

| Tipo | Extensiones | Qué se hace |
|---|---|---|
| Correo | `.eml` | Cabeceras, autenticación, recorrido, enlaces, adjuntos con hash y alertas de suplantación |
| Captura | `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.gif` | Modelo de visión (describe la pantalla) + OCR (lee el texto) |
| Documento | `.pdf` | Texto de cada página (OCR en páginas escaneadas) |
| Log o texto | `.txt` `.log` `.csv` `.json` `.xml` `.html` `.md` `.ini` `.conf` `.yaml` | Texto completo |

No admitidos de momento:

- **`.msg` de Outlook**: ábrelo en Outlook y usa *Guardar como* → formato `.eml`, o arrastra
  el correo a una carpeta desde Outlook en la web.
- **`.evtx` del Visor de eventos**: en el Visor de eventos, *Guardar todos los eventos como…* →
  `.csv` o `.xml`, o filtra antes por los eventos que te interesan (4624, 4625, 4688…).

Tamaño máximo: 25 MB (`MAX_ADJUNTO_MB`).

---

## Correos `.eml`

Cómo obtener un `.eml`:
- **Outlook en la web y Outlook nuevo**: abre el correo → *⋯* (más acciones) → *Guardar* o
  *Descargar* → se descarga como `.eml`.
- **Outlook clásico de escritorio**: solo guarda en `.msg`. Abre el mismo buzón en Outlook en
  la web y descárgalo desde ahí.
- **Gmail**: abre el correo → *⋮* → **Descargar mensaje**.
- **Thunderbird**: *Archivo* → *Guardar como* → *Archivo*.

Los nombres exactos de los menús cambian con las versiones; busca la opción de guardar o
descargar el mensaje original. Un reenvío o una captura **no** sirven para analizar
cabeceras: hace falta el mensaje original.

Lo que se analiza (sin abrir nunca enlaces ni adjuntos):

| Elemento | Qué se comprueba |
|---|---|
| `From`, `Reply-To`, `Return-Path` | Si las respuestas o los rebotes van a otro dominio |
| Nombre visible | Si muestra una dirección distinta de la real (`"soporte@microsoft.com" <otra@dominio>`) |
| `Authentication-Results` | Resultado de **SPF**, **DKIM** y **DMARC** |
| `Received` | Recorrido del correo; el último salto es el servidor de origen |
| Enlaces | Si el texto visible muestra un dominio y el enlace lleva a otro |
| Adjuntos | Nombre, tipo, tamaño, **SHA-256**, extensiones peligrosas y dobles extensiones (`factura.pdf.exe`) |

Ejemplo de alertas para el correo de prueba `backend/tests/muestras/phishing-ejemplo.eml`:

```
⚠ Las respuestas irían a otro dominio: Reply-To correo-externo.ru ≠ From m1crosoft-seguridad.top
⚠ El nombre visible muestra la dirección soporte@microsoft.com pero el correo real es alerta@m1crosoft-seguridad.top
⚠ SPF = fail: el correo no supera esa comprobación de autenticidad
⚠ DMARC = fail: el correo no supera esa comprobación de autenticidad
⚠ Enlace engañoso: muestra login.microsoftonline.com pero lleva a login[.]m1crosoft-seguridad[.]top
⚠ Adjunto de riesgo: Factura.pdf.exe
```

---

## Capturas de pantalla

Se combinan dos métodos, ambos locales:

1. **Modelo de visión** (`qwen2.5vl:7b`): describe qué es la pantalla (correo, SMS, alerta
   del antivirus, nota de rescate…), transcribe lo relevante y señala lo sospechoso.
2. **OCR** (Tesseract): lee literalmente todo el texto. Es lo que garantiza que URLs, IPs y
   dominios se extraigan exactos.

Si el modelo de visión no está instalado o falla, la captura se analiza solo con OCR y se
avisa. En un equipo sin GPU dedicada, el modelo de visión puede tardar más de un minuto por
captura: pon `VISION_ACTIVA=false` en `backend\.env` para usar solo OCR, o decide en cada
caso con `POST /adjuntos?vision=false`.

Consejos: haz la captura a tamaño real (sin reducir) y recorta lo que no aporta. Las
imágenes grandes se reducen a 1600 px de lado antes de analizarlas.

---

## Logs

El texto completo se usa para **extraer todos los IOCs**. Al modelo le llega un máximo de
12 000 caracteres (`MAX_CARACTERES_ADJUNTO`): si el log es más largo, recibe el principio y el
final, y se avisa. Para logs grandes, filtra antes lo relevante (por IP, usuario, hora o
ID de evento) y obtendrás mejores respuestas.

---

## Indicadores de compromiso (IOCs)

Se extraen por patrones, de forma exacta, de todo el contenido y del texto que escribas:

| Tipo | Ejemplo seguro | Notas |
|---|---|---|
| IP | `185[.]220[.]101[.]45` | Las privadas (`192.168.x.x`, `10.x.x.x`…) se marcan como **internas** |
| Dominio | `login[.]m1crosoft-seguridad[.]top` | Se ignoran nombres de fichero (`informe.pdf`) |
| URL | `hxxps://login[.]ejemplo[.]top/verify` | |
| Correo | `alerta@m1crosoft-seguridad[.]top` | |
| Hash | `cf365ce3…` (MD5, SHA-1 o SHA-256) | Incluye el SHA-256 de cada adjunto de un correo |
| CVE | `CVE-2024-3400` | |

- Se aceptan indicadores ya desactivados (`ejemplo[.]com`, `hxxp://`) y se normalizan.
- Siempre se **muestran desactivados**, para que no se puedan abrir por error.
- El modelo recibe esta lista como fiable y tiene instrucciones de no añadir indicadores
  que no aparezcan en ella o en tu texto.

---

## Dónde se guardan

Cada adjunto analizado se guarda en `data\adjuntos\<id>\`:

- `original.bin`: el fichero original, como **evidencia**, con un nombre neutro para que no
  se abra ni ejecute por accidente.
- `analisis.json`: el resultado del análisis.

Al crear una ficha, los adjuntos de la conversación quedan vinculados a ella. La carpeta `data\`
nunca se sube a GitHub.

> **Antivirus:** si un correo contiene malware real, Microsoft Defender puede poner en
> cuarentena `original.bin`. Es esperable; el análisis ya guardado no se ve afectado.

---

## Uso desde la consola

Con el backend en marcha:

```powershell
# Una pregunta con adjunto
scripts\preguntar.bat -a "C:\ruta\correo-sospechoso.eml" "¿Es phishing? ¿Cómo procedo?"

# Varios adjuntos
scripts\preguntar.bat -a correo.eml -a captura.png "Un usuario abrió este correo y le salió esta pantalla"

# En la conversación interactiva
scripts\preguntar.bat
> /adjuntar C:\ruta\auth.log
> Analiza este log, ¿hay algún acceso con éxito?
```

Prueba con el correo de ejemplo incluido:

```powershell
scripts\preguntar.bat -a backend\tests\muestras\phishing-ejemplo.eml "¿Es phishing? ¿Cómo procedo?"
```

---

## API

| Método | Ruta | Para qué |
|---|---|---|
| `POST` | `/adjuntos` | Subir y analizar un fichero (campo `fichero`). `?vision=false` para usar solo OCR |
| `GET` | `/adjuntos/{id}` | Ver el análisis de un adjunto |
| `POST` | `/iocs` | `{"texto": "..."}` → IOCs de un texto pegado |
| `POST` | `/chat` | Cada mensaje acepta `"adjuntos": ["<id>", ...]` |

El primer evento del chat (`"tipo": "fuentes"`) incluye ahora `"iocs"`: los indicadores del
último mensaje y sus adjuntos, para que la extensión los muestre con botón de copiar.
