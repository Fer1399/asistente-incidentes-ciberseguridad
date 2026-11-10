# 02 · Arquitectura

## Visión general

```
┌──────────── Chrome ────────────┐          ┌────────────────── Backend local (Python) ──────────────────┐
│  Extensión (Manifest V3)       │          │  FastAPI · 127.0.0.1:8000                                   │
│  ┌──────────────────────────┐  │   HTTP   │                                                             │
│  │ Panel lateral            │  │ ───────► │  /chat ──► RAG ──► ChromaDB (vectores, data/vectores)       │
│  │ Chat · Incidentes ·      │  │ ◄─────── │    │        └────► incidentes similares                     │
│  │ Ficha · Conocimiento ·   │  │ streaming│    └──────────────► Ollama: modelo de chat ─┐                │
│  │ Ajustes                  │  │  NDJSON  │  /adjuntos ─► correo · OCR · visión · IOCs  │                │
│  └──────────────────────────┘  │          │  /documentos ─► extracción ─► troceado ─► embeddings          │
│  Service worker:               │          │  /incidentes ─► SQLite (data/asistente.db)  │                │
│  menú contextual               │          │  /copia ─► .zip                             │                │
└────────────────────────────────┘          └─────────────────────────────────────────────┼────────────────┘
                                                                                          ▼
                                                                    Ollama · 127.0.0.1:11434
                                                                    chat · visión · embeddings
                               Todo en el mismo equipo · nada sale de localhost
```

| Componente | Tecnología | Función |
|---|---|---|
| Extensión | JavaScript (módulos ES), sin dependencias ni compilación | Interfaz en el panel lateral de Chrome |
| Backend | Python 3.12, FastAPI, Uvicorn | API, lógica del asistente, análisis de artefactos, fichas |
| Modelos | Ollama | Chat (`qwen2.5`), visión (`qwen2.5vl`), embeddings (`bge-m3`) |
| Base vectorial | ChromaDB integrado | Búsqueda por significado (RAG) |
| Base de datos | SQLite | Documentos, fichas, pasos, cronología, conversaciones |
| PDF | PyMuPDF | Leer PDFs y generar informes |
| OCR | Tesseract | PDFs escaneados y capturas |

---

## Flujo de una pregunta

1. **Adjuntos** (si los hay): `POST /adjuntos` analiza cada fichero (correo, captura, log o
   PDF) y devuelve alertas, IOCs y texto. La extensión guarda el identificador.
2. **Chat**: `POST /chat` con la conversación y los identificadores de los adjuntos.
3. **Búsqueda**: la pregunta (más un resumen de los adjuntos) se convierte en vector con
   `bge-m3` y se buscan los fragmentos más parecidos en ChromaDB.
4. **Incidentes similares**: búsqueda aparte entre los incidentes cerrados en memoria.
5. **Cabecera del playbook**: si la fuente principal es un playbook, se añade su primer
   fragmento (con las técnicas MITRE correctas).
6. **Mensaje al modelo**: system prompt + conversación + adjuntos (alertas, IOCs, contenido) +
   contexto numerado `[1]`, `[2]`… + pregunta.
7. **Respuesta en streaming**: primero las fuentes, IOCs e incidentes similares; después el
   texto según se genera; al final, las técnicas MITRE citadas con su nombre oficial.
8. **Ficha** (opcional): si la conversación está vinculada a una ficha, se guardan la pregunta
   y la respuesta.

---

## Estructura del código

```
backend/
├── app/
│   ├── main.py            API: rutas, arranque, /health, /modelos, /mitre
│   ├── config.py          configuración (.env) y validación de direcciones locales
│   ├── prompts.py         system prompt y formato del contexto
│   ├── asistente.py       preparación de la conversación y selección de fuentes
│   ├── ollama_client.py   cliente de Ollama (chat en streaming y visión)
│   ├── embeddings.py      vectores con Ollama
│   ├── vectores.py        ChromaDB
│   ├── extraccion.py      texto de PDF (con OCR), Markdown y texto
│   ├── troceado.py        fragmentos para el RAG
│   ├── ingesta.py         cola de indexado de documentos e incidentes
│   ├── adjuntos.py        análisis de adjuntos
│   ├── correo.py          análisis de .eml
│   ├── iocs.py            extracción de indicadores
│   ├── ocr.py             Tesseract
│   ├── mitre.py           referencia MITRE ATT&CK
│   ├── incidentes.py      fichas, pasos, cronología y memoria
│   ├── informe.py         informes Markdown y PDF
│   ├── copias.py          exportar e importar copias
│   ├── db.py              SQLite
│   └── routers/           rutas por área (chat, documentos, adjuntos, incidentes, copias…)
├── evaluacion/            batería de evaluación con el modelo real
├── tests/                 pruebas (pytest), Ollama simulado y prueba de la extensión
├── preguntar.py           consola
└── run.py                 arranque

extension/
├── manifest.json
├── background.js          panel lateral y menú contextual
└── sidepanel/
    ├── index.html · styles.css · app.js
    ├── api.js             cliente del backend (con streaming)
    ├── dom.js             construcción segura de la interfaz
    ├── markdown.js        Markdown seguro
    └── vistas/            chat, incidentes, ficha, conocimiento, ajustes

knowledge/                 playbooks y referencia MITRE (se indexan al arrancar)
scripts/                   instalar, arrancar, preguntar y evaluar (Windows)
```

---

## Datos (`data/`, excluida de Git)

```
data/
├── asistente.db           SQLite: documentos, incidentes, pasos, eventos, mensajes
├── vectores/              ChromaDB
├── documentos/            PDFs y documentos subidos
├── adjuntos/<id>/         original.bin (evidencia) y analisis.json
└── copias/                copias automáticas antes de importar
```

---

## API

Con el backend en marcha, la documentación interactiva completa está en
<http://127.0.0.1:8000/docs>. Resumen:

| Área | Rutas | Documentación |
|---|---|---|
| Estado | `GET /health`, `GET /modelos`, `GET /mitre` | — |
| Base de conocimiento | `/documentos`, `POST /buscar` | [04](04-rag.md) |
| Chat | `POST /chat` | [05](05-asistente.md) |
| Adjuntos | `POST /adjuntos`, `GET /adjuntos/{id}`, `POST /iocs` | [06](06-adjuntos.md) |
| Incidentes | `/incidentes/...` | [07](07-incidentes.md) |
| Copia de seguridad | `GET/POST /copia` | [07](07-incidentes.md#copia-de-seguridad-entre-equipos) |

---

## Decisiones de diseño

Cada decisión y su motivo están en el [registro de decisiones](decisiones.md).
