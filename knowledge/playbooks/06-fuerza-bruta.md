# Playbook: Fuerza bruta y password spraying

Tipo: intentos masivos de adivinar contraseñas contra RDP, VPN, correo, SSH, webs o Active Directory; password spraying (pocas contraseñas comunes contra muchas cuentas); credential stuffing (credenciales de filtraciones).
MITRE ATT&CK: T1110.001 (adivinación de contraseñas), T1110.003 (password spraying), T1110.004 (credential stuffing), T1133 (servicios remotos externos), T1021.001 (RDP), T1021.004 (SSH).

## Cuándo aplicar

- Muchos inicios de sesión fallidos en poco tiempo (en Windows, evento 4625; en Linux, "Failed password" en `/var/log/auth.log`).
- Bloqueos de cuentas frecuentes (evento 4740).
- Intentos contra muchas cuentas distintas desde la misma IP, o contra la misma cuenta desde muchas IPs.
- Alertas del firewall, la VPN o el servicio de correo sobre intentos de acceso.

## Severidad orientativa

- Baja: intentos fallidos contra un servicio expuesto, sin ningún acceso con éxito.
- Media: intentos dirigidos a cuentas reales de la organización o bloqueos que afectan a los usuarios.
- Alta: al menos un inicio de sesión con éxito tras los intentos fallidos.
- Crítica: acceso con éxito a una cuenta privilegiada o a un servidor crítico.

## 1. Acciones inmediatas

1. Comprobar si hay algún inicio de sesión con éxito (evento 4624) desde las mismas IPs después de los fallos. Si lo hay, aplicar también el playbook de cuenta comprometida.
2. Bloquear las IPs de origen en el firewall o en el servicio afectado.
3. Si el servicio atacado es RDP expuesto a internet, cerrarlo y dar acceso solo por VPN.
4. Restablecer la contraseña de las cuentas a las que se haya accedido y de las que tengan contraseñas débiles.

## 2. Preservación de evidencias

1. Exportar los registros de autenticación del periodo: Seguridad de Windows (4625, 4624, 4740, 4771, 4776), `auth.log` en Linux, registros de la VPN y del correo.
2. Anotar las IPs de origen, las cuentas atacadas, la frecuencia y el periodo de los intentos.
3. En eventos 4625, fijarse en el tipo de inicio de sesión (Logon Type 3 = red, 10 = RDP) y en el código de error (0xC000006A contraseña incorrecta, 0xC0000064 usuario inexistente).

## 3. Contención

1. Bloquear las IPs y rangos atacantes; en servicios web, aplicar limitación de peticiones y CAPTCHA.
2. Activar o revisar la política de bloqueo de cuentas (por ejemplo, 10 intentos fallidos y bloqueo de 15 minutos) sin que permita bloquear a todos los usuarios a propósito.
3. Exigir MFA en el servicio atacado.
4. Deshabilitar cuentas obsoletas o genéricas (admin, test, prácticas) que suelen ser objetivo.

## 4. Análisis del alcance

1. Distinguir el patrón: fuerza bruta contra pocas cuentas, password spraying contra muchas, o credential stuffing con credenciales reales filtradas.
2. Si los usuarios atacados existen de verdad, investigar cómo se obtuvieron sus nombres (web, LinkedIn, filtraciones).
3. Revisar toda la actividad de cualquier cuenta que haya iniciado sesión con éxito.
4. Comprobar si las credenciales de la organización aparecen en filtraciones conocidas.

## 5. Erradicación y recuperación

1. Cerrar o proteger los servicios expuestos innecesariamente.
2. Forzar el cambio de las contraseñas débiles o filtradas.
3. Desbloquear las cuentas legítimas afectadas por los bloqueos.

## 6. Notificación

1. Interna: responsable de seguridad y responsables de los sistemas afectados.
2. INCIBE-CERT o CCN-CERT si hubo acceso con éxito o el ataque persiste.
3. AEPD en un máximo de 72 horas solo si hubo acceso a datos personales.

## 7. Lecciones aprendidas

1. No exponer RDP ni SSH a internet; usar VPN con MFA o un bastión.
2. MFA en todos los accesos remotos y servicios en la nube.
3. Política de contraseñas largas con lista de contraseñas prohibidas.
4. Alertas automáticas ante picos de eventos 4625 y 4740.
5. Herramientas tipo fail2ban o el bloqueo de IPs del propio servicio.

## Preguntas clave para el usuario

- ¿Qué servicio están atacando (RDP, VPN, correo, web)? ¿Está expuesto a internet?
- ¿Hay algún inicio de sesión con éxito desde las IPs atacantes?
- ¿Las cuentas atacadas existen realmente en la organización?
- ¿Ese servicio tiene MFA?
