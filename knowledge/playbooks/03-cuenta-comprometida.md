# Playbook: Cuenta comprometida

Tipo: robo o uso indebido de credenciales de una cuenta de usuario, de correo, de nube o de administración.
MITRE ATT&CK: T1078 (cuentas válidas), T1110 (fuerza bruta), T1621 (bombardeo de solicitudes MFA), T1098 (manipulación de cuentas), T1114.003 (reglas de reenvío de correo), T1528 (robo de tokens de aplicación), T1539 (robo de cookies de sesión).

## Cuándo aplicar

- Inicios de sesión desde países, IPs o dispositivos inusuales, o "viajes imposibles".
- El usuario recibe solicitudes de MFA que no ha pedido.
- Correos enviados que el usuario no reconoce, reglas de reenvío nuevas o contraseña cambiada sin su intervención.
- Credenciales de la organización aparecen en una filtración o en un registro de infostealer.

## Severidad orientativa

- Media: cuenta estándar con acceso sospechoso y sin actividad maliciosa confirmada.
- Alta: actividad maliciosa confirmada (envío de correos, descarga de datos, cambios en la cuenta).
- Crítica: cuenta con privilegios (administrador de dominio, de la nube o de sistemas críticos), o acceso a datos sensibles a gran escala.

## 1. Acciones inmediatas

1. Restablecer la contraseña desde un equipo de confianza y obligar a cerrar todas las sesiones activas.
2. Revocar tokens de acceso y de actualización, y las contraseñas de aplicación.
3. Revisar los métodos de MFA registrados y eliminar los que el usuario no reconozca.
4. Si es una cuenta privilegiada, deshabilitarla temporalmente mientras se analiza y usar una cuenta de emergencia controlada.
5. Si el usuario aceptó una solicitud de MFA que no pidió, tratarlo como acceso confirmado.

## 2. Preservación de evidencias

1. Exportar los registros de inicio de sesión (fecha, IP, ubicación, dispositivo, aplicación, resultado del MFA).
2. Exportar los registros de auditoría de la cuenta: cambios de configuración, permisos, reglas de buzón, descargas y accesos a ficheros.
3. En Active Directory, recoger los eventos 4624, 4625, 4648, 4768, 4769, 4738 (cuenta modificada) y 4728/4732/4756 (añadida a grupos).
4. Anotar la cronología: primer acceso sospechoso, acciones del atacante y hora de detección.

## 3. Contención

1. Bloquear las IPs de origen del atacante en el firewall o en las políticas de acceso condicional.
2. Eliminar reglas de reenvío o borrado, delegaciones de buzón y aplicaciones OAuth no autorizadas.
3. Revisar si se crearon cuentas nuevas, se añadieron miembros a grupos privilegiados o se cambiaron permisos, y revertirlo.
4. Si la contraseña se reutilizaba en otros servicios, cambiarla también en ellos.

## 4. Análisis del alcance

1. ¿Cómo se obtuvo la credencial? Phishing, infostealer en el equipo del usuario, reutilización de una filtración, fuerza bruta o password spraying.
2. ¿A qué datos y sistemas accedió el atacante con esa cuenta? ¿Descargó o compartió información?
3. ¿Usó la cuenta para moverse a otros sistemas o enviar phishing interno?
4. Si se sospecha un infostealer, analizar el equipo del usuario: las cookies y contraseñas guardadas en el navegador pueden estar comprometidas.

## 5. Erradicación y recuperación

1. Si hubo infostealer: reinstalar el equipo y cambiar todas las contraseñas guardadas en el navegador.
2. Revisar que no queden puertas traseras: claves SSH, tokens de API, cuentas de servicio o aplicaciones registradas por el atacante.
3. Volver a habilitar la cuenta con MFA activo y monitorización reforzada durante al menos dos semanas.

## 6. Notificación

1. Interna: responsable de seguridad, responsable del sistema afectado y DPD si hubo acceso a datos personales.
2. AEPD en un máximo de 72 horas si el atacante pudo acceder a datos personales.
3. INCIBE-CERT o CCN-CERT (sector público).
4. Denuncia ante las autoridades si hubo fraude, suplantación o robo de información.

## 7. Lecciones aprendidas

1. MFA en todas las cuentas, con número de coincidencia (number matching) o FIDO2 para frenar el bombardeo de MFA.
2. Políticas de acceso condicional: bloquear países y dispositivos no gestionados.
3. Gestor de contraseñas y prohibición de reutilizar contraseñas.
4. Alertas de viajes imposibles e inicios de sesión de riesgo.
5. Separar cuentas de administración de las de uso diario.

## Preguntas clave para el usuario

- ¿Has recibido avisos de MFA que no esperabas? ¿Aceptaste alguno?
- ¿Has introducido tu contraseña en algún enlace recientemente?
- ¿Usas la misma contraseña en otros sitios?
- ¿Es una cuenta con privilegios de administración?
