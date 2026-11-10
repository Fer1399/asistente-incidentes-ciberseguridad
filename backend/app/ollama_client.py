"""Cliente asíncrono para la API local de Ollama."""

import json
from collections.abc import AsyncIterator

import httpx


class ErrorOllama(RuntimeError):
    """Ollama devolvió un error (modelo no instalado, sin memoria, etc.)."""


def normalizar_modelo(nombre: str) -> str:
    """Ollama guarda 'bge-m3' como 'bge-m3:latest'; comparamos siempre con etiqueta."""
    return nombre if ":" in nombre else f"{nombre}:latest"


class OllamaClient:
    def __init__(self, base_url: str) -> None:
        # Lectura larga: en CPU una respuesta puede tardar varios minutos.
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(10.0, read=600.0),
            trust_env=False,  # ignora proxies del sistema: solo hablamos con localhost
        )

    async def version(self) -> str:
        respuesta = await self._client.get("/api/version")
        respuesta.raise_for_status()
        return respuesta.json().get("version", "desconocida")

    async def modelos_instalados(self) -> list[str]:
        respuesta = await self._client.get("/api/tags")
        respuesta.raise_for_status()
        return [m["name"] for m in respuesta.json().get("models", [])]

    async def chat_stream(
        self,
        modelo: str,
        mensajes: list[dict],
        opciones: dict | None = None,
    ) -> AsyncIterator[str]:
        """Devuelve la respuesta del modelo trozo a trozo, según se genera."""
        payload = {"model": modelo, "messages": mensajes, "stream": True, "options": opciones or {}}
        async with self._client.stream("POST", "/api/chat", json=payload) as respuesta:
            if respuesta.status_code >= 400:
                cuerpo = (await respuesta.aread()).decode("utf-8", errors="replace")
                try:
                    detalle = json.loads(cuerpo).get("error", cuerpo)
                except json.JSONDecodeError:
                    detalle = cuerpo
                if respuesta.status_code == 404:
                    detalle = f"El modelo '{modelo}' no está instalado: ollama pull {modelo}"
                raise ErrorOllama(detalle)
            async for linea in respuesta.aiter_lines():
                if not linea.strip():
                    continue
                datos = json.loads(linea)
                if "error" in datos:
                    raise ErrorOllama(datos["error"])
                texto = datos.get("message", {}).get("content", "")
                if texto:
                    yield texto
                if datos.get("done"):
                    break

    async def describir_imagen(self, modelo: str, imagen_b64: str, instrucciones: str) -> str:
        """Pide al modelo de visión que describa una imagen (respuesta completa, sin streaming)."""
        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": instrucciones, "images": [imagen_b64]}],
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
        }
        respuesta = await self._client.post("/api/chat", json=payload)
        if respuesta.status_code == 404:
            raise ErrorOllama(f"El modelo de visión '{modelo}' no está instalado: ollama pull {modelo}")
        if respuesta.status_code >= 400:
            raise ErrorOllama(respuesta.json().get("error", respuesta.text))
        return respuesta.json().get("message", {}).get("content", "").strip()

    async def close(self) -> None:
        await self._client.aclose()
