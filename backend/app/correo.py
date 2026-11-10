"""Análisis de correos .eml sin abrir enlaces ni adjuntos.

Extrae las cabeceras relevantes, el resultado de SPF/DKIM/DMARC, el recorrido del
correo (cabeceras Received), los enlaces (con el texto que ve el usuario y el destino
real), los adjuntos con su hash, y genera alertas automáticas de suplantación.
Los adjuntos NUNCA se guardan ni se ejecutan: solo se calcula su hash.
"""

import hashlib
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser

from . import iocs

EXTENSIONES_PELIGROSAS = {
    ".exe", ".scr", ".com", ".pif", ".bat", ".cmd", ".js", ".jse", ".vbs", ".vbe", ".wsf", ".hta",
    ".ps1", ".lnk", ".iso", ".img", ".vhd", ".msi", ".jar", ".docm", ".xlsm", ".pptm", ".one",
    ".html", ".htm", ".svg", ".zip", ".rar", ".7z", ".cab",
}
MAX_CUERPO = 20000


class _LectorHTML(HTMLParser):
    """Saca el texto visible y los enlaces (texto mostrado → destino real) de un HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.texto: list[str] = []
        self.enlaces: list[dict] = []
        self._ignorar = 0
        self._enlace: dict | None = None

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "head"}:
            self._ignorar += 1
        elif tag == "a":
            self._enlace = {"url": dict(attrs).get("href") or "", "texto": ""}
        elif tag in {"br", "p", "div", "tr", "li"}:
            self.texto.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "head"} and self._ignorar:
            self._ignorar -= 1
        elif tag == "a" and self._enlace is not None:
            self._enlace["texto"] = self._enlace["texto"].strip()
            if self._enlace["url"]:
                self.enlaces.append(self._enlace)
            self._enlace = None

    def handle_data(self, data):
        if self._ignorar:
            return
        self.texto.append(data)
        if self._enlace is not None:
            self._enlace["texto"] += data


def _dominio_email(direccion: str) -> str | None:
    _, email = parseaddr(direccion or "")
    return email.rsplit("@", 1)[1].lower() if "@" in email else None


def _dominio_base(dominio: str | None) -> str | None:
    """Simplificación: los dos últimos niveles (mail.empresa.com → empresa.com)."""
    if not dominio:
        return None
    partes = dominio.lower().strip(".").split(".")
    return ".".join(partes[-2:]) if len(partes) >= 2 else dominio


def _autenticacion(mensaje: EmailMessage) -> dict:
    resultados = {"spf": None, "dkim": None, "dmarc": None}
    cabeceras = mensaje.get_all("Authentication-Results", []) + mensaje.get_all("ARC-Authentication-Results", [])
    for cabecera in cabeceras:
        for mecanismo, valor in re.findall(r"\b(spf|dkim|dmarc)=(\w+)", str(cabecera), re.IGNORECASE):
            resultados[mecanismo.lower()] = resultados[mecanismo.lower()] or valor.lower()
    if not resultados["spf"]:
        received_spf = mensaje.get("Received-SPF")
        if received_spf:
            resultados["spf"] = str(received_spf).split()[0].lower()
    return resultados


def _cuerpo(mensaje: EmailMessage) -> tuple[str, list[dict]]:
    texto_plano, html = "", ""
    for parte in mensaje.walk():
        if parte.is_multipart() or parte.get_content_disposition() == "attachment":
            continue
        tipo = parte.get_content_type()
        try:
            contenido = parte.get_content()
        except (LookupError, ValueError):
            contenido = (parte.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        if tipo == "text/plain" and not texto_plano:
            texto_plano = contenido
        elif tipo == "text/html" and not html:
            html = contenido

    enlaces: list[dict] = []
    if html:
        lector = _LectorHTML()
        lector.feed(html)
        enlaces = lector.enlaces
        if not texto_plano:
            texto_plano = "".join(lector.texto)
    for url in re.findall(r"https?://[^\s<>\"']+", texto_plano):
        if not any(e["url"] == url for e in enlaces):
            enlaces.append({"url": url, "texto": ""})

    texto_plano = re.sub(r"\n\s*\n+", "\n\n", texto_plano).strip()
    return texto_plano[:MAX_CUERPO], enlaces


def _adjuntos(mensaje: EmailMessage) -> list[dict]:
    adjuntos = []
    for parte in mensaje.iter_attachments():
        datos = parte.get_payload(decode=True) or b""
        nombre = parte.get_filename() or "(sin nombre)"
        extension = ("." + nombre.rsplit(".", 1)[1].lower()) if "." in nombre else ""
        doble_extension = bool(re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png|txt)\.\w+$", nombre, re.IGNORECASE))
        adjuntos.append({
            "nombre": nombre,
            "tipo": parte.get_content_type(),
            "tamano": len(datos),
            "sha256": hashlib.sha256(datos).hexdigest(),
            "peligroso": extension in EXTENSIONES_PELIGROSAS or doble_extension,
        })
    return adjuntos


def analizar(datos: bytes) -> dict:
    mensaje: EmailMessage = BytesParser(policy=policy.default).parsebytes(datos)

    de = str(mensaje.get("From", ""))
    responder_a = str(mensaje.get("Reply-To", ""))
    return_path = str(mensaje.get("Return-Path", ""))
    nombre_visible, email_de = parseaddr(de)

    cabeceras = {
        "de": de,
        "para": ", ".join(e for _, e in getaddresses(mensaje.get_all("To", []))),
        "responder_a": responder_a,
        "return_path": return_path,
        "asunto": str(mensaje.get("Subject", "")),
        "fecha": str(mensaje.get("Date", "")),
        "message_id": str(mensaje.get("Message-ID", "")),
        "x_originating_ip": str(mensaje.get("X-Originating-IP", "")) or None,
        "autenticacion": _autenticacion(mensaje),
        "saltos": [re.sub(r"\s+", " ", str(r)).strip() for r in mensaje.get_all("Received", [])][:12],
    }
    cuerpo, enlaces = _cuerpo(mensaje)
    adjuntos = _adjuntos(mensaje)

    # --- Alertas automáticas -------------------------------------------------
    # Cada alerta explica QUÉ se ha visto y QUÉ SIGNIFICA, para que el modelo no tenga
    # que deducirlo (y no lo interprete al revés).
    alertas: list[str] = []
    dominio_de = _dominio_email(de)
    dominio_responder = _dominio_email(responder_a)
    if responder_a and dominio_responder and _dominio_base(dominio_responder) != _dominio_base(dominio_de):
        alertas.append(
            f"Reply-To desviado: el remitente es {dominio_de}, pero si el usuario responde, la respuesta "
            f"va a {dominio_responder}. Es típico de fraudes que buscan una conversación con la víctima."
        )
    dominio_return = _dominio_email(return_path)
    if return_path and dominio_return and _dominio_base(dominio_return) != _dominio_base(dominio_de):
        alertas.append(
            f"Return-Path distinto: el remitente técnico ({dominio_return}) no coincide con el visible "
            f"({dominio_de}). Puede ser un servicio de envío legítimo o una suplantación; valorar junto a SPF/DMARC."
        )
    if nombre_visible and "@" in nombre_visible:
        email_en_nombre = re.search(r"[\w.+-]+@[\w.-]+", nombre_visible)
        if email_en_nombre and email_en_nombre.group(0).lower() != email_de.lower():
            alertas.append(
                f"Remitente falsificado: el nombre visible es \"{email_en_nombre.group(0)}\" para que el usuario "
                f"crea que escribe esa dirección, pero el correo real es {email_de}."
            )
    significado = {
        "spf": "el servidor que envió el correo no está autorizado por el dominio del remitente",
        "dkim": "la firma digital del correo no es válida: pudo ser alterado o no procede del dominio",
        "dmarc": "el dominio del remitente no supera su propia política contra la suplantación",
    }
    for mecanismo, valor in cabeceras["autenticacion"].items():
        if valor in {"fail", "softfail", "permerror"}:
            alertas.append(f"{mecanismo.upper()} = {valor}: {significado[mecanismo]}.")
        elif valor == "none":
            alertas.append(
                f"{mecanismo.upper()} = none: el correo no tiene esa protección, así que no se puede verificar "
                "su autenticidad por esa vía."
            )
    for enlace in enlaces:
        visible = iocs.extraer(enlace["texto"])
        dominios_visibles = {d["valor"] for d in visible["dominio"]}
        destino = iocs.dominio_de(enlace["url"])
        if dominios_visibles and destino and _dominio_base(destino) not in {_dominio_base(d) for d in dominios_visibles}:
            alertas.append(
                f"Enlace engañoso: el usuario VE el texto \"{', '.join(sorted(dominios_visibles))}\", pero al pulsarlo "
                f"se ABRE {iocs.defang(destino, 'dominio')}, un dominio distinto. Es la técnica clásica de phishing "
                "para robar credenciales."
            )
    for adjunto in adjuntos:
        if adjunto["peligroso"]:
            doble = re.search(r"\.(pdf|docx?|xlsx?|jpe?g|png|txt)\.\w+$", adjunto["nombre"], re.IGNORECASE)
            motivo = ("tiene doble extensión para parecer un documento, pero es un "
                      f"fichero .{adjunto['nombre'].rsplit('.', 1)[1].lower()}") if doble else \
                     "es un tipo de fichero que puede ejecutar código"
            alertas.append(f"Adjunto peligroso: {adjunto['nombre']} {motivo}. No debe abrirse fuera de un entorno aislado.")

    # --- IOCs ------------------------------------------------------------------
    texto_indicadores = "\n".join([
        de, responder_a, return_path, cabeceras["x_originating_ip"] or "", *cabeceras["saltos"],
        cuerpo, *(e["url"] for e in enlaces),
    ])
    indicadores = iocs.extraer(texto_indicadores)
    indicadores = iocs.combinar(indicadores, {
        "hash": [{"valor": a["sha256"], "seguro": a["sha256"], "algoritmo": "sha256"} for a in adjuntos]
    })

    return {
        "tipo": "correo",
        "cabeceras": cabeceras,
        "enlaces": [{"texto": e["texto"][:200], "url": e["url"], "seguro": iocs.defang(e["url"], "url")}
                    for e in enlaces[:50] if e["url"].lower().startswith(("http", "hxxp"))],
        "adjuntos": adjuntos,
        "alertas": alertas,
        "iocs": indicadores,
        "texto": _texto_para_modelo(cabeceras, enlaces, adjuntos, cuerpo),
    }


def _desactivar(texto: str) -> str:
    return re.sub(r"https?://[^\s<>\"']+", lambda m: iocs.defang(m.group(0), "url"), texto)


def _texto_para_modelo(cabeceras: dict, enlaces: list[dict], adjuntos: list[dict], cuerpo: str) -> str:
    aut = cabeceras["autenticacion"]
    lineas = [
        f"De: {cabeceras['de']}",
        f"Para: {cabeceras['para']}",
        f"Responder a: {cabeceras['responder_a'] or '(igual que De)'}",
        f"Return-Path: {cabeceras['return_path'] or '-'}",
        f"Asunto: {cabeceras['asunto']}",
        f"Fecha: {cabeceras['fecha']}",
        f"Autenticación: SPF={aut['spf'] or 'desconocido'}, DKIM={aut['dkim'] or 'desconocido'}, "
        f"DMARC={aut['dmarc'] or 'desconocido'}",
    ]
    if cabeceras["saltos"]:
        lineas.append(f"Primer salto (origen): {iocs.refang(cabeceras['saltos'][-1])[:300]}")
    if enlaces:
        lineas.append("Enlaces (texto visible → destino real):")
        for e in enlaces[:15]:
            lineas.append(f"- \"{_desactivar(e['texto'][:80])}\" → {iocs.defang(e['url'], 'url')}")
    if adjuntos:
        lineas.append("Adjuntos (no se han abierto):")
        for a in adjuntos:
            lineas.append(f"- {a['nombre']} ({a['tipo']}, {a['tamano']} bytes, sha256 {a['sha256']})")
    lineas.append("Cuerpo del mensaje (enlaces desactivados):")
    lineas.append(_desactivar(cuerpo))
    return "\n".join(lineas)
