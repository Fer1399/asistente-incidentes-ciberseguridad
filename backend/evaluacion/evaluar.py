"""Batería de evaluación del asistente con el modelo real.

Lanza los incidentes de evaluacion/casos.json contra el backend en marcha y mide, en
cada respuesta:

- estructura:  están los 8 apartados (acciones inmediatas ... MITRE ATT&CK)
- tipo:        el tipo de incidente es el esperado
- severidad:   la severidad estimada está entre las aceptables
- mitre:       todas las técnicas citadas están en la referencia y aparece alguna esperada
- citas:       se cita alguna fuente y todas las citas [n] existen
- playbook:    entre las fuentes está el playbook adecuado
- aepd:        en las fugas de datos personales se menciona la AEPD y las 72 h

Uso (con el backend en marcha):
    scripts\\evaluar.bat                       todos los casos
    scripts\\evaluar.bat ransomware-servidor   solo uno (o varios separados por espacios)
    scripts\\evaluar.bat --modelo qwen2.5:7b   con otro modelo de chat

El informe se guarda en backend/evaluacion/resultados/ (no se sube a Git).
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.mitre import verificar  # noqa: E402

RAIZ = Path(__file__).resolve().parent
URL = f"http://{settings.host}:{settings.port}"
APARTADOS = {
    "inmediatas": r"acciones inmediatas",
    "evidencias": r"evidencias",
    "contencion": r"contenci[oó]n",
    "alcance": r"alcance",
    "erradicacion": r"erradicaci[oó]n|recuperaci[oó]n",
    "notificacion": r"notificaci[oó]n",
    "lecciones": r"lecciones",
    "mitre": r"mitre",
}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# --- Métricas (también se usan en las pruebas automáticas) ------------------

def apartados_presentes(respuesta: str) -> list[str]:
    titulos = " ".join(re.findall(r"^\s*#{2,4}\s*(.+)$", respuesta, re.MULTILINE)).lower()
    return [nombre for nombre, patron in APARTADOS.items() if re.search(patron, titulos)]


def severidad_de(respuesta: str) -> str | None:
    m = re.search(r"Severidad estimada\W*(Baja|Media|Alta|Cr[ií]tica)", respuesta, re.IGNORECASE)
    if not m:
        return None
    valor = m.group(1).capitalize()
    return "Crítica" if valor.lower().startswith("cr") else valor


def tipo_de(respuesta: str) -> str:
    m = re.search(r"Tipo de incidente\W*([^·\n*|]+)", respuesta, re.IGNORECASE)
    return m.group(1).strip().lower() if m else ""


def citas_de(respuesta: str) -> list[int]:
    return [int(n) for grupo in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", respuesta) for n in re.split(r"\s*,\s*", grupo)]


def evaluar_respuesta(caso: dict, respuesta: str, fuentes: list[dict]) -> dict:
    presentes = apartados_presentes(respuesta)
    tipo = tipo_de(respuesta)
    severidad = severidad_de(respuesta)
    tecnicas = verificar(respuesta)
    citas = citas_de(respuesta)
    documentos = {f["documento"] for f in fuentes}

    resultado = {
        "estructura": len(presentes) >= 7,
        "tipo": any(t in tipo for t in caso["tipo"]),
        "severidad": severidad in caso["severidad"],
        "mitre": bool(tecnicas) and all(t["reconocida"] for t in tecnicas)
                 and (not caso["mitre"] or any(t["id"] in caso["mitre"] for t in tecnicas)),
        "citas": bool(citas) and all(1 <= n <= len(fuentes) for n in citas),
        "playbook": caso["playbook"] in documentos,
    }
    if caso.get("aepd"):
        resultado["aepd"] = "aepd" in respuesta.lower() and "72" in respuesta
    detalle = {
        "apartados": f"{len(presentes)}/8",
        "faltan": [a for a in APARTADOS if a not in presentes],
        "tipo": tipo or "-",
        "severidad": severidad or "-",
        "tecnicas": [f"{t['id']}{'' if t['reconocida'] else ' (?)'}" for t in tecnicas],
        "citas": sorted(set(citas)),
        "fuentes": len(fuentes),
    }
    return {"metricas": resultado, "detalle": detalle, "aprobado": all(resultado.values())}


# --- Ejecución ---------------------------------------------------------------

def preguntar(cliente: httpx.Client, caso: dict, modelo: str | None) -> tuple[str, list[dict], float]:
    adjuntos = []
    if caso.get("adjunto"):
        ruta = RAIZ.parent / caso["adjunto"]
        with ruta.open("rb") as f:
            r = cliente.post(f"{URL}/adjuntos", files={"fichero": (ruta.name, f)})
        r.raise_for_status()
        adjuntos.append(r.json()["id"])
    cuerpo = {"mensajes": [{"rol": "usuario", "contenido": caso["pregunta"], "adjuntos": adjuntos}], "modelo": modelo}
    texto, fuentes = [], []
    inicio = time.monotonic()
    with cliente.stream("POST", f"{URL}/chat", json=cuerpo) as r:
        r.raise_for_status()
        for linea in r.iter_lines():
            if not linea.strip():
                continue
            evento = json.loads(linea)
            if evento["tipo"] == "fuentes":
                fuentes = evento["fuentes"]
            elif evento["tipo"] == "texto":
                texto.append(evento["texto"])
            elif evento["tipo"] == "error":
                raise RuntimeError(evento["mensaje"])
    return "".join(texto), fuentes, time.monotonic() - inicio


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluar el asistente con casos de prueba")
    parser.add_argument("casos", nargs="*", help="identificadores de caso (por defecto, todos)")
    parser.add_argument("--modelo", help="modelo de chat (por defecto, CHAT_MODEL de .env)")
    args = parser.parse_args()

    casos = json.loads((RAIZ / "casos.json").read_text(encoding="utf-8"))
    if args.casos:
        casos = [c for c in casos if c["id"] in args.casos]
        if not casos:
            sys.exit(f"No hay casos con esos identificadores. Disponibles: {', '.join(c['id'] for c in casos)}")

    try:
        salud = httpx.get(f"{URL}/health", timeout=10, trust_env=False).json()
    except httpx.HTTPError:
        sys.exit(f"No se puede conectar con el backend en {URL}. Arráncalo con scripts\\iniciar.bat")
    modelo = args.modelo or salud["modelos"]["chat"]["nombre"]
    print(f"Evaluando {len(casos)} casos con {modelo}\n")

    resultados = []
    with httpx.Client(timeout=httpx.Timeout(10.0, read=900.0), trust_env=False) as cliente:
        for i, caso in enumerate(casos, start=1):
            print(f"[{i}/{len(casos)}] {caso['titulo']}…", end=" ", flush=True)
            try:
                respuesta, fuentes, segundos = preguntar(cliente, caso, args.modelo)
                evaluacion = evaluar_respuesta(caso, respuesta, fuentes)
            except Exception as error:  # un caso fallido no detiene la batería
                respuesta, segundos = f"ERROR: {error}", 0.0
                evaluacion = {"metricas": {}, "detalle": {}, "aprobado": False}
            fallos = [k for k, v in evaluacion["metricas"].items() if not v]
            estado = "OK" if evaluacion["aprobado"] else f"FALLA ({', '.join(fallos) or 'error'})"
            print(f"{estado} · {segundos:.1f} s")
            resultados.append({"caso": caso, "respuesta": respuesta, "segundos": round(segundos, 1), **evaluacion})

    guardar_informe(resultados, modelo)


def guardar_informe(resultados: list[dict], modelo: str) -> None:
    metricas = ["estructura", "tipo", "severidad", "mitre", "citas", "playbook", "aepd"]
    totales = {m: [r["metricas"].get(m) for r in resultados if m in r["metricas"]] for m in metricas}
    aprobados = sum(r["aprobado"] for r in resultados)
    tiempos = [r["segundos"] for r in resultados if r["segundos"]]

    lineas = [
        f"# Evaluación del asistente · {datetime.now():%d/%m/%Y %H:%M}",
        "",
        f"- Modelo de chat: `{modelo}`",
        f"- Casos aprobados: **{aprobados} de {len(resultados)}**",
        f"- Tiempo medio por respuesta: {sum(tiempos) / len(tiempos):.1f} s" if tiempos else "- Tiempo medio: -",
        "",
        "| Métrica | Aciertos |",
        "|---|---|",
        *(f"| {m} | {sum(bool(v) for v in vals)} de {len(vals)} |" for m, vals in totales.items() if vals),
        "",
        "| Caso | Resultado | Apartados | Tipo | Severidad (esperada) | Técnicas MITRE | Citas | s |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        d, c = r["detalle"], r["caso"]
        lineas.append(
            f"| {c['id']} | {'OK' if r['aprobado'] else 'FALLA'} | {d.get('apartados', '-')} | {d.get('tipo', '-')} | "
            f"{d.get('severidad', '-')} ({'/'.join(c['severidad'])}) | {', '.join(d.get('tecnicas', [])) or '-'} | "
            f"{d.get('citas', '-')} | {r['segundos']} |")
    lineas += ["", "## Respuestas", ""]
    for r in resultados:
        lineas += [f"### {r['caso']['titulo']} ({r['caso']['id']})", "", f"**Pregunta:** {r['caso']['pregunta']}", "",
                   r["respuesta"], "", "---", ""]

    carpeta = RAIZ / "resultados"
    carpeta.mkdir(exist_ok=True)
    marca = f"{datetime.now():%Y%m%d-%H%M}"
    informe = carpeta / f"evaluacion-{marca}.md"
    informe.write_text("\n".join(lineas), encoding="utf-8")
    (carpeta / f"evaluacion-{marca}.json").write_text(
        json.dumps({"modelo": modelo, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nAprobados: {aprobados} de {len(resultados)}")
    for m, vals in totales.items():
        if vals:
            print(f"  {m:<11} {sum(bool(v) for v in vals)}/{len(vals)}")
    print(f"\nInforme: {informe}")


if __name__ == "__main__":
    main()
