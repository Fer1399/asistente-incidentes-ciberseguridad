# 09 · Evaluar la calidad de las respuestas

Las pruebas automáticas (`pytest`) comprueban que el código funciona, pero usan modelos
simulados. Para saber si **el modelo real** responde bien hay una batería de evaluación:
15 incidentes tipo que se lanzan contra el backend y se puntúan automáticamente.

Sirve para:
- Comparar modelos (por ejemplo, `qwen2.5:7b` frente a `qwen2.5:14b`).
- Comprobar que un cambio en el prompt o en los playbooks mejora las respuestas, y no al revés.
- Saber qué tipos de incidente necesitan más trabajo.

---

## Ejecutarla

Con el backend en marcha (`scripts\iniciar.bat`), en otra consola:

```powershell
scripts\evaluar.bat                         # los 15 casos
scripts\evaluar.bat ransomware-servidor     # uno o varios casos
scripts\evaluar.bat --modelo qwen2.5:7b     # con otro modelo de chat instalado
```

Con GPU tarda unos minutos; sin GPU, bastante más (cada caso es una respuesta completa).

Al terminar muestra un resumen y guarda el informe en
`backend\evaluacion\resultados\evaluacion-AAAAMMDD-HHMM.md` (con todas las respuestas, para
revisarlas) y en `.json`. Esa carpeta no se sube a Git.

```
Aprobados: 12 de 15
  estructura  15/15
  tipo        14/15
  severidad   12/15
  mitre       14/15
  citas       13/15
  playbook    15/15
  aepd        3/3
```

*(Cifras de ejemplo.)*

---

## Qué se mide

| Métrica | Se aprueba si… |
|---|---|
| **estructura** | Aparecen al menos 7 de los 8 apartados: acciones inmediatas, evidencias, contención, análisis del alcance, erradicación, notificación, lecciones aprendidas y MITRE ATT&CK |
| **tipo** | El "Tipo de incidente" contiene alguna de las palabras esperadas |
| **severidad** | La "Severidad estimada" está entre las aceptables para el caso |
| **mitre** | Se cita alguna técnica, todas están en la referencia local y al menos una es de las esperadas |
| **citas** | Hay alguna cita `[n]` y todas corresponden a una fuente que existe |
| **playbook** | Entre las fuentes recuperadas está el playbook adecuado |
| **aepd** | (Solo fugas de datos personales) se menciona la AEPD y el plazo de 72 h |

Un caso se **aprueba** si cumple todas sus métricas.

---

## Los casos

Están en [`backend/evaluacion/casos.json`](../backend/evaluacion/casos.json):

| Caso | Incidente | Severidad aceptable |
|---|---|---|
| `phishing-credenciales` | Phishing con contraseña introducida (con el correo de ejemplo adjunto) | Alta, Crítica |
| `phishing-sin-clic` | Phishing recibido sin interacción | Baja, Media |
| `smishing` | SMS fraudulento de paquetería | Baja, Media |
| `ransomware-servidor` | Ransomware en un servidor de ficheros | Crítica, Alta |
| `malware-bloqueado` | Troyano bloqueado por el antivirus | Baja, Media |
| `infostealer` | Infostealer ejecutado | Alta, Crítica |
| `mfa-bombing` | Bombardeo de MFA con una aceptación | Alta, Crítica |
| `admin-viaje-imposible` | Administrador de dominio con viaje imposible | Crítica |
| `correo-erroneo` | Datos de 300 clientes enviados por error | Media, Alta |
| `portatil-robado` | Portátil sin cifrar con nóminas robado | Alta, Crítica |
| `nube-publica` | Carpeta en la nube pública durante meses | Media, Alta |
| `ddos-web` | Tienda online caída por DDoS | Alta, Crítica |
| `fuerza-bruta-rdp` | Fuerza bruta en RDP con un acceso con éxito | Crítica, Alta |
| `password-spraying` | Password spraying sin éxito | Baja, Media |
| `webshell` | Webshell en un servidor web | Alta, Crítica |

### Añadir un caso

Añade un objeto a `casos.json`:

```json
{
  "id": "identificador-unico",
  "titulo": "Descripción corta",
  "pregunta": "Lo que escribiría el usuario",
  "adjunto": "tests/muestras/fichero.eml",
  "tipo": ["palabras", "esperadas"],
  "severidad": ["Alta", "Crítica"],
  "mitre": ["T1486"],
  "playbook": "02-malware-ransomware.md",
  "aepd": true
}
```

`adjunto` y `aepd` son opcionales. Una prueba automática comprueba que los casos están bien
formados (playbook existente, técnicas MITRE de la referencia, severidades válidas).

---

## Cómo usar los resultados

- **Severidad que falla a menudo** → revisa la *Severidad orientativa* del playbook y la
  instrucción de severidad del prompt (`backend/app/prompts.py`).
- **Playbook no recuperado** → la pregunta y el playbook usan palabras distintas: añade al
  apartado *Cuándo aplicar* del playbook las expresiones habituales.
- **Técnicas MITRE no esperadas** → comprueba que la cabecera del playbook incluye las técnicas
  correctas.
- **Citas inválidas** → el modelo cita fuentes que no existen: con modelos pequeños es más
  frecuente; prueba con uno mayor.

Repite la evaluación después de cada cambio y compara los informes.
