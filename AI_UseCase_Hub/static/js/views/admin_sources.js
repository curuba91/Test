// Verwaltung → Quellen & Import: Zustand je Quelle, letzte Läufe, „Jetzt importieren“.

import { api } from "../api.js";
import { h, icon, emptyState, formatTs, table, status } from "../dom.js";

function stateBadge(source) {
  if (source.state === "ok") return status("ok", "check", source.state_text);
  if (source.state === "ausstehend") return status("none", "circle", source.state_text);
  return status("bad", "alert", source.state_text);
}

export async function renderSources(box, app) {
  let data = await api("GET", "/api/import/log");
  const readOnly = app.state.mode === "nur-lesen";
  const note = h("div", { role: "status" });
  draw();

  function draw() {
    box.replaceChildren(
      h("section", { class: "panel" },
        h("div", { class: "page-head" },
          h("h2", null, "Quellen"),
          h("div", { class: "toolbar" },
            app.state.test_mode ? h("button", { class: "btn", type: "button", disabled: readOnly, onclick: simulate },
              icon("plus"), "Neue Meldungen simulieren") : null,
            h("button", { class: "btn btn-primary", type: "button", disabled: readOnly, onclick: run },
              icon("refresh"), "Jetzt importieren"))),
        note,
        h("div", { class: "source-grid" }, data.sources.map((source) =>
          h("div", { class: "source-card" },
            h("h3", null, source.label, stateBadge(source)),
            h("dl", { class: "kv kv-tight" },
              h("dt", null, "Datei"), h("dd", null, source.path || "nicht angegeben"),
              h("dt", null, "Letzter Erfolg"), h("dd", null, formatTs(source.last_success) || "noch keiner"),
              h("dt", null, "Letzter Versuch"), h("dd", null, formatTs(source.last_attempt) || "noch keiner"),
              h("dt", null, "Zeilen"), h("dd", { class: "num" }, source.row_count)),
            source.message ? h("p", { class: `field-note ${source.state === "ok" ? "" : "bad"}` },
              icon(source.state === "ok" ? "circle" : "alert"), h("span", null, source.message)) : null))),
        h("p", { class: "muted" }, "Die Quell-Excels werden nur gelesen, über eine temporäre Kopie. Geprüft wird automatisch, sobald sich eine Datei ändert.")),
      h("section", { class: "panel" },
        h("h2", null, "Letzte Läufe"),
        data.items.length ? table([
          { label: "Zeit", value: (r) => formatTs(r.ts) },
          { label: "Quelle", value: (r) => r.source_label },
          { label: "Ergebnis", value: (r) => (r.status === "ok" ? status("ok", "check", "gelesen") : status("bad", "alert", "Fehler")) },
          { label: "Zeilen", num: true, value: (r) => r.row_count },
          { label: "Neu", num: true, value: (r) => r.added },
          { label: "Geändert", num: true, value: (r) => r.changed },
          { label: "Konflikte", num: true, value: (r) => r.conflicts },
          { label: "Dubletten", num: true, value: (r) => r.duplicates },
          { label: "Ohne ID", num: true, value: (r) => r.missing_id },
          { label: "Hinweis", value: (r) => r.message },
        ], data.items) : emptyState("Noch kein Importlauf. Der erste Lauf startet automatisch, sobald die Quellen eingerichtet sind, oder über „Jetzt importieren“.")));
  }

  async function finish(steps) {
    data = await api("GET", "/api/import/log");
    await app.refreshState();
    note.replaceChildren(steps && steps.length
      ? h("ul", { class: "check-list" }, steps.map((text) => h("li", null, h("span", { class: "check-open" }, icon("circle")), h("span", null, text))))
      : h("p", { class: "field-note ok" }, icon("check"), h("span", null, "Import ausgeführt.")));
    draw();
  }

  async function run() {
    try {
      await api("POST", "/api/import/run");
      await finish();
    } catch (error) {
      note.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
    }
  }

  async function simulate() {
    try {
      const result = await api("POST", "/api/import/simulate");
      await finish(result.steps);
    } catch (error) {
      note.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
    }
  }
}
