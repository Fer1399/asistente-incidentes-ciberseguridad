"""Procesado de adjuntos de un incidente: correos, logs, documentos y capturas.

Cada adjunto se convierte en:
- texto que el modelo de chat puede leer,
- indicadores de compromiso (IOCs) extraídos de TODO el contenido,
- alertas automáticas (en correos),
y se guarda en data/adjuntos/<id>/ junto con el original, como evidencia.
"""

import base64
import hashlib
import io
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from . import correo, iocs, ocr
from .config import settings
from .extraccion import extraer_pdf
from .ollama_client import OllamaClient

log = logging.getLogger("asistente.adjuntos")

TIPOS = {
    "correo": {".eml"},
    "imagen": {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"},
    "pdf": {".pdf"},
    "texto": {".txt", ".log", ".csv", ".json", ".xml", ".md", ".html", ".htm", ".ini", ".conf", ".yaml", ".yml"},
}
EXTENSIONES = set().union(*TIPOS.values())

INSTRUCCIONES_VISION = """\
Eres un analista de ciberseguridad. Describe esta captura de pantalla para investigar un \
posible incidente. Responde en español con estos apartados:
1. Qué es: tipo de pantalla o aplicación (correo, SMS, web, alerta del antivirus, nota de rescate, consola...).
2. Texto relevante: transcribe literalmente remitentes, asuntos, URLs, dominios, IPs, nombres \
de fichero, mensajes de error y cualquier petición al usuario.
3. Señales sospechosas: suplantación de marca, urgencia, petición de credenciales o pagos, \
errores ortográficos, enlaces que no coinciden.
No inventes nada que no se vea en la imagen."""


class AdjuntoNoValido(ValueError):
    """Formato no admitido o fichero ilegible."""


def tipo_de(nombre: str) -> str:
    extension = Path(nombre).suffix.lower()
    for tipo, extensiones in TIPOS.items():
        if extension in extensiones:
            return tipo
    raise AdjuntoNoValido(
        f"Formato no admitido ({extension or 'sin extensión'}). Admitidos: {', '.join(sorted(EXTENSIONES))}. "
        "Los .msg de Outlook se pueden guardar como .eml; los .evtx, exportar a .csv o .xml desde el Visor de eventos."
    )


def _decodificar(datos: bytes) -> str:
    for codificacion in ("utf-8-sig", "utf-16"):
        try:
            texto = datos.decode(codificacion)
            if codificacion == "utf-16" and "\x00" in texto:
                continue
            return texto
        except UnicodeDecodeError:
            continue
    return datos.decode("latin-1", errors="replace")


def recortar(texto: str, maximo: int) -> tuple[str, bool]:
    """Si el texto es muy largo se queda con el principio y el final (en logs, lo más útil)."""
    if len(texto) <= maximo:
        return texto, False
    mitad = maximo // 2
    omitidos = len(texto) - 2 * mitad
    return f"{texto[:mitad]}\n\n[... {omitidos} caracteres omitidos ...]\n\n{texto[-mitad:]}", True


async def _analizar_imagen(datos: bytes, ollama: OllamaClient, usar_vision: bool) -> dict:
    from PIL import Image

    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.load()
    except Exception as error:
        raise AdjuntoNoValido("La imagen no se puede abrir") from error
    imagen = imagen.convert("RGB")
    imagen.thumbnail((settings.max_lado_imagen, settings.max_lado_imagen))

    partes, metodos, avisos = [], [], []
    if ocr.disponible():
        texto_ocr = (await run_in_threadpool(ocr.leer_imagen, imagen)).strip()
        if texto_ocr:
            partes.append(f"Texto leído con OCR:\n{texto_ocr}")
        metodos.append("ocr")
    else:
        avisos.append("Tesseract no está instalado: no se ha aplicado OCR.")

    if usar_vision:
        buffer = io.BytesIO()
        imagen.save(buffer, format="PNG")
        try:
            descripcion = await ollama.describir_imagen(
                settings.vision_model, base64.b64encode(buffer.getvalue()).decode(), INSTRUCCIONES_VISION
            )
            if descripcion:
                partes.insert(0, f"Descripción del modelo de visión:\n{descripcion}")
            metodos.append("vision")
        except Exception as error:  # la captura sigue siendo útil con el OCR
            log.warning("Visión no disponible: %s", error)
            avisos.append(f"No se pudo usar el modelo de visión ({error}); solo OCR.")

    if not partes:
        raise AdjuntoNoValido("No se ha podido extraer nada de la imagen (sin OCR ni modelo de visión).")
    texto = "\n\n".join(partes)
    return {"texto": texto, "metodos": metodos, "avisos": avisos, "iocs": iocs.extraer(texto)}


async def procesar(nombre: str, datos: bytes, ollama: OllamaClient, usar_vision: bool | None = None) -> dict:
    tipo = tipo_de(nombre)
    usar_vision = settings.vision_activa if usar_vision is None else usar_vision
    resultado: dict = {"alertas": [], "avisos": [], "metodos": []}

    if tipo == "correo":
        analisis = await run_in_threadpool(correo.analizar, datos)
        resultado.update(analisis)
        resultado["metodos"] = ["cabeceras"]
    elif tipo == "imagen":
        resultado.update(await _analizar_imagen(datos, ollama, usar_vision))
    elif tipo == "pdf":
        temporal = settings.adjuntos_dir / f"_tmp_{uuid.uuid4().hex}.pdf"
        temporal.parent.mkdir(parents=True, exist_ok=True)
        temporal.write_bytes(datos)
        try:
            paginas = await run_in_threadpool(extraer_pdf, temporal)
        finally:
            temporal.unlink(missing_ok=True)
        texto = "\n\n".join(f"[Página {p.numero}]\n{p.texto}" for p in paginas if p.texto)
        resultado.update({"texto": texto, "iocs": iocs.extraer(texto), "metodos": ["texto"]})
    else:
        texto = _decodificar(datos)
        resultado.update({"texto": texto, "iocs": iocs.extraer(texto), "metodos": ["texto"]})

    # Los IOCs se sacan de todo el contenido; al modelo solo le llega un texto acotado
    texto_modelo, recortado = recortar(resultado.get("texto", ""), settings.max_caracteres_adjunto)
    if recortado:
        resultado["avisos"].append(
            "El contenido es largo: el modelo recibe el principio y el final, pero los indicadores "
            "se han extraído del fichero completo."
        )
    resultado.update({
        "id": uuid.uuid4().hex[:12],
        "nombre": Path(nombre).name,
        "tipo": tipo,
        "tamano": len(datos),
        "sha256": hashlib.sha256(datos).hexdigest(),
        "creado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "texto": texto_modelo,
        "recortado": recortado,
        "total_iocs": iocs.contar(resultado["iocs"]),
    })
    _guardar(resultado, datos)
    return resultado


def _carpeta(adjunto_id: str) -> Path:
    if not adjunto_id.isalnum():
        raise AdjuntoNoValido("Identificador no válido")
    return settings.adjuntos_dir / adjunto_id


def _guardar(adjunto: dict, datos: bytes) -> None:
    carpeta = _carpeta(adjunto["id"])
    carpeta.mkdir(parents=True, exist_ok=True)
    # El original se guarda como evidencia con un nombre neutro: nunca se ejecuta ni se abre
    (carpeta / "original.bin").write_bytes(datos)
    (carpeta / "analisis.json").write_text(json.dumps(adjunto, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar(adjunto_id: str) -> dict | None:
    try:
        ruta = _carpeta(adjunto_id) / "analisis.json"
    except AdjuntoNoValido:
        return None
    if not ruta.exists():
        return None
    return json.loads(ruta.read_text(encoding="utf-8"))


def resumen_publico(adjunto: dict) -> dict:
    """Lo que ve la extensión (sin el texto completo)."""
    claves = ("id", "nombre", "tipo", "tamano", "sha256", "creado", "metodos", "alertas", "avisos",
              "iocs", "total_iocs", "recortado", "cabeceras", "enlaces", "adjuntos")
    publico = {k: adjunto[k] for k in claves if k in adjunto}
    publico["vista_previa"] = adjunto.get("texto", "")[:1500]
    return publico


def bloque_para_modelo(adjunto: dict, completo: bool = True) -> str:
    """Bloque <adjunto> que se añade al mensaje del usuario."""
    cabecera = f'<adjunto nombre="{adjunto["nombre"]}" tipo="{adjunto["tipo"]}" sha256="{adjunto["sha256"]}">'
    partes = [cabecera]
    if adjunto.get("alertas"):
        partes.append("Alertas del análisis automático:\n" + "\n".join(f"- {a}" for a in adjunto["alertas"]))
    partes.append("Indicadores extraídos automáticamente (fiables):\n" + iocs.como_texto(adjunto["iocs"]))
    texto = adjunto.get("texto", "")
    if not completo:
        texto, _ = recortar(texto, 1500)
    partes.append("Contenido:\n" + texto)
    partes.append("</adjunto>")
    return "\n\n".join(partes)
