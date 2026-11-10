"""Troceado del texto en fragmentos para el RAG.

Estrategia:
1. Cada página se divide en párrafos; los párrafos largos, en frases; las frases
   enormes, por palabras.
2. Las piezas se juntan hasta llegar a `tamano` caracteres.
3. Cada fragmento nuevo empieza con el final del anterior (`solape`), para no
   perder el contexto cuando una idea queda partida entre dos fragmentos.
4. Un fragmento nunca mezcla dos páginas, así la cita (documento + página) es exacta.
5. En Markdown, cada fragmento empieza con su apartado ("Playbook: Phishing ›
   Contención"), para que tenga sentido por sí solo.
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .extraccion import Pagina

MIN_CARACTERES_FRAGMENTO = 30


@dataclass
class Fragmento:
    texto: str
    pagina: int | None
    indice: int
    seccion: str | None = None


def _piezas(texto: str, tamano: int) -> Iterator[str]:
    for parrafo in re.split(r"\n\s*\n", texto):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        if len(parrafo) <= tamano:
            yield parrafo
            continue
        for frase in re.split(r"(?<=[.!?;:])\s+", parrafo):
            frase = frase.strip()
            while len(frase) > tamano:
                corte = frase.rfind(" ", 0, tamano)
                if corte <= 0:
                    corte = tamano
                yield frase[:corte].strip()
                frase = frase[corte:].strip()
            if frase:
                yield frase


def _cola(texto: str, solape: int) -> str:
    """Últimos `solape` caracteres, empezando en una palabra completa."""
    if solape <= 0 or len(texto) <= solape:
        return ""
    cola = texto[-solape:]
    espacio = cola.find(" ")
    return cola[espacio + 1:] if espacio != -1 else cola


def trocear(paginas: Iterable[Pagina], tamano: int = 1000, solape: int = 150) -> list[Fragmento]:
    if solape >= tamano:
        raise ValueError("El solape debe ser menor que el tamaño del fragmento")

    fragmentos: list[Fragmento] = []

    def emitir(texto: str, pagina: Pagina) -> None:
        texto = texto.strip()
        if len(texto) < MIN_CARACTERES_FRAGMENTO:
            return
        if pagina.seccion:
            texto = f"[{pagina.seccion}]\n{texto}"
        fragmentos.append(Fragmento(texto, pagina.numero, len(fragmentos), pagina.seccion))

    for pagina in paginas:
        actual = ""
        for pieza in _piezas(pagina.texto, tamano):
            candidato = f"{actual}\n{pieza}" if actual else pieza
            if len(candidato) <= tamano:
                actual = candidato
                continue
            emitir(actual, pagina)
            cola = _cola(actual, solape)
            actual = f"{cola} {pieza}" if cola else pieza
        emitir(actual, pagina)

    return fragmentos
