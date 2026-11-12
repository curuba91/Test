// Eingabefelder nach dem Gestaltungssystem (Konzept 9.7): kein „Speichern“-Knopf,
// gespeichert wird beim Verlassen des Feldes; Bestätigung und Fehler stehen am Feld.

import { h, icon } from "./dom.js";

function display(value, kind) {
  if (value === null || value === undefined) return "";
  if (kind === "number") return String(value).replace(".", ",");
  return String(value);
}

// o: key, label, kind (text|textarea|date|number|select|checkbox), value, options, suggestions,
//    disabled, hint, warn, placeholder, rows, save(value, expected) -> Promise
export function field(o) {
  const id = `fld-${o.key}`;
  const baseline = o.kind === "checkbox" ? Boolean(o.value) : display(o.value, o.kind);
  let saving = false;
  const note = h("p", { class: "field-note", id: `${id}-note`, role: "status" });
  const saved = h("span", { class: "saved", "data-saved": o.key, role: "status" });
  const common = { id, "data-key": o.key, disabled: o.disabled, "aria-describedby": `${id}-note` };
  let input;

  if (o.kind === "select") {
    const options = o.options.some((opt) => opt.key === baseline) ? o.options
      : [{ key: baseline, label: baseline === "" ? "– bitte wählen –" : baseline }, ...o.options];
    input = h("select", common, options.map((opt) => h("option", { value: opt.key, selected: opt.key === baseline }, opt.label)));
  } else if (o.kind === "textarea") {
    input = h("textarea", { ...common, rows: String(o.rows || 4), placeholder: o.placeholder });
    input.value = baseline;
  } else if (o.kind === "checkbox") {
    input = h("input", { ...common, type: "checkbox", checked: baseline });
  } else {
    input = h("input", {
      ...common, type: o.kind === "date" ? "date" : "text", inputmode: o.kind === "number" ? "decimal" : null,
      list: o.suggestions, placeholder: o.placeholder, autocomplete: "off", spellcheck: o.kind === "text" ? null : "false",
    });
    input.value = baseline;
  }

  function resetNote() {
    note.className = o.warn ? "field-note warn" : "field-note";
    note.replaceChildren(...(o.warn ? [icon("alert"), h("span", null, o.warn)] : o.hint ? [h("span", null, o.hint)] : []));
  }
  resetNote();

  async function commit() {
    const value = o.kind === "checkbox" ? input.checked : input.value;
    if (saving || value === baseline) return;
    saving = true;
    try {
      await o.save(o.kind === "checkbox" ? value : value.trim(), o.value);
    } catch (error) {
      input.setAttribute("aria-invalid", "true");
      note.className = "field-note bad";
      note.replaceChildren(icon("alert"), h("span", null, `Nicht gespeichert: ${error.message}`));
    } finally {
      saving = false;
    }
  }
  input.addEventListener("change", commit);
  input.addEventListener("blur", commit);
  input.addEventListener("input", () => {
    if (input.hasAttribute("aria-invalid")) {
      input.removeAttribute("aria-invalid");
      resetNote();
    }
  });

  if (o.kind === "checkbox") {
    return h("div", { class: `field ${o.wide ? "wide" : ""}` },
      h("div", { class: "checkline" }, input, h("label", { for: id }, o.label), saved), note);
  }
  return h("div", { class: `field ${o.wide ? "wide" : ""}` },
    h("label", { for: id }, o.label),
    h("div", { class: "field-row" }, input, o.after || null, saved),
    note);
}

// Kompaktes Eingabefeld für Tabellenzeilen (Meilensteine, Updatehistorie, Links).
export function cell(o) {
  const baseline = display(o.value, o.kind);
  let saving = false;
  const input = h("input", {
    type: o.kind === "date" ? "date" : "text", "data-key": o.key, disabled: o.disabled, "aria-label": o.label,
    placeholder: o.placeholder, autocomplete: "off", class: o.invalid ? "overdue" : null,
  });
  input.value = baseline;
  async function commit() {
    if (saving || input.value === baseline || !o.save) return;
    saving = true;
    try {
      await o.save(input.value.trim(), o.value);
    } catch (error) {
      input.setAttribute("aria-invalid", "true");
      input.title = error.message;
      if (o.onError) o.onError(error);
    } finally {
      saving = false;
    }
  }
  input.addEventListener("change", commit);
  input.addEventListener("blur", commit);
  return input;
}

// Zeigt nach dem Neuaufbau „Gespeichert“ am Feld mit dem Schlüssel.
export function flashSaved(root, key) {
  const target = key && root.querySelector(`[data-saved="${CSS.escape(key)}"]`);
  if (!target) return;
  target.replaceChildren(icon("check"), "Gespeichert");
  setTimeout(() => target.replaceChildren(), 2500);
}

// Merkt sich das Feld mit Fokus (samt noch nicht gespeicherter Eingabe) und stellt es nach dem Neuaufbau wieder her.
export function keepFocus(root, rebuild) {
  const active = document.activeElement;
  const key = active && root.contains(active) ? active.getAttribute("data-key") : null;
  const pending = key && active.type !== "checkbox" ? { value: active.value, start: active.selectionStart } : null;
  rebuild();
  if (!key) return;
  const next = root.querySelector(`[data-key="${CSS.escape(key)}"]`);
  if (!next) return;
  if (pending && next.value !== pending.value && next.tagName !== "SELECT") {
    next.value = pending.value; // wird beim Verlassen des Feldes gespeichert
    try { next.setSelectionRange(pending.start, pending.start); } catch (error) { /* Datumsfelder */ }
  }
  next.focus();
}
