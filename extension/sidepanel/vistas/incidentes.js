// Vista Incidentes: cifras, búsqueda y lista de fichas.

import { pedir } from "../api.js";
import { ir } from "../app.js";
import { aviso, boton, chipSeveridad, fechaRelativa, h, icono, vaciar } from "../dom.js";

let filtro = "todos";
let texto = "";

export async function vistaIncidentes(contenedor) {
  const cifras = h("div", { class: "cifras" });
  const lista = h("div", { style: { display: "flex", flexDirection: "column", gap: "8px" } });
  const buscar = h("input", { type: "search", placeholder: "Buscar por título, tipo, ID o notas…", value: texto, "aria-label": "Buscar incidentes" });
  const filtros = h("div", { class: "filtros" });

  const pintarFiltros = () => vaciar(filtros, [["todos", "Todos"], ["abierto", "Abiertos"], ["cerrado", "Cerrados"]].map(([valor, nombre]) =>
    h("button", { type: "button", class: `filtro ${filtro === valor ? "activo" : ""}`, "aria-pressed": String(filtro === valor),
      onclick: () => { filtro = valor; pintarFiltros(); cargarLista(); } }, nombre)));

  const cargarLista = async () => {
    const parametros = new URLSearchParams();
    if (filtro !== "todos") parametros.set("estado", filtro);
    if (texto) parametros.set("q", texto);
    try {
      const incidentes = await pedir(`/incidentes?${parametros}`);
      vaciar(lista, incidentes.length ? incidentes.map(tarjetaIncidente)
        : h("div", { class: "vacio" }, texto || filtro !== "todos" ? "No hay incidentes con ese filtro."
          : "Aún no hay incidentes. Crea uno desde el Chat, a partir de la respuesta del asistente, o con «Nuevo»."));
    } catch (error) {
      vaciar(lista, h("div", { class: "banner banner-error" }, icono("alerta", 18), error.message));
    }
  };

  const cargarCifras = async () => {
    try {
      const r = await pedir("/incidentes/resumen");
      vaciar(cifras,
        h("div", { class: "cifra" }, h("b", {}, r.abiertos), h("span", {}, "Abiertos")),
        h("div", { class: "cifra" }, h("b", {}, r.en_memoria), h("span", {}, "En memoria")),
        h("div", { class: "cifra" }, h("b", {}, r.resolucion_media_horas != null ? `${r.resolucion_media_horas.toLocaleString("es-ES")} h` : "-"),
          h("span", {}, "Resolución media")));
    } catch { vaciar(cifras); }
  };

  let temporizador;
  buscar.addEventListener("input", () => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => { texto = buscar.value.trim(); cargarLista(); }, 250);
  });

  vaciar(contenedor,
    h("div", { class: "fila-entre", style: { padding: "8px 16px", background: "var(--superficie)", borderBottom: "1px solid var(--borde)" } },
      h("span", { class: "tenue", style: { fontSize: "12.5px" } }, "Fichas de incidente"),
      boton("Nuevo", nuevoIncidente, { icon: "mas", titulo: "Crear una ficha vacía" })),
    h("div", { class: "desplazable" }, cifras,
      h("label", { class: "buscador" }, icono("buscar"), buscar), filtros, lista));

  pintarFiltros();
  await Promise.all([cargarCifras(), cargarLista()]);
}

function tarjetaIncidente(i) {
  const plazo = i.estado === "abierto" && i.plazo_aepd;
  return h("button", { type: "button", class: "incidente", onclick: () => ir("ficha", { id: i.id }) },
    h("div", { class: "fila-entre" },
      h("span", { class: "mono tenue" }, i.id),
      h("span", { class: "tenue", style: { fontSize: "12px" } }, fechaRelativa(i.creado))),
    h("span", { class: "incidente-titulo" }, i.titulo),
    h("div", { class: "fila" },
      chipSeveridad(i.severidad),
      i.estado === "abierto"
        ? h("span", { class: "chip chip-abierto" }, `Abierto · ${i.pasos_hechos}/${i.pasos_total} pasos`)
        : h("span", { class: "chip chip-cerrado" }, i.en_memoria ? "Cerrado · en memoria" : "Cerrado"),
      plazo ? h("span", { class: `chip ${plazo.vencido ? "sev-critica" : "sev-alta"}` },
        plazo.vencido ? "Plazo AEPD vencido" : `AEPD: ${Math.max(0, Math.floor(plazo.horas_restantes))} h`) : null));
}

async function nuevoIncidente() {
  try {
    const ficha = await pedir("/incidentes", { metodo: "POST", json: { titulo: "Nuevo incidente" } });
    aviso(`Ficha ${ficha.id} creada`, "ok");
    await ir("ficha", { id: ficha.id, editarTitulo: true });
  } catch (error) {
    aviso(error.message, "error");
  }
}
