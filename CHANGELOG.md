# Cambios

## Sin publicar

- Documentación: nuevo [10 · Resultados](docs/10-resultados.md), con una prueba real
  (ransomware con `qwen2.5:14b`) y la copia de seguridad explicada paso a paso.
- Extensión: el resumen de la importación usa singular y plural correctamente
  ("1 nuevo", "2 nuevos").

## 1.0.0 · 10/11/2026

Primera versión completa.

### Asistente
- Responde **cómo proceder** ante un incidente, paso a paso: acciones inmediatas, evidencias,
  contención, análisis del alcance, erradicación y recuperación, notificación (INCIBE-CERT,
  CCN-CERT, AEPD en 72 h, NIS2, ENS), lecciones aprendidas y técnicas MITRE ATT&CK.
- Funciona **sin internet**: modelos locales con Ollama.
- **RAG** sobre una base de conocimiento local con citas `[n]` a las fuentes.
- 7 playbooks incluidos: phishing, malware y ransomware, cuenta comprometida, fuga de datos,
  DDoS, fuerza bruta y acceso no autorizado.
- Referencia local de 127 técnicas **MITRE ATT&CK** y verificación de cada técnica citada.

### Análisis de artefactos
- Correos `.eml`: cabeceras, SPF/DKIM/DMARC, Reply-To, nombre visible falsificado, enlaces
  engañosos y adjuntos peligrosos, con alertas explicadas.
- Capturas de pantalla con modelo de visión y OCR; logs, PDF y texto.
- Extracción de **indicadores de compromiso** (IP, dominio, URL, correo, hash, CVE),
  mostrados desactivados, con IPs internas y dominios legítimos marcados.

### Incidentes
- **Fichas** con checklist por fases creada desde la respuesta, hora de cada paso, cronología,
  plazo de 72 h de la AEPD, evidencias e indicadores.
- **Memoria**: los incidentes cerrados y revisados se usan como referencia en casos parecidos.
- **Informes** en Markdown y PDF generados en local.
- **Copia de seguridad** exportable e importable, con fusión y validación.

### Interfaz
- **Extensión de Chrome** con panel lateral: Chat, Incidentes, Ficha, Conocimiento y Ajustes.
- Menú contextual *Analizar con el asistente* sobre el texto seleccionado.
- Consola `scripts\preguntar.bat` como alternativa.

### Calidad
- 55 pruebas automáticas del backend, prueba de extremo a extremo de la extensión en Chrome
  y batería de evaluación de respuestas con el modelo real.
- Comprobación automática en GitHub Actions.
