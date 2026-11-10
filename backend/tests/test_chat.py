import json
import shutil
from pathlib import Path

import pytest

from app.asistente import consulta_de_busqueda
from app.config import settings
from app.extraccion import extraer_markdown
from app.ollama_client import ErrorOllama
from app.prompts import SIN_CONTEXTO, SYSTEM_PROMPT
from app.troceado import trocear

KNOWLEDGE_REPO = Path(__file__).resolve().parents[2] / "knowledge"
RESPUESTA_FALSA = ["**Tipo de incidente:** Phishing", "\n### 1. Acciones inmediatas", "\n1. Cambiar la contraseña [1]"]


class OllamaFalso:
    """Sustituye al modelo de chat: guarda lo que recibe y responde un texto fijo."""

    def __init__(self, error: Exception | None = None):
        self.recibido = None
        self.error = error

    async def chat_stream(self, modelo, mensajes, opciones=None):
        self.recibido = {"modelo": modelo, "mensajes": mensajes, "opciones": opciones}
        if self.error:
            raise self.error
        for trozo in RESPUESTA_FALSA:
            yield trozo

    async def close(self):
        pass


def _eventos(respuesta) -> list[dict]:
    return [json.loads(linea) for linea in respuesta.text.splitlines() if linea.strip()]


@pytest.fixture
def con_playbooks(tmp_path, monkeypatch):
    shutil.copytree(KNOWLEDGE_REPO, tmp_path / "knowledge")
    # El embedder falso de las pruebas no entiende significados, solo palabras:
    # bajamos el umbral para que no descarte fragmentos relacionados.
    monkeypatch.setattr(settings, "similitud_minima", 0.05)


def test_playbooks_y_referencia_se_indexan(con_playbooks, cliente):
    cliente.app.state.cola.esperar()
    docs = cliente.get("/documentos").json()
    assert len(docs) == 8  # 7 playbooks + referencia MITRE
    assert all(d["estado"] == "indexado" and d["origen"] == "incluido" for d in docs), docs


def test_markdown_conserva_el_apartado():
    secciones = extraer_markdown(KNOWLEDGE_REPO / "playbooks" / "01-phishing.md")
    nombres = [s.seccion for s in secciones]
    assert "Playbook: Phishing › 3. Contención" in nombres

    fragmentos = trocear(secciones, tamano=1000, solape=150)
    assert all(f.texto.startswith("[Playbook: Phishing") for f in fragmentos)


def test_chat_responde_con_fuentes_y_contexto(con_playbooks, cliente):
    cliente.app.state.cola.esperar()
    falso = OllamaFalso()
    cliente.app.state.ollama = falso

    pregunta = "Un usuario ha introducido su contraseña en un correo de phishing, ¿cómo procedo?"
    respuesta = cliente.post("/chat", json={"mensajes": [{"rol": "usuario", "contenido": pregunta}]})
    assert respuesta.status_code == 200
    eventos = _eventos(respuesta)

    assert eventos[0]["tipo"] == "fuentes"
    assert eventos[0]["modelo"] == settings.chat_model
    documentos = [f["documento"] for f in eventos[0]["fuentes"]]
    assert "01-phishing.md" in documentos
    assert [f["n"] for f in eventos[0]["fuentes"]] == list(range(1, len(documentos) + 1))

    texto = "".join(e["texto"] for e in eventos if e["tipo"] == "texto")
    assert texto == "".join(RESPUESTA_FALSA)
    assert eventos[-1]["tipo"] == "fin"

    enviados = falso.recibido["mensajes"]
    assert enviados[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert "<contexto>" in enviados[-1]["content"] and "[1] (" in enviados[-1]["content"]
    assert enviados[-1]["content"].endswith(pregunta)
    assert falso.recibido["opciones"]["temperature"] == settings.temperatura


def test_chat_sin_documentos_lo_indica(cliente):
    falso = OllamaFalso()
    cliente.app.state.ollama = falso
    respuesta = cliente.post("/chat", json={"mensajes": [{"rol": "usuario", "contenido": "hola"}]})
    eventos = _eventos(respuesta)
    assert eventos[0]["fuentes"] == []
    assert SIN_CONTEXTO in falso.recibido["mensajes"][-1]["content"]


def test_historial_y_modelo_elegido(cliente):
    falso = OllamaFalso()
    cliente.app.state.ollama = falso
    mensajes = [
        {"rol": "usuario", "contenido": "Tengo un ransomware en un equipo"},
        {"rol": "asistente", "contenido": "Aísla el equipo."},
        {"rol": "usuario", "contenido": "¿Y si ya está cifrado el NAS?"},
    ]
    cliente.post("/chat", json={"mensajes": mensajes, "modelo": "qwen2.5:14b"})
    enviados = falso.recibido["mensajes"]
    assert falso.recibido["modelo"] == "qwen2.5:14b"
    assert [m["role"] for m in enviados] == ["system", "user", "assistant", "user"]


def test_ultimo_mensaje_debe_ser_del_usuario(cliente):
    respuesta = cliente.post("/chat", json={"mensajes": [{"rol": "asistente", "contenido": "hola"}]})
    assert respuesta.status_code == 422


def test_error_de_ollama_se_comunica(cliente):
    cliente.app.state.ollama = OllamaFalso(error=ErrorOllama("El modelo 'x' no está instalado"))
    eventos = _eventos(cliente.post("/chat", json={"mensajes": [{"rol": "usuario", "contenido": "hola"}]}))
    assert eventos[-1] == {"tipo": "error", "mensaje": "El modelo 'x' no está instalado"}


def test_consulta_de_seguimiento_incluye_la_pregunta_anterior():
    mensajes = [
        {"rol": "usuario", "contenido": "Me ha llegado un phishing que suplanta al banco"},
        {"rol": "asistente", "contenido": "..."},
        {"rol": "usuario", "contenido": "¿y si ya hizo clic?"},
    ]
    consulta = consulta_de_busqueda(mensajes)
    assert "phishing" in consulta and "clic" in consulta
