// Vista Chat: conversación con el asistente, adjuntos (correos, logs, capturas) y fichas.

import { ErrorApi, chatStream, pedir, subirFichero } from "../api.js";
import { ir } from "../app.js";
import { aviso, boton, chipSeveridad, copiar, descargarBlob, dialogo, h, icono, vaciar } from "../dom.js";
import { renderMarkdown } from "../markdown.js";

const ACEPTADOS = ".eml,.txt,.log,.csv,.json,.xml,.md,.html,.htm,.ini,.conf,.yaml,.yml,.pdf,.png,.jpg,.jpeg,.webp,.bmp,.gif";
const NOMBRES_IOC = { ip: "IPs", dominio: "Dominios", url: "URLs", email: "Correos", hash: "Hashes", cve: "CVE" };
const SUGERENCIAS = [
  "Un usuario ha introducido su contraseña en un correo de phishing, ¿cómo procedo?",
  "Varios ficheros del servidor tienen una extensión rara y hay una nota de rescate. ¿Qué hago primero?",
  "Veo cientos de eventos 4625 desde la misma IP en el controlador de dominio. ¿Es fuerza bruta?",
];

let estado = null; // { mensajes, incidenteId, incidenteTitulo }
let ui = null; // referencias a la vista montada
let enCurso = null; // AbortController de la respuesta en curso
const pendientes = []; // adjuntos que se enviarán con la siguiente pregunta

async function cargar() {
  const { conversacion } = await chrome.storage.local.get("conversacion");
  estado = conversacion || { mensajes: [], incidenteId: null, incidenteTitulo: null };
}

async function guardar() {
  await chrome.storage.local.set({ conversacion: estado });
}

export async function abrirConversacion(conversacion) {
  estado = conversacion;
  pendientes.length = 0;
  await guardar();
  await ir("chat");
}

export function recibirSeleccion({ texto, url, titulo }) {
  if (!ui) return;
  let origen = "una página web";
  try { origen = new URL(url).hostname || origen; } catch { /* sin url */ }
  ui.entrada.value = `Analiza este contenido seleccionado en ${origen}${titulo ? ` («${titulo}»)` : ""} y dime cómo proceder:\n\n"""\n${texto}\n"""`;
  autoajustar();
  ui.entrada.focus();
  ui.entrada.setSelectionRange(0, 0);
  aviso("Texto seleccionado añadido. Revísalo y pulsa enviar.", "info");
}

// --- Vista ---------------------------------------------------------------

export async function vistaChat(contenedor) {
  await cargar();
  const lista = h("div", { class: "desplazable", id: "mensajes" });
  const entrada = h("textarea", {
    id: "entrada", rows: "2", placeholder: "Describe el incidente, pega logs o una captura…",
    "aria-label": "Mensaje para el asistente",
  });
  const selectorFichero = h("input", { type: "file", class: "oculto", accept: ACEPTADOS, multiple: true });
  const selectorImagen = h("input", { type: "file", class: "oculto", accept: "image/*" });
  const enviar = h("button", { class: "boton-icono enviar", type: "button", title: "Enviar (Intro)", "aria-label": "Enviar" }, icono("enviar"));
  const zonaPendientes = h("div", { class: "pendientes" });

  ui = { lista, entrada, enviar, zonaPendientes };

  const composer = h("div", { class: "composer" },
    zonaPendientes,
    h("div", { class: "composer-caja" },
      h("button", { class: "boton-icono", type: "button", title: "Adjuntar correo .eml, log o PDF", "aria-label": "Adjuntar fichero",
        onclick: () => selectorFichero.click() }, icono("clip")),
      h("button", { class: "boton-icono", type: "button", title: "Adjuntar captura de pantalla", "aria-label": "Adjuntar captura",
        onclick: () => selectorImagen.click() }, icono("imagen")),
      entrada, enviar, selectorFichero, selectorImagen),
    h("span", { class: "ayuda" }, "Intro para enviar · Mayús+Intro para nueva línea · pega capturas con Ctrl+V o arrastra ficheros"),
  );

  vaciar(contenedor, barraSuperior(), lista, composer);

  entrada.addEventListener("input", autoajustar);
  entrada.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviarPregunta(); }
  });
  entrada.addEventListener("paste", (e) => {
    const imagenes = [...(e.clipboardData?.files || [])].filter((f) => f.type.startsWith("image/"));
    if (imagenes.length) {
      e.preventDefault();
      imagenes.forEach((f, i) => adjuntar(f, `captura-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}${i ? `-${i}` : ""}.png`));
    }
  });
  enviar.addEventListener("click", () => (enCurso ? enCurso.abort() : enviarPregunta()));
  selectorFichero.addEventListener("change", () => { [...selectorFichero.files].forEach((f) => adjuntar(f)); selectorFichero.value = ""; });
  selectorImagen.addEventListener("change", () => { [...selectorImagen.files].forEach((f) => adjuntar(f)); selectorImagen.value = ""; });

  const alArrastrar = (e) => { e.preventDefault(); document.body.classList.add("arrastrando"); };
  const alSalir = (e) => { if (!e.relatedTarget) document.body.classList.remove("arrastrando"); };
  const alSoltar = (e) => {
    e.preventDefault();
    document.body.classList.remove("arrastrando");
    [...(e.dataTransfer?.files || [])].forEach((f) => adjuntar(f));
  };
  document.addEventListener("dragover", alArrastrar);
  document.addEventListener("dragleave", alSalir);
  document.addEventListener("drop", alSoltar);

  pintarTodo();
  pintarPendientes();
  actualizarBoton();

  return () => {
    document.removeEventListener("dragover", alArrastrar);
    document.removeEventListener("dragleave", alSalir);
    document.removeEventListener("drop", alSoltar);
    ui = null;
  };
}

function barraSuperior() {
  const izquierda = estado.incidenteId
    ? h("div", { class: "fila", style: { fontSize: "12.5px", minWidth: 0 } },
        h("span", { class: "tenue" }, "Guardando en"),
        h("button", { class: "enlace", type: "button", onclick: () => ir("ficha", { id: estado.incidenteId }) },
          estado.incidenteId))
    : h("span", { class: "tenue", style: { fontSize: "12.5px" } }, "Conversación sin ficha");
  return h("div", { class: "fila-entre", style: { padding: "8px 16px", background: "var(--superficie)", borderBottom: "1px solid var(--borde)" } },
    izquierda,
    boton("Nueva", nuevaConversacion, { clase: "boton boton-secundario", icon: "nueva", titulo: "Empezar una conversación nueva" }));
}

async function nuevaConversacion() {
  if (enCurso) enCurso.abort();
  estado = { mensajes: [], incidenteId: null, incidenteTitulo: null };
  pendientes.length = 0;
  await guardar();
  await ir("chat");
}

function autoajustar() {
  if (!ui) return;
  ui.entrada.style.height = "auto";
  ui.entrada.style.height = `${Math.min(ui.entrada.scrollHeight, 180)}px`;
}

function actualizarBoton() {
  if (!ui) return;
  const subiendo = pendientes.some((p) => p.estado === "subiendo");
  vaciar(ui.enviar, icono(enCurso ? "parar" : "enviar"));
  ui.enviar.title = enCurso ? "Detener la respuesta" : subiendo ? "Esperando a que termine el análisis del adjunto" : "Enviar (Intro)";
  ui.enviar.setAttribute("aria-label", enCurso ? "Detener" : "Enviar");
  ui.enviar.disabled = !enCurso && subiendo;
}

// --- Adjuntos ------------------------------------------------------------

async function adjuntar(fichero, nombre) {
  const pendiente = { nombre: nombre || fichero.name, estado: "subiendo" };
  pendientes.push(pendiente);
  pintarPendientes();
  actualizarBoton();
  try {
    const { vision } = await chrome.storage.local.get("vision");
    const ruta = vision === false ? "/adjuntos?vision=false" : "/adjuntos";
    const analisis = await subirFichero(ruta, fichero, pendiente.nombre);
    Object.assign(pendiente, { estado: "listo", analisis });
  } catch (error) {
    Object.assign(pendiente, { estado: "error", error: error.message });
  }
  pintarPendientes();
  actualizarBoton();
}

function pintarPendientes() {
  if (!ui) return;
  vaciar(ui.zonaPendientes, pendientes.map((p, i) => {
    const detalle = p.estado === "subiendo" ? [h("span", { class: "cargando" }), " analizando…"]
      : p.estado === "error" ? ` · ${p.error}`
        : ` · ${p.analisis.alertas.length} alertas · ${p.analisis.total_iocs} IOCs`;
    return h("span", { class: `pendiente ${p.estado === "error" ? "error" : ""}`, title: p.estado === "error" ? p.error : p.nombre },
      h("span", { style: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, p.nombre, detalle),
      h("button", { type: "button", "aria-label": `Quitar ${p.nombre}`, onclick: () => { pendientes.splice(i, 1); pintarPendientes(); actualizarBoton(); } },
        icono("cerrar", 14)));
  }));
}

// --- Enviar y recibir ---------------------------------------------------------

async function enviarPregunta() {
  const texto = ui.entrada.value.trim();
  const listos = pendientes.filter((p) => p.estado === "listo");
  if (!texto && !listos.length) return;
  if (pendientes.some((p) => p.estado === "subiendo")) return;

  const pregunta = {
    rol: "usuario",
    contenido: texto || "Analiza este adjunto y dime cómo proceder.",
    adjuntos: listos.map((p) => p.analisis),
  };
  const respuesta = { rol: "asistente", contenido: "", generando: true };
  estado.mensajes.push(pregunta, respuesta);
  pendientes.length = 0;
  ui.entrada.value = "";
  autoajustar();
  pintarPendientes();
  pintarTodo();

  const { modelo } = await chrome.storage.local.get("modelo");
  const cuerpo = {
    mensajes: estado.mensajes.slice(0, -1).map((m) => ({
      rol: m.rol, contenido: m.contenido, adjuntos: (m.adjuntos || []).map((a) => a.id),
    })).filter((m) => m.contenido),
    modelo: modelo || undefined,
    incidente_id: estado.incidenteId || undefined,
  };

  enCurso = new AbortController();
  actualizarBoton();
  let nodo = ultimoNodoRespuesta();
  let ultimoPintado = 0;
  try {
    await chatStream(cuerpo, (evento) => {
      if (evento.tipo === "fuentes") {
        Object.assign(respuesta, { fuentes: evento.fuentes, similares: evento.similares, iocs: evento.iocs, modelo: evento.modelo });
      } else if (evento.tipo === "texto") {
        respuesta.contenido += evento.texto;
      } else if (evento.tipo === "fin") {
        respuesta.segundos = evento.segundos;
        respuesta.mitre = evento.mitre;
      } else if (evento.tipo === "error") {
        respuesta.error = evento.mensaje;
      }
      // Repintar como mucho cada 80 ms: el Markdown completo se rehace en cada pintado
      const ahora = performance.now();
      if (evento.tipo !== "texto" || ahora - ultimoPintado > 80) {
        nodo = repintarRespuesta(nodo, respuesta);
        ultimoPintado = ahora;
      }
    }, enCurso.signal);
  } catch (error) {
    if (error.name === "AbortError") respuesta.detenida = true;
    else respuesta.error = error instanceof ErrorApi ? error.message : `Error inesperado: ${error.message}`;
  } finally {
    respuesta.generando = false;
    enCurso = null;
    if (!respuesta.contenido && !respuesta.error && !respuesta.detenida) respuesta.error = "No se recibió ninguna respuesta.";
    repintarRespuesta(nodo, respuesta);
    actualizarBoton();
    await guardar();
  }
}

// --- Pintado ---------------------------------------------------------------

function pintarTodo() {
  if (!ui) return;
  if (!estado.mensajes.length) {
    vaciar(ui.lista, bienvenida());
    return;
  }
  vaciar(ui.lista, estado.mensajes.map((m, i) => (m.rol === "usuario" ? nodoPregunta(m) : nodoRespuesta(m, i))));
  ui.lista.scrollTop = ui.lista.scrollHeight;
}

function ultimoNodoRespuesta() {
  return ui?.lista.lastElementChild;
}

function repintarRespuesta(nodoAnterior, mensaje) {
  if (!ui) return nodoAnterior;
  const indice = estado.mensajes.indexOf(mensaje);
  const nuevo = nodoRespuesta(mensaje, indice);
  const actual = nodoAnterior && nodoAnterior.isConnected ? nodoAnterior : ultimoNodoRespuesta();
  if (actual) actual.replaceWith(nuevo); else ui.lista.append(nuevo);
  const cercaDelFinal = ui.lista.scrollHeight - ui.lista.scrollTop - ui.lista.clientHeight < 160;
  if (cercaDelFinal || mensaje.generando) ui.lista.scrollTop = ui.lista.scrollHeight;
  return nuevo;
}

function bienvenida() {
  return h("div", { class: "tarjeta", style: { display: "flex", flexDirection: "column", gap: "10px" } },
    h("p", { class: "tarjeta-titulo", style: { margin: 0 } }, "¿Qué ha pasado?"),
    h("p", { class: "modal-texto" },
      "Describe el incidente o adjunta lo que tengas: un correo .eml, un log, un PDF o una captura de pantalla. ",
      "El asistente te dirá cómo proceder, paso a paso, usando tus playbooks y los incidentes anteriores. Todo se procesa en este equipo."),
    h("span", { class: "seccion-titulo" }, "Ejemplos"),
    SUGERENCIAS.map((s) => h("button", { class: "fuente", type: "button", style: { whiteSpace: "normal", textAlign: "left", padding: "8px 10px", borderRadius: "8px" },
      onclick: () => { ui.entrada.value = s; autoajustar(); ui.entrada.focus(); } }, s)),
  );
}

function nodoPregunta(mensaje) {
  const adjuntos = mensaje.adjuntos || [];
  const burbuja = h("div", { class: "mensaje-usuario" },
    adjuntos.map((a) => h("div", { class: "adjunto-chip" }, icono(a.tipo === "imagen" ? "imagen" : "clip", 14),
      `${a.nombre} · ${a.alertas?.length || 0} alertas · ${a.total_iocs} IOCs`)),
    h("span", { class: "texto" }, mensaje.contenido));
  const conAlertas = adjuntos.filter((a) => a.alertas?.length || a.avisos?.length);
  if (!conAlertas.length) return burbuja;
  return h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } },
    burbuja,
    conAlertas.map((a) => h("details", { class: "tarjeta", open: true },
      h("summary", {}, h("span", { class: "fila" }, icono("alerta"), `Análisis automático de ${a.nombre}`)),
      a.alertas?.length ? h("ul", { class: "alertas" }, a.alertas.map((x) => h("li", {}, x))) : null,
      a.avisos?.length ? h("p", { class: "ayuda" }, a.avisos.join(" ")) : null)));
}

function nodoRespuesta(mensaje, indice) {
  const tarjeta = h("div", { class: "tarjeta respuesta" });

  if (mensaje.similares?.length) {
    const s = mensaje.similares[0];
    tarjeta.append(h("div", { class: "banner banner-info" }, icono("historial", 18),
      h("div", { style: { display: "flex", flexDirection: "column", gap: "4px" } },
        h("b", {}, "Ya ha pasado algo parecido"),
        h("span", {}, `${s.id} · ${s.titulo}${s.severidad ? ` · ${s.severidad}` : ""}`),
        h("button", { class: "enlace", type: "button", onclick: () => ir("ficha", { id: s.id }) }, "Ver cómo se resolvió →"))));
  }

  const clasificacion = clasificar(mensaje.contenido);
  if (clasificacion.tipo || clasificacion.severidad) {
    tarjeta.append(h("div", { class: "fila" },
      clasificacion.tipo ? h("span", { class: "chip" }, clasificacion.tipo) : null,
      chipSeveridad(clasificacion.severidad),
      (mensaje.mitre ? mensaje.mitre.filter((t) => t.reconocida).map((t) => t.id) : clasificacion.mitre)
        .slice(0, 3).map((t) => h("span", { class: "chip chip-mono" }, t))));
  }

  const detalleFuente = h("div", { class: "fuente-detalle", hidden: true });
  const mostrarFuente = (n) => {
    const f = (mensaje.fuentes || []).find((x) => x.n === n);
    if (!f) return;
    detalleFuente.hidden = false;
    vaciar(detalleFuente, h("b", {}, `[${f.n}] ${f.documento}${f.pagina ? ` · p. ${f.pagina}` : ""}`), "\n", f.extracto, "…");
    tarjeta.querySelectorAll(".fuente").forEach((el) => el.classList.toggle("resaltada", el.dataset.n === String(n)));
  };

  if (mensaje.contenido) {
    const md = renderMarkdown(mensaje.contenido, { alCitar: mostrarFuente });
    if (mensaje.generando) md.lastElementChild?.classList.add("cursor");
    tarjeta.append(md);
  } else if (mensaje.generando) {
    tarjeta.append(h("div", { class: "fila tenue" }, h("span", { class: "cargando" }),
      mensaje.fuentes ? `Pensando con ${mensaje.modelo}… (en CPU puede tardar)` : "Buscando en la base de conocimiento…"));
  }

  const verificacion = nodoMitre(mensaje.mitre);
  if (verificacion) tarjeta.append(verificacion);

  if (mensaje.error) tarjeta.append(h("div", { class: "banner banner-error" }, icono("alerta", 18), h("span", {}, mensaje.error)));
  if (mensaje.detenida) tarjeta.append(h("span", { class: "ayuda" }, "Respuesta detenida."));

  const iocs = nodoIocs(mensaje.iocs);
  if (iocs) tarjeta.append(iocs);

  if (mensaje.fuentes?.length) {
    tarjeta.append(h("div", { class: "fuentes" }, h("span", { class: "tenue" }, "Fuentes:"),
      mensaje.fuentes.map((f) => h("button", {
        class: "fuente", type: "button", dataset: { n: String(f.n) }, title: f.seccion || f.documento,
        onclick: () => mostrarFuente(f.n),
      }, `[${f.n}] ${f.tipo === "incidente" ? "Incidente " : ""}${f.documento}${f.pagina ? ` · p. ${f.pagina}` : ""}`))),
    detalleFuente);
  }

  if (!mensaje.generando && mensaje.contenido) {
    tarjeta.append(h("div", { class: "respuesta-pie" },
      estado.incidenteId
        ? boton("Ver ficha", () => ir("ficha", { id: estado.incidenteId }), { clase: "boton boton-secundario", icon: "escudo" })
        : boton("Crear ficha de incidente", () => crearFicha(indice), { icon: "escudo" }),
      boton("", () => copiar(mensaje.contenido, "Respuesta copiada"), { clase: "boton-icono", icon: "copiar", titulo: "Copiar respuesta" }),
      boton("", () => descargarBlob(new Blob([mensaje.contenido], { type: "text/markdown" }), "respuesta-asistente.md"),
        { clase: "boton-icono", icon: "descargar", titulo: "Descargar como Markdown" }),
      mensaje.segundos ? h("span", { class: "ayuda", style: { marginLeft: "auto", alignSelf: "center" } },
        `${mensaje.modelo} · ${mensaje.segundos} s`) : null));
  }
  return tarjeta;
}

// Técnicas MITRE citadas, con su nombre oficial según la referencia local (backend/app/mitre.py)
function nodoMitre(tecnicas) {
  if (!tecnicas?.length) return null;
  const desconocidas = tecnicas.filter((t) => !t.reconocida).length;
  return h("details", { class: "iocs", open: desconocidas > 0 },
    h("summary", { class: "fila-entre", style: { fontSize: "12px" } },
      h("b", {}, `Técnicas MITRE ATT&CK citadas (${tecnicas.length})`),
      desconocidas ? h("span", { class: "chip sev-alta" }, `${desconocidas} sin verificar`) : h("span", { class: "chip sev-baja" }, "todas reconocidas")),
    h("span", { class: "ayuda" }, "Nombre oficial según la referencia local. Si no coincide con lo que dice la respuesta, manda el nombre oficial."),
    tecnicas.map((t) => h("div", { class: "mitre-fila" },
      h("span", { class: "chip chip-mono" }, t.id),
      t.reconocida
        ? h("span", {}, h("b", {}, t.nombre), ` · ${t.nombre_es}`, h("span", { class: "tenue" }, ` · ${t.tactica}`))
        : h("span", { class: "mitre-desconocida" },
          t.tecnica_padre ? `Subtécnica no recogida en la referencia local (técnica: ${t.tecnica_padre}). ` : "No está en la referencia local. ",
          "Verifícala en attack.mitre.org antes de usarla."))));
}

function nodoIocs(iocs) {
  if (!iocs) return null;
  const tipos = Object.entries(iocs).filter(([, lista]) => lista.length);
  if (!tipos.length) return null;
  const todos = tipos.flatMap(([, lista]) => lista.filter((e) => !e.legitimo && !e.interna).map((e) => e.seguro));
  const total = tipos.reduce((n, [, lista]) => n + lista.length, 0);
  // Con muchos indicadores, la lista empieza plegada para no tapar la respuesta
  return h("details", { class: "iocs", open: total <= 8 },
    h("summary", { class: "fila-entre", style: { fontSize: "12px" } }, h("b", {}, `Indicadores detectados (${total})`),
      todos.length ? h("button", { class: "enlace", type: "button", style: { fontSize: "12px" },
        onclick: (e) => { e.preventDefault(); copiar(todos.join("\n"), `${todos.length} indicadores copiados (desactivados)`); } },
      "Copiar todos") : null),
    tipos.map(([tipo, lista]) => h("div", { class: "iocs-fila" },
      h("span", { class: "tenue", style: { minWidth: "62px" } }, NOMBRES_IOC[tipo]),
      lista.slice(0, 25).map((e) => h("button", {
        type: "button",
        class: `ioc ${e.legitimo || e.interna ? "ioc-legitimo" : ""}`,
        title: e.interna ? "IP interna" : e.legitimo === "propio" ? "Dominio propio"
          : e.legitimo === "conocido" ? "Dominio legítimo conocido (posible marca suplantada)" : "Copiar (desactivado)",
        onclick: () => copiar(e.seguro),
      }, e.seguro)),
      lista.length > 25 ? h("span", { class: "tenue" }, `y ${lista.length - 25} más`) : null)));
}

function clasificar(texto) {
  const tipo = texto.match(/Tipo de incidente\W*([^·\n*|]+)/i)?.[1]?.trim().replace(/[:.]$/, "");
  let severidad = texto.match(/Severidad estimada\W*(Baja|Media|Alta|Cr[ií]tica)/i)?.[1];
  if (severidad) severidad = severidad.toLowerCase().startsWith("cr") ? "Crítica" : severidad[0].toUpperCase() + severidad.slice(1).toLowerCase();
  const mitre = [...new Set(texto.match(/\bT\d{4}(?:\.\d{3})?\b/g) || [])];
  return { tipo: tipo?.slice(0, 40), severidad, mitre };
}

// --- Crear ficha desde la respuesta -------------------------------------------

function crearFicha(indiceRespuesta) {
  const respuesta = estado.mensajes[indiceRespuesta];
  const { tipo } = clasificar(respuesta.contenido);
  const titulo = h("input", { class: "entrada", value: tipo || "", placeholder: "Título del incidente", maxlength: "150" });
  const datos = h("input", { type: "checkbox" });
  let cerrar;
  const crear = async (e) => {
    const botonCrear = e.currentTarget;
    botonCrear.disabled = true;
    try {
      const ficha = await pedir("/incidentes", {
        metodo: "POST",
        json: {
          titulo: titulo.value.trim() || undefined,
          datos_personales: datos.checked,
          respuesta_asistente: respuesta.contenido,
          mensajes: estado.mensajes.slice(0, indiceRespuesta + 1).filter((m) => m.contenido).map((m) => ({
            rol: m.rol, contenido: m.contenido, adjuntos: (m.adjuntos || []).map((a) => a.id),
          })),
        },
      });
      estado.incidenteId = ficha.id;
      estado.incidenteTitulo = ficha.titulo;
      await guardar();
      cerrar();
      aviso(`Ficha ${ficha.id} creada con ${ficha.progreso.total} pasos`, "ok");
      await ir("ficha", { id: ficha.id });
    } catch (error) {
      aviso(error.message, "error");
      botonCrear.disabled = false;
    }
  };
  cerrar = dialogo({
    titulo: "Crear ficha de incidente",
    cuerpo: h("div", { style: { display: "flex", flexDirection: "column", gap: "12px" } },
      h("p", { class: "modal-texto" }, "Los pasos de la respuesta se convertirán en una checklist. Las siguientes preguntas de esta conversación se guardarán en la ficha."),
      h("label", { class: "campo" }, "Título", titulo),
      h("label", { class: "interruptor" },
        h("span", {}, "Hay datos personales afectados", h("br"), h("span", { class: "ayuda" }, "Activa el plazo de 72 h para notificar a la AEPD")),
        datos)),
    acciones: [
      boton("Cancelar", () => cerrar(), { clase: "boton boton-secundario" }),
      boton("Crear ficha", crear, { icon: "escudo" }),
    ],
  });
}
