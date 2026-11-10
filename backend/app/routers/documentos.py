"""Rutas de la base de conocimiento: subir, listar, reindexar y borrar documentos."""

import hashlib
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, status

from .. import db
from ..config import settings
from ..extraccion import EXTENSIONES

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _publico(doc: dict) -> dict:
    """Lo que ve la extensión (sin rutas internas)."""
    return {k: v for k, v in doc.items() if k not in {"ruta", "sha256"}}


def _documento_o_404(doc_id: str) -> dict:
    doc = db.obtener_documento(doc_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    return doc


@router.get("")
def listar() -> list[dict]:
    return [_publico(d) for d in db.listar_documentos()]


@router.get("/{doc_id}")
def detalle(doc_id: str) -> dict:
    return _publico(_documento_o_404(doc_id))


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def subir(fichero: UploadFile, request: Request) -> dict:
    nombre = Path(fichero.filename or "documento").name
    extension = Path(nombre).suffix.lower()
    if extension not in EXTENSIONES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Formato no admitido ({extension or 'sin extensión'}). Usa: {', '.join(sorted(EXTENSIONES))}",
        )

    settings.documentos_dir.mkdir(parents=True, exist_ok=True)
    limite = settings.max_subida_mb * 1024 * 1024
    h = hashlib.sha256()
    tamano = 0
    with tempfile.NamedTemporaryFile(dir=settings.documentos_dir, suffix=extension, delete=False) as tmp:
        ruta_tmp = Path(tmp.name)
        while bloque := fichero.file.read(1024 * 1024):
            tamano += len(bloque)
            if tamano > limite:
                tmp.close()
                ruta_tmp.unlink(missing_ok=True)
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    f"El documento supera {settings.max_subida_mb} MB",
                )
            h.update(bloque)
            tmp.write(bloque)

    sha = h.hexdigest()
    existente = db.buscar_documento(sha256=sha)
    if existente:
        ruta_tmp.unlink(missing_ok=True)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"mensaje": f"Este documento ya está en la base como '{existente['nombre']}'",
             "documento": _publico(existente)},
        )

    doc = db.crear_documento(nombre, sha, "usuario", str(ruta_tmp))
    ruta_final = settings.documentos_dir / f"{doc['id']}{extension}"
    shutil.move(ruta_tmp, ruta_final)
    db.actualizar_documento(doc["id"], ruta=str(ruta_final))

    request.app.state.cola.encolar(doc["id"])
    return _publico(db.obtener_documento(doc["id"]))


@router.post("/{doc_id}/reindexar", status_code=status.HTTP_202_ACCEPTED)
def reindexar(doc_id: str, request: Request) -> dict:
    _documento_o_404(doc_id)
    request.app.state.cola.encolar(doc_id)
    return _publico(db.obtener_documento(doc_id))


@router.post("/reindexar-todo", status_code=status.HTTP_202_ACCEPTED)
def reindexar_todo(request: Request) -> dict:
    """Necesario si se cambia el modelo de embeddings."""
    documentos = db.listar_documentos()
    for doc in documentos:
        request.app.state.cola.encolar(doc["id"])
    return {"encolados": len(documentos)}


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(doc_id: str, request: Request) -> None:
    doc = _documento_o_404(doc_id)
    if doc["origen"] == "incluido":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Es un playbook incluido en el proyecto; para quitarlo, bórralo de la carpeta knowledge/",
        )
    if doc["estado"] == "procesando":
        raise HTTPException(status.HTTP_409_CONFLICT, "Espera a que termine de procesarse")
    request.app.state.almacen.borrar_documento(doc_id)
    Path(doc["ruta"]).unlink(missing_ok=True)
    db.borrar_documento(doc_id)
