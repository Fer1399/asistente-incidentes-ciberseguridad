# 05 · El asistente: instrucciones, playbooks y chat

Este documento explica cómo responde el asistente, cómo se usa el chat sin la extensión
y cómo adaptar sus instrucciones y playbooks.

---

## Cómo se genera una respuesta

```
 Tu pregunta
     │
     ▼
 1. Búsqueda ──── la pregunta se convierte en vector y se buscan los 6 fragmentos
     │             más parecidos (playbooks, tus PDFs y los incidentes cerrados)
     ▼
 2. Filtro ────── se descartan los fragmentos con similitud menor de 0,30
     │             y los demás se numeran [1], [2]...
     ▼
 3. Mensaje ───── system prompt + conversación anterior + contexto numerado + pregunta
     │
     ▼
 4. Modelo ────── Ollama genera la respuesta y la va enviando según la escribe
     │
     ▼
 Respuesta con citas [n] y la lista de fuentes
```

Si la pregunta es corta y de seguimiento (*"¿y si ya hizo clic?"*), la búsqueda se hace
junto con la pregunta anterior para que tenga sentido.

---

## El system prompt

Son las instrucciones permanentes del asistente. Están en
[`backend/app/prompts.py`](../backend/app/prompts.py). Le indican que:

- Actúe como analista de respuesta a incidentes y responda **cómo proceder**.
- Use el contexto como fuente principal y lo **cite con [n]**; si usa conocimiento propio,
  lo marque como *"(conocimiento general, verificar)"*.
- No invente indicadores, normativa ni datos.
- Ante un incidente, siga siempre la misma estructura:

| Apartado | Contenido |
|---|---|
| Tipo y severidad | Baja / Media / Alta / Crítica, con una frase que lo justifique |
| 1. Acciones inmediatas | Primeros 15-30 minutos |
| 2. Preservación de evidencias | Qué guardar antes de limpiar nada |
| 3. Contención | Aislar, bloquear, revocar |
| 4. Análisis del alcance | Qué revisar para saber hasta dónde llega |
| 5. Erradicación y recuperación | Limpiar y volver a la normalidad |
| 6. Notificación | Interna, INCIBE-CERT / CCN-CERT, AEPD (72 h), denuncia, NIS2 / ENS |
| 7. Lecciones aprendidas | Qué cambiar para que no se repita |
| MITRE ATT&CK | Técnicas probables con su identificador |
| Preguntas para afinar | Máximo 3, si falta información |

- Ante logs o correos pegados, explique qué indican y liste los IOCs **desactivados**
  (`ejemplo[.]com`, `hxxp://`).
- En preguntas generales responda breve, sin forzar la estructura.
- Nunca recomiende pagar un rescate ni contraatacar.

Si cambias el prompt, reinicia el backend (`Ctrl+C` y `scripts\iniciar.bat`).

---

## Los playbooks incluidos

Están en [`knowledge/playbooks/`](../knowledge/playbooks/) y se indexan solos al arrancar:

| Playbook | Cubre |
|---|---|
| `01-phishing.md` | Phishing, smishing, vishing, credenciales introducidas |
| `02-malware-ransomware.md` | Malware, infostealers, RAT, ransomware y doble extorsión |
| `03-cuenta-comprometida.md` | Robo o uso indebido de cuentas, bombardeo de MFA |
| `04-fuga-de-datos.md` | Exfiltración, envíos erróneos, dispositivos perdidos, nube mal configurada |
| `05-ddos.md` | Denegación de servicio y extorsión con DDoS |
| `06-fuerza-bruta.md` | Fuerza bruta, password spraying, credential stuffing (RDP, VPN, SSH, AD) |
| `07-acceso-no-autorizado.md` | Intrusión, webshells, persistencia, acceso físico |

Todos siguen la misma estructura que las respuestas del asistente, más un apartado de
*Cuándo aplicar*, una *Severidad orientativa* y *Preguntas clave*. Cada apartado (`##`) se
indexa con su título delante (`[Playbook: Phishing › 3. Contención]`), así cada fragmento
se entiende por sí solo.

### Añadir o modificar un playbook

1. Crea o edita un `.md` en `knowledge/playbooks/` con la misma estructura: un título `#`
   y apartados `##`.
2. Reinicia el backend: los ficheros nuevos se añaden y los modificados se reindexan.
3. Comprueba con `POST /buscar` que aparece al preguntar por ese tipo de incidente.

Los playbooks son una guía general. Para tu organización, complétalos con contactos,
herramientas y procedimientos propios, o sube tus procedimientos internos como PDF.

---

## Técnicas MITRE ATT&CK verificadas

Los modelos pequeños aciertan el identificador de una técnica pero a menudo **inventan su
nombre** (en una prueba, `T1486` salió como "uso de herramientas legítimas" cuando es *Data
Encrypted for Impact*). Por eso hay tres protecciones:

1. **Referencia local** con 127 técnicas habituales en respuesta a incidentes
   ([`backend/app/mitre.py`](../backend/app/mitre.py)), indexada también como documento
   (`knowledge/referencia/mitre-attack.md`).
2. **Cabecera del playbook siempre en contexto**: si la respuesta se basa en un playbook, el
   modelo recibe siempre su primer fragmento, que lista sus técnicas con el nombre correcto.
   El prompt le obliga a copiar identificadores y nombres del contexto, sin inventar.
3. **Verificación visible**: al terminar cada respuesta, el backend devuelve las técnicas
   citadas con su nombre oficial y táctica, y la extensión las muestra bajo la respuesta.
   Las que no están en la referencia se marcan *sin verificar*.

Para ampliar la referencia: añade la técnica en `backend/app/mitre.py` (consultando
attack.mitre.org) y regenera el documento con `python -m app.mitre`. Una prueba automática
comprueba que todas las técnicas de los playbooks están en la referencia.

## Usar el chat sin la extensión

Además de la extensión, puedes hablar con el asistente desde la consola.
Con el backend en marcha (`scripts\iniciar.bat` en una ventana), abre **otra** ventana:

```powershell
cd <carpeta-del-proyecto>
scripts\preguntar.bat
```

Escribe tu pregunta y pulsa Intro. La respuesta aparece según se genera y al final se
listan las fuentes. Comandos:

| Comando | Efecto |
|---|---|
| `/nueva` | Empieza una conversación nueva |
| `/salir` | Termina |

Los comandos van **solos en su línea**. La consola protege la conversación (y la ficha) de
errores al escribir:

| Si escribes… | La consola… |
|---|---|
| `ficha` (sin barra) | Pregunta si querías decir `/ficha` |
| `/salir/salir` o `/fichas` | Avisa de que no es un comando y no envía nada |
| `¿cómo procedo?/nueva` | Separa el comando y ofrece enviar solo la pregunta |
| `start …`, `cd …`, `Get-…` | Avisa de que parece un comando de PowerShell y, por defecto, no lo envía |

También puedes hacer una sola pregunta:

```powershell
scripts\preguntar.bat "Un usuario ha metido su contraseña en un phishing de Microsoft 365, como procedo"
```

> En un equipo sin GPU dedicada la primera respuesta tarda más porque Ollama carga el
> modelo en memoria; las siguientes son más rápidas. Una respuesta completa puede llevar
> uno o varios minutos.

---

## API del chat

`POST /chat`

```json
{
  "mensajes": [
    { "rol": "usuario",   "contenido": "Tengo un ransomware en un equipo" },
    { "rol": "asistente", "contenido": "..." },
    { "rol": "usuario",   "contenido": "¿Y si el NAS también está cifrado?" }
  ],
  "modelo": "qwen2.5:14b"
}
```

`modelo` es opcional; por defecto se usa `CHAT_MODEL` de `.env`.

La respuesta llega en **streaming**, una línea JSON por evento (NDJSON):

| Evento | Contenido |
|---|---|
| `{"tipo": "fuentes", ...}` | Primero: modelo usado, fuentes numeradas con documento, página, apartado, similitud y extracto, e incidentes similares |
| `{"tipo": "texto", "texto": "..."}` | Muchos: trozos de la respuesta según se generan |
| `{"tipo": "fin", "segundos": 12.4}` | Al terminar |
| `{"tipo": "error", "mensaje": "..."}` | Si Ollama falla a mitad de la respuesta |

---

## Ajustes (`backend\.env`)

| Variable | Por defecto | Efecto |
|---|---|---|
| `CHAT_MODEL` | `qwen2.5:7b` / `qwen2.5:14b` | Modelo que genera las respuestas |
| `FRAGMENTOS_POR_CONSULTA` | `6` | Fragmentos recuperados por pregunta |
| `SIMILITUD_MINIMA` | `0.30` | Por debajo, el fragmento no se usa |
| `TEMPERATURA` | `0.2` | Más bajo = respuestas más estables y precisas |
| `CONTEXTO_TOKENS` | `8192` | Memoria de trabajo del modelo; subirlo usa más RAM |
| `MAX_MENSAJES_HISTORIAL` | `12` | Mensajes anteriores que se envían al modelo |

---

## Limitaciones

- El asistente es un **apoyo**: las decisiones en un incidente real las toma y responde de
  ellas quien lo gestiona.
- Un modelo de 7B puede equivocarse u omitir pasos; por eso cita las fuentes. Revisa
  siempre lo que no tenga cita.
- La normativa (plazos, obligaciones NIS2/ENS) puede cambiar: mantén actualizada la base de
  conocimiento con las guías oficiales (ver [fuentes recomendadas](fuentes-recomendadas.md)).
