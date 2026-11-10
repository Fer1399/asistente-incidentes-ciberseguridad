# Playbook: Phishing

Tipo: phishing, spear phishing, smishing (SMS), vishing (llamada), suplantación de correo.
MITRE ATT&CK: T1566.001 (adjunto malicioso), T1566.002 (enlace malicioso), T1566.003 (vía servicio), T1078 (uso de cuentas válidas), T1114 (recolección de correo), T1564.008 (reglas de buzón ocultas).

## Cuándo aplicar

- Un usuario recibe un correo, SMS o mensaje que suplanta a una entidad (banco, Microsoft 365, paquetería, dirección de la empresa) y pide pulsar un enlace, abrir un adjunto, introducir credenciales o hacer un pago.
- El filtro de correo o el EDR alerta de un enlace o adjunto malicioso.
- Un usuario avisa de que ha introducido su contraseña o abierto un adjunto sospechoso.

## Severidad orientativa

- Baja: correo recibido, nadie ha interactuado, sin más destinatarios.
- Media: varios destinatarios o alguien ha pulsado el enlace sin introducir datos.
- Alta: alguien ha introducido credenciales, ha abierto un adjunto o ha realizado un pago.
- Crítica: credenciales de administrador o de cuentas privilegiadas, malware ejecutado o fraude económico consumado.

## 1. Acciones inmediatas

1. Pedir al usuario que no borre el correo, no lo reenvíe a otros compañeros y no vuelva a pulsar el enlace.
2. Si introdujo credenciales: cambiar la contraseña desde un equipo limpio y cerrar todas las sesiones abiertas de la cuenta (revocar tokens).
3. Revisar y, si no está activo, activar el MFA de la cuenta afectada; eliminar métodos de MFA que el usuario no reconozca.
4. Si abrió un adjunto o ejecutó algo: aislar el equipo de la red sin apagarlo y pasar al playbook de malware.
5. Si hubo pago o transferencia: avisar de inmediato al banco para intentar retener la operación.

## 2. Preservación de evidencias

1. Exportar el correo original como `.eml` o `.msg`, con las cabeceras completas (no un reenvío ni una captura).
2. Anotar fecha y hora de recepción, de apertura y de la interacción del usuario.
3. Guardar los indicadores: remitente real (`Return-Path`, `From`, `Reply-To`), servidores en las cabeceras `Received`, URLs, dominios y hashes de adjuntos. Escribirlos desactivados: `ejemplo[.]com`, `hxxp://`.
4. Si hubo acceso con las credenciales, exportar los registros de inicio de sesión de la cuenta (IP, país, dispositivo, aplicación).

## 3. Contención

1. Bloquear el remitente, el dominio y las URLs en el filtro de correo, el proxy y el DNS.
2. Buscar el mismo correo en todos los buzones (por asunto, remitente o URL) y retirarlo antes de que más usuarios lo abran.
3. En cuentas comprometidas, revisar y eliminar reglas de reenvío o de borrado automático creadas por el atacante, delegaciones y aplicaciones con permisos OAuth no reconocidas.
4. Si el correo salió desde una cuenta interna comprometida, avisar a los destinatarios externos de que no lo abran.

## 4. Análisis del alcance

1. ¿Cuántos usuarios lo recibieron, cuántos lo abrieron, cuántos pulsaron el enlace y cuántos introdujeron datos?
2. Revisar los inicios de sesión de cada cuenta afectada desde la hora del correo: IPs y ubicaciones inusuales, viajes imposibles, nuevos dispositivos.
3. Revisar si el atacante envió correos desde la cuenta, leyó o descargó buzones, o accedió a otros servicios con la misma contraseña (reutilización).
4. Analizar las cabeceras: resultado de SPF, DKIM y DMARC; diferencia entre `From` y `Reply-To`; dominios parecidos al legítimo (typosquatting).
5. Si hubo adjunto, comprobar su hash con el EDR y en los registros del resto de equipos.

## 5. Erradicación y recuperación

1. Restablecer contraseñas de todas las cuentas afectadas y de los servicios donde se reutilizaba la misma contraseña.
2. Revocar sesiones y tokens; volver a registrar el MFA si hubo cambios no autorizados.
3. Eliminar reglas de buzón, reenvíos y aplicaciones OAuth maliciosas.
4. Mantener la monitorización reforzada de las cuentas afectadas durante al menos dos semanas.

## 6. Notificación

1. Interna: responsable de seguridad, dirección y, si hay datos personales, el Delegado de Protección de Datos (DPD).
2. AEPD: si el atacante pudo acceder a datos personales (buzón con datos de clientes o empleados), notificar la brecha en un máximo de 72 horas desde que se tuvo conocimiento. Si el riesgo para las personas es alto, informarlas también.
3. INCIBE-CERT (empresas y ciudadanos) o CCN-CERT (sector público): notificar el incidente y compartir los indicadores. El teléfono 017 de INCIBE ofrece ayuda gratuita.
4. Denuncia ante Policía Nacional o Guardia Civil si hubo fraude económico o suplantación.
5. Si la entidad está sujeta a NIS2 o al ENS, seguir sus plazos de notificación (en NIS2: alerta temprana en 24 h, notificación en 72 h e informe final en un mes para incidentes significativos).

## 7. Lecciones aprendidas

1. ¿Por qué pasó el filtro de correo? Ajustar reglas, reforzar DMARC (`p=quarantine` o `p=reject`) en el dominio propio.
2. Etiquetar los correos externos con un aviso visible.
3. Formación breve a los usuarios afectados con el ejemplo real (sin señalar a nadie).
4. Facilitar un botón o buzón para reportar phishing y agradecer cada aviso.
5. Extender el MFA resistente a phishing (llaves FIDO2, passkeys) a las cuentas críticas.

## Preguntas clave para el usuario

- ¿Pulsaste el enlace? ¿Introdujiste usuario y contraseña? ¿Abriste algún adjunto?
- ¿A qué hora ocurrió?
- ¿Usas esa misma contraseña en otros servicios?
- ¿Te llegó algún aviso de MFA que no esperabas?
