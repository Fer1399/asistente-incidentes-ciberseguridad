// Vista Ficha: checklist por fases, plazo AEPD, IOCs, evidencias, cronología, cierre e informe.

import { pedir } from "../api.js";
import { ir } from "../app.js";
import {
  aviso, boton, chipSeveridad, confirmar, copiar, descargarBlob, dialogo, fechaLocal, h, icono, vaciar,
} from "../dom.js";
import { abrirConversacion } from "./chat.js";

const FASES = {
  inmediatas: "Acciones inmediatas", evidencias: "Preservación de evidencias", contencion: "Contención",
  analisis: "Análisis del alcance", erradicacion: "Erradicación y recuperación", notificacion: "Notificación",
  lecciones: "Lecciones aprendidas", otros: "Otros pasos",
};
const SEVERIDADES = ["Baja", "Media", "Alta", "Crítica"];
const NOMBRES_IOC = { ip: "IPs", dominio: "Dominios", url: "URLs", email: "Correos", hash: "Hashes", cve: "CVE" };

export async function vistaFicha(contenedor, { id, editarTitulo }) {
  let ficha;
  const recargar = async () => {
    try {
      ficha = await pedir(`/incidentes/${encodeURIComponent(id)}`);
      pintar();
    } catch (error) {
      vaciar(contenedor, h("div", { class: "desplazable" },
        boton("Incidentes", () => ir("incidentes"), { clase: "enlace", icon: "atras" }),
        h("div", { class: "banner banner-error" }, icono("alerta", 18), error.message)));
    }
  };

  const accion = async (promesa, mensaje) => {
    try {
      await promesa;
      if (mensaje) aviso(mensaje, "ok");
      await recargar();
    } catch (error) {
      aviso(error.message, "error");
    }
  };

  function pintar() {
    const abierta = ficha.estado === "abierto";
    const desplazamiento = contenedor.querySelector(".desplazable")?.scrollTop || 0;
    vaciar(contenedor, cabecera(), cuerpo(), pie());
    contenedor.querySelector(".desplazable").scrollTop = desplazamiento;
    if (editarTitulo && abierta) { editarTitulo = false; editarDatos(); }

    function cabecera() {
      return h("div", { class: "ficha-cabecera" },
        h("div", { class: "fila-entre" },
          boton("Incidentes", () => ir("incidentes"), { clase: "enlace", icon: "atras" }),
          h("span", { class: `chip ${abierta ? "chip-abierto" : "chip-cerrado"}` }, abierta ? "Abierto" : ficha.en_memoria ? "Cerrado · en memoria" : "Cerrado")),
        h("span", { class: "mono tenue" }, `${ficha.id} · detectado ${fechaLocal(ficha.detectado)}`),
        h("h1", { class: "ficha-titulo" }, ficha.titulo),
        h("div", { class: "fila" },
          chipSeveridad(ficha.severidad),
          ficha.tipo ? h("span", { class: "chip" }, ficha.tipo) : null,
          abierta ? h("button", { class: "enlace", type: "button", style: { fontSize: "12px" }, onclick: editarDatos }, "Editar datos") : null));
    }

    function cuerpo() {
      return h("div", { class: "desplazable" },
        bannerPlazo(),
        tarjetaPasos(),
        ficha.descripcion ? h("div", { class: "tarjeta" }, h("p", { class: "tarjeta-titulo" }, "Descripción"),
          h("p", { class: "modal-texto", style: { whiteSpace: "pre-wrap" } }, ficha.descripcion)) : null,
        tarjetaIocs(),
        tarjetaEvidencias(),
        tarjetaConversacion(),
        abierta ? null : tarjetaCierre(),
        tarjetaCronologia(),
        abierta ? null : h("div", { class: "fila" },
          boton("Reabrir", () => confirmar("Reabrir la ficha", "Se retirará de la memoria del asistente hasta que la vuelvas a cerrar.", "Reabrir")
            .then((si) => si && accion(pedir(`/incidentes/${id}/reabrir`, { metodo: "POST" }), "Ficha reabierta")),
          { clase: "boton boton-secundario" }),
          boton("Borrar ficha", borrar, { clase: "boton boton-secundario", icon: "basura" })));
    }

    function pie() {
      const conversar = boton("Preguntar al asistente", conversarSobreFicha, { clase: "boton boton-secundario", icon: "chat", titulo: "Seguir la conversación en el Chat" });
      const informe = boton("Informe", elegirInforme, { clase: "boton boton-secundario", icon: "descargar" });
      if (!abierta) return h("div", { class: "pie-acciones" }, conversar, informe);
      return h("div", { class: "pie-acciones" },
        boton("Cerrar y guardar", cerrarFicha, { icon: "escudo", titulo: "Cerrar la ficha y guardarla en la memoria del asistente" }),
        h("button", { class: "boton-icono", type: "button", title: "Preguntar al asistente", "aria-label": "Preguntar al asistente", onclick: conversarSobreFicha }, icono("chat")),
        h("button", { class: "boton-icono", type: "button", title: "Descargar informe", "aria-label": "Descargar informe", onclick: elegirInforme }, icono("descargar")));
    }

    function bannerPlazo() {
      const plazo = ficha.plazo_aepd;
      if (!plazo || !abierta) return null;
      return h("div", { class: `banner ${plazo.vencido ? "banner-error" : "banner-aviso"}` }, icono("reloj", 18),
        h("div", {}, h("b", {}, "Posible brecha de datos personales"),
          plazo.vencido ? `El plazo de 72 h para notificar a la AEPD venció el ${fechaLocal(plazo.limite)}.`
            : `Quedan ${Math.floor(plazo.horas_restantes)} h para notificar a la AEPD si se confirma (límite: ${fechaLocal(plazo.limite)}).`));
    }

    function tarjetaPasos() {
      const { hechos, total } = ficha.progreso;
      const porFase = Object.entries(FASES).map(([fase, nombre]) => [fase, nombre, ficha.pasos.filter((p) => p.fase === fase)])
        .filter(([, , pasos]) => pasos.length);
      const faseNueva = h("select", { "aria-label": "Fase del paso" },
        Object.entries(FASES).map(([v, n]) => h("option", { value: v, selected: v === "otros" }, n)));
      const textoNuevo = h("input", { class: "entrada", placeholder: "Añadir un paso propio…", maxlength: "1000", style: { flex: "1", minWidth: "140px" } });
      const anadir = () => {
        if (textoNuevo.value.trim().length < 2) return;
        accion(pedir(`/incidentes/${id}/pasos`, { metodo: "POST", json: { fase: faseNueva.value, texto: textoNuevo.value.trim() } }));
      };
      textoNuevo.addEventListener("keydown", (e) => { if (e.key === "Enter") anadir(); });

      return h("div", { class: "tarjeta", style: { display: "flex", flexDirection: "column", gap: "6px" } },
        h("div", { class: "fila-entre" }, h("p", { class: "tarjeta-titulo", style: { margin: 0 } }, "Procedimiento"),
          h("span", { class: "tenue", style: { fontSize: "12px" } }, `${hechos} de ${total} pasos`)),
        h("div", { class: "barra", role: "progressbar", "aria-valuenow": String(hechos), "aria-valuemax": String(total) },
          h("div", { style: { width: `${total ? (hechos / total) * 100 : 0}%` } })),
        total ? null : h("p", { class: "ayuda" }, "Sin pasos todavía. Pregunta al asistente o añade los tuyos."),
        porFase.map(([, nombre, pasos]) => [
          h("span", { class: "seccion-titulo", style: { marginTop: "8px" } }, nombre),
          pasos.map((p) => {
            const casilla = h("input", { type: "checkbox", checked: p.hecho, disabled: !abierta, "aria-label": p.texto });
            casilla.addEventListener("change", () => accion(pedir(`/incidentes/${id}/pasos/${p.id}`, { metodo: "PATCH", json: { hecho: casilla.checked } })));
            return h("label", { class: `paso ${p.hecho ? "hecho" : ""}` }, casilla,
              h("span", { style: { flex: "1" } }, h("span", { class: "paso-texto" }, p.texto),
                p.hecho ? h("span", { class: "paso-hora" }, ` · ${fechaLocal(p.hecho_en)}`) : null,
                p.origen === "usuario" ? h("span", { class: "paso-hora" }, " · propio") : null),
              abierta ? h("button", { class: "paso-quitar", type: "button", title: "Quitar paso", "aria-label": `Quitar paso: ${p.texto}`,
                onclick: (e) => { e.preventDefault(); accion(pedir(`/incidentes/${id}/pasos/${p.id}`, { metodo: "DELETE" })); } }, icono("cerrar", 14)) : null);
          }),
        ]),
        abierta ? h("div", { class: "fila", style: { marginTop: "8px" } }, faseNueva, textoNuevo,
          boton("", anadir, { clase: "boton-icono", icon: "mas", titulo: "Añadir paso" })) : null);
    }

    function tarjetaIocs() {
      const tipos = Object.entries(ficha.iocs).filter(([, l]) => l.length);
      if (!tipos.length) return null;
      const delAtacante = tipos.flatMap(([, l]) => l.filter((e) => !e.legitimo && !e.interna).map((e) => e.seguro));
      return h("details", { class: "tarjeta", open: true },
        h("summary", {}, `Indicadores (${tipos.reduce((n, [, l]) => n + l.length, 0)})`),
        h("div", { class: "iocs", style: { border: "none", padding: 0, background: "none" } },
          tipos.map(([tipo, lista]) => h("div", { class: "iocs-fila" },
            h("span", { class: "tenue", style: { minWidth: "62px" } }, NOMBRES_IOC[tipo]),
            lista.map((e) => h("button", { type: "button", class: `ioc ${e.legitimo || e.interna ? "ioc-legitimo" : ""}`,
              title: e.interna ? "IP interna" : e.legitimo ? "Dominio legítimo o propio" : "Copiar (desactivado)",
              onclick: () => copiar(e.seguro) }, e.seguro)))),
          delAtacante.length ? h("button", { class: "enlace", type: "button", style: { fontSize: "12px", marginTop: "4px" },
            onclick: () => copiar(delAtacante.join("\n"), `${delAtacante.length} indicadores copiados`) }, "Copiar los del atacante") : null));
    }

    function tarjetaEvidencias() {
      if (!ficha.adjuntos.length) return null;
      return h("details", { class: "tarjeta" },
        h("summary", {}, `Evidencias analizadas (${ficha.adjuntos.length})`),
        ficha.adjuntos.map((a) => h("div", { class: "resultado" },
          h("b", {}, a.nombre), h("span", { class: "mono tenue" }, `SHA-256 ${a.sha256}`),
          a.alertas?.length ? h("ul", { class: "alertas" }, a.alertas.map((x) => h("li", {}, x))) : null)));
    }

    function tarjetaConversacion() {
      if (!ficha.mensajes.length) return null;
      return h("details", { class: "tarjeta" },
        h("summary", {}, `Conversación con el asistente (${ficha.mensajes.length})`),
        h("p", { class: "ayuda", style: { marginTop: 0 } },
          abierta ? "Va en el anexo del informe. Quita lo que no aporte (pruebas, comandos escritos por error…)."
            : "Va en el anexo del informe."),
        ficha.mensajes.map((m) => h("div", { class: "resultado" },
          h("div", { class: "fila-entre" },
            h("b", {}, `${m.rol === "usuario" ? "Usuario" : "Asistente"} · ${fechaLocal(m.fecha)}`),
            abierta ? h("button", { class: "paso-quitar", type: "button", title: "Quitar de la conversación",
              "aria-label": "Quitar este mensaje de la conversación",
              onclick: () => confirmar("Quitar mensaje", "Dejará de aparecer en la ficha y en el informe.", "Quitar", true)
                .then((si) => si && accion(pedir(`/incidentes/${id}/mensajes/${m.id}`, { metodo: "DELETE" }), "Mensaje quitado")),
            }, icono("basura", 14)) : null),
          h("span", { style: { whiteSpace: "pre-wrap" } }, m.contenido.length > 280 ? `${m.contenido.slice(0, 280)}…` : m.contenido))));
    }

    function tarjetaCierre() {
      return h("div", { class: "tarjeta", style: { display: "flex", flexDirection: "column", gap: "6px" } },
        h("p", { class: "tarjeta-titulo", style: { margin: 0 } }, `Cerrado el ${fechaLocal(ficha.cerrado)}`),
        h("span", { class: "seccion-titulo" }, "Lo que se hizo"),
        h("p", { class: "modal-texto", style: { whiteSpace: "pre-wrap" } }, ficha.notas_cierre),
        ficha.lecciones ? [h("span", { class: "seccion-titulo" }, "Lecciones aprendidas"),
          h("p", { class: "modal-texto", style: { whiteSpace: "pre-wrap" } }, ficha.lecciones)] : null);
    }

    function tarjetaCronologia() {
      const nota = h("input", { class: "entrada", placeholder: "Añadir una nota a la cronología…", maxlength: "5000", style: { flex: "1" } });
      const anadirNota = () => nota.value.trim() && accion(pedir(`/incidentes/${id}/notas`, { metodo: "POST", json: { texto: nota.value.trim() } }), "Nota añadida");
      nota.addEventListener("keydown", (e) => { if (e.key === "Enter") anadirNota(); });
      return h("details", { class: "tarjeta" },
        h("summary", {}, `Cronología (${ficha.eventos.length})`),
        h("ol", { class: "cronologia" }, [...ficha.eventos].reverse().map((e) =>
          h("li", {}, h("time", { datetime: e.fecha }, fechaLocal(e.fecha)), h("span", {}, e.texto)))),
        abierta ? h("div", { class: "fila", style: { marginTop: "10px" } }, nota,
          boton("", anadirNota, { clase: "boton-icono", icon: "mas", titulo: "Añadir nota" })) : null);
    }
  }

  // --- Acciones -------------------------------------------------------------

  function editarDatos() {
    const titulo = h("input", { class: "entrada", value: ficha.titulo, maxlength: "150" });
    const tipo = h("input", { class: "entrada", value: ficha.tipo || "", maxlength: "80", placeholder: "Phishing, ransomware…" });
    const severidad = h("select", {}, h("option", { value: "" }, "Sin valorar"),
      SEVERIDADES.map((s) => h("option", { value: s, selected: ficha.severidad === s }, s)));
    const datos = h("input", { type: "checkbox", checked: ficha.datos_personales });
    const descripcion = h("textarea", { rows: "4", maxlength: "10000" }, ficha.descripcion || "");
    let cerrar;
    const guardarCambios = async () => {
      const cambios = { titulo: titulo.value.trim() || ficha.titulo, tipo: tipo.value.trim() || undefined,
        severidad: severidad.value || undefined, datos_personales: datos.checked, descripcion: descripcion.value };
      cerrar();
      await accion(pedir(`/incidentes/${id}`, { metodo: "PATCH", json: cambios }), "Datos guardados");
    };
    cerrar = dialogo({
      titulo: "Datos del incidente",
      cuerpo: h("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } },
        h("label", { class: "campo" }, "Título", titulo),
        h("div", { class: "fila", style: { flexWrap: "nowrap" } },
          h("label", { class: "campo", style: { flex: "1" } }, "Tipo", tipo),
          h("label", { class: "campo" }, "Severidad", severidad)),
        h("label", { class: "campo" }, "Descripción", descripcion),
        h("label", { class: "interruptor" }, h("span", {}, "Hay datos personales afectados (plazo de 72 h para la AEPD)"), datos)),
      acciones: [boton("Cancelar", () => cerrar(), { clase: "boton boton-secundario" }), boton("Guardar", guardarCambios)],
    });
  }

  function cerrarFicha() {
    const pendientes = ficha.pasos.filter((p) => !p.hecho).length;
    const notas = h("textarea", { rows: "5", maxlength: "20000",
      placeholder: "Qué se hizo realmente, en qué orden, qué funcionó y qué no. Es lo que el asistente recordará la próxima vez." });
    const lecciones = h("textarea", { rows: "3", maxlength: "10000", placeholder: "Qué cambiar para que no se repita (opcional)" });
    const memoria = h("input", { type: "checkbox", checked: true });
    let cerrar;
    const confirmarCierre = async (e) => {
      if (notas.value.trim().length < 10) { aviso("Escribe al menos una frase sobre lo que se hizo (mínimo 10 caracteres).", "error"); notas.focus(); return; }
      e.currentTarget.disabled = true;
      cerrar();
      await accion(pedir(`/incidentes/${id}/cerrar`, { metodo: "POST",
        json: { notas_cierre: notas.value.trim(), lecciones: lecciones.value.trim() || undefined, guardar_en_memoria: memoria.checked } }),
      memoria.checked ? "Ficha cerrada y guardada en la memoria" : "Ficha cerrada");
    };
    cerrar = dialogo({
      titulo: "Cerrar el incidente",
      cuerpo: h("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } },
        pendientes ? h("div", { class: "banner banner-aviso" }, icono("alerta", 18),
          h("span", {}, `Quedan ${pendientes} pasos sin marcar. Se guardarán como «propuestos que no se realizaron».`)) : null,
        h("label", { class: "campo" }, "Lo que se hizo (obligatorio)", notas),
        h("label", { class: "campo" }, "Lecciones aprendidas", lecciones),
        h("label", { class: "interruptor" }, h("span", {}, "Guardar en la memoria del asistente", h("br"),
          h("span", { class: "ayuda" }, "Aparecerá como «incidente similar» en casos parecidos")), memoria)),
      acciones: [boton("Cancelar", () => cerrar(), { clase: "boton boton-secundario" }), boton("Cerrar incidente", confirmarCierre, { icon: "escudo" })],
    });
  }

  function elegirInforme() {
    let cerrar;
    const anexo = h("input", { type: "checkbox", checked: true });
    const descargar = async (formato) => {
      cerrar();
      try {
        const blob = await pedir(`/incidentes/${id}/informe?formato=${formato}&anexo=${anexo.checked}`, { binario: true });
        descargarBlob(blob, `informe-${id}.${formato}`);
      } catch (error) {
        aviso(error.message, "error");
      }
    };
    cerrar = dialogo({
      titulo: "Descargar informe",
      cuerpo: h("div", { style: { display: "flex", flexDirection: "column", gap: "10px" } },
        h("p", { class: "modal-texto" }, "Resumen, cronología, procedimiento con la hora de cada paso, indicadores, evidencias y cierre."),
        h("label", { class: "interruptor" }, h("span", {}, `Incluir las consultas al asistente como anexo (${ficha.mensajes.length} mensajes)`), anexo)),
      acciones: [boton("Markdown", () => descargar("md"), { clase: "boton boton-secundario" }), boton("PDF", () => descargar("pdf"), { icon: "descargar" })],
    });
  }

  async function conversarSobreFicha() {
    await abrirConversacion({
      mensajes: ficha.mensajes.map((m) => ({ rol: m.rol, contenido: m.contenido, adjuntos: [] })),
      incidenteId: ficha.estado === "abierto" ? ficha.id : null,
      incidenteTitulo: ficha.titulo,
    });
    if (ficha.estado !== "abierto") aviso("La ficha está cerrada: la conversación no se guardará en ella.", "info");
  }

  async function borrar() {
    const si = await confirmar("Borrar la ficha", `Se borrará ${ficha.id} con sus pasos, cronología y conversación, y se retirará de la memoria. No se puede deshacer.`, "Borrar", true);
    if (!si) return;
    try {
      await pedir(`/incidentes/${id}`, { metodo: "DELETE" });
      const { conversacion } = await chrome.storage.local.get("conversacion");
      if (conversacion?.incidenteId === id) await chrome.storage.local.set({ conversacion: { ...conversacion, incidenteId: null } });
      aviso("Ficha borrada", "ok");
      await ir("incidentes");
    } catch (error) {
      aviso(error.message, "error");
    }
  }

  await recargar();
}
