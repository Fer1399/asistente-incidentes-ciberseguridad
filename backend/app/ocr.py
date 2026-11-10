"""OCR local con Tesseract: PDFs escaneados y capturas de pantalla."""

import shutil
from functools import lru_cache
from pathlib import Path

from .config import settings

TESSERACT_WINDOWS = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class OCRNoDisponible(RuntimeError):
    """Tesseract no está instalado o no se encuentra."""


@lru_cache
def ruta_tesseract() -> str | None:
    if settings.tesseract_cmd and Path(settings.tesseract_cmd).exists():
        return settings.tesseract_cmd
    encontrado = shutil.which("tesseract")
    if encontrado:
        return encontrado
    if TESSERACT_WINDOWS.exists():
        return str(TESSERACT_WINDOWS)
    return None


def disponible() -> bool:
    return ruta_tesseract() is not None


def _pytesseract():
    ruta = ruta_tesseract()
    if not ruta:
        raise OCRNoDisponible("Tesseract no está instalado. Ver docs/01-instalacion.md")
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = ruta
    return pytesseract


@lru_cache
def idiomas() -> str:
    """Español + inglés si están instalados; si no, lo que haya."""
    try:
        instalados = set(_pytesseract().get_languages(config=""))
    except Exception:
        instalados = set()
    elegidos = [idioma for idioma in ("spa", "eng") if idioma in instalados]
    return "+".join(elegidos) or "eng"


def leer_imagen(imagen) -> str:
    """Devuelve el texto de una imagen PIL."""
    return _pytesseract().image_to_string(imagen, lang=idiomas())
