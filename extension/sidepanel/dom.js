// Utilidades de interfaz.
//
// Toda la interfaz se construye con h(), que crea nodos del DOM y pone el texto con
// textContent. Nunca se usa innerHTML con datos: las respuestas del modelo, los correos
// y los logs pueden contener HTML malicioso y aquí nunca se interpreta.

export function h(etiqueta, atributos = {}, ...hijos) {
  const el = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(atributos || {})) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (clave === "class") el.className = valor;
    else if (clave === "style" && typeof valor === "object") Object.assign(el.style, valor);
    else if (clave.startsWith("on") && typeof valor === "function") el.addEventListener(clave.slice(2), valor);
    else if (clave === "dataset") Object.assign(el.dataset, valor);
    else if (valor === true) el.setAttribute(clave, "");
    else el.setAttribute(clave, valor);
  }
  anadir(el, hijos);
  return el;
}

function anadir(el, hijos) {
  for (const hijo of hijos.flat(Infinity)) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    el.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
}

export function vaciar(el, ...hijos) {
  el.replaceChildren();
  anadir(el, hijos);
  return el;
}

// Iconos SVG de trazo (sin dependencias externas)
const TRAZOS = {
  escudo: ["M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6l8-3z", "M9 12l2 2 4-4"],
  clip: ["M21 11.5l-8.5 8.5a5 5 0 0 1-7-7l9-9a3.5 3.5 0 0 1 5 5l-9 9a2 2 0 0 1-3-3l8-8"],
  imagen: ["M3 5h18v14H3z", "M21 16l-5-5-8 8", "M9 10a2 2 0 1 0 0-.01"],
  enviar: ["M5 12h14", "M13 6l6 6-6 6"],
  parar: ["M7 7h10v10H7z"],
  copiar: ["M9 9h12v12H9z", "M5 15V5a2 2 0 0 1 2-2h10"],
  descargar: ["M12 3v12", "M7 10l5 5 5-5", "M5 21h14"],
  historial: ["M3 12a9 9 0 1 0 3-6.7", "M3 4v5h5", "M12 7v5l3 2"],
  reloj: ["M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "M12 9v4l2 2", "M9 2h6"],
  buscar: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M20 20l-3.5-3.5"],
  subir: ["M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z", "M14 3v5h5", "M12 18v-6", "M9 15l3-3 3 3"],
  cerrar: ["M6 6l12 12", "M18 6L6 18"],
  mas: ["M12 5v14", "M5 12h14"],
  atras: ["M15 18l-6-6 6-6"],
  alerta: ["M12 3l10 18H2z", "M12 10v4", "M12 17v.01"],
  nueva: ["M12 5v14", "M5 12h14"],
  basura: ["M4 7h16", "M10 11v6", "M14 11v6", "M6 7l1 13h10l1-13", "M9 7V4h6v3"],
  recargar: ["M20 11a8 8 0 1 0-2.3 5.7", "M20 4v7h-7"],
  chat: ["M4 5h16v11H8l-4 4z"],
};

export function icono(nombre, tamano = 16) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", tamano);
  svg.setAttribute("height", tamano);
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("icono");
  for (const d of TRAZOS[nombre] || []) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

export function boton(texto, onclick, { clase = "boton", icon, titulo, deshabilitado, tipo = "button" } = {}) {
  return h(
    "button",
    { class: clase, type: tipo, onclick, title: titulo, "aria-label": texto ? undefined : titulo, disabled: deshabilitado },
    icon ? icono(icon) : null,
    texto ? h("span", {}, texto) : null,
  );
}

// --- Formato ---------------------------------------------------------------

export function fechaLocal(iso, conHora = true) {
  if (!iso) return "-";
  const fecha = new Date(iso);
  if (Number.isNaN(fecha.getTime())) return iso;
  const opciones = { day: "2-digit", month: "2-digit", year: "numeric" };
  if (conHora) Object.assign(opciones, { hour: "2-digit", minute: "2-digit" });
  return fecha.toLocaleString("es-ES", opciones);
}

export function fechaRelativa(iso) {
  if (!iso) return "-";
  const fecha = new Date(iso);
  const hoy = new Date();
  const mismoDia = fecha.toDateString() === hoy.toDateString();
  if (mismoDia) return `Hoy, ${fecha.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`;
  return fecha.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

export function tamanoLegible(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function chipSeveridad(severidad) {
  if (!severidad) return null;
  const clase = { Baja: "baja", Media: "media", Alta: "alta", "Crítica": "critica" }[severidad] || "neutra";
  return h("span", { class: `chip sev-${clase}` }, severidad);
}

// --- Avisos flotantes ----------------------------------------------------

export function aviso(texto, tipo = "info") {
  const contenedor = document.getElementById("avisos");
  const el = h("div", { class: `aviso aviso-${tipo}`, role: tipo === "error" ? "alert" : "status" }, texto);
  contenedor.append(el);
  setTimeout(() => el.classList.add("saliendo"), 3800);
  setTimeout(() => el.remove(), 4300);
}

export async function copiar(texto, mensaje = "Copiado") {
  try {
    await navigator.clipboard.writeText(texto);
    aviso(mensaje, "ok");
  } catch {
    aviso("No se pudo copiar al portapapeles", "error");
  }
}

export function descargarBlob(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const enlace = h("a", { href: url, download: nombre });
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// --- Diálogo modal -----------------------------------------------------------

export function dialogo({ titulo, cuerpo, acciones }) {
  const fondo = h("div", { class: "modal-fondo" });
  const caja = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": titulo },
    h("h2", { class: "modal-titulo" }, titulo), cuerpo, h("div", { class: "modal-acciones" }, acciones));
  fondo.append(caja);
  const cerrar = () => fondo.remove();
  fondo.addEventListener("click", (e) => { if (e.target === fondo) cerrar(); });
  fondo.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });
  document.body.append(fondo);
  const primero = caja.querySelector("textarea, input, select, button");
  if (primero) primero.focus();
  return cerrar;
}

export function confirmar(titulo, texto, textoBoton = "Confirmar", peligro = false) {
  return new Promise((resolver) => {
    let cerrar;
    const resolverYCerrar = (valor) => { cerrar(); resolver(valor); };
    cerrar = dialogo({
      titulo,
      cuerpo: h("p", { class: "modal-texto" }, texto),
      acciones: [
        boton("Cancelar", () => resolverYCerrar(false), { clase: "boton boton-secundario" }),
        boton(textoBoton, () => resolverYCerrar(true), { clase: peligro ? "boton boton-peligro" : "boton" }),
      ],
    });
  });
}
