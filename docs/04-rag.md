# 04 · Base de conocimiento y RAG

El asistente no se inventa los procedimientos: antes de responder busca en tu base de
conocimiento los fragmentos más parecidos a la pregunta y se los pasa al modelo como
contexto. Esa técnica se llama **RAG** (*Retrieval-Augmented Generation*, generación
aumentada por recuperación). Este documento explica cómo se construye esa base.

---

## Qué entra en la base

| Origen | Dónde está | Cómo se añade |
|---|---|---|
| **Incluido** | `knowledge/` en el repositorio (playbooks propios) | Se indexa solo al arrancar el backend. Si modificas un fichero, se reindexa. |
| **Usuario** | `data/documentos/` (no se sube a Git) | Desde la pestaña *Conocimiento* de la extensión o con `POST /documentos`. |
| **Incidentes cerrados** | `data/` | Al cerrar y revisar una ficha (ver [07](07-incidentes.md)). |

Formatos admitidos: **PDF**, **Markdown** (`.md`) y **texto** (`.txt`). Tamaño máximo por
defecto: 200 MB (`MAX_SUBIDA_MB` en `.env`).

---

## El proceso, paso a paso

```
 PDF / MD / TXT
      │
      ▼
 1. Extracción ── texto de cada página (PyMuPDF)
      │            └─ página casi vacía → se rasteriza a 300 ppp y se lee con OCR (Tesseract)
      ▼
 2. Limpieza ──── une palabras partidas por guion, quita espacios y saltos sobrantes
      │
      ▼
 3. Troceado ──── fragmentos de ~1000 caracteres con 150 de solape, sin mezclar páginas
      │
      ▼
 4. Vectores ──── cada fragmento → vector numérico con bge-m3 (Ollama, local)
      │
      ▼
 5. Guardado ──── ChromaDB (data/vectores) + estado en SQLite (data/asistente.db)
```

Los documentos se procesan **de uno en uno** en segundo plano. Mientras tanto la extensión
muestra el progreso (0-40 % lectura, 40-95 % vectores, 100 % indexado).

### 1. Extracción y OCR

PyMuPDF saca el texto de cada página. Si una página tiene menos de 40 caracteres se
considera **escaneada**: se convierte en imagen y Tesseract lee su texto en español e
inglés. La ficha del documento indica cuántas páginas se leyeron con OCR.

Sin Tesseract instalado, los PDFs escaneados quedan sin texto y el documento aparece con
error. Ver [instalación](01-instalacion.md#paso-1--instalar-los-programas).

### 3. Troceado

Un modelo no puede leer un PDF entero de golpe en cada pregunta, así que se divide en
fragmentos:

- Primero por **párrafos**; si un párrafo es largo, por **frases**; y si una frase es
  enorme, por **palabras**.
- Las piezas se van juntando hasta unos **1000 caracteres** (≈ 200 palabras).
- Cada fragmento empieza con los últimos **150 caracteres** del anterior, para que una idea
  partida entre dos fragmentos no se pierda.
- Un fragmento **nunca mezcla dos páginas**, así la cita *"guía.pdf · p. 41"* es exacta.

Se ajusta con `TAMANO_FRAGMENTO` y `SOLAPE_FRAGMENTO` en `.env` (después hay que reindexar).

### 4. Vectores (embeddings)

Un *embedding* es una lista de números que representa el **significado** de un texto. Dos
textos que hablan de lo mismo tienen vectores parecidos aunque usen palabras distintas:
*"me han robado la contraseña"* queda cerca de *"credenciales comprometidas"*.

Se usa **`bge-m3`** porque funciona bien en español y en inglés y se ejecuta en local.

> **El modelo de embeddings debe ser siempre el mismo.** Los vectores de modelos distintos
> no son comparables. Si cambias `EMBED_MODEL`, `/health` mostrará
> `"reindexar_necesario": true`; lanza `POST /documentos/reindexar-todo`.

### 5. Búsqueda

Cuando preguntas algo, la pregunta se convierte en vector y ChromaDB devuelve los
**6 fragmentos más parecidos** (`FRAGMENTOS_POR_CONSULTA`) por similitud del coseno
(de 0 a 1; cuanto más alto, más parecido). Esos fragmentos, con su documento y página,
son el contexto que recibe el modelo.

---

## Privacidad

- ChromaDB se crea **sin función de embeddings propia**: nunca intenta descargar su modelo
  por defecto de internet.
- La **telemetría** de ChromaDB está desactivada.
- Los clientes HTTP ignoran los proxies del sistema y solo hablan con `127.0.0.1`.
- Todo se guarda en `data/`, que está excluida de Git.

---

## API

| Método | Ruta | Para qué |
|---|---|---|
| `GET` | `/documentos` | Lista de documentos con estado y progreso |
| `POST` | `/documentos` | Subir un documento (campo `fichero`, multipart) |
| `GET` | `/documentos/{id}` | Detalle y progreso |
| `POST` | `/documentos/{id}/reindexar` | Volver a procesarlo |
| `POST` | `/documentos/reindexar-todo` | Reindexar todo (tras cambiar el modelo) |
| `DELETE` | `/documentos/{id}` | Borrarlo (los incluidos se quitan borrándolos de `knowledge/`) |
| `POST` | `/buscar` | `{"consulta": "...", "k": 6}` → fragmentos más parecidos |

Con el backend en marcha, la documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>: puedes subir un PDF y probar búsquedas desde ahí.

### Probarlo sin la extensión (PowerShell)

```powershell
# Subir un PDF
curl.exe -F "fichero=@C:\ruta\guia.pdf" http://127.0.0.1:8000/documentos

# Ver el progreso
curl.exe http://127.0.0.1:8000/documentos

# Buscar
curl.exe -X POST http://127.0.0.1:8000/buscar -H "Content-Type: application/json" `
  -d '{\"consulta\": \"qué hacer si un usuario introduce su contraseña en un phishing\"}'
```

---

## Estados de un documento

| Estado | Significado |
|---|---|
| `pendiente` | En cola |
| `procesando` | Leyendo o generando vectores (ver `progreso`) |
| `indexado` | Listo para las búsquedas |
| `error` | Ver `mensaje`. Lo más habitual: Ollama apagado o PDF escaneado sin Tesseract |

Al arrancar el backend, todo lo que no esté `indexado` se vuelve a intentar.

---

## Pruebas automáticas

Las pruebas usan un modelo de embeddings falso, así que no necesitan Ollama:

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest
```

Comprueban el troceado, la subida e indexado de PDFs, el rechazo de duplicados y de
formatos no admitidos, el borrado, la indexación de `knowledge/` y el OCR de páginas
escaneadas (si Tesseract está instalado).
