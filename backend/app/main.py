"""API del Asistente de Incidentes.

Rutas disponibles:
- GET  /health                      estado del backend, Ollama, modelos y base de conocimiento
- GET  /documentos                  lista de documentos
- POST /documentos                  subir un PDF, Markdown o texto
- GET  /documentos/{id}             detalle y progreso
- POST /documentos/{id}/reindexar   volver a procesarlo
- POST /documentos/reindexar-todo   tras cambiar el modelo de embeddings
- DELETE /documentos/{id}           borrarlo
- POST /buscar                      probar qué fragmentos recupera el RAG
- POST /chat                        preguntar al asistente (respuesta en streaming)
- POST /adjuntos                    analizar un correo .eml, log, PDF o captura
- GET  /adjuntos/{id}               resultado del análisis de un adjunto
- POST /iocs                        extraer indicadores de un texto
- /incidentes/...                   fichas de incidente, pasos, cierre, memoria e informes
- GET/POST /copia                   exportar o importar la copia de seguridad
- GET  /modelos                     modelos instalados en Ollama
- GET  /mitre                       referencia local de técnicas MITRE ATT&CK
"""

import os

# ChromaDB envía telemetría por defecto: la desactivamos antes de importarlo.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__, db, mitre, ocr
from . import incidentes as incidentes_mod
from .config import settings
from .embeddings import Embedder
from .ingesta import CLAVE_MODELO, ColaIngesta, reanudar_pendientes, registrar_incluidos
from .ollama_client import OllamaClient, normalizar_modelo
from .routers import adjuntos, busqueda, chat, copias, documentos, incidentes
from .vectores import AlmacenVectorial

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.inicializar()
    app.state.ollama = OllamaClient(settings.ollama_url)
    app.state.almacen = AlmacenVectorial(settings.chroma_dir)
    app.state.embedder = Embedder(settings.ollama_url, settings.embed_model)
    app.state.cola = ColaIngesta(app.state.almacen, app.state.embedder)
    app.state.cola.iniciar()
    reanudar_pendientes(app.state.cola)
    registrar_incluidos(app.state.cola)
    yield
    app.state.cola.detener()
    app.state.embedder.close()
    await app.state.ollama.close()


app = FastAPI(title="Asistente de Incidentes", version=__version__, lifespan=lifespan)

# Solo la extensión de Chrome puede llamar al backend desde el navegador.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^chrome-extension://[a-p]{32}$",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documentos.router)
app.include_router(busqueda.router)
app.include_router(chat.router)
app.include_router(adjuntos.router)
app.include_router(incidentes.router)
app.include_router(copias.router)


@app.get("/mitre")
async def referencia_mitre() -> dict:
    """Referencia local de técnicas MITRE ATT&CK (id → nombre oficial, nombre en español, táctica)."""
    return {t: {"nombre": n, "nombre_es": es, "tactica": tac} for t, (n, es, tac) in mitre.TECNICAS.items()}


@app.get("/modelos")
async def modelos() -> dict:
    """Modelos instalados en Ollama, para elegir el de chat desde la extensión."""
    try:
        instalados = await app.state.ollama.modelos_instalados()
    except httpx.HTTPError:
        instalados = []
    excluir = ("embed", "bge", "minilm", "nomic")
    return {
        "instalados": sorted(instalados),
        "chat": sorted(m for m in instalados if not any(x in m.lower() for x in excluir)),
        "por_defecto": {"chat": settings.chat_model, "vision": settings.vision_model, "embeddings": settings.embed_model},
    }


@app.get("/health")
async def health() -> dict:
    """Estado del backend, de Ollama, de los modelos y de la base de conocimiento."""
    requeridos = {
        "chat": settings.chat_model,
        "vision": settings.vision_model,
        "embeddings": settings.embed_model,
    }
    ollama: dict = {"url": settings.ollama_url, "ok": False}
    modelos = {rol: {"nombre": nombre, "instalado": False} for rol, nombre in requeridos.items()}

    try:
        ollama["version"] = await app.state.ollama.version()
        instalados = {normalizar_modelo(m) for m in await app.state.ollama.modelos_instalados()}
        ollama["ok"] = True
        for info in modelos.values():
            info["instalado"] = normalizar_modelo(info["nombre"]) in instalados
    except httpx.HTTPError as error:
        ollama["error"] = f"No se pudo conectar con Ollama: {error.__class__.__name__}"

    docs = db.listar_documentos()
    modelo_indexado = db.leer_ajuste(CLAVE_MODELO)
    conocimiento = {
        "documentos": len(docs),
        "indexados": sum(1 for d in docs if d["estado"] == "indexado"),
        "en_proceso": sum(1 for d in docs if d["estado"] in {"pendiente", "procesando"}),
        "con_error": sum(1 for d in docs if d["estado"] == "error"),
        "fragmentos": app.state.almacen.total(),
        "incidentes_en_memoria": sum(1 for i in incidentes_mod.listar(estado="cerrado") if i["en_memoria"]),
        "modelo_indexado": modelo_indexado,
        # Si se cambió EMBED_MODEL, los vectores guardados ya no son comparables
        "reindexar_necesario": bool(
            modelo_indexado and normalizar_modelo(modelo_indexado) != normalizar_modelo(settings.embed_model)
        ),
    }

    listo = ollama["ok"] and modelos["chat"]["instalado"] and modelos["embeddings"]["instalado"]
    return {
        "backend": "ok",
        "version": __version__,
        "listo": listo,
        "ollama": ollama,
        "modelos": modelos,
        "ocr": {"tesseract": ocr.disponible(), "vision_activa": settings.vision_activa},
        "conocimiento": conocimiento,
        "datos": str(settings.data_dir),
    }
