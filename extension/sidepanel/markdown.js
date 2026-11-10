// Markdown seguro para las respuestas del asistente.
//
// Convierte un subconjunto de Markdown (títulos, listas, negrita, cursiva, código,
// bloques de código, tablas sencillas y citas [n]) en nodos del DOM SIN usar innerHTML.
// Los enlaces no se convierten en clicables: en este contexto suelen ser maliciosos.

import { h } from "./dom.js";

export function renderMarkdown(texto, { alCitar } = {}) {
  const raiz = h("div", { class: "md" });
  const lineas = texto.replace(/\r/g, "").split("\n");
  let lista = null;
  let tipoLista = null;
  let parrafo = [];

  const cerrarParrafo = () => {
    if (parrafo.length) raiz.append(h("p", {}, enLinea(parrafo.join(" "), alCitar)));
    parrafo = [];
  };
  const cerrarLista = () => {
    lista = null;
    tipoLista = null;
  };

  for (let i = 0; i < lineas.length; i++) {
    const linea = lineas[i];

    if (/^\s*```/.test(linea)) {
      cerrarParrafo();
      cerrarLista();
      const codigo = [];
      i++;
      while (i < lineas.length && !/^\s*```/.test(lineas[i])) codigo.push(lineas[i++]);
      raiz.append(h("pre", { class: "md-codigo" }, h("code", {}, codigo.join("\n"))));
      continue;
    }

    if (/^\s*\|.*\|\s*$/.test(linea) && i + 1 < lineas.length && /^\s*\|[\s:|-]+\|\s*$/.test(lineas[i + 1])) {
      cerrarParrafo();
      cerrarLista();
      const celdas = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const cabecera = celdas(linea);
      i += 2;
      const filas = [];
      while (i < lineas.length && /^\s*\|.*\|\s*$/.test(lineas[i])) filas.push(celdas(lineas[i++]));
      i--;
      raiz.append(h("div", { class: "md-tabla" }, h("table", {},
        h("thead", {}, h("tr", {}, cabecera.map((c) => h("th", {}, enLinea(c, alCitar))))),
        h("tbody", {}, filas.map((f) => h("tr", {}, f.map((c) => h("td", {}, enLinea(c, alCitar)))))),
      )));
      continue;
    }

    const titulo = linea.match(/^\s*(#{1,6})\s+(.+)$/);
    if (titulo) {
      cerrarParrafo();
      cerrarLista();
      const nivel = Math.min(titulo[1].length + 1, 5);
      raiz.append(h(`h${nivel}`, { class: "md-titulo" }, enLinea(titulo[2], alCitar)));
      continue;
    }

    const numerada = linea.match(/^\s*(\d+)[.)]\s+(.+)$/);
    const vineta = linea.match(/^\s*[-*•]\s+(.+)$/);
    if (numerada || vineta) {
      cerrarParrafo();
      const tipo = numerada ? "ol" : "ul";
      if (!lista || tipoLista !== tipo) {
        lista = h(tipo, numerada ? { start: numerada[1] } : {});
        tipoLista = tipo;
        raiz.append(lista);
      }
      lista.append(h("li", {}, enLinea(numerada ? numerada[2] : vineta[1], alCitar)));
      continue;
    }

    if (!linea.trim() || /^\s*-{3,}\s*$/.test(linea)) {
      cerrarParrafo();
      if (!linea.trim() && lista && !/^\s*(\d+[.)]|[-*•])\s+/.test(lineas[i + 1] || "")) cerrarLista();
      continue;
    }

    cerrarLista();
    parrafo.push(linea.trim());
  }
  cerrarParrafo();
  return raiz;
}

// Negrita **x**, cursiva *x*, código `x` y citas [1] / [1, 2]
function enLinea(texto, alCitar) {
  const nodos = [];
  const patron = /(\*\*[^*]+\*\*|`[^`]+`|\[\d+(?:\s*,\s*\d+)*\]|(?<![\w*])\*[^*\s][^*]*\*(?!\w))/g;
  let ultimo = 0;
  for (const m of texto.matchAll(patron)) {
    if (m.index > ultimo) nodos.push(texto.slice(ultimo, m.index));
    const t = m[0];
    if (t.startsWith("**")) nodos.push(h("strong", {}, t.slice(2, -2)));
    else if (t.startsWith("`")) nodos.push(h("code", {}, t.slice(1, -1)));
    else if (t.startsWith("[")) {
      for (const n of t.slice(1, -1).split(",").map((x) => x.trim())) {
        nodos.push(h("button", {
          class: "cita", type: "button", title: `Ver la fuente ${n}`,
          onclick: () => alCitar && alCitar(Number(n)),
        }, n));
      }
    } else nodos.push(h("em", {}, t.slice(1, -1)));
    ultimo = m.index + t.length;
  }
  if (ultimo < texto.length) nodos.push(texto.slice(ultimo));
  return nodos;
}
