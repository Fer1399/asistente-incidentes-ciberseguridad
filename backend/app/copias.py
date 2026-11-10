"""Copia de seguridad: guardar los datos o llevarlos a otro equipo.

Exportar: un .zip con la base de datos, los documentos subidos y los adjuntos analizados.
Los vectores NO se incluyen: se regeneran en el equipo de destino (pesan mucho y dependen
de la versión de ChromaDB). Por eso los dos equipos deben usar el mismo EMBED_MODEL.

Importar: FUSIONA la copia con los datos actuales, no los sustituye:
- documentos que no existan (por contenido) → se añaden y se indexan;
- incidentes nuevos → se añaden; si existen en los dos lados, gana la versión más reciente;
- adjuntos que falten → se copian.
Antes de importar se guarda automáticamente una copia del estado actual en data/copias.
"""

import json
import shutil
import socket
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import __version__, db
from .config import settings

FORMATO = 1
MAX_IMPORTAR_MB = 2048
TABLAS_INCIDENTE = ("pasos", "eventos", "mensajes", "incidente_adjuntos")


class CopiaNoValida(ValueError):
    pass


def nombre_copia() -> str:
    return f"asistente-copia-{datetime.now():%Y%m%d-%H%M}.zip"


def exportar(destino: Path) -> dict:
    """Crea el .zip en `destino` y devuelve el manifiesto."""
    db.inicializar()
    with db.conexion() as con:
        resumen = {
            "documentos": con.execute("SELECT COUNT(*) FROM documentos WHERE origen = 'usuario'").fetchone()[0],
            "incidentes": con.execute("SELECT COUNT(*) FROM incidentes").fetchone()[0],
        }
    manifiesto = {
        "aplicacion": "asistente-incidentes-ciberseguridad",
        "formato": FORMATO,
        "version": __version__,
        "creado": db.ahora(),
        "equipo": socket.gethostname(),
        "modelo_embeddings": settings.embed_model,
        **resumen,
    }
    with tempfile.TemporaryDirectory() as tmp:
        copia_db = Path(tmp) / "asistente.db"
        # Copia coherente aunque el backend esté escribiendo en ese momento
        origen = sqlite3.connect(settings.db_path)
        copia = sqlite3.connect(copia_db)
        origen.backup(copia)
        copia.close()
        origen.close()

        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifiesto.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
            zf.write(copia_db, "asistente.db")
            for carpeta in ("documentos", "adjuntos"):
                raiz = settings.data_dir / carpeta
                if raiz.exists():
                    for fichero in raiz.rglob("*"):
                        if fichero.is_file() and not fichero.name.startswith("_tmp_"):
                            zf.write(fichero, f"{carpeta}/{fichero.relative_to(raiz).as_posix()}")
    return manifiesto


def _validar_zip(zf: zipfile.ZipFile) -> dict:
    nombres = zf.namelist()
    if "manifiesto.json" not in nombres or "asistente.db" not in nombres:
        raise CopiaNoValida("No es una copia del Asistente de Incidentes (falta manifiesto.json o asistente.db)")
    for nombre in nombres:
        ruta = PurePosixPath(nombre)
        if ruta.is_absolute() or ".." in ruta.parts or "\\" in nombre:
            raise CopiaNoValida(f"Ruta no permitida dentro de la copia: {nombre}")
        if not (nombre in {"manifiesto.json", "asistente.db"} or ruta.parts[0] in {"documentos", "adjuntos"}):
            raise CopiaNoValida(f"Fichero inesperado en la copia: {nombre}")
    total = sum(i.file_size for i in zf.infolist())
    if total > MAX_IMPORTAR_MB * 1024 * 1024:
        raise CopiaNoValida(f"La copia descomprimida supera {MAX_IMPORTAR_MB} MB")
    manifiesto = json.loads(zf.read("manifiesto.json"))
    if manifiesto.get("aplicacion") != "asistente-incidentes-ciberseguridad" or manifiesto.get("formato") != FORMATO:
        raise CopiaNoValida("Formato de copia no reconocido")
    return manifiesto


def importar(origen_zip: Path, almacen, cola) -> dict:
    """Fusiona la copia con los datos actuales y devuelve un resumen de lo importado."""
    db.inicializar()
    with zipfile.ZipFile(origen_zip) as zf:
        manifiesto = _validar_zip(zf)
        avisos = []
        if manifiesto.get("modelo_embeddings") != settings.embed_model:
            avisos.append(
                f"La copia se hizo con el modelo de embeddings {manifiesto.get('modelo_embeddings')} y este equipo "
                f"usa {settings.embed_model}. Lo importado se indexará con el modelo de este equipo."
            )

        # Copia de seguridad automática del estado actual
        settings.copias_dir.mkdir(parents=True, exist_ok=True)
        previa = settings.copias_dir / f"antes-de-importar-{datetime.now():%Y%m%d-%H%M%S}.zip"
        exportar(previa)

        with tempfile.TemporaryDirectory() as tmp:
            zf.extractall(tmp)
            raiz = Path(tmp)
            resumen = {"documentos_nuevos": 0, "incidentes_nuevos": 0, "incidentes_actualizados": 0,
                       "incidentes_sin_cambios": 0, "adjuntos_nuevos": 0}

            # Adjuntos analizados (carpetas data/adjuntos/<id>)
            if (raiz / "adjuntos").exists():
                for carpeta in (raiz / "adjuntos").iterdir():
                    destino = settings.adjuntos_dir / carpeta.name
                    if carpeta.is_dir() and carpeta.name.isalnum() and not destino.exists():
                        shutil.copytree(carpeta, destino)
                        resumen["adjuntos_nuevos"] += 1

            externa = sqlite3.connect(raiz / "asistente.db")
            externa.row_factory = sqlite3.Row
            try:
                # Documentos del usuario (los incluidos se indexan desde knowledge/ en cada equipo)
                for doc in externa.execute("SELECT * FROM documentos WHERE origen = 'usuario'"):
                    if db.buscar_documento(sha256=doc["sha256"]):
                        continue
                    extension = Path(doc["ruta"].replace("\\", "/")).suffix.lower()
                    fichero = raiz / "documentos" / f"{doc['id']}{extension}"
                    if not fichero.exists():
                        continue
                    settings.documentos_dir.mkdir(parents=True, exist_ok=True)
                    nuevo = db.crear_documento(doc["nombre"], doc["sha256"], "usuario", "")
                    ruta_final = settings.documentos_dir / f"{nuevo['id']}{extension}"
                    shutil.copy2(fichero, ruta_final)
                    db.actualizar_documento(nuevo["id"], ruta=str(ruta_final))
                    cola.encolar(nuevo["id"])
                    resumen["documentos_nuevos"] += 1

                # Incidentes: gana la versión más reciente
                a_memorizar = []
                with db.conexion() as con:
                    # Solo se copian columnas que existen aquí: los nombres de columna del
                    # fichero importado nunca se usan sin validar (evita inyección SQL)
                    columnas_validas = {
                        tabla: {fila["name"] for fila in con.execute(f"PRAGMA table_info({tabla})")}
                        for tabla in ("incidentes", *TABLAS_INCIDENTE)
                    }
                    for inc in externa.execute("SELECT * FROM incidentes"):
                        local = con.execute("SELECT actualizado FROM incidentes WHERE id = ?", (inc["id"],)).fetchone()
                        if local and local["actualizado"] >= inc["actualizado"]:
                            resumen["incidentes_sin_cambios"] += 1
                            continue
                        if local:
                            con.execute("DELETE FROM incidentes WHERE id = ?", (inc["id"],))
                            almacen.borrar_documento(inc["id"])
                            resumen["incidentes_actualizados"] += 1
                        else:
                            resumen["incidentes_nuevos"] += 1
                        columnas = [c for c in inc.keys() if c in columnas_validas["incidentes"]]
                        con.execute(
                            f"INSERT INTO incidentes ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})",
                            tuple(inc[c] for c in columnas),
                        )
                        for tabla in TABLAS_INCIDENTE:
                            for fila in externa.execute(f"SELECT * FROM {tabla} WHERE incidente_id = ?", (inc["id"],)):
                                cols = [c for c in fila.keys() if c != "id" and c in columnas_validas[tabla]]
                                con.execute(
                                    f"INSERT OR IGNORE INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                    tuple(fila[c] for c in cols),
                                )
                        if inc["estado"] == "cerrado" and inc["en_memoria"]:
                            a_memorizar.append(inc["id"])
                # Se encola después de guardar, para que la memoria lea los datos ya importados
                for incidente_id in a_memorizar:
                    cola.encolar_incidente(incidente_id)
            finally:
                externa.close()

    return {"manifiesto": manifiesto, "resumen": resumen, "avisos": avisos, "copia_previa": previa.name}
