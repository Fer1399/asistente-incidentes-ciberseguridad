"""Fichas de incidente: datos, pasos, cronología y memoria.

Una ficha recoge un incidente de principio a fin:
- los pasos propuestos por el asistente (como checklist con la hora de cada paso hecho),
- la cronología de lo que pasa (creación, pasos, notas, adjuntos, cierre),
- la conversación con el asistente y los adjuntos analizados,
- al cerrarla, las notas de lo que se hizo realmente y las lecciones aprendidas.

Solo las fichas CERRADAS Y REVISADAS pasan a la memoria del asistente (D-12).
"""

import json
import re
import secrets
from datetime import datetime, timedelta, timezone

from . import adjuntos as adjuntos_mod
from . import db, iocs

FASES = {
    "inmediatas": "Acciones inmediatas",
    "evidencias": "Preservación de evidencias",
    "contencion": "Contención",
    "analisis": "Análisis del alcance",
    "erradicacion": "Erradicación y recuperación",
    "notificacion": "Notificación",
    "lecciones": "Lecciones aprendidas",
    "otros": "Otros pasos",
}
SEVERIDADES = ("Baja", "Media", "Alta", "Crítica")
PLAZO_AEPD_HORAS = 72

# Título de apartado de la respuesta → fase. None = apartado que no contiene pasos.
_APARTADOS = [
    (r"inmediat", "inmediatas"),
    (r"evidencia", "evidencias"),
    (r"contenci", "contencion"),
    (r"artefacto|similar|mitre|pregunta", None),
    (r"alcance|an[aá]lisis", "analisis"),
    (r"erradic|recuperaci", "erradicacion"),
    (r"notific", "notificacion"),
    (r"lecci", "lecciones"),
]


# --- Utilidades ---------------------------------------------------------------

def nuevo_id() -> str:
    return f"INC-{datetime.now():%Y%m%d}-{secrets.token_hex(2).upper()}"


def _fila(fila) -> dict | None:
    if fila is None:
        return None
    datos = dict(fila)
    for clave in ("datos_personales", "en_memoria", "hecho"):
        if clave in datos:
            datos[clave] = bool(datos[clave])
    return datos


def registrar_evento(con, incidente_id: str, tipo: str, texto: str) -> None:
    con.execute(
        "INSERT INTO eventos (incidente_id, fecha, tipo, texto) VALUES (?, ?, ?, ?)",
        (incidente_id, db.ahora(), tipo, texto),
    )


def _tocar(con, incidente_id: str) -> None:
    con.execute("UPDATE incidentes SET actualizado = ? WHERE id = ?", (db.ahora(), incidente_id))


# --- Lectura de la respuesta del asistente ----------------------------------

def _limpiar_paso(texto: str) -> str:
    texto = re.sub(r"\s*\[\d+(?:\s*,\s*\d+)*\]", "", texto)  # quita las citas [n]
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"`([^`]+)`", r"\1", texto)
    return texto.strip(" .-*").strip() + "."


def extraer_pasos(respuesta: str) -> list[dict]:
    """Convierte los apartados numerados de la respuesta en pasos con su fase."""
    pasos, fase = [], None
    for linea in respuesta.splitlines():
        titulo = re.match(r"^\s*#{2,4}\s*(.+)$", linea)
        if titulo:
            fase = None
            for patron, destino in _APARTADOS:
                if re.search(patron, titulo.group(1), re.IGNORECASE):
                    fase = destino
                    break
            continue
        item = re.match(r"^\s*(?:\d+[.)]|[-*•])\s+(.+)$", linea)
        if fase and item:
            texto = _limpiar_paso(item.group(1))
            if len(texto) > 3:
                pasos.append({"fase": fase, "texto": texto})
    return pasos


def extraer_clasificacion(respuesta: str) -> dict:
    """Tipo y severidad de la línea "Tipo de incidente: X · Severidad estimada: Y"."""
    resultado = {}
    tipo = re.search(r"Tipo de incidente\W*([^·\n*|]+)", respuesta, re.IGNORECASE)
    if tipo:
        resultado["tipo"] = tipo.group(1).strip(" :.")[:80]
    severidad = re.search(r"Severidad estimada\W*(Baja|Media|Alta|Cr[ií]tica)", respuesta, re.IGNORECASE)
    if severidad:
        valor = severidad.group(1).capitalize()
        resultado["severidad"] = "Crítica" if valor.lower().startswith("cr") else valor
    return resultado


# --- Crear y consultar ----------------------------------------------------------

def _pregunta_de_la_respuesta(mensajes: list[dict], respuesta: str | None) -> str:
    """La pregunta que originó la respuesta con la que se crea la ficha.

    Si no se encuentra, la última pregunta con contenido (no la primera, que puede ser
    un saludo o un comando escrito por error).
    """
    for i in range(len(mensajes) - 1, 0, -1):
        if mensajes[i]["rol"] == "asistente" and (not respuesta or mensajes[i]["contenido"] == respuesta):
            if mensajes[i - 1]["rol"] == "usuario":
                return mensajes[i - 1]["contenido"]
    preguntas = [m["contenido"] for m in mensajes if m["rol"] == "usuario" and len(m["contenido"].strip()) >= 15]
    return preguntas[-1] if preguntas else next((m["contenido"] for m in mensajes if m["rol"] == "usuario"), "")


def crear(
    titulo: str | None = None,
    tipo: str | None = None,
    severidad: str | None = None,
    descripcion: str | None = None,
    datos_personales: bool = False,
    respuesta_asistente: str | None = None,
    mensajes: list[dict] | None = None,
    adjuntos: list[str] | None = None,
) -> dict:
    clasificacion = extraer_clasificacion(respuesta_asistente or "")
    tipo = tipo or clasificacion.get("tipo")
    severidad = severidad or clasificacion.get("severidad")
    if not descripcion and mensajes:
        descripcion = _pregunta_de_la_respuesta(mensajes, respuesta_asistente)[:2000]
    incidente_id = nuevo_id()
    momento = db.ahora()
    titulo = (titulo or tipo or "Incidente sin clasificar")[:150]

    with db.conexion() as con:
        con.execute(
            "INSERT INTO incidentes (id, titulo, tipo, severidad, descripcion, datos_personales, detectado, creado, actualizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (incidente_id, titulo, tipo, severidad, descripcion, int(datos_personales), momento, momento, momento),
        )
        for orden, paso in enumerate(extraer_pasos(respuesta_asistente or ""), start=1):
            con.execute(
                "INSERT INTO pasos (incidente_id, fase, texto, orden, origen) VALUES (?, ?, ?, ?, 'asistente')",
                (incidente_id, paso["fase"], paso["texto"], orden),
            )
        for mensaje in mensajes or []:
            con.execute(
                "INSERT INTO mensajes (incidente_id, fecha, rol, contenido, adjuntos) VALUES (?, ?, ?, ?, ?)",
                (incidente_id, momento, mensaje["rol"], mensaje["contenido"], json.dumps(mensaje.get("adjuntos", []))),
            )
        ids_adjuntos = set(adjuntos or []) | {a for m in mensajes or [] for a in m.get("adjuntos", [])}
        for adjunto_id in ids_adjuntos:
            if adjuntos_mod.cargar(adjunto_id):
                con.execute("INSERT OR IGNORE INTO incidente_adjuntos VALUES (?, ?)", (incidente_id, adjunto_id))
        registrar_evento(con, incidente_id, "creado", f"Ficha creada: {titulo}")
    return detalle(incidente_id)


def obtener(incidente_id: str) -> dict | None:
    with db.conexion() as con:
        return _fila(con.execute("SELECT * FROM incidentes WHERE id = ?", (incidente_id,)).fetchone())


def plazo_aepd(incidente: dict) -> dict | None:
    """Si hay datos personales afectados: límite de 72 h desde la detección."""
    if not incidente["datos_personales"]:
        return None
    limite = datetime.fromisoformat(incidente["detectado"]) + timedelta(hours=PLAZO_AEPD_HORAS)
    restantes = (limite - datetime.now(timezone.utc)).total_seconds() / 3600
    return {"limite": limite.isoformat(timespec="minutes"), "horas_restantes": round(restantes, 1),
            "vencido": restantes < 0}


def listar(estado: str | None = None, texto: str | None = None) -> list[dict]:
    consulta = (
        "SELECT i.*, "
        "(SELECT COUNT(*) FROM pasos p WHERE p.incidente_id = i.id) AS pasos_total, "
        "(SELECT COUNT(*) FROM pasos p WHERE p.incidente_id = i.id AND p.hecho = 1) AS pasos_hechos "
        "FROM incidentes i WHERE 1 = 1"
    )
    parametros: list = []
    if estado:
        consulta += " AND i.estado = ?"
        parametros.append(estado)
    if texto:
        consulta += " AND (i.titulo LIKE ? OR i.tipo LIKE ? OR i.descripcion LIKE ? OR i.id LIKE ? OR i.notas_cierre LIKE ?)"
        parametros.extend([f"%{texto}%"] * 5)
    consulta += " ORDER BY i.creado DESC"
    with db.conexion() as con:
        filas = [_fila(f) for f in con.execute(consulta, parametros).fetchall()]
    for fila in filas:
        fila["plazo_aepd"] = plazo_aepd(fila)
    return filas


def detalle(incidente_id: str) -> dict | None:
    incidente = obtener(incidente_id)
    if not incidente:
        return None
    with db.conexion() as con:
        pasos = [_fila(f) for f in con.execute(
            "SELECT * FROM pasos WHERE incidente_id = ? ORDER BY orden, id", (incidente_id,))]
        eventos = [dict(f) for f in con.execute(
            "SELECT fecha, tipo, texto FROM eventos WHERE incidente_id = ? ORDER BY fecha, id", (incidente_id,))]
        mensajes = [dict(f) for f in con.execute(
            "SELECT id, fecha, rol, contenido, adjuntos FROM mensajes WHERE incidente_id = ? ORDER BY id", (incidente_id,))]
        ids = [f["adjunto_id"] for f in con.execute(
            "SELECT adjunto_id FROM incidente_adjuntos WHERE incidente_id = ?", (incidente_id,))]
    for mensaje in mensajes:
        mensaje["adjuntos"] = json.loads(mensaje["adjuntos"])
    # El mismo fichero adjuntado dos veces (mismo SHA-256) se muestra una sola vez
    lista_adjuntos, vistos = [], set()
    for adjunto in (adjuntos_mod.cargar(i) for i in ids):
        if adjunto and adjunto["sha256"] not in vistos:
            vistos.add(adjunto["sha256"])
            lista_adjuntos.append(adjunto)

    indicadores = iocs.combinar(
        *(a["iocs"] for a in lista_adjuntos),
        *(iocs.extraer(m["contenido"]) for m in mensajes if m["rol"] == "usuario"),
        iocs.extraer(incidente.get("descripcion") or ""),
    )
    return {
        **incidente,
        "plazo_aepd": plazo_aepd(incidente),
        "pasos": pasos,
        "progreso": {"hechos": sum(p["hecho"] for p in pasos), "total": len(pasos)},
        "eventos": eventos,
        "mensajes": mensajes,
        "adjuntos": [
            {k: a.get(k) for k in ("id", "nombre", "tipo", "tamano", "sha256", "alertas", "creado")}
            for a in lista_adjuntos
        ],
        "iocs": indicadores,
        "fases": FASES,
    }


# --- Modificar ----------------------------------------------------------------

CAMPOS_EDITABLES = {"titulo", "tipo", "severidad", "descripcion", "datos_personales", "detectado"}


def actualizar(incidente_id: str, **campos) -> None:
    campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITABLES and v is not None}
    if not campos:
        return
    if "datos_personales" in campos:
        campos["datos_personales"] = int(campos["datos_personales"])
    asignaciones = ", ".join(f"{c} = ?" for c in campos)
    with db.conexion() as con:
        con.execute(f"UPDATE incidentes SET {asignaciones} WHERE id = ?", (*campos.values(), incidente_id))
        cambios = ", ".join(f"{c}: {v}" for c, v in campos.items() if c != "descripcion")
        registrar_evento(con, incidente_id, "edicion", f"Datos actualizados ({cambios or 'descripción'})")
        _tocar(con, incidente_id)


def anadir_paso(incidente_id: str, fase: str, texto: str) -> dict:
    with db.conexion() as con:
        orden = con.execute("SELECT COALESCE(MAX(orden), 0) + 1 FROM pasos WHERE incidente_id = ?",
                            (incidente_id,)).fetchone()[0]
        cursor = con.execute(
            "INSERT INTO pasos (incidente_id, fase, texto, orden, origen) VALUES (?, ?, ?, ?, 'usuario')",
            (incidente_id, fase, texto, orden),
        )
        registrar_evento(con, incidente_id, "paso", f"Paso añadido ({FASES[fase]}): {texto}")
        _tocar(con, incidente_id)
        return _fila(con.execute("SELECT * FROM pasos WHERE id = ?", (cursor.lastrowid,)).fetchone())


def actualizar_paso(incidente_id: str, paso_id: int, hecho: bool | None = None,
                    texto: str | None = None, nota: str | None = None) -> dict | None:
    with db.conexion() as con:
        paso = _fila(con.execute("SELECT * FROM pasos WHERE id = ? AND incidente_id = ?",
                                 (paso_id, incidente_id)).fetchone())
        if not paso:
            return None
        if hecho is not None and hecho != paso["hecho"]:
            con.execute("UPDATE pasos SET hecho = ?, hecho_en = ? WHERE id = ?",
                        (int(hecho), db.ahora() if hecho else None, paso_id))
            registrar_evento(con, incidente_id, "paso",
                             f"{'Hecho' if hecho else 'Desmarcado'}: {texto or paso['texto']}")
        if texto is not None:
            con.execute("UPDATE pasos SET texto = ? WHERE id = ?", (texto, paso_id))
        if nota is not None:
            con.execute("UPDATE pasos SET nota = ? WHERE id = ?", (nota, paso_id))
        _tocar(con, incidente_id)
        return _fila(con.execute("SELECT * FROM pasos WHERE id = ?", (paso_id,)).fetchone())


def borrar_paso(incidente_id: str, paso_id: int) -> bool:
    with db.conexion() as con:
        cursor = con.execute("DELETE FROM pasos WHERE id = ? AND incidente_id = ?", (paso_id, incidente_id))
        if cursor.rowcount:
            _tocar(con, incidente_id)
        return bool(cursor.rowcount)


def anadir_nota(incidente_id: str, texto: str) -> None:
    with db.conexion() as con:
        registrar_evento(con, incidente_id, "nota", texto)
        _tocar(con, incidente_id)


def anadir_mensajes(incidente_id: str, mensajes: list[dict]) -> None:
    """Guarda en la ficha un intercambio del chat y vincula sus adjuntos."""
    with db.conexion() as con:
        for mensaje in mensajes:
            con.execute(
                "INSERT INTO mensajes (incidente_id, fecha, rol, contenido, adjuntos) VALUES (?, ?, ?, ?, ?)",
                (incidente_id, db.ahora(), mensaje["rol"], mensaje["contenido"],
                 json.dumps(mensaje.get("adjuntos", []))),
            )
            for adjunto_id in mensaje.get("adjuntos", []):
                nuevo = con.execute("INSERT OR IGNORE INTO incidente_adjuntos VALUES (?, ?)",
                                    (incidente_id, adjunto_id)).rowcount
                if nuevo:
                    adjunto = adjuntos_mod.cargar(adjunto_id)
                    registrar_evento(con, incidente_id, "adjunto",
                                     f"Adjunto analizado: {adjunto['nombre'] if adjunto else adjunto_id}")
        registrar_evento(con, incidente_id, "chat", "Consulta al asistente")
        _tocar(con, incidente_id)


def borrar_mensaje(incidente_id: str, mensaje_id: int) -> bool:
    """Quita de la ficha un mensaje que no aporta (una prueba, un comando escrito por error...)."""
    with db.conexion() as con:
        fila = con.execute("SELECT rol, contenido FROM mensajes WHERE id = ? AND incidente_id = ?",
                           (mensaje_id, incidente_id)).fetchone()
        if not fila:
            return False
        con.execute("DELETE FROM mensajes WHERE id = ?", (mensaje_id,))
        autor = "del usuario" if fila["rol"] == "usuario" else "del asistente"
        resumen = fila["contenido"].strip().replace("\n", " ")[:60]
        registrar_evento(con, incidente_id, "edicion", f"Mensaje {autor} quitado de la conversación: «{resumen}»")
        _tocar(con, incidente_id)
    return True


def vincular_adjunto(incidente_id: str, adjunto_id: str) -> bool:
    adjunto = adjuntos_mod.cargar(adjunto_id)
    if not adjunto:
        return False
    with db.conexion() as con:
        if con.execute("INSERT OR IGNORE INTO incidente_adjuntos VALUES (?, ?)", (incidente_id, adjunto_id)).rowcount:
            registrar_evento(con, incidente_id, "adjunto", f"Adjunto analizado: {adjunto['nombre']}")
            _tocar(con, incidente_id)
    return True


# --- Cerrar, reabrir y memoria -----------------------------------------------

def cerrar(incidente_id: str, notas_cierre: str, lecciones: str | None, guardar_en_memoria: bool) -> None:
    with db.conexion() as con:
        con.execute(
            "UPDATE incidentes SET estado = 'cerrado', cerrado = ?, notas_cierre = ?, lecciones = ?, "
            "en_memoria = ? WHERE id = ?",
            (db.ahora(), notas_cierre, lecciones, int(guardar_en_memoria), incidente_id),
        )
        registrar_evento(con, incidente_id, "estado",
                         "Incidente cerrado" + (" y guardado en la memoria" if guardar_en_memoria else ""))
        _tocar(con, incidente_id)


def reabrir(incidente_id: str) -> None:
    with db.conexion() as con:
        con.execute("UPDATE incidentes SET estado = 'abierto', cerrado = NULL, en_memoria = 0 WHERE id = ?",
                    (incidente_id,))
        registrar_evento(con, incidente_id, "estado", "Incidente reabierto (retirado de la memoria)")
        _tocar(con, incidente_id)


def borrar(incidente_id: str) -> None:
    with db.conexion() as con:
        con.execute("DELETE FROM incidentes WHERE id = ?", (incidente_id,))


def _duracion(inicio: str, fin: str | None) -> str:
    if not fin:
        return "-"
    horas = (datetime.fromisoformat(fin) - datetime.fromisoformat(inicio)).total_seconds() / 3600
    return f"{horas:.1f} h" if horas < 48 else f"{horas / 24:.1f} días"


def texto_memoria(datos: dict) -> str:
    """Lo que el asistente "recuerda" de un incidente cerrado."""
    hechos = [p for p in datos["pasos"] if p["hecho"]]
    pendientes = [p for p in datos["pasos"] if not p["hecho"]]
    lineas = [
        f"Incidente anterior {datos['id']}: {datos['titulo']}",
        f"Tipo: {datos.get('tipo') or '-'} · Severidad: {datos.get('severidad') or '-'} · "
        f"Detectado: {datos['detectado'][:16]} · Cerrado: {(datos.get('cerrado') or '-')[:16]} · "
        f"Duración: {_duracion(datos['detectado'], datos.get('cerrado'))}",
        f"Datos personales afectados: {'sí' if datos['datos_personales'] else 'no'}",
        "",
        f"Descripción: {datos.get('descripcion') or '-'}",
        "",
        "Indicadores del incidente:",
        iocs.como_texto(datos["iocs"]),
        "",
        "Lo que se hizo realmente (notas de cierre revisadas):",
        datos.get("notas_cierre") or "-",
        "",
        "Pasos realizados:",
        *(f"- [{FASES.get(p['fase'], p['fase'])}] {p['texto']}" for p in hechos),
    ]
    if pendientes:
        lineas += ["", "Pasos propuestos que no se realizaron:",
                   *(f"- [{FASES.get(p['fase'], p['fase'])}] {p['texto']}" for p in pendientes)]
    if datos.get("lecciones"):
        lineas += ["", "Lecciones aprendidas:", datos["lecciones"]]
    return "\n".join(lineas)
