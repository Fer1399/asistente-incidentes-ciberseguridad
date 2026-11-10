"""Consola para hablar con el asistente sin la extensión de Chrome.

Uso (con el backend en marcha):
    scripts\\preguntar.bat                                     conversación interactiva
    scripts\\preguntar.bat "me ha llegado un phishing y..."    una sola pregunta
    scripts\\preguntar.bat -a correo.eml "¿es phishing?"       una pregunta con adjunto

En la conversación interactiva:
    /adjuntar RUTA   analiza un fichero (.eml, log, PDF, captura) y lo une a la siguiente pregunta
    /ficha           crea una ficha de incidente con esta conversación (y guarda las siguientes)
    /incidentes      lista las fichas
    /informe ID      guarda el informe de una ficha en Markdown y PDF en la carpeta actual
    /nueva           empezar una conversación nueva
    /salir           terminar
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

from app.config import settings
from app.iocs import como_texto

URL = f"http://{settings.host}:{settings.port}"
COMANDOS = ("adjuntar", "ficha", "incidentes", "informe", "nueva", "salir")


def hora_local(valor: str) -> str:
    try:
        return datetime.fromisoformat(valor).astimezone().strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return valor
TIEMPO = httpx.Timeout(10.0, read=900.0)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def adjuntar(ruta_texto: str) -> str | None:
    """Sube un fichero a /adjuntos, muestra el análisis y devuelve su id."""
    ruta = Path(ruta_texto.strip().strip('"'))
    if not ruta.is_absolute():
        # preguntar.bat cambia de carpeta: las rutas relativas son desde donde lo lanzaste
        ruta = Path(os.environ.get("PREGUNTAR_ORIGEN", os.getcwd())) / ruta
    if not ruta.is_file():
        print(f"[ERROR] No existe el fichero: {ruta}")
        return None
    print(f"Analizando {ruta.name}... (una captura puede tardar si se usa el modelo de visión)")
    with httpx.Client(timeout=TIEMPO, trust_env=False) as cliente, ruta.open("rb") as f:
        respuesta = cliente.post(f"{URL}/adjuntos", files={"fichero": (ruta.name, f)})
    if respuesta.status_code != 200:
        print(f"[ERROR {respuesta.status_code}] {respuesta.json().get('detail', respuesta.text)}")
        return None
    analisis = respuesta.json()
    print(f"\n[{analisis['tipo']}] {analisis['nombre']} · sha256 {analisis['sha256'][:16]}… · métodos: {', '.join(analisis['metodos'])}")
    for alerta in analisis.get("alertas", []):
        print(f"  ⚠ {alerta}")
    for aviso in analisis.get("avisos", []):
        print(f"  · {aviso}")
    print(f"Indicadores ({analisis['total_iocs']}):\n{como_texto(analisis['iocs'])}")
    return analisis["id"]


PARECE_POWERSHELL = re.compile(
    r"^\s*(start|cd|dir|ls|cls|copy|del|scripts\\|\.\\|powershell|winget|ollama|Expand-Archive|Get-\w+|Set-\w+|&\s)",
    re.IGNORECASE,
)


def preguntar_si(texto: str, por_defecto: bool = True) -> bool:
    opciones = "(S/n)" if por_defecto else "(s/N)"
    respuesta = input(f"{texto} {opciones}: ").strip().lower()
    return por_defecto if not respuesta else respuesta in ("s", "si", "sí")


def revisar_entrada(entrada: str) -> str | None:
    """Evita que comandos mal escritos lleguen al asistente (y a la ficha).

    Devuelve la línea a procesar (quizá corregida) o None si no hay que hacer nada.
    """
    palabras = entrada.split()
    # "ficha" sin barra
    if palabras[0].lower() in COMANDOS and len(palabras) <= 2:
        if preguntar_si(f"¿Querías decir /{entrada}?"):
            return "/" + entrada
    # Línea que empieza por / pero no es un comando conocido ("/salir/salir", "/fichas")
    if entrada.startswith("/"):
        nombre = re.match(r"/(\w+)", entrada)
        if not nombre or nombre.group(1).lower() not in COMANDOS or re.match(r"/\w+/", entrada):
            print("Comando no reconocido; no se ha enviado nada. Comandos: " + ", ".join("/" + c for c in COMANDOS))
            return None
        return entrada
    # Pregunta con un comando pegado al final ("¿cómo procedo?/nueva")
    pegado = re.search(r"\s*/(" + "|".join(COMANDOS) + r")\b.*$", entrada)
    if pegado:
        pregunta, comando = entrada[:pegado.start()].strip(), pegado.group(0).strip()
        print(f"Los comandos van solos en su línea. He separado «{comando}» de la pregunta.")
        if pregunta and preguntar_si(f"¿Enviar la pregunta «{pregunta[:60]}» sin el comando?"):
            print(f"Cuando termine la respuesta, escribe {comando} en una línea nueva.")
            return pregunta
        return None
    # Algo que parece un comando de PowerShell escrito en la ventana equivocada
    if PARECE_POWERSHELL.match(entrada):
        print("Esto parece un comando de PowerShell: escríbelo en otra ventana, no en la del asistente.")
        if not preguntar_si("¿Enviarlo igualmente al asistente como pregunta?", por_defecto=False):
            return None
    return entrada


def crear_ficha(historial: list[dict]) -> str | None:
    ultima_respuesta = next((m["contenido"] for m in reversed(historial) if m["rol"] == "asistente"), None)
    if not ultima_respuesta:
        print("Primero pregunta algo al asistente: la ficha se crea a partir de su respuesta.")
        return None
    datos = input("¿Hay datos personales afectados? (s/N): ").strip().lower().startswith("s")
    titulo = input("Título (Intro para usar el tipo de incidente): ").strip() or None
    respuesta = httpx.post(f"{URL}/incidentes", trust_env=False, timeout=30, json={
        "titulo": titulo, "datos_personales": datos, "respuesta_asistente": ultima_respuesta, "mensajes": historial,
    })
    if respuesta.status_code != 201:
        print(f"[ERROR {respuesta.status_code}] {respuesta.text}")
        return None
    ficha = respuesta.json()
    print(f"\nFicha {ficha['id']} creada: {ficha['titulo']} · severidad {ficha.get('severidad') or '-'} · "
          f"{ficha['progreso']['total']} pasos · {len(ficha['adjuntos'])} adjuntos")
    if ficha.get("plazo_aepd"):
        print(f"  Plazo para notificar a la AEPD: {hora_local(ficha['plazo_aepd']['limite'])}")
    print("Las siguientes preguntas de esta conversación se guardarán en la ficha.")
    print(f"Ver y cerrar la ficha: {URL}/docs (sección incidentes) o, más adelante, en la extensión.")
    return ficha["id"]


def listar_incidentes() -> None:
    fichas = httpx.get(f"{URL}/incidentes", trust_env=False, timeout=30).json()
    if not fichas:
        print("No hay fichas todavía.")
    for f in fichas:
        memoria = " · en memoria" if f["en_memoria"] else ""
        print(f"  {f['id']}  [{f['estado']}{memoria}]  {f['severidad'] or '-':8} {f['titulo']}  "
              f"({f['pasos_hechos']}/{f['pasos_total']} pasos)")


def guardar_informe(incidente_id: str) -> None:
    carpeta = Path(os.environ.get("PREGUNTAR_ORIGEN", os.getcwd()))
    for formato in ("md", "pdf"):
        respuesta = httpx.get(f"{URL}/incidentes/{incidente_id}/informe", params={"formato": formato},
                              trust_env=False, timeout=60)
        if respuesta.status_code != 200:
            print(f"[ERROR {respuesta.status_code}] {respuesta.text}")
            return
        destino = carpeta / f"informe-{incidente_id}.{formato}"
        destino.write_bytes(respuesta.content)
        print(f"Guardado: {destino}")


def preguntar(historial: list[dict], incidente_id: str | None = None) -> str:
    """Envía la conversación, imprime la respuesta según llega y la devuelve."""
    respuesta_completa = []
    fuentes = []
    with httpx.Client(timeout=TIEMPO, trust_env=False) as cliente:
        cuerpo = {"mensajes": historial, "incidente_id": incidente_id}
        with cliente.stream("POST", f"{URL}/chat", json=cuerpo) as respuesta:
            if respuesta.status_code != 200:
                respuesta.read()
                print(f"\n[ERROR {respuesta.status_code}] {respuesta.json().get('detail', respuesta.text)}")
                return ""
            for linea in respuesta.iter_lines():
                if not linea.strip():
                    continue
                evento = json.loads(linea)
                if evento["tipo"] == "fuentes":
                    fuentes = evento["fuentes"]
                    print(f"\n[{evento['modelo']} · {len(fuentes)} fuentes] pensando...\n")
                elif evento["tipo"] == "texto":
                    print(evento["texto"], end="", flush=True)
                    respuesta_completa.append(evento["texto"])
                elif evento["tipo"] == "fin":
                    print(f"\n\n[{evento['segundos']} s]")
                elif evento["tipo"] == "error":
                    print(f"\n[ERROR] {evento['mensaje']}")
    if fuentes:
        print("\nFuentes:")
        for f in fuentes:
            lugar = f" · p. {f['pagina']}" if f.get("pagina") else ""
            apartado = f" · {f['seccion']}" if f.get("seccion") else ""
            print(f"  [{f['n']}] {f['documento']}{lugar}{apartado}  (similitud {f['similitud']:.2f})")
    return "".join(respuesta_completa)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preguntar al Asistente de Incidentes")
    parser.add_argument("-a", "--adjunto", action="append", default=[], help="fichero a analizar (repetible)")
    parser.add_argument("pregunta", nargs="*", help="pregunta (si se omite, modo conversación)")
    args = parser.parse_args()

    try:
        httpx.get(f"{URL}/health", timeout=5, trust_env=False).raise_for_status()
    except httpx.HTTPError:
        print(f"No se puede conectar con el backend en {URL}. Arráncalo con scripts\\iniciar.bat")
        sys.exit(1)

    if args.pregunta or args.adjunto:
        ids = [adjuntar(r) for r in args.adjunto]
        if not all(ids):
            print("\nNo se envía la pregunta porque algún adjunto no se pudo analizar.")
            sys.exit(1)
        pregunta = " ".join(args.pregunta) or "Analiza este adjunto y dime cómo proceder."
        preguntar([{"rol": "usuario", "contenido": pregunta, "adjuntos": ids}])
        return

    print("Asistente de Incidentes · escribe tu pregunta")
    print("  /adjuntar RUTA · /ficha · /incidentes · /informe ID · /nueva · /salir")
    historial: list[dict] = []
    pendientes: list[str] = []
    incidente_id: str | None = None
    while True:
        try:
            entrada = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not entrada:
            continue
        entrada = revisar_entrada(entrada)
        if entrada is None:
            continue
        if entrada == "/salir":
            break
        if entrada == "/nueva":
            historial, pendientes, incidente_id = [], [], None
            print("Conversación nueva.")
            continue
        if entrada == "/ficha":
            if incidente_id:
                print(f"Esta conversación ya tiene la ficha {incidente_id}.")
            else:
                incidente_id = crear_ficha(historial)
            continue
        if entrada == "/incidentes":
            listar_incidentes()
            continue
        if entrada.startswith("/informe"):
            identificador = entrada[len("/informe"):].strip() or incidente_id
            if identificador:
                guardar_informe(identificador)
            else:
                print("Uso: /informe INC-AAAAMMDD-XXXX")
            continue
        if entrada.startswith("/adjuntar"):
            adjunto_id = adjuntar(entrada[len("/adjuntar"):])
            if adjunto_id:
                pendientes.append(adjunto_id)
                print("Adjunto listo: se enviará con tu siguiente pregunta.")
            continue
        historial.append({"rol": "usuario", "contenido": entrada, "adjuntos": pendientes})
        # Con ficha, el backend guarda la pregunta y la respuesta en ella
        respuesta = preguntar(historial, incidente_id)
        if respuesta:
            historial.append({"rol": "asistente", "contenido": respuesta})
            pendientes = []
        else:
            historial.pop()


if __name__ == "__main__":
    main()
