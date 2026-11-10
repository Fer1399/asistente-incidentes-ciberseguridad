# 07 · Fichas de incidente, memoria, informes y copias de seguridad

Una **ficha** recoge un incidente de principio a fin: qué pasó, qué propuso el asistente,
qué se hizo y cuándo, las evidencias y lo aprendido. Al cerrarla y revisarla, pasa a la
**memoria** del asistente: si vuelve a ocurrir algo parecido, te dirá cómo se resolvió.

---

## Ciclo de vida

```
 Chat con el asistente
        │  "Crear ficha"
        ▼
 ┌─ ABIERTA ──────────────────────────────────────────────┐
 │ · Tipo y severidad sacados de la respuesta              │
 │ · Pasos de la respuesta → checklist por fases           │
 │ · Marcas cada paso al hacerlo → queda la hora           │
 │ · Añades pasos propios, notas y adjuntos                │
 │ · Las nuevas consultas al asistente se guardan aquí     │
 │ · Si hay datos personales: cuenta atrás de 72 h (AEPD)  │
 └────────────────────────────────────────────────────────┘
        │  "Cerrar" con notas de lo que se hizo (obligatorias)
        ▼
 ┌─ CERRADA ──────────────────────────────────────────────┐
 │ · Se guarda en la memoria (salvo que lo desactives)     │
 │ · Aparece como "incidente similar" en casos parecidos   │
 │ · Informe en Markdown o PDF                             │
 └────────────────────────────────────────────────────────┘
        │  "Reabrir" (se retira de la memoria)
        ▼
      ABIERTA
```

---

## Crear una ficha

Desde el chat, tras la respuesta del asistente. El backend:

- Lee **tipo** y **severidad** de la línea *"Tipo de incidente: … · Severidad estimada: …"*.
- Convierte los apartados numerados de la respuesta (acciones inmediatas, evidencias,
  contención, análisis, erradicación, notificación, lecciones) en **pasos** de una checklist,
  quitando las citas `[n]`. No convierte en pasos el análisis del artefacto, las técnicas
  MITRE ni las preguntas.
- Guarda la conversación y **vincula los adjuntos** que se usaron.
- Reúne los **IOCs** de los adjuntos y de lo que escribiste.

Identificador: `INC-AAAAMMDD-XXXX` (fecha + 4 caracteres aleatorios), para que no choquen
los incidentes creados en equipos distintos si se fusionan copias.

### Desde la consola

```powershell
scripts\preguntar.bat
> /adjuntar C:\ruta\correo.eml
> Un usuario metió su contraseña en este correo, ¿cómo procedo?
  (respuesta del asistente)
> /ficha
¿Hay datos personales afectados? (s/N): s
Título (Intro para usar el tipo de incidente): Phishing Microsoft 365 - Contabilidad
Ficha INC-20261110-A94F creada: ... · severidad Alta · 18 pasos · 1 adjuntos
> ¿Y si también abrió el adjunto?        ← se guarda en la ficha
> /incidentes                             ← lista las fichas
> /informe INC-20261110-A94F              ← guarda el informe .md y .pdf
```

Marcar pasos, editar y cerrar la ficha se hace desde la extensión ([08](08-extension.md)).

---

## El plazo de 72 horas

Si marcas que hay **datos personales afectados**, la ficha calcula el límite para notificar
la brecha a la AEPD: 72 horas desde la **detección** (`detectado`, que por defecto es el
momento de crear la ficha; puedes corregirlo si lo detectaste antes). La ficha muestra las
horas restantes y si el plazo ha vencido.

---

## Cerrar y guardar en memoria

Al cerrar hay que escribir **qué se hizo realmente** (mínimo 10 caracteres) y, opcionalmente,
las **lecciones aprendidas**. Es lo que el asistente recordará, por eso es obligatorio:
así aprende de procedimientos revisados por una persona y no de sus propias respuestas
(decisión D-12).

Lo que se guarda en la memoria de cada incidente:

- Tipo, severidad, fechas y duración.
- Descripción e indicadores.
- **Lo que se hizo** (notas de cierre).
- Pasos realizados y pasos propuestos que **no** se hicieron.
- Lecciones aprendidas.

### Incidentes similares

En cada pregunta al chat se buscan aparte los incidentes cerrados más parecidos (similitud
≥ 0,55, ajustable con `SIMILITUD_INCIDENTE`). Si hay alguno:

- Se añade al contexto del modelo, que empieza su respuesta con *"Incidente similar
  anterior"*: qué se hizo entonces y qué conviene repetir o evitar.
- La extensión mostrará el aviso *"Ya ha pasado algo parecido"* con enlace a la ficha.

Para no usar un incidente como referencia, **reábrelo** (se retira de la memoria) o ciérralo
con `guardar_en_memoria: false`.

---

## Informes

`GET /incidentes/{id}/informe?formato=md` o `?formato=pdf`. Contenido:

1. Resumen: tipo, severidad, estado, fechas, duración, pasos completados, datos personales
   y límite de notificación a la AEPD.
2. Descripción.
3. Cronología con todo lo ocurrido.
4. Procedimiento por fases, con `[x]` y la hora de cada paso hecho.
5. Indicadores de compromiso (desactivados), marcando IPs internas y dominios legítimos.
6. Evidencias analizadas con su SHA-256 y sus alertas.
7. Cierre: lo que se hizo y lecciones aprendidas.
8. Anexo: las consultas al asistente (opcional: `?anexo=false` para no incluirlo).

Antes de generar el informe, revisa la **conversación** guardada en la ficha y quita lo que
no aporte (preguntas de prueba, comandos escritos por error): `DELETE
/incidentes/{id}/mensajes/{mensaje}` o, en la extensión, la sección *Conversación con el
asistente* de la ficha. Si el mismo fichero se adjuntó varias veces, aparece una sola vez.

El PDF se genera en local con PyMuPDF, en A4 y con numeración de páginas.

---

## Copia de seguridad entre equipos

> Guía paso a paso con capturas, qué contiene la copia y cómo volver atrás tras importar:
> [10 · Resultados, apartado 6](10-resultados.md#6-copia-de-seguridad-exportar-e-importar).

| | |
|---|---|
| **Exportar** | `GET /copia` descarga `asistente-copia-AAAAMMDD-HHMM.zip` |
| **Importar** | `POST /copia` con el `.zip` |

La copia contiene la base de datos (incidentes y registro de documentos), los **PDFs que
subiste** y los **adjuntos analizados**. No contiene los vectores: el equipo que la importa
los regenera con su propio modelo de embeddings (por eso los dos deben usar `bge-m3`). Los
playbooks de `knowledge/` tampoco van: cada equipo los tiene en su copia del proyecto.

**Importar fusiona, no sustituye:**

| Elemento | Qué pasa |
|---|---|
| Documento que ya existe (mismo contenido) | Se ignora |
| Documento nuevo | Se añade y se indexa |
| Incidente nuevo | Se añade (y se guarda en memoria si estaba cerrado así) |
| Incidente que existe en los dos equipos | Gana la versión **modificada más recientemente** |
| Adjunto que falta | Se copia |

Antes de importar se guarda automáticamente una copia del estado actual en
`data\copias\antes-de-importar-….zip`, por si hay que volver atrás.

### Usos habituales

- **Copia periódica**: exporta al terminar cada incidente o una vez por semana y guarda el
  `.zip` fuera del equipo.
- **Cambiar de equipo**: instala el proyecto en el nuevo, arranca el backend una vez e
  importa la última copia.
- **Trabajar en dos equipos**: exporta en uno e importa en el otro; al fusionar, de cada
  incidente se queda la versión modificada más recientemente.

> La copia contiene información sensible de incidentes. Guárdala cifrada (por ejemplo, en
> un USB con BitLocker To Go) y no la subas a GitHub.

### Restaurar desde cero

Si un equipo se estropea: instala el proyecto, arranca el backend una vez e importa la
última copia.

---

## Ajustes relacionados (`backend\.env`)

| Variable | Por defecto | Efecto |
|---|---|---|
| `DOMINIOS_PROPIOS` | vacío | Dominios de tu organización, separados por comas. Sus indicadores se marcan como *propios* |
| `SIMILITUD_INCIDENTE` | `0.55` | A partir de qué parecido se considera "similar" un incidente cerrado |

---

## API

| Método | Ruta | Para qué |
|---|---|---|
| `GET` | `/incidentes?estado=abierto&q=texto` | Listar y buscar |
| `GET` | `/incidentes/resumen` | Abiertos, cerrados, en memoria, resolución media, plazos AEPD activos |
| `POST` | `/incidentes` | Crear (con `respuesta_asistente`, `mensajes`, `adjuntos`, `datos_personales`…) |
| `GET` | `/incidentes/{id}` | Ficha completa: pasos, cronología, mensajes, adjuntos, IOCs, plazo |
| `PATCH` | `/incidentes/{id}` | Cambiar título, tipo, severidad, descripción, datos personales, detección |
| `DELETE` | `/incidentes/{id}` | Borrar (también de la memoria) |
| `POST` | `/incidentes/{id}/pasos` | Añadir un paso propio |
| `PATCH` | `/incidentes/{id}/pasos/{paso}` | Marcar como hecho, editar texto o nota |
| `DELETE` | `/incidentes/{id}/pasos/{paso}` | Quitar un paso |
| `POST` | `/incidentes/{id}/notas` | Añadir una nota a la cronología |
| `DELETE` | `/incidentes/{id}/mensajes/{mensaje}` | Quitar un mensaje de la conversación guardada |
| `POST` | `/incidentes/{id}/adjuntos/{adjunto}` | Vincular un adjunto analizado |
| `POST` | `/incidentes/{id}/cerrar` | Cerrar con `notas_cierre`, `lecciones` y `guardar_en_memoria` |
| `POST` | `/incidentes/{id}/reabrir` | Reabrir (sale de la memoria) |
| `GET` | `/incidentes/{id}/informe?formato=md\|pdf&anexo=true\|false` | Informe, con o sin las consultas al asistente |
| `POST` | `/incidentes/similares` | `{"texto": "..."}` → incidentes cerrados parecidos |
| `POST` | `/chat` | Con `"incidente_id"`, la pregunta y la respuesta se guardan en la ficha |
| `GET` / `POST` | `/copia` | Exportar / importar la copia de seguridad |
