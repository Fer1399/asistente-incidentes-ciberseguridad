"""Configuración de las pruebas.

Las pruebas no necesitan Ollama: sustituyen el modelo de embeddings por uno falso
que convierte el texto en un vector de palabras. Así se comprueba todo el flujo
(subida, extracción, troceado, almacenamiento y búsqueda) en cualquier equipo.
"""

import hashlib
import math
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import main  # noqa: E402
from app.config import settings  # noqa: E402

DIMENSIONES = 256


class EmbedderFalso:
    modelo = "falso"

    def vectorizar(self, textos, progreso=None):
        vectores = [self._vector(t) for t in textos]
        if progreso:
            progreso(len(vectores), len(textos))
        return vectores

    def vectorizar_uno(self, texto):
        return self._vector(texto)

    def close(self):
        pass

    @staticmethod
    def _vector(texto):
        v = [0.0] * DIMENSIONES
        for palabra in re.findall(r"\w+", texto.lower()):
            indice = int(hashlib.md5(palabra.encode()).hexdigest(), 16) % DIMENSIONES
            v[indice] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "knowledge_dir", tmp_path / "knowledge")
    monkeypatch.setattr(main, "Embedder", lambda *a, **k: EmbedderFalso())
    with TestClient(main.app) as c:
        yield c


def crear_pdf(ruta: Path, paginas: list[str]) -> Path:
    import pymupdf

    documento = pymupdf.open()
    for texto in paginas:
        pagina = documento.new_page()
        pagina.insert_textbox(pymupdf.Rect(50, 50, 550, 800), texto, fontsize=11)
    documento.save(ruta)
    documento.close()
    return ruta
