"""Adjuntos de un incidente (correos, logs, capturas) y extracción de IOCs."""

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from .. import adjuntos, iocs
from ..config import settings

router = APIRouter(tags=["adjuntos"])


@router.post("/adjuntos")
async def subir_adjunto(fichero: UploadFile, request: Request, vision: bool | None = None) -> dict:
    """Analiza un adjunto y devuelve su resumen, alertas e IOCs.

    `vision`: usar el modelo de visión con las capturas (por defecto, VISION_ACTIVA de .env).
    """
    nombre = fichero.filename or "adjunto"
    try:
        adjuntos.tipo_de(nombre)
    except adjuntos.AdjuntoNoValido as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from error

    limite = settings.max_adjunto_mb * 1024 * 1024
    datos = await fichero.read(limite + 1)
    if len(datos) > limite:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"El adjunto supera {settings.max_adjunto_mb} MB")
    if not datos:
        raise HTTPException(422, "El fichero está vacío")

    try:
        resultado = await adjuntos.procesar(nombre, datos, request.app.state.ollama, vision)
    except adjuntos.AdjuntoNoValido as error:
        raise HTTPException(422, str(error)) from error
    return adjuntos.resumen_publico(resultado)


@router.get("/adjuntos/{adjunto_id}")
def ver_adjunto(adjunto_id: str) -> dict:
    adjunto = adjuntos.cargar(adjunto_id)
    if not adjunto:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
    return adjuntos.resumen_publico(adjunto)


class Texto(BaseModel):
    texto: str = Field(max_length=500_000)


@router.post("/iocs")
def extraer_iocs(entrada: Texto) -> dict:
    """Extrae los IOCs de un texto pegado (logs, alertas, un correo copiado...)."""
    resultado = iocs.extraer(entrada.texto)
    return {"iocs": resultado, "total": iocs.contar(resultado)}
