// Rahmen der Anwendung: Navigation, Bänder, Statusmenü, Lebenszeichen.
// Geschäftsregeln gibt es hier nicht; angezeigt wird, was die API liefert.

import { api, onConnectionProblem } from "./api.js";
import { h, add, icon, formatTs } from "./dom.js";
import { renderStart } from "./views/start.js";
import { renderUsecases } from "./views/usecases.js";
import { renderTickets } from "./views/tickets.js";
import { renderAdmin } from "./views/admin.js";
import { renderSearch } from "./views/search.js";

const HEARTBEAT_MS = 15000;
const main = document.getElementById("main");
const bands = document.getElementById("bands");
const tools = document.getElementById("tools");

const app = {
  state: null,
  connection: "ok", // ok | offline | token | ended
  async refreshState() {
    app.state = await api("GET", "/api/state");
    renderBands();
    renderTools();
    return app.state;
  },
};

const AREAS = {
  start: renderStart,
  usecases: renderUsecases,
  tickets: renderTickets,
  verwaltung: renderAdmin,
  suche: renderSearch,
};

function parseHash() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  return { area: parts[0] || "start", rest: parts.slice(1) };
}

let renderRun = 0;

async function route() {
  if (app.connection === "ended") return;
  const { area, rest } = parseHash();
  const render = AREAS[area];
  if (!render) {
    location.replace("#/start");
    return;
  }
  for (const link of document.querySelectorAll(".mainnav a")) {
    if (link.dataset.area === area) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  const run = ++renderRun;
  const view = document.createDocumentFragment();
  try {
    await render(view, rest, app);
  } catch (error) {
    if (run !== renderRun) return;
    main.replaceChildren(h("div", { class: "panel" },
      h("h1", null, "Seite konnte nicht geladen werden"),
      h("p", null, error.message)));
    return;
  }
  if (run !== renderRun) return; // inzwischen wurde woanders hin navigiert
  main.replaceChildren(view);
}

function band(kind, symbol, text, action) {
  return h("div", { class: `band band-${kind}`, role: "status" }, icon(symbol), h("span", null, text), action || null);
}

function renderBands() {
  const items = [];
  const state = app.state;
  if (app.connection === "offline") {
    items.push(band("red", "alert",
      "Der Hub läuft nicht mehr. Startdatei AI_UseCase_Hub.pyw doppelklicken, dann diese Seite neu laden.",
      h("button", { class: "btn", type: "button", onclick: () => location.reload() }, "Neu laden")));
  } else if (app.connection === "token") {
    items.push(band("red", "alert", "Der Hub wurde neu gestartet. Diese Seite ist veraltet.",
      h("button", { class: "btn", type: "button", onclick: () => location.reload() }, "Neu laden")));
  }
  if (state) {
    if (state.test_mode) items.push(band("amber", "alert", "TESTMODUS – es wird mit Beispieldaten gearbeitet"));
    if (state.mode === "nur-lesen") {
      items.push(band(state.db_state === "ok" ? "amber" : "red", "lock",
        `Nur-Lese-Modus${state.read_only_reason ? ": " + state.read_only_reason : ""}`,
        state.db_state === "defekt"
          ? h("button", { class: "btn", type: "button", onclick: restoreBackup }, "Jüngstes gültiges Backup wiederherstellen")
          : null));
    }
    for (const warning of state.warnings || []) items.push(band("amber", "alert", warning));
  }
  bands.replaceChildren(...items);
}

function renderTools() {
  const state = app.state;
  if (!state) return;
  const readOnly = state.mode === "nur-lesen";
  const menuWasOpen = Boolean(tools.querySelector(".status-menu[open]"));
  const oldSearch = tools.querySelector(".search");
  const search = h("input", {
    type: "search", class: "search", placeholder: "Suche (ID, Titel, Melder:in)", "aria-label": "Suche",
    value: oldSearch ? oldSearch.value : null,
  });
  search.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && search.value.trim()) location.hash = `#/suche/${encodeURIComponent(search.value.trim())}`;
  });
  const hadFocus = oldSearch && document.activeElement === oldSearch;
  const create = h("a", {
    class: "btn", href: readOnly ? null : "#/usecases/neu", "aria-disabled": readOnly ? "true" : null,
    title: "Use Case oder Ticket manuell anlegen",
  }, icon("plus"), "Neu");
  const minutes = state.auto_shutdown_minutes;
  const menu = h("details", { class: "status-menu", open: menuWasOpen },
    h("summary", { class: readOnly ? "status-readonly" : "status-write" },
      icon(readOnly ? "lock" : "check"), readOnly ? "Nur-Lesen" : "Schreibmodus"),
    h("div", { class: "status-panel" },
      h("dl", { class: "stat-list" },
        h("div", null, h("dt", null, "Angemeldet"), h("dd", null, `${state.user} an ${state.machine}`)),
        h("div", null, h("dt", null, "Letzter Import"), h("dd", null, formatTs(state.last_import) || "noch keiner")),
        h("div", null, h("dt", null, "Automatisches Ende"),
          h("dd", null, minutes ? `nach ${minutes} min ohne Tab` : "aus")),
        h("div", null, h("dt", null, "Version"), h("dd", null, state.version))),
      h("button", { class: "btn", type: "button", onclick: shutdown }, icon("power"), "Hub beenden")));
  tools.replaceChildren(search, create, menu);
  if (hadFocus) search.focus();
}

// Rückfrage ist hier vorgesehen: Ein Stand wird verworfen (Konzept 9.7).
async function restoreBackup() {
  if (!window.confirm("Die beschädigte Datenbank durch das jüngste gültige Backup ersetzen? Die beschädigte Datei bleibt unter neuem Namen im Datenordner erhalten.")) return;
  try {
    await api("POST", "/api/backups/restore");
  } catch (error) {
    window.alert(error.message);
  }
  await app.refreshState();
  route();
}

async function shutdown() {
  try {
    await api("POST", "/api/shutdown");
  } catch (error) {
    return; // Band zeigt den Verbindungsfehler
  }
  app.connection = "ended";
  bands.replaceChildren();
  tools.replaceChildren();
  main.replaceChildren(h("div", { class: "panel" },
    h("h1", null, "Hub beendet"),
    h("p", null, "Dieses Fenster kann geschlossen werden. Neustart per Doppelklick auf AI_UseCase_Hub.pyw.")));
}

function stamp(state) {
  return state ? `${state.revision}|${state.last_import}|${state.mode}|${state.db_state}|${state.test_mode}` : "";
}

// Seiten, die sich selbst aktualisieren, wenn ein Import neue Daten gebracht hat.
const LIVE = ["#/start", "#/verwaltung/quellen", "#/verwaltung/konflikte", "#/usecases/stufe"];
const LIVE_EXACT = ["#/tickets"];

async function heartbeat() {
  if (app.connection === "ended" || app.connection === "token") return;
  try {
    await api("POST", "/api/heartbeat");
    if (app.connection === "offline") app.connection = "ok";
    const before = stamp(app.state);
    await app.refreshState();
    const typing = ["INPUT", "SELECT", "TEXTAREA"].includes((document.activeElement || {}).tagName);
    if (before !== stamp(app.state) && !typing && (LIVE.some((prefix) => location.hash.startsWith(prefix)) || LIVE_EXACT.includes(location.hash))) route();
  } catch (error) {
    // onConnectionProblem setzt das Band
  }
}

onConnectionProblem((kind) => {
  if (app.connection === "ended" || app.connection === kind) return;
  app.connection = kind;
  renderBands();
});

document.addEventListener("click", (event) => {
  const menu = document.querySelector(".status-menu[open]");
  if (menu && !menu.contains(event.target)) menu.removeAttribute("open");
});
document.addEventListener("keydown", (event) => {
  const menu = document.querySelector(".status-menu[open]");
  if (event.key === "Escape" && menu) {
    menu.removeAttribute("open");
    menu.querySelector("summary").focus();
  }
});
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) heartbeat();
});
window.addEventListener("hashchange", () => {
  route().then(() => main.focus());
});

async function init() {
  try {
    await app.refreshState();
  } catch (error) {
    add(main, h("div", { class: "panel" }, h("h1", null, "Keine Verbindung zum Hub"), h("p", null, error.message)));
    return;
  }
  heartbeat();
  setInterval(heartbeat, HEARTBEAT_MS);
  // Ersteinrichtung: beim ersten Aufruf direkt zu den Einstellungen.
  if (!app.state.configured && !location.hash) location.replace("#/verwaltung/einstellungen");
  else if (!location.hash) location.replace("#/start");
  route();
}

init();
