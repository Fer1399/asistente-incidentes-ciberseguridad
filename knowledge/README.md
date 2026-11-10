# Base de conocimiento incluida

Los documentos de esta carpeta (`.md`, `.pdf`, `.txt`) se indexan automáticamente
cada vez que arranca el backend: los nuevos se añaden y los modificados se reindexan.

- `playbooks/`: procedimientos de respuesta para 7 tipos de incidente (phishing, malware y
  ransomware, cuenta comprometida, fuga de datos, DDoS, fuerza bruta y acceso no autorizado).
  Ver [docs/05-asistente.md](../docs/05-asistente.md) para añadir o modificar playbooks.
- `referencia/mitre-attack.md`: técnicas MITRE ATT&CK habituales con su nombre oficial. Se
  genera desde `backend/app/mitre.py` (`python -m app.mitre`): no lo edites a mano.

Tus propios PDFs (guías, normativa, procedimientos internos) súbelos desde la pestaña
**Conocimiento** de la extensión; se guardan en `data/` y no se publican en GitHub.

Este README no se indexa.
