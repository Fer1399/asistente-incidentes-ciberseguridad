# Playbook: Denegación de servicio (DoS/DDoS)

Tipo: ataque volumétrico (inundación de tráfico), ataque de protocolo (SYN flood), ataque a la capa de aplicación (peticiones HTTP masivas), extorsión con amenaza de DDoS.
MITRE ATT&CK: T1498 (denegación de servicio de red), T1498.001 (inundación directa), T1498.002 (reflexión y amplificación), T1499 (denegación de servicio del endpoint), T1499.002 (agotamiento del servicio).

## Cuándo aplicar

- Una web, VPN o servicio expuesto deja de responder o va muy lento sin cambios internos que lo expliquen.
- El tráfico entrante se dispara, con muchas IPs de origen o peticiones repetidas a la misma URL.
- El proveedor de internet o de hosting avisa de un ataque.
- Se recibe un mensaje que amenaza con un ataque si no se paga.

## Severidad orientativa

- Baja: picos breves sin impacto en el servicio.
- Media: degradación del servicio sin interrupción total.
- Alta: servicio principal caído o inaccesible para los clientes.
- Crítica: interrupción prolongada de servicios esenciales, o DDoS usado como distracción de otro ataque.

## 1. Acciones inmediatas

1. Confirmar que es un ataque y no un fallo propio o un pico legítimo (campaña, noticia, actualización).
2. Contactar con el proveedor de internet, hosting o servicio anti-DDoS (CDN, WAF) y activar la mitigación.
3. Comunicar a los usuarios internos que hay una incidencia en curso para evitar acciones descoordinadas.
4. Vigilar el resto de sistemas: un DDoS puede ser una cortina de humo para otra intrusión.

## 2. Preservación de evidencias

1. Guardar los registros del firewall, el balanceador, el servidor web y el WAF durante el ataque.
2. Si es posible, capturar una muestra de tráfico (`.pcap`) durante unos minutos.
3. Anotar la hora de inicio, los picos, los servicios afectados y las medidas aplicadas con su hora.
4. Conservar cualquier mensaje de extorsión.

## 3. Contención

1. Aplicar limitación de peticiones (rate limiting) y filtros en el WAF para el patrón del ataque (URL, user-agent, método).
2. Bloquear países o rangos de IP de origen si no hay clientes legítimos en ellos.
3. Activar la protección anti-DDoS del proveedor o derivar el tráfico a un servicio de limpieza (scrubbing).
4. Desactivar temporalmente funciones costosas del servicio (búsquedas, generación de informes) para reducir la carga.
5. En ataques de amplificación, revisar que los servidores propios (DNS, NTP, memcached) no se estén usando como amplificadores.

## 4. Análisis del alcance

1. Identificar el tipo de ataque (volumétrico, de protocolo o de aplicación) y su pico de tráfico o peticiones por segundo.
2. Determinar qué servicios estuvieron afectados y durante cuánto tiempo.
3. Revisar si hubo intentos de intrusión o actividad anómala en paralelo.

## 5. Erradicación y recuperación

1. Mantener la mitigación activa hasta que el tráfico se normalice durante un periodo prolongado.
2. Retirar gradualmente los bloqueos temporales que afecten a usuarios legítimos.
3. Comprobar la integridad de los servicios y que no hay otras alertas pendientes.

## 6. Notificación

1. Interna: dirección, comunicación y atención al cliente.
2. INCIBE-CERT o CCN-CERT (sector público), compartiendo las IPs y patrones.
3. Denuncia ante las autoridades, especialmente si hubo extorsión. No pagar.
4. Obligaciones de NIS2 o ENS si la interrupción afecta a servicios sujetos a ellas.
5. La AEPD solo interviene si hay datos personales afectados (normalmente no en un DDoS puro, salvo pérdida de disponibilidad relevante).

## 7. Lecciones aprendidas

1. Contratar protección anti-DDoS o CDN para los servicios expuestos.
2. Tener los contactos de emergencia del proveedor documentados y probados.
3. Arquitectura con capacidad de escalado y caché.
4. Plan de comunicación para clientes durante caídas del servicio.

## Preguntas clave para el usuario

- ¿Qué servicio está afectado y desde cuándo?
- ¿Habéis recibido algún mensaje de amenaza o extorsión?
- ¿Tenéis protección anti-DDoS, CDN o WAF contratada?
- ¿Hay otras alertas de seguridad al mismo tiempo?
