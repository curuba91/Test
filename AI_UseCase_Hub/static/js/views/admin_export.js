// Verwaltung → Export & Bericht: Reporting-Excel, Vollexport, Druckansichten, Auswahlliste fürs Ticket-Formular.

import { api } from "../api.js";
import { h, icon, emptyState, formatTs, status } from "../dom.js";

export async function renderExport(box, app) {
  const readOnly = app.state.mode === "nur-lesen";
  const [info, tools, list] = await Promise.all([api("GET", "/api/handover"), api("GET", "/api/export/toollist"), api("GET", "/api/usecases")]);
  const note = h("div", { role: "status" });
  const say = (ok, text) => note.replaceChildren(h("p", { class: `field-note ${ok ? "ok" : "bad"}` }, icon(ok ? "check" : "alert"), h("span", null, text)));
  const report = info.outputs.reporting;
  const lines = h("textarea", { rows: "6", readonly: true, "aria-label": "Auswahlliste" });
  lines.value = tools.lines.join("\n");
  const pick = h("select", { "aria-label": "Use Case für den Steckbrief" }, list.items.map((u) => h("option", { value: u.id }, `${u.id} – ${u.title}`)));
  box.replaceChildren(
    h("section", { class: "panel" },
      h("h2", null, "Reporting-Excel"),
      h("dl", { class: "kv" },
        h("dt", null, "Ordner"), h("dd", null, info.reporting_folder || "Team-Ordner nicht eingerichtet"),
        h("dt", null, "Zuletzt geschrieben"),
        h("dd", null, report ? [report.ok ? status("ok", "check", formatTs(report.ts)) : status("bad", "alert", "nicht geschrieben"), report.message ? ` ${report.message}` : ""] : "in dieser Sitzung noch nicht")),
      h("p", { class: "muted" }, `Wird ${info.publish_delay} Sekunden nach der letzten Änderung und beim Beenden neu geschrieben. Sechs Tabellen mit festen Namen und Spalten; keine E-Mail-Adressen, keine Notizfelder.`),
      note,
      h("div", { class: "toolbar" },
        h("button", { class: "btn btn-primary", type: "button", disabled: readOnly, onclick: async () => {
          try {
            const result = (await api("POST", "/api/export/reporting")).outputs.reporting;
            say(result.ok, result.ok ? `Geschrieben: ${result.path}` : result.message);
          } catch (error) { say(false, error.message); }
        } }, icon("refresh"), "Reporting-Excel jetzt schreiben"),
        h("button", { class: "btn", type: "button", disabled: readOnly, onclick: async () => {
          try {
            say(true, `Vollexport geschrieben: ${(await api("POST", "/api/export/full")).path}`);
          } catch (error) { say(false, error.message); }
        } }, "Vollexport aller Tabellen (inklusive Protokoll)"))),
    h("section", { class: "panel" },
      h("h2", null, "Druckansicht"),
      h("p", { class: "muted" }, "Die Ansicht öffnet sich zum Drucken; als PDF speichern über die Druckfunktion des Browsers."),
      h("div", { class: "toolbar" },
        h("a", { class: "btn", href: "#/druck/status" }, "Statusbericht"),
        pick,
        h("button", { class: "btn", type: "button", disabled: !list.items.length, onclick: () => { location.hash = `#/druck/steckbrief/${encodeURIComponent(pick.value)}`; } }, "Steckbrief öffnen"))),
    h("section", { class: "panel" },
      h("h2", null, "Auswahlliste für das Ticket-Formular", h("span", { class: "count" }, `(${tools.lines.length})`)),
      h("p", { class: "muted" }, "Diese Zeilen als Auswahlmöglichkeiten des Feldes „Betroffenes Tool“ ins Formular kopieren. Beginnt ein Ticket mit einer dieser IDs, ordnet der Hub es automatisch zu."),
      tools.lines.length ? [lines, h("div", { class: "toolbar" }, h("button", { class: "btn", type: "button", onclick: async () => {
        try { await navigator.clipboard.writeText(lines.value); } catch (error) { lines.select(); document.execCommand("copy"); }
        say(true, "Auswahlliste kopiert.");
      } }, "Liste kopieren"))] : emptyState("Noch keine abgeschlossenen Lösungen. In der Liste stehen alle Use Cases der Phase „Abgeschlossen“.")));
}
