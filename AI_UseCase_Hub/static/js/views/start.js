// Start: in zehn Sekunden wissen, was heute zu tun ist (Konzept 9.2).

import { api } from "../api.js";
import { h, icon, emptyState, pageHead, formatDate } from "../dom.js";

function actionGroup(title, level, symbol, items) {
  if (!items.length) return null;
  return h("section", { class: "stack-tight" },
    h("h3", { class: `group-title level-${level}` }, icon(symbol), `${title} (${items.length})`),
    h("ul", { class: "action-list" }, items.map((item) =>
      h("li", null, h("a", { href: item.target },
        h("span", { class: `level-${level}` }, icon(symbol)),
        h("span", { class: "action-subject" }, item.subject),
        h("span", { class: "action-text" }, item.text),
        icon("arrow"))))));
}

function stat(label, value) {
  return h("div", null, h("dt", null, label), h("dd", null, value === null || value === undefined ? "–" : value));
}

export async function renderStart(view, _rest, app) {
  const actions = await api("GET", "/api/actions");
  const state = app.state;
  const total = actions.blocking.length + actions.open.length;
  const lastImport = state.last_import || "noch keiner";

  const work = h("section", { class: "panel" },
    h("h2", null, "Handlungsbedarf", h("span", { class: "count" }, `(${total})`)),
    total === 0 ? emptyState(`Kein Handlungsbedarf. Letzter Import: ${lastImport}.`) : null,
    actionGroup("Blockierend", "blocking", "alert", actions.blocking),
    actionGroup("Offen", "open", "circle", actions.open));

  const incoming = h("section", { class: "panel" },
    h("h2", null, "Neu eingegangen", h("span", { class: "count" }, `(${actions.new.length})`)),
    emptyState("Hier erscheinen neue Meldungen aus den beiden Formularen, sobald der Import läuft (Phase 1)."));

  const counts = state.counts || {};
  const deadline = state.deadline || {};
  const guideline = (state.labels || {}).guideline || "Richtlinie";
  const side = h("aside", { class: "stack" },
    h("section", { class: "panel" },
      h("h2", null, "Bestand"),
      h("dl", { class: "stat-list" },
        stat("Eingang", counts.eingang), stat("Umsetzung", counts.umsetzung),
        stat("Governance", counts.governance), stat("Betrieb", counts.betrieb),
        stat("Offene Tickets", counts.tickets_open))),
    h("section", { class: "panel" },
      h("h2", null, `Stichtag ${guideline}`),
      h("p", { class: deadline.date ? null : "muted" },
        deadline.date
          ? `${formatDate(deadline.date)} (Vorlauf ${deadline.lead_days} Tage)`
          : `Nicht festgelegt. Vorlauf: ${deadline.lead_days} Tage. Das Datum steht in standort.json.`)));

  view.append(
    pageHead("Start"),
    h("div", { class: "cols" }, h("div", { class: "stack" }, work, incoming), side));
}
