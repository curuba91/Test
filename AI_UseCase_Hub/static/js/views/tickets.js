// Tickets (Konzept 9.5): Board mit vier Spalten, Erledigte als Tabelle, Ticket als Seitenleiste.
// Adressen: #/tickets, #/tickets/<ID>.

import { api } from "../api.js";
import { h, icon, emptyState, pageHead, formatDate, formatTs, table, status } from "../dom.js";
import { field, flashSaved, keepFocus } from "../fields.js";

const BOARD = ["Neu", "In Analyse", "In Umsetzung", "Gelöst"];
const DONE = ["Geschlossen", "Abgelehnt"];
const SEVERITY = { hoch: ["bad", "alert"], mittel: ["open", "circle"], niedrig: ["none", "dash"] };
const memory = { usecase: "", severity: "", assignee: "", done: false };
let notice = null; // Bestätigung der automatischen Buchung (S9) mit „Rückgängig“

function severity(value) {
  return value ? status(...SEVERITY[value], `Schwere ${value}`) : h("span", { class: "muted" }, "Schwere offen");
}

export async function renderTickets(view, rest, app) {
  const readOnly = app.state.mode === "nur-lesen";
  const data = await api("GET", "/api/tickets");
  let tickets = data.items;
  const statusOptions = data.lists.ticket_status.map((e) => ({ key: e.key, label: e.label }));
  const root = h("div", { class: "stack" });
  const toast = h("div", { role: "status" });
  const board = h("div");
  const side = h("div");
  view.append(root);

  function showNotice() {
    if (!notice) { toast.replaceChildren(); return; }
    const { booking } = notice;
    const text = booking.booked
      ? `Automatisch gebucht: Version ${booking.version} aus ${booking.ticket_id} in die Updatehistorie von ${booking.usecase_id}`
        + (booking.version_raised ? `, Version von ${booking.old_version || "(leer)"} auf ${booking.version} angehoben.` : ".")
      : booking.hint;
    toast.replaceChildren(h("p", { class: `field-note ${booking.booked ? "ok" : "warn"}` }, icon(booking.booked ? "check" : "alert"),
      h("span", null, text, booking.booked && booking.hint ? ` ${booking.hint}` : ""),
      booking.booked ? h("button", { class: "btn", type: "button", onclick: async () => {
        notice = null;
        await api("POST", `/api/tickets/${encodeURIComponent(booking.ticket_id)}/undo-booking`, { old_version: booking.old_version });
        window.dispatchEvent(new Event("hashchange"));
      } }, "Rückgängig") : null));
  }

  async function patch(id, name, value, expected) {
    const body = { field: name, value };
    if (expected !== undefined) body.expected = expected;
    const result = await api("PATCH", `/api/tickets/${encodeURIComponent(id)}`, body);
    notice = result.booking ? { booking: result.booking } : (name === "status" ? null : notice);
    tickets = (await api("GET", "/api/tickets")).items;
    app.refreshState();
    return result;
  }

  async function move(id, value) {
    try {
      await patch(id, "status", value);
    } catch (error) {
      notice = null;
      toast.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
      return;
    }
    drawBoard();
    showNotice();
    if (rest[0] === id) drawSide(await api("GET", `/api/tickets/${encodeURIComponent(id)}`));
  }

  function distinct(get) {
    return [...new Set(tickets.map(get).filter(Boolean))].sort((a, b) => a.localeCompare(b, "de", { numeric: true }));
  }

  function filterSelect(label, all, values, name) {
    if (memory[name] && !values.includes(memory[name])) memory[name] = "";
    const el = h("select", { "aria-label": label, onchange: () => { memory[name] = el.value; drawBoard(); } },
      h("option", { value: "" }, all), values.map((v) => h("option", { value: v, selected: v === memory[name] }, v)));
    return el;
  }

  function card(t) {
    const select = h("select", { "aria-label": `Status von ${t.id}`, disabled: readOnly, onchange: () => move(t.id, select.value) },
      statusOptions.map((o) => h("option", { value: o.key, selected: o.key === t.status }, o.label)));
    const el = h("article", { class: "card", draggable: readOnly ? null : "true", "aria-current": rest[0] === t.id ? "true" : null },
      h("div", { class: "card-head" }, h("a", { href: `#/tickets/${encodeURIComponent(t.id)}` }, t.id), severity(t.severity)),
      h("p", { class: "card-title" }, t.title || "(ohne Titel)"),
      h("p", { class: "muted" }, t.usecase_id ? `${t.usecase_id} · ${t.usecase_title}` : "kein Use Case zugeordnet"),
      h("p", { class: "muted" }, `${t.age_days} ${t.age_days === 1 ? "Tag" : "Tage"} alt · ${t.assignee || "niemand zuständig"}`),
      select);
    el.addEventListener("dragstart", (event) => { event.dataTransfer.setData("text/plain", t.id); event.dataTransfer.effectAllowed = "move"; });
    el.addEventListener("click", (event) => { if (!event.target.closest("a, select")) location.hash = `#/tickets/${encodeURIComponent(t.id)}`; });
    return el;
  }

  function drawBoard() {
    const shown = tickets.filter((t) => (!memory.usecase || t.usecase_id === memory.usecase)
      && (!memory.severity || t.severity === memory.severity) && (!memory.assignee || t.assignee === memory.assignee));
    const done = h("input", { type: "checkbox", id: "show-done", checked: memory.done, onchange: () => { memory.done = done.checked; drawBoard(); } });
    const columns = BOARD.map((name) => {
      const own = shown.filter((t) => t.status === name);
      const column = h("section", { class: "column", "aria-label": name },
        h("h2", null, name, h("span", { class: "count" }, `(${own.length})`)),
        own.length ? own.map(card) : h("p", { class: "muted column-empty" }, "leer"));
      column.addEventListener("dragover", (event) => { event.preventDefault(); column.classList.add("drop"); });
      column.addEventListener("dragleave", () => column.classList.remove("drop"));
      column.addEventListener("drop", (event) => {
        event.preventDefault();
        column.classList.remove("drop");
        const id = event.dataTransfer.getData("text/plain");
        const ticket = tickets.find((t) => t.id === id);
        if (ticket && ticket.status !== name) move(id, name);
      });
      return column;
    });
    const closed = shown.filter((t) => DONE.includes(t.status));
    board.replaceChildren(
      h("section", { class: "panel" },
        h("div", { class: "toolbar" },
          filterSelect("Use Case", "Alle Use Cases", distinct((t) => t.usecase_id), "usecase"),
          filterSelect("Schwere", "Jede Schwere", distinct((t) => t.severity), "severity"),
          filterSelect("Zuständig", "Alle Zuständigen", distinct((t) => t.assignee), "assignee"),
          h("span", { class: "checkline" }, done, h("label", { for: "show-done" }, `Erledigte anzeigen (${closed.length})`))),
        tickets.length ? h("div", { class: "board" }, columns)
          : emptyState("Noch keine Tickets. Sie kommen über das Formular „Problem mit AI-Tool melden“ (Quelle 2) oder über „Neu“ in der Kopfzeile.")),
      memory.done ? h("section", { class: "panel" },
        h("h2", null, "Erledigt", h("span", { class: "count" }, `(${closed.length})`)),
        closed.length ? table([
          { label: "ID", value: (t) => h("a", { href: `#/tickets/${encodeURIComponent(t.id)}` }, t.id) },
          { label: "Titel", value: (t) => t.title },
          { label: "Use Case", value: (t) => t.usecase_id || "–" },
          { label: "Status", value: (t) => t.status },
          { label: "Geschlossen am", value: (t) => formatDate(t.closed_at) || "–" },
          { label: "Fix-Version", value: (t) => t.fix_version || "–" },
        ], closed) : emptyState("Keine geschlossenen oder abgelehnten Tickets.")) : null);
  }

  function drawSide(detail) {
    const t = detail.ticket;
    const save = (name) => async (value, expected) => {
      try {
        const result = await patch(t.id, name, value, expected);
        keepFocus(side, () => drawSide(result));
        flashSaved(side, name);
        drawBoard();
        showNotice();
      } catch (error) {
        if (error.code === "stale") drawSide(await api("GET", `/api/tickets/${encodeURIComponent(t.id)}`));
        throw error;
      }
    };
    const f = (name, label, extra) => field({
      key: name, label, kind: "text", value: t[name], disabled: readOnly, save: save(name), wide: true,
      warn: detail.differs.includes(name) ? `Weicht von der Meldung ab. In der Meldung: „${detail.src[name]}“` : null, ...extra,
    });
    const usecases = usecaseOptions || [];
    side.replaceChildren(h("aside", { class: "side", "aria-label": `Ticket ${t.id}` },
      h("div", { class: "page-head" },
        h("h2", null, `${t.id}`), h("a", { class: "btn", href: "#/tickets" }, icon("x"), "Schließen")),
      h("p", { class: "muted" }, `${t.age_days} ${t.age_days === 1 ? "Tag" : "Tage"} alt · gemeldet am ${formatDate(t.submitted_at || t.created_at)}${t.reporter ? ` von ${t.reporter}` : ""}`),
      h("div", { class: "form-grid one" },
        f("title", "Titel"),
        f("description", "Beschreibung", { kind: "textarea" }),
        f("affected_tool_raw", "Betroffenes Tool (laut Meldung)"),
        f("usecase_id", "Use Case", { kind: "select", options: [{ key: "", label: "– nicht zugeordnet –" },
          ...usecases.map((u) => ({ key: u.id, label: `${u.id} – ${u.title}` }))] }),
        f("status", "Status", { kind: "select", options: statusOptions }),
        f("type", "Typ", { suggestions: "list-ticket-type" }),
        f("severity", "Schwere", { kind: "select", options: [{ key: "", label: "– offen –" },
          ...data.lists.ticket_severity.map((e) => ({ key: e.key, label: e.label }))] }),
        f("assignee", "Zuständig"),
        f("fix_version", "Fix-Version", { hint: "Format Haupt.Neben[.Patch]. Wird beim ersten Wechsel auf Gelöst oder Geschlossen in die Updatehistorie gebucht." }),
        f("cause", "Ursache", { kind: "textarea", rows: 3 }),
        f("solution", "Lösung", { kind: "textarea", rows: 3 })),
      h("datalist", { id: "list-ticket-type" }, data.lists.ticket_type.map((v) => h("option", { value: v }))),
      h("h2", null, "Verlauf"),
      h("ul", { class: "history" }, detail.history.map((r) => h("li", null,
        h("span", { class: "muted" }, `${formatTs(r.ts)} · ${r.user || r.source}`),
        h("span", null, `${r.field_label}: ${r.old_value || "(leer)"} → ${r.new_value || "(leer)"}`))))));
  }

  let usecaseOptions = null;
  drawBoard();
  showNotice();
  root.append(pageHead("Tickets"), toast, h("div", { class: rest[0] ? "with-side" : null }, board, side));
  if (rest[0]) {
    usecaseOptions = (await api("GET", "/api/usecases")).items.map((u) => ({ id: u.id, title: u.title }));
    drawSide(await api("GET", `/api/tickets/${encodeURIComponent(rest[0])}`));
  }
}
