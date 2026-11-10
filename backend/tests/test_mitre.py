import json
import re
from pathlib import Path

from app import mitre

from .test_chat import KNOWLEDGE_REPO, OllamaFalso, con_playbooks  # noqa: F401


def test_todas_las_tecnicas_de_los_playbooks_estan_en_la_referencia():
    for playbook in (KNOWLEDGE_REPO / "playbooks").glob("*.md"):
        for tecnica in re.findall(r"\bT\d{4}(?:\.\d{3})?\b", playbook.read_text(encoding="utf-8")):
            assert tecnica in mitre.TECNICAS, f"{tecnica} de {playbook.name} no está en la referencia"


def test_documento_de_referencia_esta_al_dia():
    generado = (KNOWLEDGE_REPO / "referencia" / "mitre-attack.md").read_text(encoding="utf-8")
    assert generado == mitre.documento_referencia(), "Regenera con: python -m app.mitre"


def test_verificar_marca_nombres_oficiales_y_desconocidas():
    texto = "- T1486: Uso de herramientas legítimas\n- T1490\n- T1499.999 inventada\n- T1486 repetida"
    resultado = mitre.verificar(texto)
    assert [r["id"] for r in resultado] == ["T1486", "T1490", "T1499.999"]
    assert resultado[0]["nombre"] == "Data Encrypted for Impact" and resultado[0]["tactica"] == "Impacto"
    assert resultado[2]["reconocida"] is False and resultado[2]["tecnica_padre"] == "Endpoint Denial of Service"


def test_chat_incluye_cabecera_del_playbook_y_verificacion(con_playbooks, cliente):  # noqa: F811
    cliente.app.state.cola.esperar()
    falso = OllamaFalso()
    cliente.app.state.ollama = falso
    pregunta = {"rol": "usuario", "contenido": "Ransomware: nota de rescate, ficheros cifrados y copias de sombra borradas"}
    eventos = [json.loads(l) for l in cliente.post("/chat", json={"mensajes": [pregunta]}).text.splitlines()]
    contexto = falso.recibido["mensajes"][-1]["content"]
    # La cabecera del playbook principal (con sus técnicas MITRE) siempre llega al modelo
    assert "MITRE ATT&CK: T" in contexto
    assert eventos[-1]["tipo"] == "fin" and isinstance(eventos[-1]["mitre"], list)


def test_ruta_mitre(cliente):
    tabla = cliente.get("/mitre").json()
    assert tabla["T1566.002"]["nombre"] == "Spearphishing Link"
