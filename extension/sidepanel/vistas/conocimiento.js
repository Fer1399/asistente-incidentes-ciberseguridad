// Vista Conocimiento: subir PDFs y documentos, ver el progreso del indexado y probar búsquedas.

import { pedir, subirFichero } from "../api.js";
import { aviso, boton, confirmar, h, icono, vaciar } from "../dom.js";

const ACEPTADOS = ".pdf,.md,.txt";

export async function vistaConocimiento(contenedor) {
  const cifras = h("div", { class: "cifras" });
  const avisoReindexar = h("div", {});
  const lista = h("div", { class: "tarjeta", style: { padding: 0 } });
  const selector = h("input", { type: "file", class: "oculto", accept: ACEPTADOS, multiple: true });
  const zona = h("div", { class: "zona-subida" },
    icono("subir", 28),
    h("b", {}, "Arrastra aquí tus PDFs"),
    h("span", { class: "ayuda" }, "Guías, playbooks, normativa, procedimientos internos (.pdf, .md, .txt). Los PDF escaneados se leen con OCR."),
    boton("Elegir ficheros", () => selector.click(), { clase: "boton boton-secundario" }),
    selector);
  const consulta = h("input", { class: "entrada", placeholder: "p. ej. notificación brecha 72 horas", style: { flex: "1" } });
  const resultados = h("div", {});
  let temporizador = null;

  const subir = async (ficheros) => {
    for (const fichero of ficheros) {
      try {
        await subirFichero("/documentos", fichero);
        aviso(`${fichero.name}: en cola para indexar`, "ok");
      } catch (error) {
        aviso(`${fichero.name}: ${error.message}`, "error");
      }
    }
    await cargar();
  };

  async function cargar() {
    let documentos;
    try {
      const [docs, salud] = await Promise.all([pedir("/documentos"), pedir("/health")]);
      documentos = docs;
      const c = salud.conocimiento;
      vaciar(cifras,
        h("div", { class: "cifra" }, h("b", {}, c.documentos), h("span", {}, "Documentos")),
        h("div", { class: "cifra" }, h("b", {}, c.fragmentos.toLocaleString("es-ES")), h("span", {}, "Fragmentos")),
        h("div", { class: "cifra" }, h("b", {}, c.incidentes_en_memoria), h("span", {}, "Incidentes")));
      vaciar(avisoReindexar, c.reindexar_necesario ? h("div", { class: "banner banner-aviso" }, icono("alerta", 18),
        h("div", {}, h("b", {}, "Hay que reindexar"), `La base se creó con ${c.modelo_indexado} y ahora se usa otro modelo de embeddings. `,
          boton("Reindexar todo", async () => { await pedir("/documentos/reindexar-todo", { metodo: "POST" }); cargar(); }, { clase: "enlace" })))
        : null);
    } catch (error) {
      vaciar(lista, h("div", { class: "banner banner-error", style: { margin: "12px" } }, icono("alerta", 18), error.message));
      return;
    }
    vaciar(lista, documentos.length ? documentos.map(filaDocumento)
      : h("div", { class: "vacio" }, "Todavía no hay documentos. Los playbooks incluidos aparecen al arrancar el backend."));

    clearTimeout(temporizador);
    if (documentos.some((d) => ["pendiente", "procesando"].includes(d.estado))) temporizador = setTimeout(cargar, 2000);
  }

  function filaDocumento(d) {
    const extension = d.nombre.split(".").pop().toUpperCase();
    let estado;
    if (d.estado === "indexado") {
      estado = h("span", { class: "ayuda" },
        `${d.origen === "incluido" ? "Incluido · " : ""}Indexado · ${d.fragmentos} fragmentos${d.paginas ? ` · ${d.paginas} páginas` : ""}${d.paginas_ocr ? ` · ${d.paginas_ocr} con OCR` : ""}`);
    } else if (d.estado === "error") {
      estado = h("span", { class: "ayuda", style: { color: "var(--peligro)" } }, `Error: ${d.mensaje}`);
    } else {
      estado = [h("div", { class: "barra" }, h("div", { style: { width: `${d.progreso}%` } })),
        h("span", { class: "ayuda" }, `${d.mensaje || "En cola"} · ${d.progreso} %`)];
    }
    const acciones = [];
    if (d.estado === "error" || d.estado === "indexado") {
      acciones.push(boton("", async () => { await pedir(`/documentos/${d.id}/reindexar`, { metodo: "POST" }); cargar(); },
        { clase: "boton-icono", icon: "recargar", titulo: "Volver a indexar" }));
    }
    if (d.origen === "usuario" && d.estado !== "procesando") {
      acciones.push(boton("", async () => {
        if (!(await confirmar("Borrar documento", `Se quitará «${d.nombre}» de la base de conocimiento.`, "Borrar", true))) return;
        try { await pedir(`/documentos/${d.id}`, { metodo: "DELETE" }); aviso("Documento borrado", "ok"); } catch (e) { aviso(e.message, "error"); }
        cargar();
      }, { clase: "boton-icono", icon: "basura", titulo: "Borrar documento" }));
    }
    return h("div", { class: "documento" },
      h("div", { class: `doc-tipo ${extension === "PDF" ? "" : "md"}` }, extension.slice(0, 4)),
      h("div", { class: "doc-info" }, h("span", { class: "doc-nombre", title: d.nombre }, d.nombre), estado),
      acciones);
  }

  async function buscar() {
    if (consulta.value.trim().length < 2) return;
    vaciar(resultados, h("div", { class: "fila tenue", style: { padding: "8px 0" } }, h("span", { class: "cargando" }), "Buscando…"));
    try {
      const r = await pedir("/buscar", { metodo: "POST", json: { consulta: consulta.value.trim() } });
      vaciar(resultados, r.resultados.length ? r.resultados.map((x) => h("div", { class: "resultado" },
        h("div", { class: "fila-entre" },
          h("b", {}, `${x.documento}${x.pagina ? ` · p. ${x.pagina}` : ""}`),
          h("span", { class: `chip ${x.similitud >= 0.5 ? "sev-baja" : ""}` }, `similitud ${x.similitud.toFixed(2)}`)),
        x.seccion ? h("span", { class: "tenue" }, x.seccion) : null,
        h("span", {}, x.texto.slice(0, 300).replace(/^\[[^\]]+\]\n/, ""), x.texto.length > 300 ? "…" : "")))
        : h("p", { class: "ayuda" }, "Sin resultados."));
    } catch (error) {
      vaciar(resultados, h("p", { class: "ayuda", style: { color: "var(--peligro)" } }, error.message));
    }
  }

  selector.addEventListener("change", () => { subir([...selector.files]); selector.value = ""; });
  for (const evento of ["dragenter", "dragover"]) zona.addEventListener(evento, (e) => { e.preventDefault(); zona.classList.add("activa"); });
  zona.addEventListener("dragleave", () => zona.classList.remove("activa"));
  zona.addEventListener("drop", (e) => { e.preventDefault(); zona.classList.remove("activa"); subir([...e.dataTransfer.files]); });
  consulta.addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });

  vaciar(contenedor, h("div", { class: "desplazable" },
    zona, cifras, avisoReindexar,
    h("span", { class: "seccion-titulo" }, "Documentos"), lista,
    h("div", { class: "tarjeta", style: { display: "flex", flexDirection: "column", gap: "8px" } },
      h("p", { class: "tarjeta-titulo", style: { margin: 0 } }, "Probar una búsqueda"),
      h("span", { class: "ayuda" }, "Comprueba qué fragmentos recupera el asistente antes de preguntar."),
      h("div", { class: "fila", style: { flexWrap: "nowrap" } }, consulta, boton("", buscar, { clase: "boton-icono", icon: "buscar", titulo: "Buscar" })),
      resultados)));

  await cargar();
  return () => clearTimeout(temporizador);
}
