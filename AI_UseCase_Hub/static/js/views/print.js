// Druckansichten (Konzept 11.2): Statusbericht und Steckbrief je Use Case. PDF über die Druckfunktion des Browsers.

import { api } from "../api.js";
import { h, icon, formatDate, formatTs, table } from "../dom.js";

const NOTICE = "Der Vorabcheck ersetzt keine Freigabe. Die verbindliche Entscheidung trifft die zuständige Qualitäts- bzw. Validierungsfunktion.";

function head(title, sub) {
  return h("div", { class: "page-head" },
    h("div", null, h("h1", null, title), h("p", null, sub)),
    h("div", { class: "toolbar no-print" },
      h("a", { class: "btn", href: "#/verwaltung/export" }, "Zurück"),
      h("button", { class: "btn btn-primary", type: "button", onclick: () => window.print() }, "Drucken")));
}

export async function renderPrint(view, rest) {
  if (rest[0] === "steckbrief" && rest[1]) {
    const d = await api("GET", `/api/usecases/${encodeURIComponent(rest[1])}`);
    const uc = d.usecase;
    const last = d.validations[0];
    view.append(h("div", { class: "print-page stack" },
      head(`${uc.id} – ${uc.title}`, `Steckbrief · Stand ${formatTs(new Date().toISOString())}`),
      h("section", { class: "panel" }, h("dl", { class: "kv" },
        h("dt", null, "Stufe"), h("dd", null, `${d.stepper.stage_label}${d.stepper.stage === "governance" ? ` (${d.stepper.gov_done} von ${d.stepper.gov_total} Schritten)` : ""}`),
        h("dt", null, "Owner"), h("dd", null, uc.owner || "–"),
        h("dt", null, "Bereich"), h("dd", null, uc.area || "–"),
        h("dt", null, "Typ · Herkunft"), h("dd", null, `${uc.type || "–"} · ${uc.origin || "–"}`),
        h("dt", null, "Version"), h("dd", null, uc.version || "–"),
        h("dt", null, "Einordnung"), h("dd", null, `${uc.reg_status}${uc.reg_result ? ` – ${uc.reg_result}` : ""}${uc.reg_reference ? ` (Verweis: ${uc.reg_reference})` : ""}`))),
      h("section", { class: "panel" }, h("h2", null, "Beschreibung"), h("p", { class: "pre" }, uc.description || "–"),
        h("h2", null, "Nutzen"), h("p", { class: "pre" }, uc.benefit || "–")),
      h("section", { class: "panel" }, h("h2", null, `Offene Punkte (${d.actions.length})`),
        d.actions.length ? h("ul", { class: "check-list" }, d.actions.map((a) => h("li", null, icon(a.level === "blockierend" ? "alert" : "circle"),
          h("span", null, `${a.level === "blockierend" ? "Blockierend" : "Offen"}: ${a.text}`)))) : h("p", null, "Keine offenen Punkte.")),
      last ? h("p", { class: "muted" }, NOTICE) : null));
    return;
  }
  const r = await api("GET", "/api/report/status");
  const c = r.counts;
  view.append(h("div", { class: "print-page stack" },
    head("AI Use Case Hub – Statusbericht", `Stand ${formatTs(r.generated)}${r.labels.site ? ` · ${r.labels.site}` : ""}`),
    h("section", { class: "panel" }, h("h2", null, "Bestand"),
      h("dl", { class: "kv" },
        h("dt", null, "Eingang"), h("dd", null, c.eingang), h("dt", null, "Umsetzung"), h("dd", null, c.umsetzung),
        h("dt", null, "Governance"), h("dd", null, c.governance), h("dt", null, "Betrieb"), h("dd", null, c.betrieb),
        h("dt", null, "Offene Tickets"), h("dd", null, c.tickets_open),
        h("dt", null, "Eingeordnet"), h("dd", null, `${c.reg_confirmed} von ${c.reg_total} abgeschlossenen Lösungen${r.deadline.date ? ` · Stichtag ${formatDate(r.deadline.date)}` : ""}`))),
    h("section", { class: "panel" }, h("h2", null, `Blockierende Punkte (${r.blocking.length})`),
      r.blocking.length ? table([{ label: "ID", value: (a) => a.subject }, { label: "Titel", value: (a) => a.title },
        { label: "Punkt", value: (a) => a.text }], r.blocking) : h("p", null, "Keine blockierenden Punkte.")),
    h("section", { class: "panel" }, h("h2", null, `Governance-Fortschritt (${r.governance.length})`),
      r.governance.length ? table([{ label: "ID", value: (u) => u.id }, { label: "Titel", value: (u) => u.title },
        { label: "Stufe", value: (u) => u.stage_label }, { label: "Fortschritt", value: (u) => `${u.gov_done} von ${u.gov_total}` },
        { label: "Einordnung", value: (u) => u.reg_status }, { label: "Nächster Schritt", value: (u) => u.next_step || "–" }], r.governance)
        : h("p", null, "Noch keine abgeschlossenen Lösungen.")),
    h("p", { class: "muted" }, NOTICE)));
}
