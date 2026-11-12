// Use Cases – Liste (Konzept 9.3): eine Tabelle, Stufe als Umschalter, sortierbar und filterbar.
// Unteradressen: #/usecases/stufe/<stufe>, #/usecases/neu, #/usecases/<ID>/<abschnitt>.

import { api } from "../api.js";
import { h, icon, emptyState, pageHead, formatDate, formatTs, status } from "../dom.js";
import { renderUsecase } from "./usecase.js";

const TABS = [["eingang", "Eingang"], ["umsetzung", "Umsetzung"], ["governance", "Governance"], ["betrieb", "Betrieb"],
  ["archiv", "Archiv"], ["alle", "Alle"]];
const ATTENTION = {
  blockierend: ["bad", "alert", "blockiert"], offen: ["open", "circle", "offen"], keiner: ["ok", "check", "erledigt"],
};
const RANK = { blockierend: 0, offen: 1, keiner: 2 };
const text = (a, b) => String(a || "").localeCompare(String(b || ""), "de", { numeric: true });
// Leere Werte ans Ende, unabhängig von der Richtung.
const withEmptyLast = (get, compare) => (a, b, dir) => {
  const x = get(a), y = get(b);
  const ex = x === null || x === undefined || x === "", ey = y === null || y === undefined || y === "";
  if (ex || ey) return ex === ey ? 0 : (ex ? 1 : -1);
  return compare(x, y) * dir;
};
const byText = (get) => withEmptyLast(get, text);
const byNumber = (get) => withEmptyLast(get, (x, y) => x - y);

const FIXED = [
  { key: "attention", label: "Status", sort: (a, b, dir) => (RANK[a.attention] - RANK[b.attention]) * dir,
    value: (r) => (r.stage === "archiv" ? status("none", "dash", "Archiv") : status(...ATTENTION[r.attention])) },
  { key: "id", label: "ID", sort: byText((r) => r.id), value: (r) => h("a", { href: `#/usecases/${encodeURIComponent(r.id)}` }, r.id) },
  { key: "title", label: "Titel", sort: byText((r) => r.title), value: (r) => r.title || "(ohne Titel)" },
  { key: "owner", label: "Owner", sort: byText((r) => r.owner), value: (r) => r.owner || "–" },
  { key: "next_step", label: "Nächster Schritt", sort: byText((r) => r.next_step),
    value: (r) => (r.next_step ? h("a", { href: r.next_target }, r.next_step) : "–") },
];
const EXTRA = {
  eingang: [
    { key: "area", label: "Bereich", sort: byText((r) => r.area), value: (r) => r.area || "–" },
    { key: "reporter", label: "Melder:in", sort: byText((r) => r.reporter), value: (r) => r.reporter || "–" },
    { key: "submitted", label: "Eingang", sort: byText((r) => r.submitted), value: (r) => formatDate(r.submitted) },
    { key: "score", label: "Score", num: true, sort: byNumber((r) => r.score), value: (r) => (r.score === null ? "–" : String(r.score).replace(".", ",")) },
  ],
  umsetzung: [
    { key: "milestone", label: "Nächster Meilenstein", sort: byText((r) => r.next_milestone && r.next_milestone.title),
      value: (r) => (r.next_milestone ? r.next_milestone.title : "–") },
    { key: "due", label: "fällig am", sort: byText((r) => r.next_milestone && r.next_milestone.planned_date),
      value: (r) => (r.next_milestone ? [formatDate(r.next_milestone.planned_date), r.next_milestone.overdue ? [" ", status("bad", "alert", "überfällig")] : null] : "–") },
  ],
  governance: [
    { key: "progress", label: "Fortschritt", num: true, sort: byNumber((r) => (r.gov_total ? r.gov_done / r.gov_total : 1)),
      value: (r) => `${r.gov_done} von ${r.gov_total}` },
    { key: "reg", label: "Einordnung", sort: byText((r) => r.reg_status), value: (r) => r.reg_status },
  ],
  betrieb: [
    { key: "version", label: "Version", sort: byText((r) => r.version), value: (r) => r.version || "–" },
    { key: "lc_owner", label: "Life-Cycle-Owner", sort: byText((r) => r.lc_owner), value: (r) => r.lc_owner || "–" },
    { key: "review", label: "Nächstes Review", sort: byText((r) => r.next_review), value: (r) => formatDate(r.next_review) || "–" },
    { key: "tickets", label: "Offene Tickets", num: true, sort: byNumber((r) => r.open_tickets), value: (r) => r.open_tickets },
  ],
  archiv: [
    { key: "phase", label: "Phase", sort: byText((r) => r.phase), value: (r) => r.phase },
    { key: "updated", label: "Zuletzt geändert", sort: byText((r) => r.updated_at), value: (r) => formatTs(r.updated_at) },
  ],
};
EXTRA.alle = EXTRA.archiv;
// Standard-Sortierung je Umschalter: [Spalte, Richtung]; Eingang zusätzlich „blockierend zuerst“.
const DEFAULT_SORT = { eingang: ["score", -1], umsetzung: ["due", 1], governance: ["progress", 1], betrieb: ["review", 1],
  archiv: ["updated", -1], alle: ["updated", -1] };

// Bleibt beim Zurückkehren erhalten (Konzept 9.3).
const memory = { tab: "eingang", sort: {}, owner: "", area: "", q: "" };

export async function renderUsecases(view, rest, app) {
  if (rest[0] === "neu") return renderNew(view, app);
  if (rest[0] === "stufe") {
    if (TABS.some(([key]) => key === rest[1])) memory.tab = rest[1];
  } else if (rest[0]) {
    return renderUsecase(view, rest[0], rest[1], app);
  }
  const rows = (await api("GET", "/api/usecases")).items;
  const tableBox = h("div");
  const tabsBox = h("div", { class: "toggle", role: "group", "aria-label": "Stufe" });
  const count = (key) => rows.filter((r) => key === "alle" || r.stage === key).length;
  const distinct = (get) => [...new Set(rows.map(get).filter(Boolean))].sort(text);

  const search = h("input", { type: "search", class: "grow", placeholder: "Filter: ID, Titel, Melder:in", "aria-label": "Liste filtern", value: memory.q,
    oninput: () => { memory.q = search.value; drawTable(); } });
  const owner = select("Owner", "Alle Owner", distinct((r) => r.owner), "owner");
  const area = select("Bereich", "Alle Bereiche", distinct((r) => r.area), "area");

  function select(label, all, values, name) {
    if (memory[name] && !values.includes(memory[name])) memory[name] = "";
    const el = h("select", { "aria-label": label, onchange: () => { memory[name] = el.value; drawTable(); } },
      h("option", { value: "" }, all), values.map((v) => h("option", { value: v, selected: v === memory[name] }, v)));
    return el;
  }

  function drawTabs() {
    tabsBox.replaceChildren(...TABS.map(([key, label]) =>
      h("a", { href: `#/usecases/stufe/${key}`, "aria-current": key === memory.tab ? "true" : null },
        label, h("span", { class: "count" }, count(key)))));
  }

  function drawTable() {
    const tab = memory.tab;
    const columns = [...FIXED, ...EXTRA[tab]];
    const needle = memory.q.trim().toLowerCase();
    const shown = rows.filter((r) => (tab === "alle" || r.stage === tab)
      && (!memory.owner || r.owner === memory.owner) && (!memory.area || r.area === memory.area)
      && (!needle || [r.id, r.title, r.reporter].some((v) => String(v || "").toLowerCase().includes(needle))));
    const [sortKey, sortDir] = memory.sort[tab] || DEFAULT_SORT[tab];
    const column = columns.find((c) => c.key === sortKey) || columns[1];
    const usesDefault = !memory.sort[tab];
    shown.sort((a, b) => (usesDefault && tab === "eingang" ? RANK[a.attention] - RANK[b.attention] : 0)
      || column.sort(a, b, sortDir) || text(a.id, b.id));
    if (!shown.length) {
      tableBox.replaceChildren(emptyState(rows.length
        ? "Kein Use Case passt zu Stufe und Filter. Filter leeren oder eine andere Stufe wählen."
        : "Noch keine Use Cases. Sie entstehen durch den Import aus Quelle 1 oder über „Neu“ in der Kopfzeile."));
      return;
    }
    tableBox.replaceChildren(h("div", { class: "table-wrap" }, h("table", { class: "table rows-link" },
      h("caption", null, `${shown.length} von ${count(tab)} Use Cases`),
      h("thead", null, h("tr", null, columns.map((c) => {
        const active = c.key === column.key;
        return h("th", { scope: "col", class: c.num ? "num" : null, "aria-sort": active ? (sortDir === 1 ? "ascending" : "descending") : null },
          h("button", { class: "sort", type: "button", onclick: () => { memory.sort[tab] = [c.key, active ? -sortDir : 1]; drawTable(); } },
            c.label, active ? icon(sortDir === 1 ? "up" : "down") : null));
      }))),
      h("tbody", null, shown.map((row) => {
        const tr = h("tr", null, columns.map((c) => h("td", { class: c.num ? "num" : null }, c.value(row))));
        tr.addEventListener("click", (event) => {
          if (!event.target.closest("a, button")) location.hash = `#/usecases/${encodeURIComponent(row.id)}`;
        });
        return tr;
      })))));
  }

  drawTabs();
  drawTable();
  view.append(
    pageHead("Use Cases"),
    h("section", { class: "panel" },
      tabsBox,
      h("div", { class: "toolbar" }, search, owner, area),
      tableBox));
}

async function renderNew(view, app) {
  const readOnly = app.state.mode === "nur-lesen";
  const note = h("p", { class: "field-note", role: "status" },
    h("span", null, "Manuell angelegte Einträge erhalten eine ID der Form M-001 (Use Case) oder TM-001 (Ticket). Alles Weitere wird danach gepflegt."));
  const kind = h("select", { id: "new-kind", disabled: readOnly },
    h("option", { value: "usecases" }, "Use Case"), h("option", { value: "tickets" }, "Ticket"));
  const input = h("input", { type: "text", id: "new-title", disabled: readOnly, autocomplete: "off" });
  const create = async () => {
    try {
      const detail = await api("POST", `/api/${kind.value}`, { title: input.value });
      location.hash = kind.value === "tickets" ? `#/tickets/${encodeURIComponent(detail.ticket.id)}`
        : `#/usecases/${encodeURIComponent(detail.usecase.id)}/ueberblick`;
    } catch (error) {
      note.className = "field-note bad";
      note.replaceChildren(icon("alert"), h("span", null, error.message));
      input.setAttribute("aria-invalid", "true");
    }
  };
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") create(); });
  view.append(
    h("a", { class: "back", href: "#/usecases" }, "← Use Cases"),
    pageHead("Manuell anlegen"),
    h("section", { class: "panel" },
      h("div", { class: "form-grid" },
        h("div", { class: "field" }, h("label", { for: "new-kind" }, "Art"), kind),
        h("div", { class: "field" }, h("label", { for: "new-title" }, "Titel"),
          h("div", { class: "field-row" }, input,
            h("button", { class: "btn btn-primary", type: "button", disabled: readOnly, onclick: create }, "Anlegen")))),
      note));
  setTimeout(() => input.focus(), 0);
}
