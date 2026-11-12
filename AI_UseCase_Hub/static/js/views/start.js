// Start: in zehn Sekunden wissen, was heute zu tun ist (Konzept 9.2).

import { api } from "../api.js";
import { h, icon, emptyState, pageHead, formatDate, formatTs } from "../dom.js";

const SHOWN_OPEN = 8;

function actionGroup(title, level, symbol, items, limit) {
  if (!items.length) return null;
  const list = h("ul", { class: "action-list" });
  const more = h("div");
  const draw = (count) => {
    list.replaceChildren(...items.slice(0, count).map((item) =>
      h("li", null, h("a", { href: item.target },
        h("span", { class: `level-${level}` }, icon(symbol)),
        h("span", { class: "action-subject" }, item.subject),
        h("span", { class: "action-text" }, item.text, item.title ? h("span", { class: "muted" }, ` · ${item.title}`) : null),
        icon("arrow")))));
    more.replaceChildren(items.length > count
      ? h("button", { class: "btn", type: "button", onclick: () => draw(items.length) }, `Alle ${items.length} anzeigen`) : "");
  };
  draw(limit || items.length);
  return h("section", { class: "stack-tight" },
    h("h3", { class: `group-title level-${level}` }, icon(symbol), `${title} (${items.length})`), list, more);
}

function stat(label, value, target) {
  const shown = value === null || value === undefined ? "–" : value;
  return h("div", null, h("dt", null, label), h("dd", null, target ? h("a", { href: target }, shown) : shown));
}

export async function renderStart(view, _rest, app) {
  const actions = await api("GET", "/api/actions");
  const state = app.state;
  const total = actions.blocking.length + actions.open.length;
  const lastImport = formatTs(state.last_import) || "noch keiner";

  const work = h("section", { class: "panel" },
    h("h2", null, "Handlungsbedarf", h("span", { class: "count" }, `(${total})`)),
    total === 0 ? emptyState(`Kein Handlungsbedarf. Letzter Import: ${lastImport}.`) : null,
    actionGroup("Blockierend", "blocking", "alert", actions.blocking),
    actionGroup("Offen", "open", "circle", actions.open, SHOWN_OPEN));

  const fresh = actions.new;
  const incoming = h("section", { class: "panel" },
    h("h2", null, "Neu eingegangen", h("span", { class: "count" }, `(${fresh.total})`)),
    fresh.items.length
      ? h("ul", { class: "new-list" }, fresh.items.map((item) =>
          h("li", null, h("a", { href: item.target },
            h("span", { class: "action-subject" }, item.id),
            h("span", { class: "action-text" }, item.title || "(ohne Titel)"),
            h("span", { class: "chip" }, item.action),
            icon("arrow")))))
      : emptyState("Keine neuen Meldungen. Hier erscheinen unbewertete Use Cases und neue Tickets aus den beiden Formularen."),
    fresh.total > fresh.items.length
      ? h("p", { class: "muted" }, `Angezeigt werden die ${fresh.items.length} neuesten von ${fresh.total}.`) : null);

  const counts = state.counts || {};
  const deadline = state.deadline || {};
  const guideline = (state.labels || {}).guideline || "Richtlinie";
  const side = h("aside", { class: "stack" },
    h("section", { class: "panel" },
      h("h2", null, "Bestand"),
      h("dl", { class: "stat-list" },
        stat("Eingang", counts.eingang, "#/usecases/stufe/eingang"),
        stat("Umsetzung", counts.umsetzung, "#/usecases/stufe/umsetzung"),
        stat("Governance", counts.governance, "#/usecases/stufe/governance"),
        stat("Betrieb", counts.betrieb, "#/usecases/stufe/betrieb"),
        stat("Offene Tickets", counts.tickets_open, "#/tickets"))),
    h("section", { class: "panel" },
      h("h2", null, `Stichtag ${guideline}`),
      h("p", { class: deadline.date ? null : "muted" },
        deadline.date
          ? `${formatDate(deadline.date)} (Vorlauf ${deadline.lead_days} Tage)`
          : `Nicht festgelegt. Vorlauf: ${deadline.lead_days} Tage. Das Datum steht in standort.json.`),
      counts.reg_total === undefined ? null : h("p", null,
        h("a", { href: "#/usecases/stufe/governance" }, `${counts.reg_confirmed} von ${counts.reg_total}`),
        " abgeschlossenen Lösungen eingeordnet")));

  view.append(
    pageHead("Start"),
    h("div", { class: "cols" }, h("div", { class: "stack" }, work, incoming), side));
}
