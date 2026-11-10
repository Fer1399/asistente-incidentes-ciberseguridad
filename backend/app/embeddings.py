"""Generación de vectores (embeddings) con el modelo local de Ollama."""

from collections.abc import Callable

import httpx


class OllamaNoDisponible(RuntimeError):
    """Ollama no responde o el modelo de embeddings no está instalado."""


class Embedder:
    def __init__(self, base_url: str, modelo: str, lote: int = 16) -> None:
        self.modelo = modelo
        self.lote = lote
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, read=300.0),
            trust_env=False,  # solo localhost, sin proxies
        )

    def vectorizar(
        self,
        textos: list[str],
        progreso: Callable[[int, int], None] | None = None,
    ) -> list[list[float]]:
        vectores: list[list[float]] = []
        for inicio in range(0, len(textos), self.lote):
            lote = textos[inicio:inicio + self.lote]
            try:
                respuesta = self._client.post("/api/embed", json={"model": self.modelo, "input": lote})
            except httpx.TransportError as error:
                raise OllamaNoDisponible(
                    "Ollama no responde. Comprueba que está en marcha (scripts\\iniciar.bat)."
                ) from error
            if respuesta.status_code == 404:
                raise OllamaNoDisponible(
                    f"El modelo de embeddings '{self.modelo}' no está instalado: ollama pull {self.modelo}"
                )
            respuesta.raise_for_status()
            vectores.extend(respuesta.json()["embeddings"])
            if progreso:
                progreso(len(vectores), len(textos))
        return vectores

    def vectorizar_uno(self, texto: str) -> list[float]:
        return self.vectorizar([texto])[0]

    def close(self) -> None:
        self._client.close()
