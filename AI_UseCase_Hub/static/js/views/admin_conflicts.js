// Verwaltung → Konflikte: Gegenüberstellung alt/neu/Hub, Entscheidung per Klick (Regel S5).

import { api } from "../api.js";
import { h, icon, emptyState, formatTs, table } from "../dom.js";

export async function renderConflicts(box, app) {
  let data = await api("GET", "/api/conflicts");
  const readOnly = app.state.mode === "nur-lesen";
  const note = h("div", { role: "status" });
  draw();

  function value(text) {
    return text === "" ? h("span", { class: "muted" }, "(leer)") : text;
  }

  function draw() {
    box.replaceChildren(
      h("section", { class: "panel" },
        h("h2", null, "Offene Konflikte", h("span", { class: "count" }, `(${data.open.length})`)),
        note,
        data.open.length ? data.open.map((c) =>
          h("article", { class: "conflict" },
            h("h3", null, `${c.entity_id} · ${c.entity_label} · Feld ${c.field_label}`),
            h("dl", { class: "conflict-values" },
              h("div", null, h("dt", null, "Bisher in der Quelle"), h("dd", null, value(c.old_src_value))),
              h("div", { class: "changed" }, h("dt", null, "Neu in der Quelle"), h("dd", null, value(c.new_src_value))),
              h("div", { class: "changed" }, h("dt", null, "Im Hub geändert"), h("dd", null, value(c.hub_value)))),
            h("div", { class: "toolbar" },
              h("button", { class: "btn", type: "button", disabled: readOnly, onclick: () => resolve(c, "quelle") },
                "Quelle übernehmen"),
              h("button", { class: "btn", type: "button", disabled: readOnly, onclick: () => resolve(c, "hub") },
                "Hub-Wert behalten"),
              h("span", { class: "muted" }, `erkannt am ${formatTs(c.created_at)}`))))
          : emptyState("Keine offenen Konflikte. Ein Konflikt entsteht, wenn ein Feld im Hub geändert wurde und sich danach auch in der Quelle ändert.")),
      h("section", { class: "panel" },
        h("h2", null, "Zuletzt entschieden"),
        data.decided.length ? table([
          { label: "Entschieden am", value: (c) => formatTs(c.resolved_at) },
          { label: "Datensatz", value: (c) => c.entity_id },
          { label: "Feld", value: (c) => c.field_label },
          { label: "Entscheidung", value: (c) => c.resolution },
        ], data.decided) : emptyState("Noch keine Entscheidungen. Der vorherige Wert bleibt in jedem Fall im Protokoll nachlesbar.")));
  }

  async function resolve(conflict, choice) {
    try {
      const result = await api("POST", `/api/conflicts/${conflict.id}/resolve`, { choice });
      note.replaceChildren(h("p", { class: "field-note ok" }, icon("check"),
        h("span", null, `${conflict.entity_id}, Feld ${conflict.field_label}: ${result.resolution}.`)));
    } catch (error) {
      note.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
    }
    data = await api("GET", "/api/conflicts");
    await app.refreshState();
    draw();
  }
}
