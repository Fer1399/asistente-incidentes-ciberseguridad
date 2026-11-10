"""Rutas de las fichas de incidente."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import incidentes, informe
from ..config import settings
from ..embeddings import OllamaNoDisponible

router = APIRouter(prefix="/incidentes", tags=["incidentes"])

Fase = Literal["inmediatas", "evidencias", "contencion", "analisis", "erradicacion", "notificacion", "lecciones", "otros"]
Severidad = Literal["Baja", "Media", "Alta", "Crítica"]


class MensajeFicha(BaseModel):
    rol: Literal["usuario", "asistente"]
    contenido: str = Field(min_length=1, max_length=60000)
    adjuntos: list[str] = Field(default_factory=list)


class NuevaFicha(BaseModel):
    titulo: str | None = Field(default=None, max_length=150)
    tipo: str | None = Field(default=None, max_length=80)
    severidad: Severidad | None = None
    descripcion: str | None = Field(default=None, max_length=10000)
    datos_personales: bool = False
    respuesta_asistente: str | None = Field(
        default=None, max_length=60000,
        description="Respuesta del asistente de la que se sacan tipo, severidad y pasos")
    mensajes: list[MensajeFicha] = Field(default_factory=list, max_length=200)
    adjuntos: list[str] = Field(default_factory=list)


class CambiosFicha(BaseModel):
    titulo: str | None = Field(default=None, max_length=150)
    tipo: str | None = Field(default=None, max_length=80)
    severidad: Severidad | None = None
    descripcion: str | None = Field(default=None, max_length=10000)
    datos_personales: bool | None = None
    detectado: str | None = Field(default=None, description="Fecha ISO en que se tuvo conocimiento")


class NuevoPaso(BaseModel):
    fase: Fase = "otros"
    texto: str = Field(min_length=2, max_length=1000)


class CambiosPaso(BaseModel):
    hecho: bool | None = None
    texto: str | None = Field(default=None, min_length=2, max_length=1000)
    nota: str | None = Field(default=None, max_length=2000)


class Nota(BaseModel):
    texto: str = Field(min_length=1, max_length=5000)


class Cierre(BaseModel):
    notas_cierre: str = Field(
        min_length=10, max_length=20000,
        description="Lo que se hizo realmente. Es lo que el asistente recordará: obligatorio")
    lecciones: str | None = Field(default=None, max_length=10000)
    guardar_en_memoria: bool = True


class Similares(BaseModel):
    texto: str = Field(min_length=3, max_length=20000)
    k: int = Field(default=3, ge=1, le=10)


def _existe(incidente_id: str) -> dict:
    incidente = incidentes.obtener(incidente_id)
    if not incidente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Incidente no encontrado")
    return incidente


def _abierto(incidente_id: str) -> dict:
    incidente = _existe(incidente_id)
    if incidente["estado"] != "abierto":
        raise HTTPException(status.HTTP_409_CONFLICT, "El incidente está cerrado; reábrelo para modificarlo")
    return incidente


@router.get("")
def listar(estado: Literal["abierto", "cerrado"] | None = None, q: str | None = None) -> list[dict]:
    return incidentes.listar(estado, q)


@router.get("/resumen")
def resumen() -> dict:
    """Cifras para la cabecera de la pestaña Incidentes."""
    todos = incidentes.listar()
    cerrados = [i for i in todos if i["estado"] == "cerrado" and i["cerrado"]]
    horas = [(datetime.fromisoformat(i["cerrado"]) - datetime.fromisoformat(i["detectado"])).total_seconds() / 3600
             for i in cerrados]
    return {
        "abiertos": sum(1 for i in todos if i["estado"] == "abierto"),
        "cerrados": len(cerrados),
        "en_memoria": sum(1 for i in todos if i["en_memoria"]),
        "resolucion_media_horas": round(sum(horas) / len(horas), 1) if horas else None,
        "plazos_aepd_activos": sum(1 for i in todos if i["estado"] == "abierto" and i["plazo_aepd"]),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def crear(ficha: NuevaFicha) -> dict:
    return incidentes.crear(**ficha.model_dump())


@router.post("/similares")
async def similares(consulta: Similares, request: Request) -> list[dict]:
    """Incidentes cerrados parecidos a un texto (para el aviso "ya ha pasado algo parecido")."""
    estado = request.app.state
    try:
        vector = await run_in_threadpool(estado.embedder.vectorizar_uno, consulta.texto)
    except OllamaNoDisponible as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    return await run_in_threadpool(buscar_similares, estado.almacen, vector, consulta.k)


def buscar_similares(almacen, vector: list[float], k: int = 3) -> list[dict]:
    """Un resultado por incidente (el fragmento más parecido), por encima del umbral."""
    resultados = almacen.buscar(vector, k * 4, filtro={"tipo": "incidente"})
    vistos, salida = set(), []
    for r in resultados:
        if r["doc_id"] in vistos or r["similitud"] < settings.similitud_incidente:
            continue
        vistos.add(r["doc_id"])
        incidente = incidentes.obtener(r["doc_id"])
        if incidente:
            salida.append({
                "id": incidente["id"], "titulo": incidente["titulo"], "tipo": incidente["tipo"],
                "severidad": incidente["severidad"], "cerrado": incidente["cerrado"],
                "similitud": r["similitud"], "texto": r["texto"],
            })
        if len(salida) == k:
            break
    return salida


@router.get("/{incidente_id}")
def ver(incidente_id: str) -> dict:
    _existe(incidente_id)
    return incidentes.detalle(incidente_id)


@router.patch("/{incidente_id}")
def modificar(incidente_id: str, cambios: CambiosFicha) -> dict:
    _abierto(incidente_id)
    incidentes.actualizar(incidente_id, **cambios.model_dump(exclude_none=True))
    return incidentes.detalle(incidente_id)


@router.delete("/{incidente_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(incidente_id: str, request: Request) -> None:
    _existe(incidente_id)
    request.app.state.almacen.borrar_documento(incidente_id)
    incidentes.borrar(incidente_id)


@router.post("/{incidente_id}/pasos", status_code=status.HTTP_201_CREATED)
def nuevo_paso(incidente_id: str, paso: NuevoPaso) -> dict:
    _abierto(incidente_id)
    return incidentes.anadir_paso(incidente_id, paso.fase, paso.texto)


@router.patch("/{incidente_id}/pasos/{paso_id}")
def modificar_paso(incidente_id: str, paso_id: int, cambios: CambiosPaso) -> dict:
    _abierto(incidente_id)
    paso = incidentes.actualizar_paso(incidente_id, paso_id, **cambios.model_dump())
    if not paso:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paso no encontrado")
    return paso


@router.delete("/{incidente_id}/pasos/{paso_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_paso(incidente_id: str, paso_id: int) -> None:
    _abierto(incidente_id)
    if not incidentes.borrar_paso(incidente_id, paso_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paso no encontrado")


@router.post("/{incidente_id}/notas", status_code=status.HTTP_201_CREATED)
def nueva_nota(incidente_id: str, nota: Nota) -> dict:
    _abierto(incidente_id)
    incidentes.anadir_nota(incidente_id, nota.texto)
    return incidentes.detalle(incidente_id)


@router.delete("/{incidente_id}/mensajes/{mensaje_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar_mensaje(incidente_id: str, mensaje_id: int) -> None:
    """Quita un mensaje de la conversación guardada (no aparecerá en el informe)."""
    _abierto(incidente_id)
    if not incidentes.borrar_mensaje(incidente_id, mensaje_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mensaje no encontrado")


@router.post("/{incidente_id}/adjuntos/{adjunto_id}", status_code=status.HTTP_201_CREATED)
def vincular(incidente_id: str, adjunto_id: str) -> dict:
    _abierto(incidente_id)
    if not incidentes.vincular_adjunto(incidente_id, adjunto_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjunto no encontrado")
    return incidentes.detalle(incidente_id)


@router.post("/{incidente_id}/cerrar")
def cerrar(incidente_id: str, cierre: Cierre, request: Request) -> dict:
    """Cierra la ficha. Con guardar_en_memoria, pasa a la memoria del asistente."""
    _abierto(incidente_id)
    incidentes.cerrar(incidente_id, cierre.notas_cierre, cierre.lecciones, cierre.guardar_en_memoria)
    if cierre.guardar_en_memoria:
        request.app.state.cola.encolar_incidente(incidente_id)
    return incidentes.detalle(incidente_id)


@router.post("/{incidente_id}/reabrir")
def reabrir(incidente_id: str, request: Request) -> dict:
    incidente = _existe(incidente_id)
    if incidente["estado"] != "cerrado":
        raise HTTPException(status.HTTP_409_CONFLICT, "El incidente ya está abierto")
    request.app.state.almacen.borrar_documento(incidente_id)
    incidentes.reabrir(incidente_id)
    return incidentes.detalle(incidente_id)


@router.get("/{incidente_id}/informe")
def descargar_informe(incidente_id: str, formato: Literal["md", "pdf"] = "md", anexo: bool = True) -> Response:
    """Informe del incidente. Con anexo=false no incluye las consultas al asistente."""
    _existe(incidente_id)
    datos = incidentes.detalle(incidente_id)
    nombre = f"informe-{incidente_id}"
    if formato == "pdf":
        contenido, tipo = informe.pdf(datos, anexo), "application/pdf"
    else:
        contenido, tipo = informe.markdown(datos, anexo).encode("utf-8"), "text/markdown; charset=utf-8"
    return Response(contenido, media_type=tipo,
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.{formato}"'})
