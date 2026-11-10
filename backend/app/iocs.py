"""Extracción de indicadores de compromiso (IOCs) de cualquier texto.

- Acepta indicadores ya "desactivados" (ejemplo[.]com, hxxp://) y los normaliza.
- Devuelve cada indicador también desactivado, para mostrarlo sin riesgo de clic.
- Marca las IPs internas (privadas, loopback...) para no confundirlas con las del atacante.

La extracción es por patrones: rápida y fiable para lo que aparece literalmente en el
texto. No adivina nada, y por eso el asistente usa esta lista en lugar de "leer" los
indicadores por su cuenta.
"""

import ipaddress
import re
from urllib.parse import urlsplit

from .config import settings

MAX_POR_TIPO = 500

# Extensiones de fichero que parecen dominios ("informe.pdf", "script.py")
EXTENSIONES_FICHERO = {
    "exe", "dll", "js", "vbs", "ps1", "psm1", "bat", "cmd", "scr", "png", "jpg", "jpeg", "gif", "bmp",
    "pdf", "doc", "docx", "docm", "xls", "xlsx", "xlsm", "ppt", "pptx", "rar", "7z", "txt", "log", "csv",
    "json", "xml", "html", "htm", "php", "asp", "aspx", "jsp", "iso", "img", "lnk", "hta", "msi", "eml",
    "msg", "py", "sh", "md", "ini", "cfg", "tmp", "dat", "bin", "sys", "jar", "gz", "tar", "evtx", "ps",
}
# Dominios genéricos frecuentes. Los de dos letras (.es, .ru, .cn...) se aceptan todos.
TLD_GENERICOS = {
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz", "io", "app", "dev", "xyz", "top",
    "online", "site", "club", "shop", "store", "live", "tech", "cloud", "email", "link", "click", "news",
    "pro", "mobi", "name", "icu", "buzz", "cyou", "vip", "work", "support", "help", "services", "zip",
    "mov", "website", "space", "fun", "life", "world", "digital", "network", "host", "page", "blog",
    "today", "lol", "rest", "bond", "sbs", "cfd", "monster", "quest", "loan", "win", "bid", "party",
}

# Dominios legítimos muy suplantados. Que aparezcan en un correo no significa que sean del
# atacante: normalmente son la marca que se está suplantando.
DOMINIOS_CONOCIDOS = {
    "microsoft.com", "microsoftonline.com", "office.com", "office365.com", "outlook.com", "live.com",
    "hotmail.com", "sharepoint.com", "onedrive.com", "windows.net", "azure.com", "google.com",
    "gmail.com", "googleapis.com", "apple.com", "icloud.com", "amazon.com", "amazon.es", "aws.amazon.com",
    "paypal.com", "facebook.com", "instagram.com", "whatsapp.com", "linkedin.com", "twitter.com", "x.com",
    "github.com", "dropbox.com", "docusign.net", "docusign.com", "adobe.com", "zoom.us", "dhl.com",
    "ups.com", "fedex.com", "correos.es", "seg-social.es", "agenciatributaria.gob.es", "agenciatributaria.es",
    "gob.es", "incibe.es", "ccn-cert.cni.es", "aepd.es", "bbva.es", "santander.com", "caixabank.es",
    "ing.es", "bankinter.com", "netflix.com", "spotify.com", "mozilla.org", "w3.org", "schemas.microsoft.com",
}

_URL = re.compile(r"\bhttps?://[^\s<>\"'`]+", re.IGNORECASE)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,24}\b")
_DOMINIO = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}\b", re.IGNORECASE)
_IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?!\d|\.\d)")
_HASH = re.compile(r"\b(?:[a-fA-F0-9]{64}|[a-fA-F0-9]{40}|[a-fA-F0-9]{32})\b")
_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

TIPOS_HASH = {32: "md5", 40: "sha1", 64: "sha256"}


def refang(texto: str) -> str:
    """Convierte indicadores desactivados en su forma real para poder detectarlos."""
    texto = re.sub(r"\[\.\]|\(\.\)|\{\.\}|\[dot\]|\(dot\)", ".", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\[:\]", ":", texto)
    texto = re.sub(r"\[@\]|\[at\]", "@", texto, flags=re.IGNORECASE)
    return re.sub(r"\bhxxp(s?)\b", r"http\1", texto, flags=re.IGNORECASE)


def defang(valor: str, tipo: str) -> str:
    """Versión segura para mostrar: no es clicable ni se resuelve por error."""
    if tipo == "url":
        try:
            partes = urlsplit(valor)
        except ValueError:
            return re.sub(r"^http", "hxxp", valor, flags=re.IGNORECASE).replace(".", "[.]")
        esquema = partes.scheme.lower().replace("http", "hxxp")
        resto = valor[len(partes.scheme) + 3:]
        host = partes.netloc
        return f"{esquema}://{host.replace('.', '[.]')}{resto[len(host):]}"
    if tipo in {"dominio", "ip"}:
        return valor.replace(".", "[.]")
    if tipo == "email":
        usuario, _, dominio = valor.partition("@")
        return f"{usuario}@{dominio.replace('.', '[.]')}"
    return valor


def _limpiar_url(url: str) -> str:
    return url.rstrip(".,;:!?)]}>'\"")


def dominio_de(url_o_email: str) -> str | None:
    if "@" in url_o_email and "://" not in url_o_email:
        return url_o_email.rsplit("@", 1)[1].lower()
    try:
        return (urlsplit(url_o_email).hostname or "").lower() or None
    except ValueError:
        return None


def _dominio_valido(dominio: str) -> bool:
    tld = dominio.rsplit(".", 1)[-1].lower()
    if tld in EXTENSIONES_FICHERO:
        return False
    if len(tld) == 2:
        return True
    return tld in TLD_GENERICOS


def _coincide(dominio: str, lista) -> bool:
    dominio = dominio.lower().strip(".")
    return any(dominio == d or dominio.endswith("." + d) for d in lista)


def clasificar_dominio(dominio: str | None) -> str | None:
    """"propio" (tu organización), "conocido" (legítimo, quizá suplantado) o None."""
    if not dominio:
        return None
    if _coincide(dominio, settings.lista_dominios_propios):
        return "propio"
    if _coincide(dominio, DOMINIOS_CONOCIDOS):
        return "conocido"
    return None


def _es_ip(valor: str) -> bool:
    try:
        ipaddress.ip_address(valor)
        return True
    except ValueError:
        return False


def extraer(texto: str) -> dict[str, list[dict]]:
    """Devuelve {"ip": [...], "dominio": [...], "url": [...], "email": [...], "hash": [...], "cve": [...]}.

    Cada indicador es {"valor", "seguro"} y, según el tipo, "interna" (IP) o "algoritmo" (hash).
    """
    texto = refang(texto or "")
    resultado: dict[str, list[dict]] = {t: [] for t in ("ip", "dominio", "url", "email", "hash", "cve")}
    vistos: set[tuple[str, str]] = set()

    def anadir(tipo: str, valor: str, **extra) -> None:
        clave = (tipo, valor.lower())
        if clave in vistos or len(resultado[tipo]) >= MAX_POR_TIPO:
            return
        vistos.add(clave)
        resultado[tipo].append({"valor": valor, "seguro": defang(valor, tipo), **extra})

    for url in map(_limpiar_url, _URL.findall(texto)):
        anadir("url", url)
        host = dominio_de(url)
        if host and not _es_ip(host) and _dominio_valido(host):
            anadir("dominio", host)

    for email in _EMAIL.findall(texto):
        anadir("email", email)
        dominio = email.rsplit("@", 1)[1].lower()
        if _dominio_valido(dominio):
            anadir("dominio", dominio)

    sin_urls_ni_emails = _EMAIL.sub(" ", _URL.sub(" ", texto))
    for dominio in _DOMINIO.findall(sin_urls_ni_emails):
        if _dominio_valido(dominio) and not _es_ip(dominio):
            anadir("dominio", dominio.lower())

    for ip in _IPV4.findall(texto):
        direccion = ipaddress.ip_address(ip)
        interna = direccion.is_private or direccion.is_loopback or direccion.is_link_local or direccion.is_reserved
        anadir("ip", ip, interna=interna)

    for valor in _HASH.findall(texto):
        if valor.isdigit():  # números largos, no hashes
            continue
        anadir("hash", valor.lower(), algoritmo=TIPOS_HASH[len(valor)])

    for cve in _CVE.findall(texto):
        anadir("cve", cve.upper())

    for tipo in ("dominio", "url", "email"):
        for elemento in resultado[tipo]:
            dominio = elemento["valor"] if tipo == "dominio" else dominio_de(elemento["valor"])
            clase = clasificar_dominio(dominio)
            if clase:
                elemento["legitimo"] = clase

    return resultado


def combinar(*listas: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Une varios resultados de extraer() sin duplicados."""
    total: dict[str, list[dict]] = {t: [] for t in ("ip", "dominio", "url", "email", "hash", "cve")}
    vistos: set[tuple[str, str]] = set()
    for iocs in listas:
        for tipo, elementos in iocs.items():
            for elemento in elementos:
                clave = (tipo, elemento["valor"].lower())
                if clave not in vistos and len(total[tipo]) < MAX_POR_TIPO:
                    vistos.add(clave)
                    total[tipo].append(elemento)
    return total


def contar(iocs: dict[str, list[dict]]) -> int:
    return sum(len(v) for v in iocs.values())


def como_texto(iocs: dict[str, list[dict]]) -> str:
    """Lista legible (y desactivada) para incluir en el contexto del modelo."""
    nombres = {"ip": "IPs", "dominio": "Dominios", "url": "URLs", "email": "Correos",
               "hash": "Hashes", "cve": "Vulnerabilidades"}
    lineas = []
    for tipo, elementos in iocs.items():
        if not elementos:
            continue
        valores = []
        for e in elementos[:40]:
            if e.get("interna"):
                nota = " (IP interna)"
            elif e.get("legitimo") == "propio":
                nota = " (dominio propio)"
            elif e.get("legitimo") == "conocido":
                nota = " (dominio legítimo conocido; posible marca suplantada, no del atacante)"
            elif e.get("algoritmo"):
                nota = f" ({e['algoritmo']})"
            else:
                nota = ""
            valores.append(e["seguro"] + nota)
        resto = f" y {len(elementos) - 40} más" if len(elementos) > 40 else ""
        lineas.append(f"- {nombres[tipo]}: {', '.join(valores)}{resto}")
    return "\n".join(lineas) if lineas else "- Ninguno detectado"
