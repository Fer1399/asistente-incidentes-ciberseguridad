import pytest

from app import ocr

from .conftest import crear_pdf

PAGINA_1 = (
    "Gestión de incidentes de ransomware.\n\n"
    "Aislar inmediatamente el equipo de la red y no apagarlo para conservar la memoria."
)
PAGINA_2 = (
    "Respuesta ante phishing.\n\n"
    "Si el usuario introdujo su contraseña, cambiarla, cerrar sesiones y revisar el MFA. "
    "Guardar el correo original con cabeceras como evidencia."
)


def _subir(cliente, ruta):
    with ruta.open("rb") as f:
        return cliente.post("/documentos", files={"fichero": (ruta.name, f, "application/pdf")})


def test_subir_pdf_indexa_y_busca(cliente, tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", [PAGINA_1, PAGINA_2])

    respuesta = _subir(cliente, pdf)
    assert respuesta.status_code == 202
    doc_id = respuesta.json()["id"]

    cliente.app.state.cola.esperar()
    doc = cliente.get(f"/documentos/{doc_id}").json()
    assert doc["estado"] == "indexado", doc["mensaje"]
    assert doc["paginas"] == 2
    assert doc["fragmentos"] >= 2

    resultados = cliente.post("/buscar", json={"consulta": "phishing contraseña MFA"}).json()["resultados"]
    assert resultados[0]["documento"] == "guia.pdf"
    assert resultados[0]["pagina"] == 2

    salud = cliente.get("/health").json()["conocimiento"]
    assert salud["indexados"] == 1
    assert salud["modelo_indexado"] == "falso"


def test_rechaza_duplicados(cliente, tmp_path):
    pdf = crear_pdf(tmp_path / "guia.pdf", [PAGINA_1])
    assert _subir(cliente, pdf).status_code == 202
    cliente.app.state.cola.esperar()
    assert _subir(cliente, pdf).status_code == 409


def test_rechaza_formatos_no_admitidos(cliente, tmp_path):
    malo = tmp_path / "virus.exe"
    malo.write_bytes(b"MZ")
    assert _subir(cliente, malo).status_code == 415


def test_borrar_documento(cliente, tmp_path):
    doc_id = _subir(cliente, crear_pdf(tmp_path / "guia.pdf", [PAGINA_1])).json()["id"]
    cliente.app.state.cola.esperar()

    assert cliente.delete(f"/documentos/{doc_id}").status_code == 204
    assert cliente.get(f"/documentos/{doc_id}").status_code == 404
    assert cliente.get("/health").json()["conocimiento"]["fragmentos"] == 0


def test_indexa_carpeta_knowledge_al_arrancar(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    from app.config import settings

    from .conftest import EmbedderFalso

    carpeta = tmp_path / "knowledge" / "playbooks"
    carpeta.mkdir(parents=True)
    (carpeta / "phishing.md").write_text("# Phishing\n\n" + PAGINA_2, encoding="utf-8")
    (tmp_path / "knowledge" / "README.md").write_text("no indexar", encoding="utf-8")

    monkeypatch.setattr(settings, "data_dir", tmp_path / "data")
    monkeypatch.setattr(settings, "knowledge_dir", tmp_path / "knowledge")
    monkeypatch.setattr(main, "Embedder", lambda *a, **k: EmbedderFalso())

    with TestClient(main.app) as cliente:
        cliente.app.state.cola.esperar()
        docs = cliente.get("/documentos").json()
        assert [d["nombre"] for d in docs] == ["phishing.md"]
        assert docs[0]["origen"] == "incluido"
        assert cliente.delete(f"/documentos/{docs[0]['id']}").status_code == 403


@pytest.mark.skipif(not ocr.disponible(), reason="Tesseract no instalado")
def test_pdf_escaneado_usa_ocr(cliente, tmp_path):
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont

    imagen = Image.new("RGB", (1700, 400), "white")
    dibujo = ImageDraw.Draw(imagen)
    try:
        fuente = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        fuente = ImageFont.load_default()
    dibujo.text((40, 60), "Incident response: isolate the infected host", fill="black", font=fuente)
    dibujo.text((40, 200), "and preserve the evidence before cleaning", fill="black", font=fuente)
    png = tmp_path / "escaneo.png"
    imagen.save(png)

    documento = pymupdf.open()
    pagina = documento.new_page()
    pagina.insert_image(pagina.rect, filename=str(png))
    ruta = tmp_path / "escaneado.pdf"
    documento.save(ruta)
    documento.close()

    doc_id = _subir(cliente, ruta).json()["id"]
    cliente.app.state.cola.esperar()
    doc = cliente.get(f"/documentos/{doc_id}").json()
    assert doc["estado"] == "indexado", doc["mensaje"]
    assert doc["paginas_ocr"] == 1
