// Tickets: Board und Seitenleiste folgen in Phase 3.

import { h, emptyState, pageHead } from "../dom.js";

export async function renderTickets(view) {
  view.append(
    pageHead("Tickets"),
    h("section", { class: "panel" },
      emptyState("Hier stehen Meldungen zu produktiven Lösungen als Board. Tickets kommen aus Quelle 2 oder werden manuell angelegt; das Board wird in Phase 3 gebaut.")));
}
