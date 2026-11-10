// Service worker de la extensión.
// - Abre el panel lateral al pulsar el icono.
// - Añade "Analizar con el asistente" al menú contextual del texto seleccionado.
// No hace ninguna petición de red: todo lo que habla con el backend está en el panel.

const MENU_ID = "analizar-seleccion";

chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Analizar con el asistente",
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID || !info.selectionText) return;

  // Abrir el panel debe hacerse dentro del gesto del usuario: primero, antes de cualquier await
  const apertura = chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {});

  // El panel recoge este texto al abrirse (o al instante, si ya estaba abierto)
  await chrome.storage.session.set({
    seleccionPendiente: {
      texto: info.selectionText.slice(0, 20000),
      url: tab?.url || "",
      titulo: tab?.title || "",
      momento: Date.now(),
    },
  });
  await apertura;
});
