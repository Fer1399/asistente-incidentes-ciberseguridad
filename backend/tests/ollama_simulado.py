"""Ollama simulado, para probar y hacer demostraciones sin modelos reales.

Imita las rutas de la API de Ollama que usa el backend:
- /api/version, /api/tags
- /api/embed     vectores por "bolsa de palabras" (parecido por palabras, no por significado)
- /api/chat      respuesta fija con la estructura del asistente, en streaming; con
                 imágenes devuelve una descripción fija

Uso (en lugar de Ollama, que debe estar parado):
    .venv\\Scripts\\python.exe -m uvicorn tests.ollama_simulado:app --port 11434

Con este simulador las búsquedas son por palabras: conviene bajar los umbrales en .env
(SIMILITUD_MINIMA=0.05 y SIMILITUD_INCIDENTE=0.1).
"""

import asyncio
import hashlib
import json
import math
import re

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Ollama simulado")

MODELOS = ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5vl:7b", "bge-m3:latest"]
DIMENSIONES = 256

RESPUESTA = """**Tipo de incidente:** Phishing · **Severidad estimada:** Alta (el usuario introdujo sus credenciales; Crítica si ejecutó el adjunto)

### Análisis del artefacto
El correo es **malicioso**: suplanta a Microsoft para robar credenciales.
- **Reply-To desviado**: las respuestas irían a `correo-externo[.]ru`, no al remitente.
- **Remitente falsificado**: el nombre visible muestra soporte@microsoft[.]com, pero el correo real es de `m1crosoft-seguridad[.]top`.
- **SPF y DMARC fallan**: el servidor emisor no está autorizado por el dominio.
- **Enlace engañoso**: el usuario ve `login.microsoftonline.com`, pero se abre `login[.]m1crosoft-seguridad[.]top`.
- **Adjunto peligroso**: `Factura.pdf.exe` es un ejecutable con doble extensión.

### 1. Acciones inmediatas (primeros 15-30 minutos)
1. Cambiar la contraseña del usuario desde un equipo limpio y cerrar todas sus sesiones [1].
2. Revisar el MFA de la cuenta y eliminar métodos que el usuario no reconozca [1].
3. Preguntar al usuario si abrió `Factura.pdf.exe`; si lo hizo, aislar su equipo sin apagarlo.

### 2. Preservación de evidencias
1. Guardar el correo original como .eml con todas sus cabeceras [2].
2. Exportar los inicios de sesión de la cuenta desde la hora de recepción del correo.

### 3. Contención
1. Bloquear `m1crosoft-seguridad[.]top` y `correo-externo[.]ru` en el filtro de correo, el proxy y el DNS [3].
2. Buscar el mismo correo en todos los buzones y retirarlo [3].

### 4. Análisis del alcance
1. Revisar si hubo inicios de sesión desde IPs o países inusuales tras el robo de la contraseña.
2. Comprobar si se crearon reglas de reenvío en el buzón.

### 5. Erradicación y recuperación
1. Eliminar reglas de buzón y aplicaciones OAuth no reconocidas.
2. Mantener la cuenta en vigilancia reforzada dos semanas.

### 6. Notificación
1. Avisar al responsable de seguridad y al DPD.
2. Si el atacante accedió a datos personales, notificar a la AEPD en un máximo de 72 horas [4].

### 7. Lecciones aprendidas
1. Configurar DMARC en modo `reject` y etiquetar los correos externos.

### MITRE ATT&CK
- T1566.002 (enlace malicioso)
- T1566.001 (adjunto malicioso)
- T1078 (uso de cuentas válidas)

### Preguntas para afinar
1. ¿El usuario abrió el adjunto?
2. ¿A qué hora introdujo la contraseña?
"""

DESCRIPCION_IMAGEN = """1. Qué es: captura de un correo electrónico que suplanta a Microsoft 365.
2. Texto relevante: "Su cuenta será bloqueada en 24 horas", botón "Verificar cuenta".
3. Señales sospechosas: urgencia, petición de credenciales, remitente externo."""


def _vector(texto: str) -> list[float]:
    v = [0.0] * DIMENSIONES
    for palabra in re.findall(r"\w+", texto.lower()):
        v[int(hashlib.md5(palabra.encode()).hexdigest(), 16) % DIMENSIONES] += 1.0
    norma = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norma for x in v]


@app.get("/api/version")
async def version():
    return {"version": "simulado"}


@app.get("/api/tags")
async def tags():
    return {"models": [{"name": m} for m in MODELOS]}


@app.post("/api/embed")
async def embed(peticion: Request):
    datos = await peticion.json()
    entradas = datos["input"] if isinstance(datos["input"], list) else [datos["input"]]
    return {"model": datos["model"], "embeddings": [_vector(t) for t in entradas]}


@app.post("/api/chat")
async def chat(peticion: Request):
    datos = await peticion.json()
    if any(m.get("images") for m in datos["messages"]):
        return {"message": {"role": "assistant", "content": DESCRIPCION_IMAGEN}, "done": True}

    async def generar():
        for trozo in re.findall(r"\S+\s*", RESPUESTA):
            yield json.dumps({"message": {"role": "assistant", "content": trozo}, "done": False}) + "\n"
            await asyncio.sleep(0.004)
        yield json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}) + "\n"

    return StreamingResponse(generar(), media_type="application/x-ndjson")
