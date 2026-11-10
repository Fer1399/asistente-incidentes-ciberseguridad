# Seguridad

El Asistente de Incidentes maneja información sensible (correos maliciosos, indicadores,
datos de incidentes y, a veces, datos personales). Este documento explica cómo está
protegido, qué no cubre y cómo informar de un problema.

## Modelo de amenazas

| Supuesto | Consecuencia |
|---|---|
| Se usa en **un equipo de una sola persona** | El backend no tiene usuarios ni contraseñas: cualquier programa que se ejecute en ese mismo equipo puede llamar a su API |
| Los **artefactos analizados pueden ser maliciosos** (correos, adjuntos, PDFs, capturas, logs) | Se tratan siempre como datos: nunca se ejecutan, abren ni interpretan como HTML |
| Las **respuestas del modelo pueden ser erróneas** o estar influidas por el contenido analizado (inyección de instrucciones) | El asistente es un apoyo: las decisiones las toma una persona, y las fuentes, indicadores y técnicas MITRE se verifican aparte |
| Las **copias de seguridad pueden venir de fuera** | Se validan antes de importarlas |

## Medidas

### Red
- El backend solo escucha en `127.0.0.1`; la configuración rechaza cualquier otra dirección,
  y también una dirección de Ollama que no sea local.
- Los clientes HTTP ignoran los proxies del sistema (`trust_env=False`).
- ChromaDB se usa **integrado**, sin su servidor HTTP, con la telemetría desactivada y sin
  función de embeddings propia (no descarga nada).
- La extensión tiene una política de seguridad de contenidos (CSP) que solo permite conectar
  con `127.0.0.1` y `localhost`, y no carga recursos externos (ni fuentes ni scripts).
- CORS: el backend solo acepta peticiones del navegador procedentes de extensiones de Chrome.

### Extensión
- Permisos mínimos: `sidePanel`, `contextMenus`, `storage` y acceso a `127.0.0.1`/`localhost`.
  **No** tiene acceso al contenido de las páginas que visitas: el menú contextual solo envía
  el texto que seleccionas, y lo coloca en el cuadro de mensaje para que lo revises.
- La interfaz se construye con nodos del DOM y `textContent`: nunca `innerHTML`, `eval` ni
  similares con datos.
- El Markdown de las respuestas se interpreta con un analizador propio que no crea enlaces.

### Artefactos
- Los adjuntos de los correos nunca se guardan sueltos ni se ejecutan: solo se calcula su hash.
- El original de cada fichero analizado se guarda como `data/adjuntos/<id>/original.bin`, con
  un nombre neutro para que no se abra por accidente.
- Los indicadores se muestran siempre desactivados (`ejemplo[.]com`, `hxxp://`).
- Límites de tamaño: 25 MB por adjunto y 200 MB por documento.
- Las imágenes se reducen antes de analizarlas.

### Copias de seguridad
- Se valida el manifiesto, el formato, que ninguna ruta salga de su carpeta (`..`, rutas
  absolutas) y el tamaño total descomprimido (máximo 2 GB).
- Los nombres de columna de la base de datos importada se comparan con los reales antes de
  usarlos en consultas: una copia manipulada no puede inyectar SQL.
- Antes de importar se guarda automáticamente una copia del estado actual.

### Datos
- Todo se guarda en la carpeta `data/`, excluida de Git.
- Las consultas SQL usan parámetros; los nombres de columna proceden siempre de listas fijas.

## Dependencias

Comprobar vulnerabilidades conocidas de las dependencias de Python:

```powershell
cd backend
.venv\Scripts\python.exe -m pip install pip-audit
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

Avisos conocidos que **no afectan** a este proyecto (revisados el 10/11/2026):

| Aviso | Paquete | Por qué no afecta |
|---|---|---|
| CVE-2026-45829, CVE-2026-45830, CVE-2026-45831, CVE-2026-45833 | `chromadb` | Afectan a las rutas `/api/v2/...` y al sistema de permisos del **servidor HTTP** de ChromaDB. Aquí ChromaDB se usa integrado en el proceso (`PersistentClient`) y su servidor nunca se arranca |

PyMuPDF procesa PDFs que pueden ser maliciosos: mantenlo actualizado
(`pip install -U pymupdf` dentro del entorno) y, si analizas muestras peligrosas, hazlo en
una máquina virtual.

## Recomendaciones de uso

- Usa el asistente en un equipo con disco cifrado (BitLocker) y una sola cuenta de usuario.
- Guarda las copias de seguridad cifradas (por ejemplo, un USB con BitLocker To Go): contienen
  información sensible de los incidentes.
- Analiza muestras de malware reales en una máquina virtual aislada.
- No subas a GitHub la carpeta `data/`, ni copias de seguridad, ni el `.env` (ya están en
  `.gitignore`).

## Informar de una vulnerabilidad

Si encuentras un problema de seguridad, **no abras una incidencia pública**. Usa la pestaña
**Security → Report a vulnerability** del repositorio en GitHub, con una descripción y, si es
posible, los pasos para reproducirlo. No incluyas datos reales de incidentes.
