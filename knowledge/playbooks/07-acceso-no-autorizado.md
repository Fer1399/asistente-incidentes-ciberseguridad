# Playbook: Acceso no autorizado e intrusión

Tipo: intrusión en un servidor o red mediante una vulnerabilidad, acceso físico no autorizado, uso de privilegios sin permiso, webshell, persistencia del atacante en la red.
MITRE ATT&CK: T1190 (explotación de una aplicación expuesta), T1133 (servicios remotos externos), T1078 (cuentas válidas), T1068 (explotación para escalar privilegios), T1505.003 (webshell), T1136 (creación de cuentas), T1053 (tareas programadas), T1070 (eliminación de rastros).

## Cuándo aplicar

- Ficheros, cuentas, servicios o tareas programadas que nadie ha creado.
- Un servidor web con ficheros nuevos sospechosos (webshells) o cambios en la página.
- Alertas del IDS, EDR o WAF de explotación de una vulnerabilidad.
- Registros de auditoría borrados (evento 1102) o huecos en los logs.
- Acceso a salas, armarios de red o equipos por personas no autorizadas.

## Severidad orientativa

- Media: intento de explotación sin éxito confirmado.
- Alta: intrusión confirmada en un sistema sin privilegios de dominio.
- Crítica: acceso con privilegios de administrador de dominio, compromiso de servidores críticos o atacante con persistencia en la red.

## 1. Acciones inmediatas

1. Aislar el sistema comprometido de la red sin apagarlo, o restringir su tráfico a lo imprescindible para investigar.
2. No avisar al atacante: evitar cambios llamativos hasta conocer el alcance, salvo que haya daño en curso.
3. Si la entrada fue por una vulnerabilidad, aplicar el parche o una mitigación temporal (desactivar el servicio, regla en el WAF).
4. Activar el equipo de respuesta y fijar un canal de comunicación fuera de los sistemas comprometidos.

## 2. Preservación de evidencias

1. Volcar la memoria y, si es posible, hacer una imagen forense del disco antes de modificar nada.
2. Exportar los registros del sistema, de la aplicación, del servidor web, del firewall y del EDR.
3. Guardar copia de los ficheros sospechosos (webshells, scripts, binarios) y calcular su hash SHA-256.
4. Documentar la cronología y mantener la cadena de custodia.

## 3. Contención

1. Bloquear las IPs y dominios usados por el atacante.
2. Deshabilitar las cuentas creadas o usadas por el atacante y cambiar las contraseñas de las cuentas con privilegios.
3. Eliminar la persistencia identificada: webshells, tareas programadas, servicios, claves de registro `Run`, claves SSH autorizadas.
4. Segmentar el sistema comprometido del resto de la red.

## 4. Análisis del alcance

1. Identificar el vector de entrada: vulnerabilidad concreta (CVE), credenciales robadas, acceso remoto mal protegido.
2. Reconstruir los movimientos del atacante: qué sistemas tocó, qué cuentas usó, qué datos consultó o extrajo.
3. Buscar los mismos indicadores (hashes, IPs, nombres de fichero, cuentas) en el resto de la infraestructura.
4. En Active Directory, revisar cambios en grupos privilegiados (4728, 4732, 4756), cuentas nuevas (4720), cambios en GPO y uso de herramientas de volcado de credenciales.

## 5. Erradicación y recuperación

1. Reconstruir los sistemas comprometidos desde una base limpia y parcheada.
2. Restaurar datos desde copias verificadas anteriores a la intrusión.
3. Rotar todas las credenciales y secretos que pudieron quedar expuestos (incluida `krbtgt` si el dominio se vio afectado).
4. Revisar la configuración de seguridad antes de volver a exponer el servicio.
5. Monitorización reforzada para detectar si el atacante intenta volver.

## 6. Notificación

1. Interna: dirección, responsable de seguridad, asesoría legal y DPD.
2. AEPD en un máximo de 72 horas si hubo acceso a datos personales.
3. INCIBE-CERT o CCN-CERT (sector público).
4. Denuncia ante Policía Nacional o Guardia Civil: el acceso ilícito a sistemas es delito.
5. Obligaciones de NIS2 o ENS si la organización está sujeta a ellas.

## 7. Lecciones aprendidas

1. Inventario de servicios expuestos a internet y gestión de vulnerabilidades con prioridades.
2. Registro centralizado (SIEM) y protección de los logs frente a borrado.
3. Principio de mínimo privilegio y cuentas de administración separadas.
4. Segmentación de la red y control de accesos físicos.
5. Pruebas de intrusión periódicas.

## Preguntas clave para el usuario

- ¿Qué sistema está afectado y qué indicio has visto exactamente?
- ¿Está expuesto a internet? ¿Qué software y versión ejecuta?
- ¿Hay cuentas, ficheros o tareas que nadie reconozca?
- ¿Hay indicios de que el atacante haya pasado a otros equipos?
