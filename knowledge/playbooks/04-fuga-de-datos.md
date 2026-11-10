# Playbook: Fuga de datos

Tipo: exfiltración por un atacante, publicación o envío accidental, pérdida o robo de dispositivos, filtración por parte de un empleado (insider), almacenamiento en la nube mal configurado.
MITRE ATT&CK: T1041 (exfiltración por el canal de mando y control), T1048 (exfiltración por protocolo alternativo), T1567 (exfiltración a un servicio web), T1530 (datos de almacenamiento en la nube), T1213 (datos de repositorios de información), T1052 (exfiltración por medio físico).

## Cuándo aplicar

- Datos de la organización aparecen publicados en internet, en foros o en un sitio de filtraciones de ransomware.
- Un correo con datos personales se envió al destinatario equivocado.
- Se pierde o roban un portátil, un móvil o un USB con información.
- Un bucket o carpeta compartida en la nube es accesible públicamente.
- Un empleado copia o envía información sin autorización.

## Severidad orientativa

- Media: pocos registros, datos no sensibles, o dispositivo perdido con cifrado de disco activo.
- Alta: datos personales de clientes o empleados, información confidencial de la empresa.
- Crítica: categorías especiales de datos (salud, datos biométricos, ideología), datos bancarios, credenciales, gran volumen de afectados o datos ya publicados.

## 1. Acciones inmediatas

1. Detener la fuga: retirar el acceso público, revocar enlaces compartidos, bloquear la cuenta implicada o el canal de salida.
2. Si fue un envío erróneo: pedir al destinatario que borre la información y lo confirme por escrito.
3. Si es un dispositivo perdido: borrado remoto si está gestionado (MDM), revocar sus sesiones y certificados, y comprobar si el disco estaba cifrado.
4. Avisar cuanto antes al DPD: empieza a contar el plazo de 72 horas para la AEPD.

## 2. Preservación de evidencias

1. Capturar dónde aparecen los datos (URL, fecha, captura de pantalla) sin descargar más de lo necesario.
2. Exportar los registros de acceso al repositorio, servidor o servicio en la nube afectado.
3. Guardar los correos o mensajes implicados con sus cabeceras.
4. Documentar qué datos, de cuántas personas y desde qué fecha estuvieron expuestos.

## 3. Contención

1. Corregir la configuración que permitió el acceso (permisos públicos, enlaces "cualquiera con el enlace", puertos abiertos).
2. Cambiar contraseñas, claves de API y certificados que estuvieran entre los datos filtrados.
3. Si es un insider: retirar accesos de forma coordinada con Recursos Humanos y asesoría legal.
4. Solicitar la retirada del contenido a la plataforma donde se ha publicado.

## 4. Análisis del alcance

1. Inventariar qué datos se han visto afectados: tipos de datos, categorías especiales, número de personas y de registros.
2. Determinar si hubo acceso efectivo por terceros (registros de descarga) o solo exposición.
3. Identificar la causa raíz: error humano, configuración, ataque externo o acción deliberada.
4. Valorar el riesgo para las personas afectadas: suplantación de identidad, fraude, daño reputacional, discriminación.

## 5. Erradicación y recuperación

1. Aplicar la corrección de forma permanente y revisar configuraciones similares en otros sistemas.
2. Si se filtraron credenciales, rotarlas todas y vigilar su uso.
3. Monitorizar si los datos reaparecen en otras fuentes.

## 6. Notificación

1. Interna: DPD, dirección, asesoría legal y comunicación.
2. AEPD: notificar la brecha de datos personales en un máximo de 72 horas desde que se tuvo conocimiento, salvo que sea improbable que suponga un riesgo para las personas. Si no se dispone de toda la información, notificar por fases.
3. Personas afectadas: informarles sin dilación indebida si el riesgo para sus derechos es alto, explicando qué ha pasado, qué datos y qué deben hacer (cambiar contraseñas, vigilar sus cuentas).
4. Registrar la brecha en el registro interno de brechas aunque no se notifique a la AEPD.
5. INCIBE-CERT o CCN-CERT, y denuncia si hay delito.

## 7. Lecciones aprendidas

1. Clasificación de la información y prevención de fuga de datos (DLP) en correo y nube.
2. Cifrado de disco obligatorio en portátiles y móviles.
3. Revisión periódica de permisos y enlaces compartidos en la nube.
4. Retraso o confirmación en el envío de correos externos con adjuntos.
5. Procedimiento de baja de empleados que retire los accesos el mismo día.

## Preguntas clave para el usuario

- ¿Qué datos se han visto afectados y de cuántas personas?
- ¿Se sabe si alguien los ha descargado o solo estuvieron expuestos?
- ¿Desde cuándo estaban expuestos y cuándo os disteis cuenta?
- ¿Hay datos de salud, bancarios o de menores?
