// Punto de entrada del panel lateral: navegación, estado del backend y menú contextual.

import { cargarConfiguracion, pedir } from "./api.js";
import { vaciar } from "./dom.js";
import { vistaAjustes } from "./vistas/ajustes.js";
import { recibirSeleccion, vistaChat } from "./vistas/chat.js";
import { vistaConocimiento } from "./vistas/conocimiento.js";
import { vistaFicha } from "./vistas/ficha.js";
import { vistaIncidentes } from "./vistas/incidentes.js";

const VISTAS = {
  chat: vistaChat,
  incidentes: vistaIncidentes,
  ficha: vistaFicha,
  conocimiento: vistaConocimiento,
  ajustes: vistaAjustes,
};
// La ficha se muestra bajo la pestaña "Incidentes"
const PESTANA_DE = { ficha: "incidentes" };

let limpiarVista = null;
export const salud = { datos: null, oyentes: new Set() };

export async function ir(vista, parametros = {}) {
  if (limpiarVista) limpiarVista();
  limpiarVista = null;
  const contenedor = document.getElementById("vista");
  vaciar(contenedor);
  for (const pestana of document.querySelectorAll(".pestana")) {
    pestana.classList.toggle("activa", pestana.dataset.vista === (PESTANA_DE[vista] || vista));
  }
  const resultado = await VISTAS[vista](contenedor, parametros);
  if (typeof resultado === "function") limpiarVista = resultado;
  await chrome.storage.session.set({ ultimaVista: vista === "ficha" ? "incidentes" : vista });
}

export async function comprobarSalud() {
  const estado = document.getElementById("estado");
  const texto = document.getElementById("estado-texto");
  const sub = document.getElementById("marca-sub");
  try {
    const datos = await pedir("/health");
    salud.datos = datos;
    const { modelo } = await chrome.storage.local.get("modelo");
    const listo = datos.listo;
    estado.className = `estado ${listo ? "ok" : "mal"}`;
    texto.textContent = listo ? "Conectado" : datos.ollama.ok ? "Faltan modelos" : "Ollama apagado";
    sub.textContent = `${modelo || datos.modelos.chat.nombre} · sin conexión a internet`;
  } catch {
    salud.datos = null;
    estado.className = "estado mal";
    texto.textContent = "Sin backend";
    sub.textContent = "Arranca scripts\\iniciar.bat";
  }
  for (const oyente of salud.oyentes) oyente(salud.datos);
}

async function revisarSeleccion() {
  const { seleccionPendiente } = await chrome.storage.session.get("seleccionPendiente");
  if (!seleccionPendiente) return;
  await chrome.storage.session.remove("seleccionPendiente");
  await ir("chat");
  recibirSeleccion(seleccionPendiente);
}

async function iniciar() {
  await cargarConfiguracion();
  for (const pestana of document.querySelectorAll(".pestana")) {
    pestana.addEventListener("click", () => ir(pestana.dataset.vista));
  }
  document.getElementById("estado").addEventListener("click", () => ir("ajustes"));

  await comprobarSalud();
  setInterval(comprobarSalud, 30000);

  const { ultimaVista } = await chrome.storage.session.get("ultimaVista");
  await ir(VISTAS[ultimaVista] ? ultimaVista : "chat");
  await revisarSeleccion();

  // Si el panel ya estaba abierto cuando se usa el menú contextual
  chrome.storage.onChanged.addListener((cambios, area) => {
    if (area === "session" && cambios.seleccionPendiente?.newValue) revisarSeleccion();
  });
}

iniciar();
