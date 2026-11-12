// Use Cases: Liste und Detailseite folgen in Phase 2.

import { h, emptyState, pageHead } from "../dom.js";

export async function renderUsecases(view) {
  view.append(
    pageHead("Use Cases"),
    h("section", { class: "panel" },
      emptyState("Hier stehen alle Use Cases von der Meldung bis zum Betrieb. Die Liste füllt sich mit dem ersten Import aus Quelle 1; Liste und Detailseite werden in Phase 2 gebaut.")));
}
