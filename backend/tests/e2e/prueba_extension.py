"""Prueba de extremo a extremo: la extensión cargada en Chrome real contra el backend.

Requisitos: pip install playwright, Google Chrome instalado, el backend en marcha y,
para que sea reproducible, el Ollama simulado (tests/ollama_simulado.py) en lugar del real.
Ver docs/08-extension.md, apartado "Prueba automática de la extensión".

Uso:  python tests/e2e/prueba_extension.py CARPETA_CAPTURAS [RUTA_CHROME]
"""

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[3]
EXT = RAIZ / "extension"
SALIDA = Path(sys.argv[1] if len(sys.argv) > 1 else "capturas-e2e").resolve()
CHROME = sys.argv[2] if len(sys.argv) > 2 else shutil.which("google-chrome") or shutil.which("chrome")
CORREO = RAIZ / "backend" / "tests" / "muestras" / "phishing-ejemplo.eml"
SALIDA.mkdir(parents=True, exist_ok=True)

errores = []

with sync_playwright() as p:
    contexto = p.chromium.launch_persistent_context(
        str(SALIDA / "perfil"),
        executable_path=CHROME,
        headless=False,
        args=["--headless=new", f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"],
        viewport={"width": 420, "height": 860},
        device_scale_factor=2,
    )
    worker = contexto.service_workers[0] if contexto.service_workers else contexto.wait_for_event("serviceworker")
    ext_id = worker.url.split("/")[2]
    print("extension id:", ext_id)

    pagina = contexto.new_page()
    pagina.on("console", lambda m: errores.append(f"[{m.type}] {m.text}") if m.type in ("error", "warning") else None)
    pagina.on("pageerror", lambda e: errores.append(f"[pageerror] {e}"))
    pagina.goto(f"chrome-extension://{ext_id}/sidepanel/index.html")
    pagina.wait_for_selector("#estado.ok", timeout=15000)
    pagina.screenshot(path=SALIDA / "01-chat-vacio.png")

    # Chat con adjunto
    pagina.set_input_files("input[type=file][accept^='.eml']", str(CORREO))
    pagina.wait_for_selector(".pendiente:not(.error) >> text=alertas", timeout=20000)
    pagina.fill("#entrada", "Un usuario metió su contraseña en este correo, ¿cómo procedo?")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector(".respuesta-pie", timeout=60000)
    pagina.wait_for_timeout(400)
    pagina.screenshot(path=SALIDA / "02-chat-respuesta.png", full_page=False)
    lista = pagina.locator("#mensajes")
    lista.evaluate("el => el.scrollTop = el.scrollHeight")
    pagina.wait_for_timeout(200)
    pagina.screenshot(path=SALIDA / "03-chat-fuentes.png")

    # Verificación MITRE bajo la respuesta
    assert pagina.locator("text=Técnicas MITRE ATT&CK citadas").count() >= 1, "falta la verificación MITRE"
    pagina.locator("summary >> text=Técnicas MITRE ATT&CK citadas").first.click()
    pagina.locator("text=Técnicas MITRE ATT&CK citadas").first.scroll_into_view_if_needed()
    pagina.screenshot(path=SALIDA / "03b-mitre.png")
    print("verificación MITRE:", pagina.locator(".mitre-fila").count(), "técnicas")

    # Cita → fuente
    pagina.locator(".cita").first.click()
    assert pagina.locator(".fuente-detalle:not([hidden])").count() == 1, "la cita no muestra la fuente"

    # Crear ficha
    pagina.click("text=Crear ficha de incidente")
    pagina.fill(".modal input.entrada", "Phishing Microsoft 365 - Contabilidad")
    pagina.check(".modal input[type=checkbox]")
    pagina.click(".modal-acciones >> text=Crear ficha")
    pagina.wait_for_selector(".ficha-titulo", timeout=10000)
    pagina.wait_for_timeout(300)
    # Marcar tres pasos
    for i in range(3):
        pagina.locator(".paso input[type=checkbox]:not(:checked)").first.check()
        pagina.wait_for_timeout(350)
    pagina.fill("input[placeholder^='Añadir un paso propio']", "Bloquear la IP 185.220.101.45 en el firewall perimetral")
    pagina.keyboard.press("Enter")
    pagina.wait_for_timeout(500)
    pagina.screenshot(path=SALIDA / "04-ficha.png")
    progreso = pagina.locator(".tarjeta >> text=/de \\d+ pasos/").first.inner_text()
    print("progreso:", progreso)

    # Quitar un mensaje de la conversación guardada en la ficha
    pagina.click("summary >> text=Conversación con el asistente (2)")
    pagina.locator("button[aria-label='Quitar este mensaje de la conversación']").last.click()
    pagina.click(".modal-acciones >> text=Quitar")
    pagina.wait_for_selector("summary >> text=Conversación con el asistente (1)", timeout=10000)
    print("mensaje quitado de la ficha: True")

    # Lista de incidentes
    pagina.click(".pestana[data-vista=incidentes]")
    pagina.wait_for_selector(".incidente", timeout=10000)
    pagina.screenshot(path=SALIDA / "05-incidentes.png")

    # Cerrar la ficha
    pagina.locator(".incidente").first.click()
    pagina.wait_for_selector(".ficha-titulo")
    pagina.click("text=Cerrar y guardar")
    pagina.fill(".modal textarea >> nth=0", "Se cambió la contraseña a los 10 minutos, se revocaron las sesiones y se bloqueó el dominio. Nadie más abrió el correo.")
    pagina.fill(".modal textarea >> nth=1", "Activar DMARC en modo reject y etiquetar los correos externos.")
    pagina.click(".modal-acciones >> text=Cerrar incidente")
    pagina.wait_for_selector("text=Cerrado · en memoria", timeout=10000)
    pagina.wait_for_timeout(1500)
    pagina.screenshot(path=SALIDA / "06-ficha-cerrada.png")

    # Nueva conversación: debe aparecer el aviso de incidente similar
    pagina.click(".pestana[data-vista=chat]")
    pagina.click("text=Nueva")
    pagina.wait_for_selector("text=¿Qué ha pasado?")
    pagina.fill("#entrada", "Otro usuario ha metido su contraseña en un phishing de Microsoft 365")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector(".respuesta-pie", timeout=60000)
    similar = pagina.locator("text=Ya ha pasado algo parecido").count()
    print("aviso de incidente similar:", similar)
    pagina.locator("#mensajes").evaluate("el => el.scrollTop = 0")
    pagina.screenshot(path=SALIDA / "07-chat-similar.png")

    # Conocimiento
    pagina.click(".pestana[data-vista=conocimiento]")
    pagina.wait_for_selector(".documento", timeout=10000)
    pagina.fill("input[placeholder^='p. ej.']", "notificación brecha 72 horas AEPD")
    pagina.keyboard.press("Enter")
    pagina.wait_for_selector(".resultado", timeout=10000)
    pagina.screenshot(path=SALIDA / "08-conocimiento.png")

    # Ajustes
    pagina.click(".pestana[data-vista=ajustes]")
    pagina.wait_for_selector("text=Bloqueadas")
    pagina.wait_for_timeout(300)
    pagina.screenshot(path=SALIDA / "09-ajustes.png")

    # Exportar copia (descarga)
    with pagina.expect_download() as descarga:
        pagina.click("text=Exportar")
    print("copia descargada:", descarga.value.suggested_filename)

    # Menú contextual: simular lo que guarda el service worker
    worker.evaluate("""() => chrome.storage.session.set({ seleccionPendiente: {
        texto: 'Failed password for root from 203.0.113.7 port 22 ssh2 (x500)', url: 'https://siem.empresa.es/alertas', titulo: 'SIEM', momento: Date.now() } })""")
    pagina.wait_for_timeout(1200)
    valor = pagina.locator("#entrada").input_value()
    print("seleccion recibida en el chat:", "203.0.113.7" in valor)
    pagina.screenshot(path=SALIDA / "10-seleccion.png")

    contexto.close()

print("\nERRORES DE CONSOLA:" if errores else "\nSin errores de consola")
for e in errores:
    print(" ", e)
