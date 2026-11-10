"""Referencia local de técnicas MITRE ATT&CK (Enterprise) habituales en respuesta a incidentes.

Sirve para:
- generar knowledge/referencia/mitre-attack.md, que se indexa en la base de conocimiento;
- que la extensión muestre el nombre oficial de cada técnica citada y marque las que no
  reconoce (los modelos pequeños inventan a menudo los nombres).

No es la matriz completa: son las técnicas que aparecen con más frecuencia en phishing,
malware, ransomware, cuentas comprometidas, fugas de datos, DDoS e intrusiones.
Fuente: attack.mitre.org. Si una técnica no está aquí, no significa que no exista.
"""

import re

# id: (nombre oficial en inglés, nombre en español, táctica principal)
TECNICAS: dict[str, tuple[str, str, str]] = {
    # Reconocimiento y preparación de recursos
    "T1595": ("Active Scanning", "Escaneo activo", "Reconocimiento"),
    "T1598": ("Phishing for Information", "Phishing para obtener información", "Reconocimiento"),
    "T1583": ("Acquire Infrastructure", "Adquirir infraestructura", "Preparación de recursos"),
    "T1583.001": ("Domains", "Registrar dominios", "Preparación de recursos"),
    "T1585": ("Establish Accounts", "Crear cuentas para el ataque", "Preparación de recursos"),
    "T1586": ("Compromise Accounts", "Comprometer cuentas de terceros", "Preparación de recursos"),
    "T1588": ("Obtain Capabilities", "Obtener capacidades (malware, herramientas)", "Preparación de recursos"),
    # Acceso inicial
    "T1189": ("Drive-by Compromise", "Compromiso por visita a una web", "Acceso inicial"),
    "T1190": ("Exploit Public-Facing Application", "Explotar una aplicación expuesta", "Acceso inicial"),
    "T1133": ("External Remote Services", "Servicios remotos externos (VPN, RDP)", "Acceso inicial"),
    "T1199": ("Trusted Relationship", "Relación de confianza (proveedor)", "Acceso inicial"),
    "T1195": ("Supply Chain Compromise", "Compromiso de la cadena de suministro", "Acceso inicial"),
    "T1200": ("Hardware Additions", "Añadir hardware", "Acceso inicial"),
    "T1091": ("Replication Through Removable Media", "Propagación por medios extraíbles", "Acceso inicial"),
    "T1566": ("Phishing", "Phishing", "Acceso inicial"),
    "T1566.001": ("Spearphishing Attachment", "Phishing con adjunto malicioso", "Acceso inicial"),
    "T1566.002": ("Spearphishing Link", "Phishing con enlace malicioso", "Acceso inicial"),
    "T1566.003": ("Spearphishing via Service", "Phishing por otro servicio (redes sociales, mensajería)", "Acceso inicial"),
    "T1566.004": ("Spearphishing Voice", "Phishing por voz (vishing)", "Acceso inicial"),
    "T1078": ("Valid Accounts", "Uso de cuentas válidas", "Acceso inicial"),
    "T1078.002": ("Domain Accounts", "Cuentas de dominio", "Acceso inicial"),
    "T1078.004": ("Cloud Accounts", "Cuentas en la nube", "Acceso inicial"),
    # Ejecución
    "T1059": ("Command and Scripting Interpreter", "Intérprete de comandos y scripts", "Ejecución"),
    "T1059.001": ("PowerShell", "PowerShell", "Ejecución"),
    "T1059.003": ("Windows Command Shell", "Consola de comandos de Windows (cmd)", "Ejecución"),
    "T1047": ("Windows Management Instrumentation", "WMI", "Ejecución"),
    "T1204": ("User Execution", "Ejecución por el usuario", "Ejecución"),
    "T1204.001": ("Malicious Link", "El usuario abre un enlace malicioso", "Ejecución"),
    "T1204.002": ("Malicious File", "El usuario abre un fichero malicioso", "Ejecución"),
    "T1569.002": ("Service Execution", "Ejecución mediante servicios", "Ejecución"),
    # Persistencia y escalada de privilegios
    "T1053": ("Scheduled Task/Job", "Tarea programada", "Persistencia"),
    "T1053.005": ("Scheduled Task", "Tarea programada de Windows", "Persistencia"),
    "T1136": ("Create Account", "Crear cuentas", "Persistencia"),
    "T1098": ("Account Manipulation", "Manipulación de cuentas", "Persistencia"),
    "T1505.003": ("Web Shell", "Webshell", "Persistencia"),
    "T1543": ("Create or Modify System Process", "Crear o modificar procesos del sistema", "Persistencia"),
    "T1543.003": ("Windows Service", "Servicio de Windows", "Persistencia"),
    "T1547": ("Boot or Logon Autostart Execution", "Ejecución automática al arrancar o iniciar sesión", "Persistencia"),
    "T1547.001": ("Registry Run Keys / Startup Folder", "Claves Run del registro / carpeta de inicio", "Persistencia"),
    "T1556": ("Modify Authentication Process", "Modificar el proceso de autenticación", "Persistencia"),
    "T1574": ("Hijack Execution Flow", "Secuestro del flujo de ejecución", "Persistencia"),
    "T1068": ("Exploitation for Privilege Escalation", "Explotación para escalar privilegios", "Escalada de privilegios"),
    "T1548": ("Abuse Elevation Control Mechanism", "Abuso de mecanismos de elevación (UAC)", "Escalada de privilegios"),
    "T1055": ("Process Injection", "Inyección en procesos", "Escalada de privilegios"),
    # Evasión de defensas
    "T1027": ("Obfuscated Files or Information", "Ficheros o información ofuscados", "Evasión de defensas"),
    "T1036": ("Masquerading", "Enmascaramiento", "Evasión de defensas"),
    "T1036.007": ("Double File Extension", "Doble extensión de fichero", "Evasión de defensas"),
    "T1070": ("Indicator Removal", "Eliminación de rastros", "Evasión de defensas"),
    "T1070.001": ("Clear Windows Event Logs", "Borrado de los registros de eventos de Windows", "Evasión de defensas"),
    "T1112": ("Modify Registry", "Modificar el registro", "Evasión de defensas"),
    "T1218": ("System Binary Proxy Execution", "Ejecución mediante binarios del sistema (LOLBins)", "Evasión de defensas"),
    "T1497": ("Virtualization/Sandbox Evasion", "Evasión de máquinas virtuales y sandbox", "Evasión de defensas"),
    "T1562": ("Impair Defenses", "Debilitar las defensas", "Evasión de defensas"),
    "T1562.001": ("Disable or Modify Tools", "Desactivar o modificar herramientas de seguridad", "Evasión de defensas"),
    "T1564.008": ("Email Hiding Rules", "Reglas de correo para ocultar mensajes", "Evasión de defensas"),
    # Acceso a credenciales
    "T1003": ("OS Credential Dumping", "Volcado de credenciales del sistema", "Acceso a credenciales"),
    "T1003.001": ("LSASS Memory", "Memoria de LSASS", "Acceso a credenciales"),
    "T1110": ("Brute Force", "Fuerza bruta", "Acceso a credenciales"),
    "T1110.001": ("Password Guessing", "Adivinación de contraseñas", "Acceso a credenciales"),
    "T1110.002": ("Password Cracking", "Descifrado de contraseñas", "Acceso a credenciales"),
    "T1110.003": ("Password Spraying", "Password spraying", "Acceso a credenciales"),
    "T1110.004": ("Credential Stuffing", "Credential stuffing (credenciales filtradas)", "Acceso a credenciales"),
    "T1040": ("Network Sniffing", "Captura de tráfico de red", "Acceso a credenciales"),
    "T1056": ("Input Capture", "Captura de lo que se teclea", "Acceso a credenciales"),
    "T1056.001": ("Keylogging", "Keylogger", "Acceso a credenciales"),
    "T1528": ("Steal Application Access Token", "Robo de tokens de acceso de aplicaciones", "Acceso a credenciales"),
    "T1539": ("Steal Web Session Cookie", "Robo de cookies de sesión", "Acceso a credenciales"),
    "T1552": ("Unsecured Credentials", "Credenciales sin proteger", "Acceso a credenciales"),
    "T1555": ("Credentials from Password Stores", "Credenciales de almacenes de contraseñas", "Acceso a credenciales"),
    "T1555.003": ("Credentials from Web Browsers", "Credenciales guardadas en el navegador", "Acceso a credenciales"),
    "T1557": ("Adversary-in-the-Middle", "Atacante en medio (AitM)", "Acceso a credenciales"),
    "T1558": ("Steal or Forge Kerberos Tickets", "Robo o falsificación de tickets Kerberos", "Acceso a credenciales"),
    "T1558.003": ("Kerberoasting", "Kerberoasting", "Acceso a credenciales"),
    "T1621": ("Multi-Factor Authentication Request Generation", "Bombardeo de solicitudes de MFA", "Acceso a credenciales"),
    # Descubrimiento
    "T1016": ("System Network Configuration Discovery", "Descubrimiento de la configuración de red", "Descubrimiento"),
    "T1018": ("Remote System Discovery", "Descubrimiento de equipos remotos", "Descubrimiento"),
    "T1046": ("Network Service Discovery", "Descubrimiento de servicios de red", "Descubrimiento"),
    "T1057": ("Process Discovery", "Descubrimiento de procesos", "Descubrimiento"),
    "T1069": ("Permission Groups Discovery", "Descubrimiento de grupos de permisos", "Descubrimiento"),
    "T1082": ("System Information Discovery", "Descubrimiento de información del sistema", "Descubrimiento"),
    "T1083": ("File and Directory Discovery", "Descubrimiento de ficheros y carpetas", "Descubrimiento"),
    "T1087": ("Account Discovery", "Descubrimiento de cuentas", "Descubrimiento"),
    "T1482": ("Domain Trust Discovery", "Descubrimiento de relaciones de confianza del dominio", "Descubrimiento"),
    # Movimiento lateral
    "T1021": ("Remote Services", "Servicios remotos", "Movimiento lateral"),
    "T1021.001": ("Remote Desktop Protocol", "Escritorio remoto (RDP)", "Movimiento lateral"),
    "T1021.002": ("SMB/Windows Admin Shares", "Recursos compartidos administrativos (SMB)", "Movimiento lateral"),
    "T1021.004": ("SSH", "SSH", "Movimiento lateral"),
    "T1534": ("Internal Spearphishing", "Phishing interno", "Movimiento lateral"),
    "T1550.002": ("Pass the Hash", "Pass the hash", "Movimiento lateral"),
    "T1570": ("Lateral Tool Transfer", "Transferencia de herramientas entre equipos", "Movimiento lateral"),
    # Recolección
    "T1005": ("Data from Local System", "Datos del equipo local", "Recolección"),
    "T1074": ("Data Staged", "Datos preparados para extraer", "Recolección"),
    "T1113": ("Screen Capture", "Capturas de pantalla", "Recolección"),
    "T1114": ("Email Collection", "Recolección de correo", "Recolección"),
    "T1114.001": ("Local Email Collection", "Recolección de correo local", "Recolección"),
    "T1114.002": ("Remote Email Collection", "Recolección de correo remoto", "Recolección"),
    "T1114.003": ("Email Forwarding Rule", "Reglas de reenvío de correo", "Recolección"),
    "T1119": ("Automated Collection", "Recolección automatizada", "Recolección"),
    "T1213": ("Data from Information Repositories", "Datos de repositorios de información (SharePoint, wikis)", "Recolección"),
    "T1530": ("Data from Cloud Storage", "Datos de almacenamiento en la nube", "Recolección"),
    "T1560": ("Archive Collected Data", "Comprimir los datos recolectados", "Recolección"),
    # Mando y control
    "T1071": ("Application Layer Protocol", "Protocolo de capa de aplicación", "Mando y control"),
    "T1071.001": ("Web Protocols", "Protocolos web (HTTP/HTTPS)", "Mando y control"),
    "T1105": ("Ingress Tool Transfer", "Descarga de herramientas", "Mando y control"),
    "T1571": ("Non-Standard Port", "Puerto no estándar", "Mando y control"),
    "T1572": ("Protocol Tunneling", "Tunelización de protocolos", "Mando y control"),
    "T1573": ("Encrypted Channel", "Canal cifrado", "Mando y control"),
    # Exfiltración
    "T1020": ("Automated Exfiltration", "Exfiltración automatizada", "Exfiltración"),
    "T1041": ("Exfiltration Over C2 Channel", "Exfiltración por el canal de mando y control", "Exfiltración"),
    "T1048": ("Exfiltration Over Alternative Protocol", "Exfiltración por un protocolo alternativo", "Exfiltración"),
    "T1052": ("Exfiltration Over Physical Medium", "Exfiltración por medio físico", "Exfiltración"),
    "T1052.001": ("Exfiltration over USB", "Exfiltración por USB", "Exfiltración"),
    "T1567": ("Exfiltration Over Web Service", "Exfiltración a un servicio web", "Exfiltración"),
    "T1567.002": ("Exfiltration to Cloud Storage", "Exfiltración a almacenamiento en la nube", "Exfiltración"),
    # Impacto
    "T1485": ("Data Destruction", "Destrucción de datos", "Impacto"),
    "T1486": ("Data Encrypted for Impact", "Cifrado de datos (ransomware)", "Impacto"),
    "T1489": ("Service Stop", "Detención de servicios", "Impacto"),
    "T1490": ("Inhibit System Recovery", "Impedir la recuperación (borrar copias de sombra y backups)", "Impacto"),
    "T1491": ("Defacement", "Desfiguración (defacement)", "Impacto"),
    "T1496": ("Resource Hijacking", "Secuestro de recursos (criptominería)", "Impacto"),
    "T1498": ("Network Denial of Service", "Denegación de servicio de red", "Impacto"),
    "T1498.001": ("Direct Network Flood", "Inundación directa de la red", "Impacto"),
    "T1498.002": ("Reflection Amplification", "Amplificación por reflexión", "Impacto"),
    "T1499": ("Endpoint Denial of Service", "Denegación de servicio del equipo o servicio", "Impacto"),
    "T1499.002": ("Service Exhaustion Flood", "Agotamiento del servicio", "Impacto"),
    "T1561": ("Disk Wipe", "Borrado de discos", "Impacto"),
    "T1657": ("Financial Theft", "Robo o fraude económico", "Impacto"),
}

_PATRON = re.compile(r"\bT\d{4}(?:\.\d{3})?\b")


def citadas(texto: str) -> list[str]:
    """Identificadores de técnica que aparecen en un texto, sin repetir y en orden."""
    vistos: list[str] = []
    for tecnica in _PATRON.findall(texto or ""):
        if tecnica not in vistos:
            vistos.append(tecnica)
    return vistos


def verificar(texto: str) -> list[dict]:
    """Cada técnica citada con su nombre oficial, o marcada como no reconocida."""
    resultado = []
    for tecnica in citadas(texto):
        datos = TECNICAS.get(tecnica)
        padre = TECNICAS.get(tecnica.split(".")[0]) if "." in tecnica else None
        resultado.append({
            "id": tecnica,
            "reconocida": datos is not None,
            "nombre": datos[0] if datos else None,
            "nombre_es": datos[1] if datos else None,
            "tactica": datos[2] if datos else (padre[2] if padre else None),
            "tecnica_padre": padre[0] if (padre and not datos) else None,
        })
    return resultado


def documento_referencia() -> str:
    """Markdown que se guarda en knowledge/referencia/mitre-attack.md."""
    lineas = [
        "# Referencia MITRE ATT&CK",
        "",
        "Técnicas de MITRE ATT&CK (Enterprise) más habituales en la respuesta a incidentes, con su",
        "identificador, su nombre oficial en inglés y su táctica. Usa SIEMPRE estos identificadores y",
        "nombres; no inventes otros. Fuente: attack.mitre.org.",
        "",
        "Fichero generado desde backend/app/mitre.py: no lo edites a mano.",
    ]
    por_tactica: dict[str, list[str]] = {}
    for tecnica, (nombre, nombre_es, tactica) in TECNICAS.items():
        por_tactica.setdefault(tactica, []).append(f"- {tecnica} {nombre}: {nombre_es}.")
    for tactica, filas in por_tactica.items():
        lineas += ["", f"## Táctica: {tactica}", "", *filas]
    return "\n".join(lineas) + "\n"


if __name__ == "__main__":
    from pathlib import Path

    destino = Path(__file__).resolve().parents[2] / "knowledge" / "referencia" / "mitre-attack.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(documento_referencia(), encoding="utf-8")
    print(f"Escrito {destino} ({len(TECNICAS)} técnicas)")
