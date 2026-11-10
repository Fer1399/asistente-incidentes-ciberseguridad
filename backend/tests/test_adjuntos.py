import json
from pathlib import Path

import pytest

from app import iocs, ocr
from app.correo import analizar

from .test_chat import OllamaFalso

MUESTRAS = Path(__file__).parent / "muestras"
CORREO = MUESTRAS / "phishing-ejemplo.eml"


# --- IOCs ---------------------------------------------------------------------

def test_iocs_admite_indicadores_desactivados_y_los_devuelve_seguros():
    resultado = iocs.extraer("Entrar en hxxps://login-banco[.]top/acceso desde 185.220.101[.]45")
    assert resultado["url"][0]["valor"] == "https://login-banco.top/acceso"
    assert resultado["url"][0]["seguro"] == "hxxps://login-banco[.]top/acceso"
    assert resultado["ip"][0] == {"valor": "185.220.101.45", "seguro": "185[.]220[.]101[.]45", "interna": False}


def test_iocs_marca_ips_internas_y_tipos_de_hash():
    texto = ("Conexion de 192.168.1.20 a 8.8.8.8, hash d41d8cd98f00b204e9800998ecf8427e y "
             "da39a3ee5e6b4b0d3255bfef95601890afd80709")
    resultado = iocs.extraer(texto)
    assert {(i["valor"], i["interna"]) for i in resultado["ip"]} == {("192.168.1.20", True), ("8.8.8.8", False)}
    assert [h["algoritmo"] for h in resultado["hash"]] == ["md5", "sha1"]


def test_iocs_ignora_nombres_de_fichero_y_versiones():
    resultado = iocs.extraer("Se ejecutó factura.pdf.exe y script.ps1, versión 10.0.19045.1 del sistema")
    assert resultado["dominio"] == []
    assert resultado["ip"] == []


def test_ruta_iocs(cliente):
    respuesta = cliente.post("/iocs", json={"texto": "Fallos de login desde 45.33.32.156 (CVE-2024-3400)"})
    assert respuesta.json()["total"] == 2


# --- Correos ------------------------------------------------------------------

def test_correo_detecta_suplantacion():
    resultado = analizar(CORREO.read_bytes())
    alertas = "\n".join(resultado["alertas"])
    assert "Reply-To" in alertas
    assert "SPF = fail" in alertas and "DMARC = fail" in alertas
    assert "Enlace engañoso" in alertas and "login.microsoftonline.com" in alertas
    assert "Factura.pdf.exe" in alertas
    assert resultado["cabeceras"]["autenticacion"] == {"spf": "fail", "dkim": "none", "dmarc": "fail"}
    assert any(i["valor"] == "185.220.101.45" for i in resultado["iocs"]["ip"])
    assert resultado["adjuntos"][0]["peligroso"] is True
    assert "https://" not in resultado["texto"]  # el modelo solo ve enlaces desactivados


# --- Ruta /adjuntos y chat ----------------------------------------------------

def test_subir_correo_y_preguntar(cliente):
    with CORREO.open("rb") as f:
        respuesta = cliente.post("/adjuntos", files={"fichero": (CORREO.name, f)})
    assert respuesta.status_code == 200
    adjunto = respuesta.json()
    assert adjunto["tipo"] == "correo" and adjunto["total_iocs"] > 0
    assert cliente.get(f"/adjuntos/{adjunto['id']}").json()["sha256"] == adjunto["sha256"]

    falso = OllamaFalso()
    cliente.app.state.ollama = falso
    mensajes = [{"rol": "usuario", "contenido": "¿Es phishing? ¿Cómo procedo?", "adjuntos": [adjunto["id"]]}]
    eventos = [json.loads(l) for l in cliente.post("/chat", json={"mensajes": mensajes}).text.splitlines()]

    assert any(i["valor"] == "185.220.101.45" for i in eventos[0]["iocs"]["ip"])
    ultimo = falso.recibido["mensajes"][-1]["content"]
    assert '<adjunto nombre="phishing-ejemplo.eml" tipo="correo"' in ultimo
    assert "Enlace engañoso" in ultimo
    assert ultimo.endswith("¿Es phishing? ¿Cómo procedo?")


def test_adjunto_inexistente_en_el_chat(cliente):
    mensajes = [{"rol": "usuario", "contenido": "hola", "adjuntos": ["noexiste123"]}]
    assert cliente.post("/chat", json={"mensajes": mensajes}).status_code == 404


def test_log_largo_se_recorta_pero_conserva_todos_los_iocs(cliente, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_caracteres_adjunto", 2000)
    lineas = [f"2026-11-10 10:{i % 60:02d} Failed password for root from 203.0.113.{i % 250} port 22" for i in range(500)]
    lineas.append("2026-11-10 11:59 Accepted password for admin from 198.51.100.77 port 22")
    respuesta = cliente.post("/adjuntos", files={"fichero": ("auth.log", "\n".join(lineas).encode())})
    adjunto = respuesta.json()
    assert adjunto["recortado"] is True
    ips = {i["valor"] for i in adjunto["iocs"]["ip"]}
    assert "198.51.100.77" in ips and len(ips) == 251


def test_formato_no_admitido(cliente):
    respuesta = cliente.post("/adjuntos", files={"fichero": ("muestra.exe", b"MZ")})
    assert respuesta.status_code == 415


@pytest.mark.skipif(not ocr.disponible(), reason="Tesseract no instalado")
def test_captura_con_ocr_y_vision(cliente, tmp_path):
    from PIL import Image, ImageDraw, ImageFont

    imagen = Image.new("RGB", (1400, 300), "white")
    try:
        fuente = ImageFont.truetype("DejaVuSans.ttf", 40)
    except OSError:
        fuente = ImageFont.load_default()
    ImageDraw.Draw(imagen).text((30, 100), "Verify your account at secure-login.example.top", fill="black", font=fuente)
    ruta = tmp_path / "captura.png"
    imagen.save(ruta)

    class VisionFalsa(OllamaFalso):
        async def describir_imagen(self, modelo, imagen_b64, instrucciones):
            return "1. Qué es: un correo que pide verificar la cuenta."

    cliente.app.state.ollama = VisionFalsa()
    with ruta.open("rb") as f:
        adjunto = cliente.post("/adjuntos", files={"fichero": ("captura.png", f)}).json()
    assert adjunto["metodos"] == ["ocr", "vision"]
    assert any("secure-login.example.top" in d["valor"] for d in adjunto["iocs"]["dominio"])
    assert "modelo de visión" in adjunto["vista_previa"]


@pytest.mark.skipif(not ocr.disponible(), reason="Tesseract no instalado")
def test_captura_sin_modelo_de_vision_usa_solo_ocr(cliente, tmp_path):
    from PIL import Image, ImageDraw

    imagen = Image.new("RGB", (800, 200), "white")
    ImageDraw.Draw(imagen).text((20, 80), "ERROR 0x80070005 ACCESS DENIED", fill="black")
    ruta = tmp_path / "error.png"
    imagen.resize((1600, 400)).save(ruta)

    with ruta.open("rb") as f:
        adjunto = cliente.post("/adjuntos?vision=false", files={"fichero": ("error.png", f)}).json()
    assert adjunto["metodos"] == ["ocr"]
