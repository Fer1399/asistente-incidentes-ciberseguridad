"""Configuración del backend, leída de backend/.env.

Toda dirección de red se valida para que sea local: el asistente nunca
debe hablar con nada fuera de este equipo.
"""

from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000

    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen2.5:7b"
    vision_model: str = "qwen2.5vl:7b"
    embed_model: str = "bge-m3"

    data_dir: Path = Path("data")
    knowledge_dir: Path = Path("knowledge")
    tesseract_cmd: str | None = None

    # RAG
    tamano_fragmento: int = 1000      # caracteres por fragmento
    solape_fragmento: int = 150       # caracteres repetidos entre fragmentos seguidos
    fragmentos_por_consulta: int = 6  # cuántos fragmentos se recuperan por pregunta
    max_subida_mb: int = 200          # tamaño máximo de un documento subido
    similitud_minima: float = 0.30    # por debajo, el fragmento no se usa como contexto

    # Chat
    temperatura: float = 0.2          # baja: respuestas precisas y estables
    contexto_tokens: int = 8192       # ventana de contexto del modelo de chat
    max_mensajes_historial: int = 12  # mensajes anteriores que se envían al modelo

    # Adjuntos (correos, logs, capturas)
    vision_activa: bool = True          # False: las capturas se leen solo con OCR (más rápido en CPU)
    max_adjunto_mb: int = 25            # tamaño máximo de un adjunto
    max_caracteres_adjunto: int = 12000 # texto de un adjunto que se pasa al modelo
    max_lado_imagen: int = 1600         # las capturas se reducen a este tamaño antes de analizarlas

    # Dominios de tu organización, separados por comas (p. ej. "empresa.es,empresa.com").
    # Sus indicadores se marcan como "propios" y no como posibles del atacante.
    dominios_propios: str = ""

    # Memoria de incidentes
    similitud_incidente: float = 0.55  # a partir de aquí, un incidente cerrado se considera "similar"

    @field_validator("host")
    @classmethod
    def host_local(cls, value: str) -> str:
        if value not in LOCAL_HOSTS:
            raise ValueError(
                f"HOST={value!r} no es local. Usa 127.0.0.1 para que el backend "
                "solo sea accesible desde este equipo."
            )
        return value

    @field_validator("ollama_url")
    @classmethod
    def ollama_local(cls, value: str) -> str:
        hostname = urlparse(value).hostname
        if hostname not in LOCAL_HOSTS:
            raise ValueError(
                f"OLLAMA_URL={value!r} apunta fuera de este equipo. "
                "Solo se permiten localhost, 127.0.0.1 o ::1."
            )
        return value.rstrip("/")

    @field_validator("data_dir", "knowledge_dir")
    @classmethod
    def ruta_absoluta(cls, value: Path) -> Path:
        return value if value.is_absolute() else (REPO_DIR / value).resolve()

    @property
    def lista_dominios_propios(self) -> list[str]:
        return [d.strip().lower().lstrip("@.") for d in self.dominios_propios.split(",") if d.strip()]

    @property
    def copias_dir(self) -> Path:
        return self.data_dir / "copias"

    @property
    def documentos_dir(self) -> Path:
        return self.data_dir / "documentos"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "vectores"

    @property
    def adjuntos_dir(self) -> Path:
        return self.data_dir / "adjuntos"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "asistente.db"


settings = Settings()
