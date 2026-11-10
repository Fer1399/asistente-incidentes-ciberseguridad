"""Almacén vectorial local con ChromaDB.

Los vectores se calculan siempre con Ollama (embeddings.py) y se pasan ya hechos:
la colección se crea SIN función de embeddings para que ChromaDB nunca intente
descargar su modelo por defecto de internet.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

COLECCION = "conocimiento"


class AlmacenVectorial:
    def __init__(self, ruta) -> None:
        self._cliente = chromadb.PersistentClient(
            path=str(ruta),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )
        self._coleccion = self._cliente.get_or_create_collection(
            name=COLECCION,
            embedding_function=None,
            metadata={"hnsw:space": "cosine"},
        )

    def total(self) -> int:
        return self._coleccion.count()

    def anadir(self, ids: list[str], textos: list[str], vectores: list[list[float]], metadatos: list[dict]) -> None:
        # ChromaDB no admite valores None en los metadatos
        limpios = [{k: v for k, v in m.items() if v is not None} for m in metadatos]
        for inicio in range(0, len(ids), 500):
            fin = inicio + 500
            self._coleccion.upsert(
                ids=ids[inicio:fin],
                documents=textos[inicio:fin],
                embeddings=vectores[inicio:fin],
                metadatas=limpios[inicio:fin],
            )

    def borrar_documento(self, doc_id: str) -> None:
        self._coleccion.delete(where={"doc_id": doc_id})

    def fragmento(self, doc_id: str, indice: int) -> dict | None:
        r = self._coleccion.get(where={"$and": [{"doc_id": doc_id}, {"fragmento": indice}]},
                                include=["documents", "metadatas"])
        if not r["ids"]:
            return None
        return {"texto": r["documents"][0], **(r["metadatas"][0] or {})}

    def contar_documento(self, doc_id: str) -> int:
        return len(self._coleccion.get(where={"doc_id": doc_id}, include=[])["ids"])

    def buscar(self, vector: list[float], k: int, filtro: dict | None = None) -> list[dict]:
        if self.total() == 0:
            return []
        resultado = self._coleccion.query(
            query_embeddings=[vector],
            n_results=min(k, self.total()),
            where=filtro,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {"texto": texto, **(metadatos or {}), "similitud": round(1 - distancia, 4)}
            for texto, metadatos, distancia in zip(
                resultado["documents"][0], resultado["metadatas"][0], resultado["distances"][0]
            )
        ]
