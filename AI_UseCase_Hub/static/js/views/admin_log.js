// Verwaltung → Protokoll: alle Änderungen (filterbar) und das Fehlerprotokoll.

import { api } from "../api.js";
import { h, emptyState, formatTs, table } from "../dom.js";

const PAGE = 100;

export async function renderLog(box) {
  const filter = { q: "", source: "", limit: PAGE };
  const results = h("div", { class: "stack-tight" });
  const search = h("input", {
    type: "search", class: "grow", placeholder: "Filter: ID, Feld, Wert oder Benutzer", "aria-label": "Protokoll filtern",
    oninput: () => { clearTimeout(search.timer); search.timer = setTimeout(() => { filter.q = search.value.trim(); filter.limit = PAGE; load(); }, 250); },
  });
  const source = h("select", { "aria-label": "Herkunft", onchange: () => { filter.source = source.value; filter.limit = PAGE; load(); } },
    h("option", { value: "" }, "Alle Herkünfte"),
    ["oberfläche", "import", "regel", "übergabe"].map((name) => h("option", { value: name }, name)));
  const errors = await api("GET", "/api/errors");

  box.replaceChildren(
    h("section", { class: "panel" },
      h("h2", null, "Änderungen"),
      h("div", { class: "toolbar" }, search, source),
      results),
    h("section", { class: "panel" },
      h("h2", null, "Fehler", h("span", { class: "count" }, `(${errors.lines.length})`)),
      errors.lines.length
        ? [h("p", { class: "muted" }, `Auszug aus ${errors.path}`), h("div", { class: "loglines", tabindex: "0" }, errors.lines.join("\n"))]
        : emptyState("Keine Fehler protokolliert. Unerwartete Fehler des Hubs erscheinen hier und in der Datei hub_fehler.log.")));
  await load();

  async function load() {
    const query = new URLSearchParams({ limit: String(filter.limit) });
    if (filter.q) query.set("q", filter.q);
    if (filter.source) query.set("source", filter.source);
    const data = await api("GET", `/api/audit?${query}`);
    if (!data.items.length) {
      results.replaceChildren(emptyState(filter.q || filter.source
        ? "Kein Eintrag passt zum Filter."
        : "Noch keine Änderungen. Jede Änderung an einem Datensatz erscheint hier mit altem und neuem Wert."));
      return;
    }
    results.replaceChildren(
      table([
        { label: "Zeit", value: (r) => formatTs(r.ts) },
        { label: "Wer", value: (r) => (r.user ? `${r.user} an ${r.machine}` : "–") },
        { label: "Datensatz", value: (r) => r.entity_id },
        { label: "Feld", value: (r) => r.field_label },
        { label: "Alt", value: (r) => r.old_value },
        { label: "Neu", value: (r) => r.new_value },
        { label: "Herkunft", value: (r) => r.source },
      ], data.items, `${data.items.length} von ${data.total} Einträgen, neueste zuerst`),
      data.total > data.items.length
        ? h("div", null, h("button", { class: "btn", type: "button", onclick: () => { filter.limit += PAGE; load(); } }, "Weitere laden"))
        : null);
  }
}
