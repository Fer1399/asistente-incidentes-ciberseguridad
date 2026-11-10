"""Exportar e importar la copia de seguridad."""

import os
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from .. import copias

router = APIRouter(prefix="/copia", tags=["copia de seguridad"])


def _temporal() -> Path:
    descriptor, ruta = tempfile.mkstemp(suffix=".zip")
    os.close(descriptor)  # en Windows un fichero abierto no se puede borrar
    return Path(ruta)


@router.get("")
async def exportar(tareas: BackgroundTasks) -> FileResponse:
    """Descarga un .zip con incidentes, documentos subidos y adjuntos analizados."""
    temporal = _temporal()
    await run_in_threadpool(copias.exportar, temporal)
    tareas.add_task(temporal.unlink, missing_ok=True)
    return FileResponse(temporal, media_type="application/zip", filename=copias.nombre_copia())


@router.post("")
async def importar(fichero: UploadFile, request: Request) -> dict:
    """Fusiona una copia con los datos de este equipo (no borra nada de lo que ya hay)."""
    if not (fichero.filename or "").lower().endswith(".zip"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "La copia debe ser un fichero .zip")
    temporal = _temporal()
    try:
        with temporal.open("wb") as destino:
            while bloque := await fichero.read(1024 * 1024):
                destino.write(bloque)
        estado = request.app.state
        return await run_in_threadpool(copias.importar, temporal, estado.almacen, estado.cola)
    except zipfile.BadZipFile as error:
        raise HTTPException(422, "El fichero no es un .zip válido") from error
    except copias.CopiaNoValida as error:
        raise HTTPException(422, str(error)) from error
    finally:
        temporal.unlink(missing_ok=True)
