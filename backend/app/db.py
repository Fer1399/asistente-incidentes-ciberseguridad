"""Base de datos SQLite: registro de documentos y ajustes internos.

Los vectores viven en ChromaDB (ver vectores.py); aquí se guarda el estado de cada
documento (procesando, indexado, error...) y datos que deben sobrevivir a reinicios.
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import settings

ESQUEMA = """
CREATE TABLE IF NOT EXISTS documentos (
    id                TEXT PRIMARY KEY,
    nombre            TEXT NOT NULL,
    sha256            TEXT NOT NULL UNIQUE,
    origen            TEXT NOT NULL,              -- 'usuario' o 'incluido'
    ruta              TEXT NOT NULL,
    estado            TEXT NOT NULL,              -- pendiente, procesando, indexado, error
    progreso          INTEGER NOT NULL DEFAULT 0, -- 0-100
    mensaje           TEXT,
    paginas           INTEGER NOT NULL DEFAULT 0,
    paginas_ocr       INTEGER NOT NULL DEFAULT 0,
    fragmentos        INTEGER NOT NULL DEFAULT 0,
    modelo_embeddings TEXT,
    creado            TEXT NOT NULL,
    actualizado       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

-- Fichas de incidente -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidentes (
    id               TEXT PRIMARY KEY,              -- INC-20261110-A3F9
    titulo           TEXT NOT NULL,
    tipo             TEXT,
    severidad        TEXT,                          -- Baja, Media, Alta, Crítica
    estado           TEXT NOT NULL DEFAULT 'abierto',   -- abierto, cerrado
    descripcion      TEXT,
    datos_personales INTEGER NOT NULL DEFAULT 0,    -- activa el plazo de 72 h de la AEPD
    detectado        TEXT NOT NULL,                 -- cuándo se tuvo conocimiento
    creado           TEXT NOT NULL,
    actualizado      TEXT NOT NULL,
    cerrado          TEXT,
    notas_cierre     TEXT,                          -- lo que se hizo realmente (revisado)
    lecciones        TEXT,
    en_memoria       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pasos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    incidente_id TEXT NOT NULL REFERENCES incidentes(id) ON DELETE CASCADE,
    fase         TEXT NOT NULL,
    texto        TEXT NOT NULL,
    orden        INTEGER NOT NULL,
    hecho        INTEGER NOT NULL DEFAULT 0,
    hecho_en     TEXT,
    origen       TEXT NOT NULL DEFAULT 'asistente',  -- asistente o usuario
    nota         TEXT
);

CREATE TABLE IF NOT EXISTS eventos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    incidente_id TEXT NOT NULL REFERENCES incidentes(id) ON DELETE CASCADE,
    fecha        TEXT NOT NULL,
    tipo         TEXT NOT NULL,
    texto        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mensajes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    incidente_id TEXT NOT NULL REFERENCES incidentes(id) ON DELETE CASCADE,
    fecha        TEXT NOT NULL,
    rol          TEXT NOT NULL,
    contenido    TEXT NOT NULL,
    adjuntos     TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS incidente_adjuntos (
    incidente_id TEXT NOT NULL REFERENCES incidentes(id) ON DELETE CASCADE,
    adjunto_id   TEXT NOT NULL,
    PRIMARY KEY (incidente_id, adjunto_id)
);
"""

CAMPOS_ACTUALIZABLES = {
    "nombre", "sha256", "ruta", "estado", "progreso", "mensaje", "paginas",
    "paginas_ocr", "fragmentos", "modelo_embeddings",
}


def ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def conexion():
    con = sqlite3.connect(settings.db_path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with conexion() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(ESQUEMA)


# --- Documentos -------------------------------------------------------------

def crear_documento(nombre: str, sha256: str, origen: str, ruta: str) -> dict:
    momento = ahora()
    doc = {
        "id": uuid.uuid4().hex[:12],
        "nombre": nombre,
        "sha256": sha256,
        "origen": origen,
        "ruta": ruta,
        "estado": "pendiente",
        "creado": momento,
        "actualizado": momento,
    }
    with conexion() as con:
        con.execute(
            "INSERT INTO documentos (id, nombre, sha256, origen, ruta, estado, creado, actualizado) "
            "VALUES (:id, :nombre, :sha256, :origen, :ruta, :estado, :creado, :actualizado)",
            doc,
        )
    return obtener_documento(doc["id"])


def actualizar_documento(doc_id: str, **campos) -> None:
    desconocidos = set(campos) - CAMPOS_ACTUALIZABLES
    if desconocidos:
        raise ValueError(f"Campos no permitidos: {desconocidos}")
    campos["actualizado"] = ahora()
    asignaciones = ", ".join(f"{campo} = :{campo}" for campo in campos)
    with conexion() as con:
        con.execute(f"UPDATE documentos SET {asignaciones} WHERE id = :id", {**campos, "id": doc_id})


def obtener_documento(doc_id: str) -> dict | None:
    with conexion() as con:
        fila = con.execute("SELECT * FROM documentos WHERE id = ?", (doc_id,)).fetchone()
    return dict(fila) if fila else None


def buscar_documento(*, sha256: str | None = None, ruta: str | None = None) -> dict | None:
    columna, valor = ("sha256", sha256) if sha256 else ("ruta", ruta)
    with conexion() as con:
        fila = con.execute(f"SELECT * FROM documentos WHERE {columna} = ?", (valor,)).fetchone()
    return dict(fila) if fila else None


def listar_documentos() -> list[dict]:
    with conexion() as con:
        filas = con.execute("SELECT * FROM documentos ORDER BY creado DESC").fetchall()
    return [dict(f) for f in filas]


def borrar_documento(doc_id: str) -> None:
    with conexion() as con:
        con.execute("DELETE FROM documentos WHERE id = ?", (doc_id,))


# --- Ajustes ----------------------------------------------------------------

def leer_ajuste(clave: str) -> str | None:
    with conexion() as con:
        fila = con.execute("SELECT valor FROM ajustes WHERE clave = ?", (clave,)).fetchone()
    return fila["valor"] if fila else None


def guardar_ajuste(clave: str, valor: str) -> None:
    with conexion() as con:
        con.execute(
            "INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, valor),
        )
