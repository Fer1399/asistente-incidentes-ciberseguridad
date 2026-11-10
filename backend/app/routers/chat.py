"""Chat con el asistente.

POST /chat responde en streaming con una línea JSON por evento (NDJSON):

    {"tipo": "fuentes", "fuentes": [...], "similares": [...], "iocs": {...}, "modelo": "qwen2.5:7b"}
    {"tipo": "texto", "texto": "### 1. Acciones..."}     ← muchas veces, según se genera
    {"tipo": "fin", "segundos": 12.4, "mitre": [...]}  ← técnicas citadas con su nombre oficial
    {"tipo": "error", "mensaje": "..."}                  ← solo si algo falla a mitad
"""

import json
import logging
import time
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import adjuntos as adjuntos_mod
from .. import incidentes, iocs, mitre
from ..asistente import (
    con_cabecera_de_playbook,
    construir_mensajes,
    consulta_de_busqueda,
    expandir_adjuntos,
    fuente_publica,
    seleccionar_fuentes,
)
from ..config import settings
from ..embeddings import OllamaNoDisponible
from ..ollama_client import ErrorOllama
from .incidentes import buscar_similares

router = APIRouter(tags=["chat"])
log = logging.getLogger("asistente.chat")


class Mensaje(BaseModel):
    rol: Literal["usuario", "asistente"]
    contenido: str = Field(min_length=1, max_length=40000)
    adjuntos: list[str] = Field(default_factory=list, max_length=10, description="Ids devueltos por POST /adjuntos")


class PeticionChat(BaseModel):
    mensajes: list[Mensaje] = Field(min_length=1, max_length=100)
    modelo: str | None = Field(default=None, max_length=100, description="Por defecto, CHAT_MODEL")
    incidente_id: str | None = Field(
        default=None, max_length=40,
        description="Si se indica, la pregunta y la respuesta se guardan en esa ficha")


def _linea(evento: dict) -> bytes:
    return (json.dumps(evento, ensure_ascii=False) + "\n").encode("utf-8")


@router.post("/chat")
async def chat(peticion: PeticionChat, request: Request) -> StreamingResponse:
    mensajes = [m.model_dump() for m in peticion.mensajes]
    if mensajes[-1]["rol"] != "usuario":
        raise HTTPException(422, "El último mensaje debe ser del usuario")

    estado = request.app.state
    modelo = peticion.modelo or settings.chat_model
    if peticion.incidente_id and not incidentes.obtener(peticion.incidente_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidente no encontrado")
    ultimo_original = {**mensajes[-1]}

    # 0. Cargar los adjuntos ya analizados de cada mensaje
    adjuntos_por_mensaje = []
    for mensaje in mensajes:
        cargados = []
        for adjunto_id in mensaje.pop("adjuntos", []):
            adjunto = adjuntos_mod.cargar(adjunto_id)
            if not adjunto:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Adjunto no encontrado: {adjunto_id}")
            cargados.append(adjunto)
        adjuntos_por_mensaje.append(cargados)
    adjuntos_ultimo = adjuntos_por_mensaje[-1]
    indicadores = iocs.combinar(iocs.extraer(mensajes[-1]["contenido"]), *(a["iocs"] for a in adjuntos_ultimo))

    # 1. Recuperar contexto de la base de conocimiento
    try:
        consulta = consulta_de_busqueda(mensajes, adjuntos_ultimo)
        vector = await run_in_threadpool(estado.embedder.vectorizar_uno, consulta)
    except OllamaNoDisponible as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    resultados = await run_in_threadpool(estado.almacen.buscar, vector, settings.fragmentos_por_consulta)
    # Los incidentes cerrados parecidos se buscan aparte: si no, los PDFs largos los taparían
    similares = await run_in_threadpool(buscar_similares, estado.almacen, vector, 2)
    similares = [s for s in similares if s["id"] != peticion.incidente_id]
    ya_incluidos = {(r.get("doc_id"), r["texto"]) for r in resultados}
    for similar in similares:
        if (similar["id"], similar["texto"]) not in ya_incluidos:
            resultados.insert(0, {"texto": similar["texto"], "documento": f"{similar['id']} · {similar['titulo']}",
                                  "doc_id": similar["id"], "tipo": "incidente", "similitud": similar["similitud"]})
    resultados = await run_in_threadpool(con_cabecera_de_playbook, resultados, estado.almacen)
    fuentes = seleccionar_fuentes(resultados)
    similares = [{k: v for k, v in s.items() if k != "texto"} for s in similares]

    # 2. Preparar la conversación y generar la respuesta
    conversacion = construir_mensajes(expandir_adjuntos(mensajes, adjuntos_por_mensaje), fuentes)
    opciones = {"temperature": settings.temperatura, "num_ctx": settings.contexto_tokens}

    async def generar():
        inicio = time.monotonic()
        yield _linea({
            "tipo": "fuentes",
            "modelo": modelo,
            "fuentes": [fuente_publica(f) for f in fuentes],
            "similares": similares,
            "iocs": indicadores,
        })
        respuesta: list[str] = []
        try:
            async for trozo in estado.ollama.chat_stream(modelo, conversacion, opciones):
                respuesta.append(trozo)
                yield _linea({"tipo": "texto", "texto": trozo})
            if peticion.incidente_id:
                await run_in_threadpool(incidentes.anadir_mensajes, peticion.incidente_id, [
                    ultimo_original, {"rol": "asistente", "contenido": "".join(respuesta)},
                ])
            yield _linea({"tipo": "fin", "segundos": round(time.monotonic() - inicio, 1),
                          "mitre": mitre.verificar("".join(respuesta))})
        except ErrorOllama as error:
            yield _linea({"tipo": "error", "mensaje": str(error)})
        except httpx.HTTPError as error:
            log.warning("Fallo de conexión con Ollama: %r", error)
            yield _linea({"tipo": "error", "mensaje": "Se perdió la conexión con Ollama. ¿Sigue en marcha?"})

    return StreamingResponse(generar(), media_type="application/x-ndjson")
