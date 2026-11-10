"""Informe de un incidente en Markdown y en PDF, generado en local.

El PDF se maqueta con PyMuPDF (ya instalado para leer PDFs), sin servicios externos.
"""

import html
from datetime import datetime

from . import __version__, iocs
from .incidentes import FASES

NOMBRES_IOC = {"ip": "IP", "dominio": "Dominio", "url": "URL", "email": "Correo", "hash": "Hash", "cve": "CVE"}


def _fecha(valor: str | None) -> str:
    if not valor:
        return "-"
    try:
        return datetime.fromisoformat(valor).astimezone().strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return valor


def _duracion(datos: dict) -> str:
    if not datos.get("cerrado"):
        return "en curso"
    horas = (datetime.fromisoformat(datos["cerrado"]) - datetime.fromisoformat(datos["detectado"])).total_seconds() / 3600
    return f"{horas:.1f} horas" if horas < 48 else f"{horas / 24:.1f} días"


def _nota_ioc(elemento: dict) -> str:
    if elemento.get("interna"):
        return "IP interna"
    if elemento.get("legitimo") == "propio":
        return "dominio propio"
    if elemento.get("legitimo") == "conocido":
        return "legítimo conocido (posible marca suplantada)"
    return elemento.get("algoritmo", "")


def _filas_iocs(datos: dict) -> list[tuple[str, str, str]]:
    return [(NOMBRES_IOC[tipo], e["seguro"], _nota_ioc(e))
            for tipo, elementos in datos["iocs"].items() for e in elementos]


def _pasos_por_fase(datos: dict) -> list[tuple[str, list[dict]]]:
    return [(nombre, [p for p in datos["pasos"] if p["fase"] == clave])
            for clave, nombre in FASES.items() if any(p["fase"] == clave for p in datos["pasos"])]


# --- Markdown -----------------------------------------------------------------

def markdown(datos: dict, anexo: bool = True) -> str:
    plazo = datos.get("plazo_aepd")
    progreso = datos["progreso"]
    lineas = [
        f"# Informe de incidente {datos['id']}",
        "",
        f"**{datos['titulo']}**",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Tipo | {datos.get('tipo') or '-'} |",
        f"| Severidad | {datos.get('severidad') or '-'} |",
        f"| Estado | {datos['estado'].capitalize()} |",
        f"| Detectado | {_fecha(datos['detectado'])} |",
        f"| Cerrado | {_fecha(datos.get('cerrado'))} |",
        f"| Duración | {_duracion(datos)} |",
        f"| Pasos completados | {progreso['hechos']} de {progreso['total']} |",
        f"| Datos personales afectados | {'Sí' if datos['datos_personales'] else 'No'} |",
    ]
    if plazo:
        lineas.append(f"| Límite notificación AEPD (72 h) | {_fecha(plazo['limite'])} |")
    lineas += ["", "## Descripción", "", datos.get("descripcion") or "-", ""]

    lineas += ["## Cronología", "", "| Fecha | Suceso |", "|---|---|"]
    lineas += [f"| {_fecha(e['fecha'])} | {e['texto'].replace('|', '/')} |" for e in datos["eventos"]]
    lineas.append("")

    lineas += ["## Procedimiento", ""]
    for nombre, pasos in _pasos_por_fase(datos):
        lineas += [f"### {nombre}", ""]
        for p in pasos:
            marca = "x" if p["hecho"] else " "
            hora = f" — *{_fecha(p['hecho_en'])}*" if p["hecho"] else ""
            nota = f" (nota: {p['nota']})" if p.get("nota") else ""
            lineas.append(f"- [{marca}] {p['texto']}{hora}{nota}")
        lineas.append("")

    filas = _filas_iocs(datos)
    lineas += ["## Indicadores de compromiso", ""]
    if filas:
        lineas += ["| Tipo | Indicador (desactivado) | Nota |", "|---|---|---|"]
        lineas += [f"| {t} | `{v}` | {n} |" for t, v, n in filas]
    else:
        lineas.append("No se han registrado indicadores.")
    lineas.append("")

    if datos["adjuntos"]:
        lineas += ["## Evidencias analizadas", "", "| Fichero | Tipo | SHA-256 |", "|---|---|---|"]
        lineas += [f"| {a['nombre']} | {a['tipo']} | `{a['sha256']}` |" for a in datos["adjuntos"]]
        for a in datos["adjuntos"]:
            if a.get("alertas"):
                lineas += ["", f"Alertas de **{a['nombre']}**:", *(f"- {x}" for x in a["alertas"])]
        lineas.append("")

    lineas += ["## Cierre", "", "### Lo que se hizo", "", datos.get("notas_cierre") or "_Pendiente de cierre._", "",
               "### Lecciones aprendidas", "", datos.get("lecciones") or "-", ""]

    if anexo and datos["mensajes"]:
        lineas += ["## Anexo: consultas al asistente", ""]
        for m in datos["mensajes"]:
            autor = "Usuario" if m["rol"] == "usuario" else "Asistente"
            lineas += [f"**{autor}** · {_fecha(m['fecha'])}", "", m["contenido"], "", "---", ""]

    lineas.append(f"*Generado el {datetime.now():%d/%m/%Y %H:%M} por el Asistente de Incidentes v{__version__} "
                  "(funcionamiento local, sin conexión).*")
    return "\n".join(lineas)


# --- PDF ----------------------------------------------------------------------

CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #16191F; line-height: 1.4; }
h1 { font-size: 20pt; color: #1A3FA0; margin-bottom: 2pt; }
h2 { font-size: 13pt; color: #1A3FA0; margin-top: 14pt; border-bottom: 1px solid #C9D7FA; }
h3 { font-size: 11pt; margin-top: 8pt; margin-bottom: 2pt; }
p { margin-top: 2pt; margin-bottom: 4pt; }
table { width: 100%; border-collapse: collapse; margin-bottom: 6pt; }
td, th { border: 1px solid #D5D9E0; padding: 3pt; font-size: 9pt; vertical-align: top; }
th { font-weight: bold; color: #1A3FA0; text-align: left; }
.sub { color: #5B6370; font-size: 9pt; }
.hecho { color: #1F6B3A; }
.pendiente { color: #8A4200; }
.mono { font-family: monospace; font-size: 8pt; }
.autor { font-size: 10.5pt; margin-top: 10pt; color: #1A3FA0; }
.md-titulo { font-weight: bold; margin-top: 6pt; }
.md-item { margin-left: 12pt; }
"""

# Las fuentes base del PDF solo cubren Latin-1: se sustituyen los símbolos que no lo están
SUSTITUCIONES = {"≠": "!=", "›": ">", "→": "->", "←": "<-", "✓": "[x]", "✔": "[x]", "✗": "[ ]", "⚠": "(!)",
                 "•": "-", "…": "...", "“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "·": "-"}


def _t(texto) -> str:
    texto = "" if texto is None else str(texto)
    for original, sustituto in SUSTITUCIONES.items():
        texto = texto.replace(original, sustituto)
    texto = texto.encode("latin-1", errors="replace").decode("latin-1")
    return html.escape(texto)


def _parrafos(texto: str | None) -> str:
    if not texto:
        return "<p>-</p>"
    return "".join(f"<p>{_t(linea)}</p>" for linea in texto.splitlines() if linea.strip())


def _markdown_a_html(texto: str) -> str:
    """Convierte el Markdown de las respuestas del asistente en HTML sencillo para el PDF."""
    import re

    salida = []
    for linea in texto.splitlines():
        linea = linea.rstrip()
        if not linea.strip() or re.fullmatch(r"\s*-{3,}\s*", linea):
            continue
        titulo = re.match(r"^\s*#{1,6}\s+(.+)$", linea)
        numerada = re.match(r"^\s*(\d+)[.)]\s+(.+)$", linea)
        vineta = re.match(r"^\s*[-*•]\s+(.+)$", linea)
        if titulo:
            contenido, etiqueta = titulo.group(1), "<p class='md-titulo'>{}</p>"
        elif numerada:
            contenido, etiqueta = f"{numerada.group(1)}. {numerada.group(2)}", "<p class='md-item'>{}</p>"
        elif vineta:
            contenido, etiqueta = f"- {vineta.group(1)}", "<p class='md-item'>{}</p>"
        else:
            contenido, etiqueta = linea.strip(), "<p>{}</p>"
        html_linea = _t(contenido)
        html_linea = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html_linea)
        html_linea = re.sub(r"`([^`]+)`", r"<span class='mono'>\1</span>", html_linea)
        salida.append(etiqueta.format(html_linea))
    return "".join(salida) or "<p>-</p>"


def _html(datos: dict, anexo: bool = True) -> str:
    plazo = datos.get("plazo_aepd")
    progreso = datos["progreso"]
    filas_resumen = [
        ("Tipo", datos.get("tipo") or "-"), ("Severidad", datos.get("severidad") or "-"),
        ("Estado", datos["estado"].capitalize()), ("Detectado", _fecha(datos["detectado"])),
        ("Cerrado", _fecha(datos.get("cerrado"))), ("Duración", _duracion(datos)),
        ("Pasos completados", f"{progreso['hechos']} de {progreso['total']}"),
        ("Datos personales afectados", "Sí" if datos["datos_personales"] else "No"),
    ]
    if plazo:
        filas_resumen.append(("Límite notificación AEPD (72 h)", _fecha(plazo["limite"])))

    partes = [
        f"<h1>Informe de incidente</h1><p class='sub'>{_t(datos['id'])}</p>",
        f"<h3>{_t(datos['titulo'])}</h3>",
        "<table>" + "".join(f"<tr><th>{_t(k)}</th><td>{_t(v)}</td></tr>" for k, v in filas_resumen) + "</table>",
        "<h2>Descripción</h2>", _parrafos(datos.get("descripcion")),
        "<h2>Cronología</h2><table><tr><th>Fecha</th><th>Suceso</th></tr>",
        *(f"<tr><td>{_t(_fecha(e['fecha']))}</td><td>{_t(e['texto'])}</td></tr>" for e in datos["eventos"]),
        "</table>", "<h2>Procedimiento</h2>",
    ]
    for nombre, pasos in _pasos_por_fase(datos):
        partes.append(f"<h3>{_t(nombre)}</h3>")
        for p in pasos:
            if p["hecho"]:
                partes.append(f"<p class='hecho'>[x] {_t(p['texto'])} <span class='sub'>({_t(_fecha(p['hecho_en']))})</span></p>")
            else:
                partes.append(f"<p class='pendiente'>[ ] {_t(p['texto'])}</p>")

    partes.append("<h2>Indicadores de compromiso</h2>")
    filas = _filas_iocs(datos)
    if filas:
        partes.append("<table><tr><th>Tipo</th><th>Indicador (desactivado)</th><th>Nota</th></tr>")
        partes += [f"<tr><td>{_t(t)}</td><td class='mono'>{_t(v)}</td><td>{_t(n)}</td></tr>" for t, v, n in filas]
        partes.append("</table>")
    else:
        partes.append("<p>No se han registrado indicadores.</p>")

    if datos["adjuntos"]:
        partes.append("<h2>Evidencias analizadas</h2><table><tr><th>Fichero</th><th>Tipo</th><th>SHA-256</th></tr>")
        partes += [f"<tr><td>{_t(a['nombre'])}</td><td>{_t(a['tipo'])}</td><td class='mono'>{_t(a['sha256'])}</td></tr>"
                   for a in datos["adjuntos"]]
        partes.append("</table>")
        for a in datos["adjuntos"]:
            if a.get("alertas"):
                partes.append(f"<p><b>Alertas de {_t(a['nombre'])}:</b></p>")
                partes += [f"<p>- {_t(x)}</p>" for x in a["alertas"]]

    partes += ["<h2>Cierre</h2><h3>Lo que se hizo</h3>",
               _parrafos(datos.get("notas_cierre") or "Pendiente de cierre."),
               "<h3>Lecciones aprendidas</h3>", _parrafos(datos.get("lecciones"))]

    if anexo and datos["mensajes"]:
        partes.append("<h2>Anexo: consultas al asistente</h2>")
        for m in datos["mensajes"]:
            autor = "Usuario" if m["rol"] == "usuario" else "Asistente"
            partes.append(f"<p class='autor'><b>{autor}</b> - {_t(_fecha(m['fecha']))}</p>")
            partes.append(_markdown_a_html(m["contenido"]))

    partes.append(f"<p class='sub'>Generado el {datetime.now():%d/%m/%Y %H:%M} por el Asistente de Incidentes "
                  f"v{__version__} (funcionamiento local, sin conexión).</p>")
    return "<html><body>" + "".join(partes) + "</body></html>"


def pdf(datos: dict, anexo: bool = True) -> bytes:
    import io

    import pymupdf

    buffer = io.BytesIO()
    historia = pymupdf.Story(html=_html(datos, anexo), user_css=CSS)
    escritor = pymupdf.DocumentWriter(buffer)
    pagina = pymupdf.paper_rect("a4")
    zona = pagina + (50, 50, -50, -60)
    hay_mas = True
    while hay_mas:
        dispositivo = escritor.begin_page(pagina)
        hay_mas, _ = historia.place(zona)
        historia.draw(dispositivo)
        escritor.end_page()
    escritor.close()

    # Pie de página con número de página
    documento = pymupdf.open("pdf", buffer.getvalue())
    total = documento.page_count
    for numero, hoja in enumerate(documento, start=1):
        hoja.insert_text((50, pagina.height - 30), f"{datos['id']} - Página {numero} de {total}",
                         fontsize=8, color=(0.36, 0.39, 0.44))
    resultado = documento.tobytes(garbage=3, deflate=True)
    documento.close()
    return resultado
