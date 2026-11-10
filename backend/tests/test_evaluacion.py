import json
from pathlib import Path

from evaluacion.evaluar import apartados_presentes, citas_de, evaluar_respuesta, severidad_de, tipo_de

from .test_incidentes import RESPUESTA

CASOS = Path(__file__).resolve().parents[1] / "evaluacion" / "casos.json"


def test_casos_bien_formados():
    from app.mitre import TECNICAS

    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    assert len(casos) == 15 and len({c["id"] for c in casos}) == 15
    playbooks = {p.name for p in (Path(__file__).resolve().parents[2] / "knowledge" / "playbooks").glob("*.md")}
    for caso in casos:
        assert caso["playbook"] in playbooks, caso["id"]
        assert all(t in TECNICAS for t in caso["mitre"]), caso["id"]
        assert set(caso["severidad"]) <= {"Baja", "Media", "Alta", "Crítica"}, caso["id"]


def test_metricas_de_una_respuesta():
    assert tipo_de(RESPUESTA) == "phishing"
    assert severidad_de(RESPUESTA) == "Alta"
    assert citas_de("Paso [1]. Otro [2, 3].") == [1, 2, 3]
    assert set(apartados_presentes(RESPUESTA)) >= {"inmediatas", "evidencias", "contencion", "notificacion", "mitre"}

    caso = {"tipo": ["phishing"], "severidad": ["Alta"], "mitre": ["T1566.002"], "playbook": "01-phishing.md"}
    fuentes = [{"documento": "01-phishing.md"}, {"documento": "x"}, {"documento": "y"}]
    resultado = evaluar_respuesta(caso, RESPUESTA, fuentes)
    assert resultado["metricas"]["tipo"] and resultado["metricas"]["severidad"]
    assert resultado["metricas"]["mitre"] and resultado["metricas"]["citas"] and resultado["metricas"]["playbook"]
    assert resultado["metricas"]["estructura"] is False  # a RESPUESTA le faltan apartados


def test_detecta_tecnica_inventada():
    caso = {"tipo": ["ransomware"], "severidad": ["Crítica"], "mitre": ["T1486"], "playbook": "02-malware-ransomware.md"}
    resultado = evaluar_respuesta(caso, "### MITRE ATT&CK\n- T1486\n- T1999.999", [])
    assert resultado["metricas"]["mitre"] is False
