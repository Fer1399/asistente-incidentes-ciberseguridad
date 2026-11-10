// Cliente del backend local. Solo habla con 127.0.0.1 / localhost.

const POR_DEFECTO = "http://127.0.0.1:8000";
let base = POR_DEFECTO;

export async function cargarConfiguracion() {
  const { backendUrl } = await chrome.storage.local.get("backendUrl");
  base = esLocal(backendUrl) ? backendUrl.replace(/\/+$/, "") : POR_DEFECTO;
  return base;
}

export function esLocal(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" && ["127.0.0.1", "localhost"].includes(u.hostname);
  } catch {
    return false;
  }
}

export async function guardarUrl(url) {
  if (!esLocal(url)) throw new Error("Solo se permiten direcciones locales (127.0.0.1 o localhost)");
  await chrome.storage.local.set({ backendUrl: url });
  base = url.replace(/\/+$/, "");
}

export function urlBase() {
  return base;
}

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje);
    this.estado = estado;
  }
}

async function detalle(respuesta) {
  try {
    const datos = await respuesta.json();
    const d = datos.detail;
    if (typeof d === "string") return d;
    if (d?.mensaje) return d.mensaje;
    if (Array.isArray(d)) return d.map((x) => x.msg).join("; ");
    return JSON.stringify(d);
  } catch {
    return respuesta.statusText;
  }
}

export async function pedir(ruta, { metodo = "GET", json, cuerpo, senal, binario = false } = {}) {
  let respuesta;
  try {
    respuesta = await fetch(base + ruta, {
      method: metodo,
      headers: json ? { "Content-Type": "application/json" } : undefined,
      body: json ? JSON.stringify(json) : cuerpo,
      signal: senal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ErrorApi("No se puede conectar con el backend. ¿Está en marcha scripts\\iniciar.bat?", 0);
  }
  if (!respuesta.ok) throw new ErrorApi(await detalle(respuesta), respuesta.status);
  if (respuesta.status === 204) return null;
  return binario ? respuesta.blob() : respuesta.json();
}

export function subirFichero(ruta, fichero, nombre) {
  const datos = new FormData();
  datos.append("fichero", fichero, nombre || fichero.name);
  return pedir(ruta, { metodo: "POST", cuerpo: datos });
}

// Chat en streaming: una línea JSON por evento (ver backend/app/routers/chat.py)
export async function chatStream(cuerpo, alEvento, senal) {
  let respuesta;
  try {
    respuesta = await fetch(base + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
      signal: senal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ErrorApi("No se puede conectar con el backend. ¿Está en marcha scripts\\iniciar.bat?", 0);
  }
  if (!respuesta.ok) throw new ErrorApi(await detalle(respuesta), respuesta.status);

  const lector = respuesta.body.getReader();
  const decodificador = new TextDecoder();
  let pendiente = "";
  for (;;) {
    const { value, done } = await lector.read();
    if (done) break;
    pendiente += decodificador.decode(value, { stream: true });
    const lineas = pendiente.split("\n");
    pendiente = lineas.pop();
    for (const linea of lineas) if (linea.trim()) alEvento(JSON.parse(linea));
  }
  if (pendiente.trim()) alEvento(JSON.parse(pendiente));
}
