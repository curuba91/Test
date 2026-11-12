// Globale Suche über ID, Titel und Melder:in (Kopfzeile).

import { api } from "../api.js";
import { h, emptyState, pageHead, table } from "../dom.js";

export async function renderSearch(view, rest) {
  const q = rest.join("/");
  const data = await api("GET", `/api/search?q=${encodeURIComponent(q)}`);
  view.append(
    pageHead(`Suche: ${q}`, `${data.items.length} Treffer in Use Cases und Tickets`),
    h("section", { class: "panel" },
      data.items.length ? table([
        { label: "Art", value: (r) => r.kind },
        { label: "ID", value: (r) => h("a", { href: r.target }, r.id) },
        { label: "Titel", value: (r) => r.title },
        { label: "Stand", value: (r) => r.state },
      ], data.items) : emptyState("Kein Treffer. Gesucht wird in ID, Titel und Melder:in von Use Cases und Tickets.")));
}
