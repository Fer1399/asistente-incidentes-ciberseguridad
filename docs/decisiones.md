# Registro de decisiones

Cada decisión de diseño del proyecto, con su motivo. Sirve para entender por qué el
asistente es como es y para revisarlas si cambian las necesidades.

| # | Fecha | Decisión | Motivo |
|---|---|---|---|
| D-01 | 2026-11-10 | Funcionamiento 100 % local, sin conexiones fuera de `localhost` | Los datos de incidentes son sensibles y el asistente debe usarse sin internet |
| D-02 | 2026-11-10 | Modelos ejecutados con **Ollama** | Ejecuta LLMs en local en Windows, con API HTTP sencilla |
| D-03 | 2026-11-10 | **RAG** sobre una base de conocimiento propia | Respuestas basadas en guías y en incidentes anteriores, con fuentes citadas |
| D-04 | 2026-11-10 | El asistente responde **cómo proceder**, paso a paso (detección, evidencias, contención, análisis, erradicación, recuperación, notificación, lecciones aprendidas, MITRE ATT&CK) | Es una herramienta para resolver incidentes, no solo para describirlos |
| D-05 | 2026-11-10 | Entrada por texto, ficheros (`.eml`, `.txt`, `.log`, `.csv`, `.pdf`) y **capturas o fotos** | Los incidentes llegan en cualquier formato |
| D-06 | 2026-11-10 | Base de conocimiento a partir de **PDFs** | Las guías de referencia se distribuyen en PDF |
| D-07 | 2026-11-10 | Interfaz en el **side panel** de Chrome | Permanece abierto mientras se navega; cómodo para conversaciones largas |
| D-08 | 2026-11-10 | **Fichas de incidente** guardadas y reutilizadas | Si un incidente se repite, se recupera cómo se resolvió |
| D-09 | 2026-11-10 | **Backend local en Python** (FastAPI + ChromaDB + SQLite) | Más robusto para uso real: mejor lectura de PDFs y OCR, base vectorial persistente |
| D-10 | 2026-11-10 | Extensión en **JavaScript puro** (sin compilación) | Se carga directamente en Chrome; fácil de entender y depurar |
| D-11 | 2026-11-10 | **Exportar/importar copia de seguridad** en un `.zip` | Guardar los datos fuera del equipo y poder llevarlos a otro |
| D-12 | 2026-11-10 | Una ficha entra en la memoria **solo al cerrarla tras revisarla** | El asistente aprende de procedimientos validados, no de posibles errores del modelo |
| D-13 | 2026-11-10 | Documentación completa en `docs/` desde el inicio | El proyecto se publica en GitHub |
| D-14 | 2026-11-10 | Windows 11, arranque manual con `scripts\iniciar.bat` | No deja procesos en segundo plano; más transparente |
| D-15 | 2026-11-10 | Estilo visual claro y limpio | Legibilidad durante sesiones largas |
| D-16 | 2026-11-10 | Pestañas: Chat · Incidentes · Conocimiento · Ajustes, más la vista de ficha | Separar consulta, seguimiento, documentación y configuración |
| D-17 | 2026-11-10 | Modelo de chat según el hardware: `qwen2.5:14b` con GPU de 12 GB o más, `qwen2.5:7b` en el resto; visión `qwen2.5vl:7b`; embeddings `bge-m3` | Equilibrio entre calidad y velocidad; `bge-m3` funciona bien en español |
| D-18 | 2026-11-10 | Lectura de imágenes con modelo de visión local + **OCR con Tesseract** como respaldo | En equipos sin GPU el OCR es mucho más rápido |
| D-19 | 2026-11-10 | Extracción automática de indicadores (IOCs), mostrados desactivados (`ejemplo[.]com`) | Evitar clics accidentales en enlaces maliciosos |
| D-20 | 2026-11-10 | Checklist de pasos con hora, aviso de 72 h para la AEPD, notas de cierre, informe exportable | Seguimiento real del incidente y trazabilidad |
| D-21 | 2026-11-10 | Playbooks propios para: phishing, malware/ransomware, cuenta comprometida, fuga de datos, DDoS, fuerza bruta y acceso no autorizado | Base de conocimiento útil desde el primer día |
| D-22 | 2026-11-10 | Menú contextual *"Analizar con el asistente"* sobre texto seleccionado | Analizar correos y alertas directamente desde la web |
| D-23 | 2026-11-10 | El backend solo escucha en `127.0.0.1` y valida que Ollama sea local; telemetría de ChromaDB desactivada | Garantizar que nada sale del equipo |
| D-24 | 2026-11-10 | Repositorio `Fer1399/asistente-incidentes-ciberseguridad`, licencia **MIT** | Proyecto de portfolio: fácil de reutilizar citando al autor y sin garantía |
| D-25 | 2026-11-10 | Fragmentos de ~1000 caracteres con 150 de solape, sin mezclar páginas | Equilibrio entre contexto y precisión; citas exactas por página |
| D-26 | 2026-11-10 | OCR automático en páginas con menos de 40 caracteres, a 300 ppp, español + inglés | Leer PDFs escaneados sin intervención |
| D-27 | 2026-11-10 | Ingesta en segundo plano, un documento cada vez, con progreso en SQLite | No bloquear la API ni saturar Ollama en equipos sin GPU |
| D-28 | 2026-11-10 | Carpeta `knowledge/` indexada al arrancar; sus documentos no se pueden borrar desde la extensión | Los playbooks incluidos están siempre disponibles y versionados en Git |
| D-29 | 2026-11-10 | Documentos duplicados detectados por SHA-256 | Evitar fragmentos repetidos que sesguen las búsquedas |
| D-30 | 2026-11-10 | Aviso de reindexado si cambia el modelo de embeddings | Vectores de modelos distintos no son comparables |
| D-31 | 2026-11-10 | Pruebas automáticas con embeddings simulados | Verificar el flujo completo sin depender de Ollama |
| D-32 | 2026-11-10 | Playbooks en español con los términos técnicos en inglés | Encajan con las preguntas del usuario, con las guías de INCIBE y con la documentación técnica en inglés |
| D-33 | 2026-11-10 | Playbooks con la misma estructura que las respuestas del asistente | El modelo reproduce mejor una estructura que ve en su contexto |
| D-34 | 2026-11-10 | Cada fragmento de Markdown lleva delante su apartado (`[Playbook › Contención]`) | Un fragmento suelto se entiende y se encuentra mejor |
| D-35 | 2026-11-10 | Fuentes numeradas [n] en el contexto y citas [n] en la respuesta | Más fácil de seguir para modelos pequeños; la extensión enlaza cada número con su fuente |
| D-36 | 2026-11-10 | Respuesta en streaming (NDJSON) | En CPU una respuesta tarda; ver el texto según se genera mejora mucho la experiencia |
| D-37 | 2026-11-10 | Temperatura 0,2 y umbral de similitud 0,30 | Respuestas estables; evitar contexto irrelevante que confunda al modelo |
| D-38 | 2026-11-10 | Consola `preguntar.bat` | Usar y probar el asistente antes de tener la extensión |
| D-39 | 2026-11-10 | El asistente nunca recomienda pagar rescates ni contraatacar | Criterio ético y legal; la decisión corresponde a la dirección y las autoridades |
| D-40 | 2026-11-10 | Los adjuntos se analizan antes de llegar al modelo (alertas + IOCs + texto) | Un modelo pequeño se equivoca menos si recibe hechos ya extraídos; el análisis es reproducible |
| D-41 | 2026-11-10 | IOCs extraídos por patrones, no por el modelo, y siempre mostrados desactivados | Exactitud (sin indicadores inventados) y seguridad frente a clics accidentales |
| D-42 | 2026-11-10 | Correos: comprobación de Reply-To, Return-Path, nombre visible, SPF/DKIM/DMARC, enlaces engañosos y adjuntos peligrosos | Las señales de suplantación más habituales y objetivas |
| D-43 | 2026-11-10 | Adjuntos de correo nunca se guardan sueltos ni se ejecutan: solo su hash | Evitar la ejecución accidental de malware |
| D-44 | 2026-11-10 | Capturas: modelo de visión + OCR, con OCR como respaldo y opción de desactivar la visión | La visión entiende la pantalla; el OCR garantiza el texto exacto; en CPU la visión es lenta |
| D-45 | 2026-11-10 | Logs largos: IOCs del fichero completo, al modelo solo principio y final (12 000 caracteres) | No perder indicadores sin desbordar la memoria del modelo |
| D-46 | 2026-11-10 | Original de cada adjunto guardado como `original.bin` en `data/adjuntos` | Conservar la evidencia sin riesgo de abrirla por error |
| D-47 | 2026-11-10 | Scripts que encuentran Ollama en su carpeta de instalación aunque el PATH no esté actualizado | Evitar el error tras instalar Ollama con la consola abierta |
| D-48 | 2026-11-10 | Alertas de correo que explican qué significan ("el usuario VE… pero se ABRE…") | El modelo interpretó una alerta al revés; explicada no tiene que deducirla |
| D-49 | 2026-11-10 | Dominios propios (`DOMINIOS_PROPIOS`) y legítimos conocidos marcados en los IOCs | No presentar la marca suplantada ni la infraestructura propia como del atacante |
| D-50 | 2026-11-10 | Prompt: comentar todas las alertas, severidad en rango si falta información, citas solo de la fuente real, adaptar los pasos al caso | Corregir lo observado en las pruebas con `qwen2.5:14b` |
| D-51 | 2026-11-10 | Pasos de la ficha extraídos automáticamente de la respuesta del asistente | La checklist se crea sin copiar a mano |
| D-52 | 2026-11-10 | Cronología automática (creación, pasos con hora, notas, adjuntos, cierre) | Trazabilidad para el informe y para la notificación |
| D-53 | 2026-11-10 | Identificador `INC-AAAAMMDD-XXXX` | Legible y sin colisiones al fusionar copias de equipos distintos |
| D-54 | 2026-11-10 | Cierre con notas obligatorias; solo se memoriza lo cerrado y revisado; reabrir lo retira | Aplicación de D-12: memoria de procedimientos validados |
| D-55 | 2026-11-10 | Búsqueda separada de incidentes similares (umbral 0,55) además del RAG general | Que los PDFs largos no tapen la experiencia propia |
| D-56 | 2026-11-10 | Informe en Markdown y PDF generado con PyMuPDF | Sin dependencias nuevas ni servicios externos |
| D-57 | 2026-11-10 | Copia de seguridad sin vectores; importar fusiona y gana la versión más reciente; copia previa automática | Ligera, independiente de la versión de ChromaDB y segura para sincronizar dos equipos |
| D-58 | 2026-11-10 | Validación de la copia: manifiesto, rutas sin `..`, tamaño máximo | Evitar que un .zip manipulado escriba fuera de `data/` |
| D-59 | 2026-11-10 | Extensión Manifest V3 en JavaScript puro con módulos ES, sin compilación ni dependencias | Se carga tal cual en Chrome y es fácil de revisar (D-10) |
| D-60 | 2026-11-10 | Interfaz construida con nodos del DOM y `textContent`; nunca `innerHTML` con datos | Respuestas, correos y logs pueden contener HTML malicioso |
| D-61 | 2026-11-10 | Markdown propio y seguro: sin enlaces clicables | En incidentes, los enlaces suelen ser maliciosos |
| D-62 | 2026-11-10 | CSP que solo permite conectar con 127.0.0.1 y localhost; fuentes del sistema | Garantizar el funcionamiento sin internet y sin fugas |
| D-63 | 2026-11-10 | Permisos mínimos: sin acceso a las páginas; el menú contextual solo envía el texto seleccionado | Privacidad: la extensión no lee lo que navegas |
| D-64 | 2026-11-10 | El texto seleccionado se coloca en el cuadro de mensaje para revisarlo antes de enviar | El usuario decide qué se analiza |
| D-65 | 2026-11-10 | Modelo de chat y uso de visión elegibles desde Ajustes | Cambiar de modelo sin editar `.env` |
| D-66 | 2026-11-10 | Ollama simulado y prueba de extremo a extremo con Chrome real | Probar la extensión de forma reproducible y sin modelos |
| D-67 | 2026-11-10 | La consola no envía comandos desconocidos, separa comandos pegados a una pregunta y avisa de comandos de PowerShell | En las pruebas se colaron `/nueva`, `/salir/salir` y un comando de PowerShell en la ficha |
| D-68 | 2026-11-10 | Se pueden quitar mensajes de la conversación de una ficha abierta (queda en la cronología) | El informe debe recoger solo lo relevante, sin perder la trazabilidad |
| D-69 | 2026-11-10 | Adjuntos con el mismo SHA-256 se muestran una vez; anexo del informe opcional | Informes más limpios |
| D-70 | 2026-11-10 | Referencia local de 127 técnicas MITRE ATT&CK, indexada y con verificación visible de cada técnica citada | `qwen2.5:14b` inventó los nombres de T1486, T1490, T1497, T1499 y T1489 en una prueba real |
| D-71 | 2026-11-10 | La cabecera del playbook más relevante siempre llega al modelo | Contiene las técnicas MITRE correctas del tipo de incidente |
| D-72 | 2026-11-10 | Instalación de un solo perfil: el modelo de chat se elige según la VRAM de la GPU (o con `-ModeloChat`) | Proyecto para cualquier equipo, sin configuraciones específicas |
| D-73 | 2026-11-10 | Repositorio sin datos personales: rutas genéricas, autoría con el usuario de GitHub | Publicación abierta |
| D-74 | 2026-11-10 | Batería de 15 casos con métricas automáticas contra el modelo real | Medir la calidad de las respuestas y comparar modelos con datos |
| D-75 | 2026-11-10 | Nombres de columna de una copia importada validados contra el esquema real | Evitar inyección SQL con copias manipuladas |
| D-76 | 2026-11-10 | GitHub Actions con pruebas del backend y comprobaciones de la extensión | Detectar errores en cada cambio publicado |
