"""Búsqueda en la base de conocimiento (la pestaña "Probar una búsqueda")."""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..config import settings
from ..embeddings import OllamaNoDisponible

router = APIRouter(tags=["búsqueda"])


class Consulta(BaseModel):
    consulta: str = Field(min_length=2, max_length=4000)
    k: int | None = Field(default=None, ge=1, le=20)


@router.post("/buscar")
def buscar(consulta: Consulta, request: Request) -> dict:
    estado = request.app.state
    try:
        vector = estado.embedder.vectorizar_uno(consulta.consulta)
    except OllamaNoDisponible as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    resultados = estado.almacen.buscar(vector, consulta.k or settings.fragmentos_por_consulta)
    return {"consulta": consulta.consulta, "resultados": resultados}
