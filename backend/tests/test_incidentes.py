import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from app.incidentes import extraer_clasificacion, extraer_pasos

from .conftest import EmbedderFalso
from .test_chat import OllamaFalso

CORREO = Path(__file__).parent / "muestras" / "phishing-ejemplo.eml"

RESPUESTA = """### Análisis del artefacto
El correo es phishing.
- **Reply-To desviado**: las respuestas van a otro dominio.

**Tipo de incidente:** Phishing · **Severidad estimada:** Alta (el usuario introdujo credenciales)

### 1. Acciones inmediatas (primeros 15-30 minutos)
1. Cambiar la contraseña y cerrar sesiones [2].
2. Revisar el MFA de la cuenta [2, 3].

### 2. Preservación de evidencias
1. Guardar el correo original como .eml [1].

### 3. Contención
1. Bloquear el dominio `login[.]m1crosoft-seguridad[.]top` en el filtro de correo.

### 6. Notificación
1. Avisar al DPD.

### MITRE ATT&CK
- T1566.002 (enlace malicioso)

### Preguntas para afinar
1. ¿A qué hora ocurrió?
"""


@pytest.fixture
def con_memoria(monkeypatch):
    # El embedder de las pruebas compara palabras, no significados: umbral más bajo
    monkeypatch.setattr(settings, "similitud_incidente", 0.1)
    monkeypatch.setattr(settings, "similitud_minima", 0.05)


def _subir_correo(cliente) -> str:
    with CORREO.open("rb") as f:
        return cliente.post("/adjuntos", files={"fichero": (CORREO.name, f)}).json()["id"]


def _crear(cliente, **extra) -> dict:
    adjunto = _subir_correo(cliente)
    cuerpo = {
        "respuesta_asistente": RESPUESTA,
        "mensajes": [
            {"rol": "usuario", "contenido": "Un usuario metió su contraseña en este correo", "adjuntos": [adjunto]},
            {"rol": "asistente", "contenido": RESPUESTA},
        ],
        **extra,
    }
    respuesta = cliente.post("/incidentes", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Lectura de la respuesta --------------------------------------------------

def test_extrae_clasificacion_y_pasos_de_la_respuesta():
    assert extraer_clasificacion(RESPUESTA) == {"tipo": "Phishing", "severidad": "Alta"}
    pasos = extraer_pasos(RESPUESTA)
    assert [p["fase"] for p in pasos] == ["inmediatas", "inmediatas", "evidencias", "contencion", "notificacion"]
    assert pasos[0]["texto"] == "Cambiar la contraseña y cerrar sesiones."
    assert pasos[3]["texto"] == "Bloquear el dominio login[.]m1crosoft-seguridad[.]top en el filtro de correo."
    assert all("[" not in p["texto"] or "[.]" in p["texto"] for p in pasos)  # sin citas [n]


def test_clasificacion_con_otro_formato():
    texto = "### Tipo de incidente: Ransomware · **Severidad estimada:** Crítica (varios equipos)"
    assert extraer_clasificacion(texto) == {"tipo": "Ransomware", "severidad": "Crítica"}


# --- Ficha --------------------------------------------------------------------

def test_crear_ficha_desde_el_chat(cliente):
    ficha = _crear(cliente)
    assert ficha["id"].startswith("INC-")
    assert ficha["titulo"] == "Phishing" and ficha["severidad"] == "Alta"
    assert ficha["progreso"] == {"hechos": 0, "total": 5}
    assert len(ficha["adjuntos"]) == 1 and ficha["adjuntos"][0]["nombre"] == CORREO.name
    assert any(i["valor"] == "185.220.101.45" for i in ficha["iocs"]["ip"])
    assert ficha["eventos"][0]["tipo"] == "creado"
    assert len(ficha["mensajes"]) == 2
    assert ficha["descripcion"] == "Un usuario metió su contraseña en este correo"


def test_descripcion_es_la_pregunta_de_la_respuesta_usada(cliente):
    mensajes = [
        {"rol": "usuario", "contenido": "ficha"},
        {"rol": "asistente", "contenido": "Falta información."},
        {"rol": "usuario", "contenido": "Un usuario metió su contraseña en un phishing"},
        {"rol": "asistente", "contenido": RESPUESTA},
    ]
    ficha = cliente.post("/incidentes", json={"respuesta_asistente": RESPUESTA, "mensajes": mensajes}).json()
    assert ficha["descripcion"] == "Un usuario metió su contraseña en un phishing"


def test_checklist_registra_la_hora_y_la_cronologia(cliente):
    ficha = _crear(cliente)
    paso = ficha["pasos"][0]
    actualizado = cliente.patch(f"/incidentes/{ficha['id']}/pasos/{paso['id']}", json={"hecho": True}).json()
    assert actualizado["hecho"] is True and actualizado["hecho_en"]

    propio = cliente.post(f"/incidentes/{ficha['id']}/pasos",
                          json={"fase": "contencion", "texto": "Bloquear la IP en el firewall"}).json()
    assert propio["origen"] == "usuario"

    detalle = cliente.get(f"/incidentes/{ficha['id']}").json()
    assert detalle["progreso"] == {"hechos": 1, "total": 6}
    textos = [e["texto"] for e in detalle["eventos"]]
    assert any(t.startswith("Hecho: Cambiar la contraseña") for t in textos)
    assert any("Bloquear la IP" in t for t in textos)


def test_plazo_aepd_con_datos_personales(cliente):
    ficha = _crear(cliente, datos_personales=True)
    assert 71 < ficha["plazo_aepd"]["horas_restantes"] <= 72
    sin_datos = _crear(cliente)
    assert sin_datos["plazo_aepd"] is None


def test_listado_busqueda_y_resumen(cliente):
    _crear(cliente)
    _crear(cliente, titulo="Ransomware en recepción", severidad="Crítica")
    assert len(cliente.get("/incidentes").json()) == 2
    assert [i["titulo"] for i in cliente.get("/incidentes?q=ransomware").json()] == ["Ransomware en recepción"]
    assert cliente.get("/incidentes/resumen").json()["abiertos"] == 2


def test_cerrar_exige_notas_y_bloquea_cambios(cliente):
    ficha = _crear(cliente)
    assert cliente.post(f"/incidentes/{ficha['id']}/cerrar", json={"notas_cierre": "ok"}).status_code == 422
    cierre = {"notas_cierre": "Se cambió la contraseña a los 10 minutos y se bloqueó el dominio."}
    cerrada = cliente.post(f"/incidentes/{ficha['id']}/cerrar", json=cierre).json()
    assert cerrada["estado"] == "cerrado" and cerrada["en_memoria"] is True
    assert cliente.patch(f"/incidentes/{ficha['id']}", json={"titulo": "x"}).status_code == 409


# --- Memoria ------------------------------------------------------------------

def test_memoria_de_incidentes_y_aviso_de_similares(cliente, con_memoria):
    ficha = _crear(cliente)
    cliente.post(f"/incidentes/{ficha['id']}/cerrar", json={
        "notas_cierre": "Phishing de Microsoft: se cambió la contraseña, se revocaron sesiones y se bloqueó el dominio.",
        "lecciones": "Activar DMARC en modo reject.",
    })
    cliente.app.state.cola.esperar()
    assert cliente.app.state.almacen.contar_documento(ficha["id"]) > 0
    assert cliente.get("/health").json()["conocimiento"]["incidentes_en_memoria"] == 1

    similares = cliente.post("/incidentes/similares", json={"texto": "phishing de Microsoft contraseña"}).json()
    assert similares[0]["id"] == ficha["id"]

    falso = OllamaFalso()
    cliente.app.state.ollama = falso
    pregunta = {"rol": "usuario", "contenido": "Otro phishing de Microsoft, alguien metió la contraseña"}
    eventos = [json.loads(l) for l in cliente.post("/chat", json={"mensajes": [pregunta]}).text.splitlines()]
    assert eventos[0]["similares"][0]["id"] == ficha["id"]
    assert "Incidente anterior" in falso.recibido["mensajes"][-1]["content"]

    cliente.post(f"/incidentes/{ficha['id']}/reabrir")
    assert cliente.app.state.almacen.contar_documento(ficha["id"]) == 0


def test_chat_guarda_la_conversacion_en_la_ficha(cliente):
    ficha = _crear(cliente)
    cliente.app.state.ollama = OllamaFalso()
    pregunta = {"rol": "usuario", "contenido": "¿Y si también abrió el adjunto?"}
    cliente.post("/chat", json={"mensajes": [pregunta], "incidente_id": ficha["id"]})
    mensajes = cliente.get(f"/incidentes/{ficha['id']}").json()["mensajes"]
    assert [m["rol"] for m in mensajes[-2:]] == ["usuario", "asistente"]
    assert mensajes[-2]["contenido"] == pregunta["contenido"]


# --- Informes -----------------------------------------------------------------

def test_informe_markdown_y_pdf(cliente):
    import pymupdf

    ficha = _crear(cliente, datos_personales=True)
    cliente.patch(f"/incidentes/{ficha['id']}/pasos/{ficha['pasos'][0]['id']}", json={"hecho": True})

    md = cliente.get(f"/incidentes/{ficha['id']}/informe?formato=md")
    assert md.headers["content-disposition"].endswith(f'informe-{ficha["id"]}.md"')
    texto = md.text
    for apartado in ("## Cronología", "## Procedimiento", "## Indicadores de compromiso",
                     "## Evidencias analizadas", "Límite notificación AEPD", "- [x] Cambiar la contraseña"):
        assert apartado in texto

    pdf = cliente.get(f"/incidentes/{ficha['id']}/informe?formato=pdf")
    assert pdf.content.startswith(b"%PDF")
    documento = pymupdf.open("pdf", pdf.content)
    contenido = "".join(p.get_text() for p in documento)
    assert ficha["id"] in contenido and "Contención" in contenido and "Página 1 de" in contenido
    assert "###" not in contenido and "**" not in contenido  # el Markdown del anexo se interpreta


# --- Copia de seguridad -------------------------------------------------------

def test_exportar_e_importar_en_otro_equipo(cliente, tmp_path, monkeypatch, con_memoria):
    ficha = _crear(cliente)
    cliente.post(f"/incidentes/{ficha['id']}/cerrar", json={"notas_cierre": "Resuelto cambiando la contraseña."})
    from .conftest import crear_pdf

    pdf = crear_pdf(tmp_path / "guia.pdf", ["Guía de respuesta a incidentes de phishing y ransomware."])
    with pdf.open("rb") as f:
        cliente.post("/documentos", files={"fichero": ("guia.pdf", f)})
    cliente.app.state.cola.esperar()

    copia = cliente.get("/copia")
    assert copia.status_code == 200
    with zipfile.ZipFile(io.BytesIO(copia.content)) as zf:
        nombres = zf.namelist()
        assert "manifiesto.json" in nombres and "asistente.db" in nombres
        assert not any(n.startswith("vectores/") for n in nombres)

    # "Otro equipo": carpeta de datos vacía
    monkeypatch.setattr(settings, "data_dir", tmp_path / "otro-equipo")
    with TestClient(main.app) as otro:
        resultado = otro.post("/copia", files={"fichero": ("copia.zip", copia.content, "application/zip")}).json()
        assert resultado["resumen"]["incidentes_nuevos"] == 1
        assert resultado["resumen"]["documentos_nuevos"] == 1
        assert resultado["resumen"]["adjuntos_nuevos"] == 1
        otro.app.state.cola.esperar()

        importado = otro.get(f"/incidentes/{ficha['id']}").json()
        assert importado["estado"] == "cerrado" and len(importado["adjuntos"]) == 1
        assert otro.app.state.almacen.contar_documento(ficha["id"]) > 0
        assert [d["estado"] for d in otro.get("/documentos").json()] == ["indexado"]

        # Volver a importar la misma copia no duplica nada
        repetido = otro.post("/copia", files={"fichero": ("copia.zip", copia.content)}).json()
        assert repetido["resumen"]["incidentes_sin_cambios"] == 1
        assert repetido["resumen"]["documentos_nuevos"] == 0


def test_importar_copias_no_validas(cliente):
    assert cliente.post("/copia", files={"fichero": ("x.zip", b"no es un zip")}).status_code == 422
    malicioso = io.BytesIO()
    with zipfile.ZipFile(malicioso, "w") as zf:
        zf.writestr("manifiesto.json", "{}")
        zf.writestr("asistente.db", "")
        zf.writestr("../../fuera.txt", "x")
    respuesta = cliente.post("/copia", files={"fichero": ("x.zip", malicioso.getvalue())})
    assert respuesta.status_code == 422 and "no permitida" in respuesta.json()["detail"]


def test_quitar_mensajes_adjuntos_repetidos_e_informe_sin_anexo(cliente):
    adjunto_1 = _subir_correo(cliente)
    adjunto_2 = _subir_correo(cliente)  # el mismo correo adjuntado dos veces
    mensajes = [
        {"rol": "usuario", "contenido": "Un usuario metió su contraseña", "adjuntos": [adjunto_1]},
        {"rol": "asistente", "contenido": RESPUESTA},
        {"rol": "usuario", "contenido": "start (Get-ChildItem informe-*.pdf).FullName", "adjuntos": [adjunto_2]},
        {"rol": "asistente", "contenido": "Ese comando de PowerShell abre el último informe."},
    ]
    ficha = cliente.post("/incidentes", json={"respuesta_asistente": RESPUESTA, "mensajes": mensajes}).json()
    assert len(ficha["adjuntos"]) == 1

    for mensaje in ficha["mensajes"][2:]:
        assert cliente.delete(f"/incidentes/{ficha['id']}/mensajes/{mensaje['id']}").status_code == 204
    detalle = cliente.get(f"/incidentes/{ficha['id']}").json()
    assert [m["contenido"][:10] for m in detalle["mensajes"]] == ["Un usuario", RESPUESTA[:10]]
    assert any("quitado de la conversación" in e["texto"] for e in detalle["eventos"])

    con_anexo = cliente.get(f"/incidentes/{ficha['id']}/informe?formato=md").text
    sin_anexo = cliente.get(f"/incidentes/{ficha['id']}/informe?formato=md&anexo=false").text
    assert "Anexo: consultas" in con_anexo and "Anexo: consultas" not in sin_anexo


def test_importar_copia_con_columnas_maliciosas(cliente, tmp_path):
    """Una copia manipulada no puede inyectar SQL a través de los nombres de columna."""
    import sqlite3

    base = tmp_path / "asistente.db"
    con = sqlite3.connect(base)
    con.executescript("""
        CREATE TABLE documentos (id TEXT, nombre TEXT, sha256 TEXT, origen TEXT, ruta TEXT);
        CREATE TABLE incidentes (id TEXT, titulo TEXT, estado TEXT, detectado TEXT, creado TEXT,
            actualizado TEXT, en_memoria INTEGER, datos_personales INTEGER,
            "x) VALUES (1); DROP TABLE pasos; --" TEXT);
        CREATE TABLE pasos (id INTEGER, incidente_id TEXT, fase TEXT, texto TEXT, orden INTEGER);
        CREATE TABLE eventos (id INTEGER, incidente_id TEXT, fecha TEXT, tipo TEXT, texto TEXT);
        CREATE TABLE mensajes (id INTEGER, incidente_id TEXT, fecha TEXT, rol TEXT, contenido TEXT, adjuntos TEXT);
        CREATE TABLE incidente_adjuntos (incidente_id TEXT, adjunto_id TEXT);
        INSERT INTO incidentes VALUES ('INC-20260101-AAAA', 'Importado', 'abierto', '2026-01-01T00:00:00+00:00',
            '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', 0, 0, 'malicioso');
    """)
    con.commit()
    con.close()
    zipbuf = io.BytesIO()
    with zipfile.ZipFile(zipbuf, "w") as zf:
        zf.writestr("manifiesto.json", json.dumps({"aplicacion": "asistente-incidentes-ciberseguridad", "formato": 1}))
        zf.write(base, "asistente.db")
    respuesta = cliente.post("/copia", files={"fichero": ("copia.zip", zipbuf.getvalue())})
    assert respuesta.status_code == 200, respuesta.text
    assert cliente.get("/incidentes/INC-20260101-AAAA").json()["titulo"] == "Importado"
    ficha = _crear(cliente)  # la tabla de pasos sigue existiendo
    assert ficha["progreso"]["total"] == 5
