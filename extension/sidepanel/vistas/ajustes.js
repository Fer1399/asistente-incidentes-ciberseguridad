// Vista Ajustes: estado del sistema, modelos, copia de seguridad y conexión.

import { guardarUrl, pedir, subirFichero, urlBase } from "../api.js";
import { comprobarSalud, ir, salud } from "../app.js";
import { aviso, boton, descargarBlob, h, icono, vaciar } from "../dom.js";

export async function vistaAjustes(contenedor) {
  const estadoCaja = h("div", {});
  const modelosCaja = h("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } });
  const resultadoCopia = h("div", {});

  const fila = (etiqueta, valor, ok) => h("div", { class: "estado-fila" },
    h("span", {}, etiqueta), h("span", { class: ok === undefined ? "tenue" : ok ? "bien" : "mal" }, valor));

  const pintarEstado = (datos) => {
    if (!datos) {
      vaciar(estadoCaja,
        fila("Backend", "Sin conexión", false),
        h("p", { class: "ayuda" }, "Arranca el backend con scripts\\iniciar.bat y deja la ventana abierta."));
      return;
    }
    const m = datos.modelos;
    vaciar(estadoCaja,
      fila(h("span", {}, "Backend ", h("span", { class: "mono tenue" }, urlBase().replace("http://", ""))), `v${datos.version}`, true),
      fila(h("span", {}, "Ollama ", h("span", { class: "mono tenue" }, datos.ollama.url.replace("http://", ""))),
        datos.ollama.ok ? `En marcha · ${datos.ollama.version}` : "No responde", datos.ollama.ok),
      fila(`Chat: ${m.chat.nombre}`, m.chat.instalado ? "Instalado" : "Falta", m.chat.instalado),
      fila(`Visión: ${m.vision.nombre}`, m.vision.instalado ? "Instalado" : "Falta (solo OCR)", m.vision.instalado),
      fila(`Embeddings: ${m.embeddings.nombre}`, m.embeddings.instalado ? "Instalado" : "Falta", m.embeddings.instalado),
      fila("OCR (Tesseract)", datos.ocr.tesseract ? "Disponible" : "No instalado", datos.ocr.tesseract),
      fila("Conexiones fuera de este equipo", "Bloqueadas", true));
  };

  const pintarModelos = async () => {
    const { modelo, vision } = await chrome.storage.local.get(["modelo", "vision"]);
    let disponibles = [];
    let porDefecto = salud.datos?.modelos.chat.nombre;
    try {
      const r = await pedir("/modelos");
      disponibles = r.chat;
      porDefecto = r.por_defecto.chat;
    } catch { /* sin backend */ }
    const selector = h("select", { "aria-label": "Modelo de chat" },
      h("option", { value: "" }, `Por defecto del equipo (${porDefecto || "-"})`),
      disponibles.map((nombre) => h("option", { value: nombre, selected: nombre === modelo }, nombre)));
    selector.addEventListener("change", async () => {
      if (selector.value) await chrome.storage.local.set({ modelo: selector.value });
      else await chrome.storage.local.remove("modelo");
      aviso("Modelo guardado", "ok");
      comprobarSalud();
    });
    const casillaVision = h("input", { type: "checkbox", checked: vision !== false });
    casillaVision.addEventListener("change", async () => {
      await chrome.storage.local.set({ vision: casillaVision.checked });
      aviso(casillaVision.checked ? "Capturas: visión + OCR" : "Capturas: solo OCR", "ok");
    });
    vaciar(modelosCaja,
      h("label", { class: "campo" }, "Modelo de chat", selector),
      h("span", { class: "ayuda" }, "Sin GPU dedicada, un modelo de 7B; con una GPU de 12 GB o más, uno de 14B. El de embeddings no se cambia desde aquí: al cambiarlo hay que reindexar."),
      h("label", { class: "interruptor" },
        h("span", {}, "Usar el modelo de visión con las capturas", h("br"),
          h("span", { class: "ayuda" }, "Desactívalo en equipos sin GPU: solo OCR es mucho más rápido")), casillaVision));
  };

  const exportar = async (e) => {
    const b = e.currentTarget;
    b.disabled = true;
    try {
      const blob = await pedir("/copia", { binario: true });
      const d = new Date();
      const dos = (n) => String(n).padStart(2, "0");
      const fecha = `${d.getFullYear()}${dos(d.getMonth() + 1)}${dos(d.getDate())}-${dos(d.getHours())}${dos(d.getMinutes())}`;
      descargarBlob(blob, `asistente-copia-${fecha}.zip`);
      aviso("Copia descargada. Guárdala en un lugar seguro.", "ok");
    } catch (error) {
      aviso(error.message, "error");
    } finally {
      b.disabled = false;
    }
  };

  const selectorCopia = h("input", { type: "file", accept: ".zip", class: "oculto" });
  selectorCopia.addEventListener("change", async () => {
    const fichero = selectorCopia.files[0];
    selectorCopia.value = "";
    if (!fichero) return;
    vaciar(resultadoCopia, h("div", { class: "fila tenue" }, h("span", { class: "cargando" }), "Importando…"));
    try {
      const r = await subirFichero("/copia", fichero);
      const s = r.resumen;
      vaciar(resultadoCopia, h("div", { class: "banner banner-info" }, icono("escudo", 18),
        h("div", {}, h("b", {}, `Copia de ${r.manifiesto.equipo} importada`),
          `${s.incidentes_nuevos} incidentes nuevos, ${s.incidentes_actualizados} actualizados, ${s.incidentes_sin_cambios} sin cambios, `,
          `${s.documentos_nuevos} documentos y ${s.adjuntos_nuevos} adjuntos. `,
          r.avisos.join(" "), h("br"), h("span", { class: "ayuda" }, `Copia previa guardada en data\\copias\\${r.copia_previa}`))));
      comprobarSalud();
    } catch (error) {
      vaciar(resultadoCopia, h("div", { class: "banner banner-error" }, icono("alerta", 18), error.message));
    }
  });

  const urlEntrada = h("input", { class: "entrada", value: urlBase(), "aria-label": "Dirección del backend" });
  const guardarDireccion = async () => {
    try {
      await guardarUrl(urlEntrada.value.trim());
      aviso("Dirección guardada", "ok");
      await comprobarSalud();
      ir("ajustes");
    } catch (error) {
      aviso(error.message, "error");
    }
  };

  vaciar(contenedor, h("div", { class: "desplazable" },
    h("div", { class: "tarjeta" }, h("div", { class: "fila-entre" }, h("p", { class: "tarjeta-titulo" }, "Estado"),
      boton("", async () => { await comprobarSalud(); }, { clase: "boton-icono", icon: "recargar", titulo: "Comprobar ahora" })), estadoCaja),
    h("div", { class: "tarjeta" }, h("p", { class: "tarjeta-titulo" }, "Modelos"), modelosCaja),
    h("div", { class: "tarjeta", style: { display: "flex", flexDirection: "column", gap: "10px" } },
      h("p", { class: "tarjeta-titulo", style: { margin: 0 } }, "Copia de seguridad"),
      h("span", { class: "ayuda" }, "Un único .zip con incidentes, documentos subidos y adjuntos analizados, para guardarlo o llevarlo a otro equipo. Importar fusiona: no borra nada de lo que ya hay."),
      h("div", { class: "fila", style: { flexWrap: "nowrap" } },
        boton("Exportar", exportar, { icon: "descargar" }),
        boton("Importar", () => selectorCopia.click(), { clase: "boton boton-secundario", icon: "subir" }), selectorCopia),
      resultadoCopia),
    h("details", { class: "tarjeta" }, h("summary", {}, "Conexión"),
      h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } },
        h("label", { class: "campo" }, "Dirección del backend (solo 127.0.0.1 o localhost)", urlEntrada),
        boton("Guardar dirección", guardarDireccion, { clase: "boton boton-secundario" }))),
    h("p", { class: "ayuda", style: { textAlign: "center" } },
      `Asistente de Incidentes · extensión v${chrome.runtime.getManifest().version} · licencia MIT · todo se procesa en este equipo`)));

  pintarEstado(salud.datos);
  salud.oyentes.add(pintarEstado);
  await pintarModelos();
  return () => salud.oyentes.delete(pintarEstado);
}
