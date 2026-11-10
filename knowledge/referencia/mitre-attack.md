# Referencia MITRE ATT&CK

Técnicas de MITRE ATT&CK (Enterprise) más habituales en la respuesta a incidentes, con su
identificador, su nombre oficial en inglés y su táctica. Usa SIEMPRE estos identificadores y
nombres; no inventes otros. Fuente: attack.mitre.org.

Fichero generado desde backend/app/mitre.py: no lo edites a mano.

## Táctica: Reconocimiento

- T1595 Active Scanning: Escaneo activo.
- T1598 Phishing for Information: Phishing para obtener información.

## Táctica: Preparación de recursos

- T1583 Acquire Infrastructure: Adquirir infraestructura.
- T1583.001 Domains: Registrar dominios.
- T1585 Establish Accounts: Crear cuentas para el ataque.
- T1586 Compromise Accounts: Comprometer cuentas de terceros.
- T1588 Obtain Capabilities: Obtener capacidades (malware, herramientas).

## Táctica: Acceso inicial

- T1189 Drive-by Compromise: Compromiso por visita a una web.
- T1190 Exploit Public-Facing Application: Explotar una aplicación expuesta.
- T1133 External Remote Services: Servicios remotos externos (VPN, RDP).
- T1199 Trusted Relationship: Relación de confianza (proveedor).
- T1195 Supply Chain Compromise: Compromiso de la cadena de suministro.
- T1200 Hardware Additions: Añadir hardware.
- T1091 Replication Through Removable Media: Propagación por medios extraíbles.
- T1566 Phishing: Phishing.
- T1566.001 Spearphishing Attachment: Phishing con adjunto malicioso.
- T1566.002 Spearphishing Link: Phishing con enlace malicioso.
- T1566.003 Spearphishing via Service: Phishing por otro servicio (redes sociales, mensajería).
- T1566.004 Spearphishing Voice: Phishing por voz (vishing).
- T1078 Valid Accounts: Uso de cuentas válidas.
- T1078.002 Domain Accounts: Cuentas de dominio.
- T1078.004 Cloud Accounts: Cuentas en la nube.

## Táctica: Ejecución

- T1059 Command and Scripting Interpreter: Intérprete de comandos y scripts.
- T1059.001 PowerShell: PowerShell.
- T1059.003 Windows Command Shell: Consola de comandos de Windows (cmd).
- T1047 Windows Management Instrumentation: WMI.
- T1204 User Execution: Ejecución por el usuario.
- T1204.001 Malicious Link: El usuario abre un enlace malicioso.
- T1204.002 Malicious File: El usuario abre un fichero malicioso.
- T1569.002 Service Execution: Ejecución mediante servicios.

## Táctica: Persistencia

- T1053 Scheduled Task/Job: Tarea programada.
- T1053.005 Scheduled Task: Tarea programada de Windows.
- T1136 Create Account: Crear cuentas.
- T1098 Account Manipulation: Manipulación de cuentas.
- T1505.003 Web Shell: Webshell.
- T1543 Create or Modify System Process: Crear o modificar procesos del sistema.
- T1543.003 Windows Service: Servicio de Windows.
- T1547 Boot or Logon Autostart Execution: Ejecución automática al arrancar o iniciar sesión.
- T1547.001 Registry Run Keys / Startup Folder: Claves Run del registro / carpeta de inicio.
- T1556 Modify Authentication Process: Modificar el proceso de autenticación.
- T1574 Hijack Execution Flow: Secuestro del flujo de ejecución.

## Táctica: Escalada de privilegios

- T1068 Exploitation for Privilege Escalation: Explotación para escalar privilegios.
- T1548 Abuse Elevation Control Mechanism: Abuso de mecanismos de elevación (UAC).
- T1055 Process Injection: Inyección en procesos.

## Táctica: Evasión de defensas

- T1027 Obfuscated Files or Information: Ficheros o información ofuscados.
- T1036 Masquerading: Enmascaramiento.
- T1036.007 Double File Extension: Doble extensión de fichero.
- T1070 Indicator Removal: Eliminación de rastros.
- T1070.001 Clear Windows Event Logs: Borrado de los registros de eventos de Windows.
- T1112 Modify Registry: Modificar el registro.
- T1218 System Binary Proxy Execution: Ejecución mediante binarios del sistema (LOLBins).
- T1497 Virtualization/Sandbox Evasion: Evasión de máquinas virtuales y sandbox.
- T1562 Impair Defenses: Debilitar las defensas.
- T1562.001 Disable or Modify Tools: Desactivar o modificar herramientas de seguridad.
- T1564.008 Email Hiding Rules: Reglas de correo para ocultar mensajes.

## Táctica: Acceso a credenciales

- T1003 OS Credential Dumping: Volcado de credenciales del sistema.
- T1003.001 LSASS Memory: Memoria de LSASS.
- T1110 Brute Force: Fuerza bruta.
- T1110.001 Password Guessing: Adivinación de contraseñas.
- T1110.002 Password Cracking: Descifrado de contraseñas.
- T1110.003 Password Spraying: Password spraying.
- T1110.004 Credential Stuffing: Credential stuffing (credenciales filtradas).
- T1040 Network Sniffing: Captura de tráfico de red.
- T1056 Input Capture: Captura de lo que se teclea.
- T1056.001 Keylogging: Keylogger.
- T1528 Steal Application Access Token: Robo de tokens de acceso de aplicaciones.
- T1539 Steal Web Session Cookie: Robo de cookies de sesión.
- T1552 Unsecured Credentials: Credenciales sin proteger.
- T1555 Credentials from Password Stores: Credenciales de almacenes de contraseñas.
- T1555.003 Credentials from Web Browsers: Credenciales guardadas en el navegador.
- T1557 Adversary-in-the-Middle: Atacante en medio (AitM).
- T1558 Steal or Forge Kerberos Tickets: Robo o falsificación de tickets Kerberos.
- T1558.003 Kerberoasting: Kerberoasting.
- T1621 Multi-Factor Authentication Request Generation: Bombardeo de solicitudes de MFA.

## Táctica: Descubrimiento

- T1016 System Network Configuration Discovery: Descubrimiento de la configuración de red.
- T1018 Remote System Discovery: Descubrimiento de equipos remotos.
- T1046 Network Service Discovery: Descubrimiento de servicios de red.
- T1057 Process Discovery: Descubrimiento de procesos.
- T1069 Permission Groups Discovery: Descubrimiento de grupos de permisos.
- T1082 System Information Discovery: Descubrimiento de información del sistema.
- T1083 File and Directory Discovery: Descubrimiento de ficheros y carpetas.
- T1087 Account Discovery: Descubrimiento de cuentas.
- T1482 Domain Trust Discovery: Descubrimiento de relaciones de confianza del dominio.

## Táctica: Movimiento lateral

- T1021 Remote Services: Servicios remotos.
- T1021.001 Remote Desktop Protocol: Escritorio remoto (RDP).
- T1021.002 SMB/Windows Admin Shares: Recursos compartidos administrativos (SMB).
- T1021.004 SSH: SSH.
- T1534 Internal Spearphishing: Phishing interno.
- T1550.002 Pass the Hash: Pass the hash.
- T1570 Lateral Tool Transfer: Transferencia de herramientas entre equipos.

## Táctica: Recolección

- T1005 Data from Local System: Datos del equipo local.
- T1074 Data Staged: Datos preparados para extraer.
- T1113 Screen Capture: Capturas de pantalla.
- T1114 Email Collection: Recolección de correo.
- T1114.001 Local Email Collection: Recolección de correo local.
- T1114.002 Remote Email Collection: Recolección de correo remoto.
- T1114.003 Email Forwarding Rule: Reglas de reenvío de correo.
- T1119 Automated Collection: Recolección automatizada.
- T1213 Data from Information Repositories: Datos de repositorios de información (SharePoint, wikis).
- T1530 Data from Cloud Storage: Datos de almacenamiento en la nube.
- T1560 Archive Collected Data: Comprimir los datos recolectados.

## Táctica: Mando y control

- T1071 Application Layer Protocol: Protocolo de capa de aplicación.
- T1071.001 Web Protocols: Protocolos web (HTTP/HTTPS).
- T1105 Ingress Tool Transfer: Descarga de herramientas.
- T1571 Non-Standard Port: Puerto no estándar.
- T1572 Protocol Tunneling: Tunelización de protocolos.
- T1573 Encrypted Channel: Canal cifrado.

## Táctica: Exfiltración

- T1020 Automated Exfiltration: Exfiltración automatizada.
- T1041 Exfiltration Over C2 Channel: Exfiltración por el canal de mando y control.
- T1048 Exfiltration Over Alternative Protocol: Exfiltración por un protocolo alternativo.
- T1052 Exfiltration Over Physical Medium: Exfiltración por medio físico.
- T1052.001 Exfiltration over USB: Exfiltración por USB.
- T1567 Exfiltration Over Web Service: Exfiltración a un servicio web.
- T1567.002 Exfiltration to Cloud Storage: Exfiltración a almacenamiento en la nube.

## Táctica: Impacto

- T1485 Data Destruction: Destrucción de datos.
- T1486 Data Encrypted for Impact: Cifrado de datos (ransomware).
- T1489 Service Stop: Detención de servicios.
- T1490 Inhibit System Recovery: Impedir la recuperación (borrar copias de sombra y backups).
- T1491 Defacement: Desfiguración (defacement).
- T1496 Resource Hijacking: Secuestro de recursos (criptominería).
- T1498 Network Denial of Service: Denegación de servicio de red.
- T1498.001 Direct Network Flood: Inundación directa de la red.
- T1498.002 Reflection Amplification: Amplificación por reflexión.
- T1499 Endpoint Denial of Service: Denegación de servicio del equipo o servicio.
- T1499.002 Service Exhaustion Flood: Agotamiento del servicio.
- T1561 Disk Wipe: Borrado de discos.
- T1657 Financial Theft: Robo o fraude económico.
