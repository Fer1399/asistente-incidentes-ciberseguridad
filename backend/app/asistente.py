"""Lógica del asistente: recuperar contexto y preparar la conversación para el modelo."""

from .adjuntos import bloque_para_modelo
from .config import settings
from .prompts import SYSTEM_PROMPT, mensaje_con_contexto

ROLES = {"usuario": "user", "asistente": "assistant"}
MIN_CARACTERES_CONSULTA = 60


def consulta_de_busqueda(mensajes: list[dict], adjuntos_ultimo: list[dict] | None = None) -> str:
    """Texto con el que se busca en la base de conocimiento.

    - Una pregunta de seguimiento corta ("¿y si ya ha hecho clic?") no tiene sentido por
      sí sola, así que se le añade la pregunta anterior del usuario.
    - Si la pregunta lleva adjuntos, se añade un resumen (tipo, alertas, asunto y el
      principio del contenido) para encontrar el playbook adecuado.
    """
    preguntas = [m["contenido"] for m in mensajes if m["rol"] == "usuario"]
    consulta = preguntas[-1]
    if len(consulta) < MIN_CARACTERES_CONSULTA and len(preguntas) > 1:
        consulta = f"{preguntas[-2]}\n{consulta}"
    for adjunto in adjuntos_ultimo or []:
        resumen = [f"Adjunto de tipo {adjunto['tipo']}"]
        if adjunto.get("cabeceras"):
            resumen.append(f"Correo con asunto: {adjunto['cabeceras'].get('asunto', '')}")
        resumen.extend(adjunto.get("alertas", [])[:5])
        resumen.append(adjunto.get("texto", "")[:500])
        consulta += "\n" + "\n".join(resumen)
    return consulta


def expandir_adjuntos(mensajes: list[dict], adjuntos_por_mensaje: list[list[dict]]) -> list[dict]:
    """Incorpora los adjuntos al texto de cada mensaje del usuario.

    El último mensaje con adjuntos los lleva completos; los anteriores, resumidos,
    para no llenar la memoria del modelo en conversaciones largas.
    """
    ultimo_con_adjuntos = max((i for i, a in enumerate(adjuntos_por_mensaje) if a), default=-1)
    expandidos = []
    for i, (mensaje, adjuntos_mensaje) in enumerate(zip(mensajes, adjuntos_por_mensaje)):
        if not adjuntos_mensaje:
            expandidos.append(mensaje)
            continue
        bloques = [bloque_para_modelo(a, completo=(i == ultimo_con_adjuntos)) for a in adjuntos_mensaje]
        expandidos.append({**mensaje, "contenido": "\n\n".join(bloques) + "\n\n" + mensaje["contenido"]})
    return expandidos


def con_cabecera_de_playbook(resultados: list[dict], almacen) -> list[dict]:
    """Añade la cabecera del playbook más relevante si la búsqueda no la ha traído.

    La cabecera (primer fragmento) contiene el tipo de incidente y sus técnicas MITRE
    ATT&CK con el nombre correcto: así el modelo no tiene que inventarlas.
    """
    principal = next((r for r in resultados
                      if r.get("origen") == "incluido" and "Playbook" in (r.get("seccion") or "")), None)
    if not principal or any(r.get("doc_id") == principal["doc_id"] and r.get("fragmento") == 0 for r in resultados):
        return resultados
    cabecera = almacen.fragmento(principal["doc_id"], 0)
    if not cabecera:
        return resultados
    posicion = resultados.index(principal) + 1
    return [*resultados[:posicion], {**cabecera, "similitud": principal["similitud"]}, *resultados[posicion:]]


def seleccionar_fuentes(resultados: list[dict]) -> list[dict]:
    """Descarta lo poco relacionado y numera las fuentes para que el modelo las cite."""
    fuentes = []
    for resultado in resultados:
        if resultado["similitud"] < settings.similitud_minima:
            continue
        fuentes.append({**resultado, "n": len(fuentes) + 1})
    return fuentes


def construir_mensajes(mensajes: list[dict], fuentes: list[dict]) -> list[dict]:
    """System prompt + historial reciente + última pregunta con el contexto del RAG."""
    historial = mensajes[-settings.max_mensajes_historial:]
    salida = [{"role": "system", "content": SYSTEM_PROMPT}]
    for mensaje in historial[:-1]:
        salida.append({"role": ROLES[mensaje["rol"]], "content": mensaje["contenido"]})
    salida.append({"role": "user", "content": mensaje_con_contexto(historial[-1]["contenido"], fuentes)})
    return salida


def fuente_publica(fuente: dict) -> dict:
    """Lo que la extensión muestra de cada fuente (sin el texto completo)."""
    return {
        "n": fuente["n"],
        "documento": fuente["documento"],
        "pagina": fuente.get("pagina"),
        "seccion": fuente.get("seccion"),
        "tipo": fuente.get("tipo", "documento"),
        "doc_id": fuente.get("doc_id"),
        "similitud": fuente["similitud"],
        "extracto": fuente["texto"][:280],
    }
