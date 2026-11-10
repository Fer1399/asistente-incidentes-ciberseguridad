"""Arranca el backend con la dirección y el puerto de backend/.env."""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    print(f"Asistente de Incidentes -> http://{settings.host}:{settings.port}")
    print("Comprueba el estado en /health. Pulsa Ctrl+C para parar.")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, log_level="info")
