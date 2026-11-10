"""Ingesta de documentos: extraer → trocear → vectorizar → guardar.

Los documentos se procesan de uno en uno en un hilo aparte, para no bloquear la API
ni saturar Ollama. El progreso se guarda en SQLite y la extensión lo consulta.
"""

import hashlib
import logging
import queue
import threading
from pathlib import Path

from . import db, incidentes
from .config import settings
from .embeddings import Embedder
from .extraccion import EXTENSIONES, Pagina, extraer
from .troceado import trocear
from .vectores import AlmacenVectorial

log = logging.getLogger("asistente.ingesta")

CLAVE_MODELO = "modelo_embeddings_indexado"


def sha256_fichero(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def procesar_documento(doc_id: str, almacen: AlmacenVectorial, embedder: Embedder) -> None:
    doc = db.obtener_documento(doc_id)
    if not doc:
        return

    def estado(**campos) -> None:
        db.actualizar_documento(doc_id, **campos)

    try:
        estado(estado="procesando", progreso=0, mensaje="Leyendo el documento")
        paginas = extraer(
            Path(doc["ruta"]),
            progreso=lambda hecho, total: estado(progreso=int(hecho / total * 40)),
        )
        fragmentos = trocear(paginas, settings.tamano_fragmento, settings.solape_fragmento)
        if not fragmentos:
            raise ValueError(
                "No se ha encontrado texto. Si es un PDF escaneado, instala Tesseract para leerlo con OCR."
            )

        estado(progreso=40, mensaje=f"Generando vectores de {len(fragmentos)} fragmentos")
        vectores = embedder.vectorizar(
            [f.texto for f in fragmentos],
            progreso=lambda hecho, total: estado(progreso=40 + int(hecho / total * 55)),
        )

        almacen.borrar_documento(doc_id)  # por si se está reindexando
        almacen.anadir(
            ids=[f"{doc_id}-{f.indice}" for f in fragmentos],
            textos=[f.texto for f in fragmentos],
            vectores=vectores,
            metadatos=[
                {
                    "doc_id": doc_id,
                    "documento": doc["nombre"],
                    "origen": doc["origen"],
                    "tipo": "documento",
                    "pagina": f.pagina,
                    "seccion": f.seccion,
                    "fragmento": f.indice,
                }
                for f in fragmentos
            ],
        )
        estado(
            estado="indexado",
            progreso=100,
            mensaje=None,
            paginas=sum(1 for p in paginas if p.numero is not None),
            paginas_ocr=sum(1 for p in paginas if p.ocr),
            fragmentos=len(fragmentos),
            modelo_embeddings=embedder.modelo,
        )
        db.guardar_ajuste(CLAVE_MODELO, embedder.modelo)
        log.info("Indexado %s (%d fragmentos)", doc["nombre"], len(fragmentos))
    except Exception as error:  # el error se muestra en la extensión
        log.exception("Error indexando %s", doc["nombre"])
        estado(estado="error", mensaje=str(error))


def memorizar_incidente(incidente_id: str, almacen: AlmacenVectorial, embedder: Embedder) -> None:
    """Guarda (o retira) un incidente cerrado en la memoria del asistente."""
    datos = incidentes.detalle(incidente_id)
    if not datos or datos["estado"] != "cerrado" or not datos["en_memoria"]:
        almacen.borrar_documento(incidente_id)
        return
    nombre = f"{incidente_id} · {datos['titulo']}"
    fragmentos = trocear(
        [Pagina(None, incidentes.texto_memoria(datos), seccion=f"Incidente anterior {nombre}")],
        settings.tamano_fragmento, settings.solape_fragmento,
    )
    try:
        vectores = embedder.vectorizar([f.texto for f in fragmentos])
    except Exception:
        log.exception("No se pudo guardar en memoria el incidente %s; se reintentará al arrancar", incidente_id)
        return
    almacen.borrar_documento(incidente_id)
    almacen.anadir(
        ids=[f"{incidente_id}-{f.indice}" for f in fragmentos],
        textos=[f.texto for f in fragmentos],
        vectores=vectores,
        metadatos=[{"doc_id": incidente_id, "documento": nombre, "origen": "incidente", "tipo": "incidente",
                    "seccion": f.seccion, "fragmento": f.indice, "severidad": datos.get("severidad")}
                   for f in fragmentos],
    )
    log.info("Incidente %s guardado en memoria (%d fragmentos)", incidente_id, len(fragmentos))


class ColaIngesta:
    """Un único hilo que procesa, en orden de llegada, documentos e incidentes a memorizar."""

    def __init__(self, almacen: AlmacenVectorial, embedder: Embedder) -> None:
        self.almacen = almacen
        self.embedder = embedder
        self._cola: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self._hilo = threading.Thread(target=self._trabajar, name="ingesta", daemon=True)

    def iniciar(self) -> None:
        self._hilo.start()

    def encolar(self, doc_id: str) -> None:
        db.actualizar_documento(doc_id, estado="pendiente", progreso=0, mensaje="En cola")
        self._cola.put(("documento", doc_id))

    def encolar_incidente(self, incidente_id: str) -> None:
        self._cola.put(("incidente", incidente_id))

    def esperar(self) -> None:
        """Bloquea hasta que la cola se vacía (se usa en las pruebas)."""
        self._cola.join()

    def detener(self) -> None:
        self._cola.put(None)

    def _trabajar(self) -> None:
        while True:
            tarea = self._cola.get()
            try:
                if tarea is None:
                    return
                tipo, identificador = tarea
                if tipo == "documento":
                    procesar_documento(identificador, self.almacen, self.embedder)
                else:
                    memorizar_incidente(identificador, self.almacen, self.embedder)
            except Exception:
                log.exception("Error en la tarea %s", tarea)
            finally:
                self._cola.task_done()


def registrar_incluidos(cola: ColaIngesta) -> int:
    """Indexa los documentos de knowledge/ (playbooks incluidos en el repositorio).

    Se ejecuta al arrancar: añade los nuevos y reindexa los que han cambiado.
    """
    carpeta = settings.knowledge_dir
    if not carpeta.exists():
        return 0
    nuevos = 0
    for ruta in sorted(carpeta.rglob("*")):
        if ruta.suffix.lower() not in EXTENSIONES or ruta.name.lower() == "readme.md":
            continue
        sha = sha256_fichero(ruta)
        existente = db.buscar_documento(ruta=str(ruta))
        if existente and existente["sha256"] == sha:
            continue
        if existente:
            db.actualizar_documento(existente["id"], sha256=sha)
            cola.encolar(existente["id"])
        else:
            if db.buscar_documento(sha256=sha):
                continue  # mismo contenido ya subido por el usuario
            doc = db.crear_documento(ruta.name, sha, "incluido", str(ruta))
            cola.encolar(doc["id"])
        nuevos += 1
    return nuevos


def reanudar_pendientes(cola: ColaIngesta) -> None:
    """Vuelve a encolar lo que quedó a medias o falló (p. ej. Ollama estaba apagado)."""
    for doc in db.listar_documentos():
        if doc["estado"] != "indexado":
            cola.encolar(doc["id"])
    # Incidentes marcados para memoria cuyos vectores no están (fallo previo o copia importada)
    for incidente in incidentes.listar(estado="cerrado"):
        if incidente["en_memoria"] and not cola.almacen.contar_documento(incidente["id"]):
            cola.encolar_incidente(incidente["id"])
