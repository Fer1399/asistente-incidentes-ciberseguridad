"""Extracción de texto de documentos de la base de conocimiento.

- PDF: texto de cada página con PyMuPDF. Si una página casi no tiene texto
  (PDF escaneado), se rasteriza y se lee con OCR.
- Markdown y texto plano: se leen tal cual.
"""

import io
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import ocr

EXTENSIONES = {".pdf", ".md", ".txt"}
MIN_CARACTERES_PAGINA = 40  # por debajo, se considera página escaneada
DPI_OCR = 300


@dataclass
class Pagina:
    numero: int | None  # None en documentos sin páginas (Markdown, texto)
    texto: str
    ocr: bool = False
    seccion: str | None = None  # "Título › Apartado" en Markdown


def limpiar(texto: str) -> str:
    texto = texto.replace("\x00", "")
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)  # palabras partidas al final de línea
    texto = re.sub(r"[ \t ]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _ocr_pagina(pagina) -> str | None:
    if not ocr.disponible():
        return None
    from PIL import Image

    imagen = Image.open(io.BytesIO(pagina.get_pixmap(dpi=DPI_OCR).tobytes("png")))
    return ocr.leer_imagen(imagen)


def extraer_pdf(ruta: Path, progreso: Callable[[int, int], None] | None = None) -> list[Pagina]:
    import pymupdf

    paginas: list[Pagina] = []
    with pymupdf.open(ruta) as documento:
        total = documento.page_count
        for indice, pagina in enumerate(documento, start=1):
            texto = pagina.get_text("text")
            usado_ocr = False
            if len(texto.strip()) < MIN_CARACTERES_PAGINA:
                texto_ocr = _ocr_pagina(pagina)
                if texto_ocr and len(texto_ocr.strip()) > len(texto.strip()):
                    texto, usado_ocr = texto_ocr, True
            paginas.append(Pagina(indice, limpiar(texto), usado_ocr))
            if progreso:
                progreso(indice, total)
    return paginas


def extraer_texto(ruta: Path) -> list[Pagina]:
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    return [Pagina(None, limpiar(texto))]


def extraer_markdown(ruta: Path) -> list[Pagina]:
    """Divide el Markdown por apartados (##) y recuerda en cuál está cada trozo.

    Así un fragmento como "1. Cambiar la contraseña..." se guarda como
    "Playbook: Phishing › Acciones inmediatas", y la búsqueda sabe de qué trata.
    """
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    titulo = ruta.stem
    secciones: list[Pagina] = []
    apartado: str | None = None
    lineas: list[str] = []

    def cerrar() -> None:
        contenido = limpiar("\n".join(lineas))
        if contenido:
            nombre = f"{titulo} › {apartado}" if apartado else titulo
            secciones.append(Pagina(None, contenido, seccion=nombre))

    for linea in texto.splitlines():
        if m := re.match(r"^#\s+(.+)", linea):
            titulo = m.group(1).strip()
            continue
        if m := re.match(r"^##\s+(.+)", linea):
            cerrar()
            apartado, lineas = m.group(1).strip(), []
            continue
        lineas.append(linea)
    cerrar()
    return secciones


def extraer(ruta: Path, progreso: Callable[[int, int], None] | None = None) -> list[Pagina]:
    extension = ruta.suffix.lower()
    if extension == ".pdf":
        return extraer_pdf(ruta, progreso)
    if extension == ".md":
        return extraer_markdown(ruta)
    if extension == ".txt":
        return extraer_texto(ruta)
    raise ValueError(f"Tipo de documento no soportado: {extension}")
