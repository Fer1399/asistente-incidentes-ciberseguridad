"""Comprueba que se interpreta bien el streaming de la API de Ollama (sin Ollama real)."""

import asyncio
import json

import httpx
import pytest

from app.ollama_client import ErrorOllama, OllamaClient


def _cliente(manejador) -> OllamaClient:
    cliente = OllamaClient("http://127.0.0.1:11434")
    cliente._client = httpx.AsyncClient(base_url="http://127.0.0.1:11434", transport=httpx.MockTransport(manejador))
    return cliente


async def _recoger(cliente: OllamaClient) -> str:
    trozos = [t async for t in cliente.chat_stream("qwen2.5:7b", [{"role": "user", "content": "hola"}])]
    await cliente.close()
    return "".join(trozos)


def test_lee_la_respuesta_por_trozos():
    lineas = [
        {"message": {"role": "assistant", "content": "Aísla "}, "done": False},
        {"message": {"role": "assistant", "content": "el equipo."}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True},
    ]

    def manejador(peticion: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(peticion.content)
        assert cuerpo["stream"] is True and cuerpo["model"] == "qwen2.5:7b"
        return httpx.Response(200, text="\n".join(json.dumps(linea) for linea in lineas))

    assert asyncio.run(_recoger(_cliente(manejador))) == "Aísla el equipo."


def test_modelo_no_instalado():
    def manejador(peticion):
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(ErrorOllama, match="ollama pull qwen2.5:7b"):
        asyncio.run(_recoger(_cliente(manejador)))


def test_error_a_mitad_de_respuesta():
    def manejador(peticion):
        return httpx.Response(200, text=json.dumps({"error": "out of memory"}))

    with pytest.raises(ErrorOllama, match="out of memory"):
        asyncio.run(_recoger(_cliente(manejador)))
