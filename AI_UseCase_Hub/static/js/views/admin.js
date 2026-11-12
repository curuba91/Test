// Verwaltung mit sechs Unterseiten (Konzept 9.6). In Phase 0 sind die
// Einstellungen (Ersteinrichtung der Pfade) funktionsfähig.

import { api } from "../api.js";
import { h, icon, emptyState, pageHead } from "../dom.js";
import { renderSources } from "./admin_sources.js";
import { renderConflicts } from "./admin_conflicts.js";
import { renderLog } from "./admin_log.js";

const BUILT = { quellen: renderSources, konflikte: renderConflicts, protokoll: renderLog };

const PAGES = [
  ["quellen", "Quellen & Import", ""],
  ["konflikte", "Konflikte", ""],
  ["protokoll", "Protokoll", ""],
  ["export", "Export & Bericht", "Hier entstehen Reporting-Excel, Druckansicht und die Auswahlliste für das Ticket-Formular (Phase 5)."],
  ["uebergabe", "Übergabe & Backups", "Hier stehen Übergabestand, Sperre und die Backups zum Wiederherstellen (Phase 5)."],
  ["einstellungen", "Einstellungen", ""],
];

export async function renderAdmin(view, rest, app) {
  const current = PAGES.find((page) => page[0] === rest[0]);
  if (!current) {
    location.replace("#/verwaltung/einstellungen");
    return;
  }
  view.append(
    pageHead("Verwaltung"),
    h("nav", { class: "subnav", "aria-label": "Verwaltung" }, PAGES.map(([key, label]) =>
      h("a", { href: `#/verwaltung/${key}`, "aria-current": key === current[0] ? "page" : null }, label))));
  if (current[0] === "einstellungen" || BUILT[current[0]]) {
    const box = h("div", { class: "stack" });
    view.append(box);
    await (BUILT[current[0]] || renderSettings)(box, app);
  } else {
    view.append(h("section", { class: "panel" }, h("h2", null, current[1]), emptyState(current[2])));
  }
}

async function renderSettings(box, app) {
  let settings = await api("GET", "/api/settings");
  const readOnly = app.state.mode === "nur-lesen";
  draw();

  function draw(focusKey) {
    box.replaceChildren(
      settings.configured ? null : h("section", { class: "panel" },
        h("h2", null, "Ersteinrichtung"),
        h("p", null, "Drei Pfade angeben: die beiden Quell-Excels und den Team-Ordner. Pfade werden relativ zum Programmordner gespeichert und gelten damit auf jedem Rechner, auf dem der Team-Ordner synchronisiert ist. Die Datenbank bleibt immer lokal.")),
      h("section", { class: "panel" },
        h("h2", null, "Pfade"),
        h("dl", { class: "kv" },
          h("dt", null, "Programmordner"), h("dd", null, settings.program_dir),
          h("dt", null, "Lokaler Datenordner"), h("dd", null, settings.data_dir)),
        Object.entries(settings.paths).map(([key, info]) => pathField(key, info)),
        publishRow()),
      h("section", { class: "panel" }, h("h2", null, "Betrieb"),
        numberField("auto", "auto_shutdown_minutes", "Automatisch beenden nach", "Minuten", 0, 240,
          "Minuten ohne offenen Browser-Tab, nach denen sich der Hub selbst beendet. 0 schaltet das ab."),
        numberField("interval", "import_interval_seconds", "Quellen prüfen alle", "Sekunden", 5, 3600,
          "Abstand, in dem der Hub prüft, ob sich eine Quell-Excel geändert hat."),
        testModeField()),
      siteSection());
    if (focusKey) {
      const target = box.querySelector(`[data-focus="${focusKey}"]`);
      if (target) target.focus();
    }
  }

  async function save(body, note, input, focusKey) {
    try {
      settings = await api("PUT", "/api/settings", body);
    } catch (error) {
      const text = Object.values(error.fields || {})[0] || error.message;
      note.className = "field-note bad";
      note.replaceChildren(icon("alert"), h("span", null, `Nicht gespeichert: ${text}`));
      input.setAttribute("aria-invalid", "true");
      return;
    }
    await app.refreshState();
    draw(focusKey);
    const saved = box.querySelector(`[data-saved="${focusKey}"]`);
    if (saved) {
      saved.replaceChildren(icon("check"), "Gespeichert");
      setTimeout(() => saved.replaceChildren(), 2500);
    }
  }

  function pathField(key, info) {
    const id = `path-${key}`;
    const note = h("p", { class: "field-note", id: `${id}-note`, role: "status" });
    if (!info.stored) {
      note.append(icon("circle"), h("span", null, "Noch nicht angegeben."));
    } else if (info.error) {
      note.className = "field-note bad";
      note.append(icon("alert"), h("span", null, info.error));
    } else {
      note.className = "field-note ok";
      note.append(icon("check"), h("span", null, `Gefunden: ${info.resolved}`));
    }
    const input = h("input", {
      type: "text", id, value: info.stored, disabled: readOnly, spellcheck: "false", autocomplete: "off",
      "data-focus": key, "aria-describedby": `${id}-note`,
      placeholder: info.kind === "file" ? "z. B. ../Quellen/Datei.xlsx" : "z. B. ..",
      onchange: () => save({ paths: { [key]: input.value } }, note, input, key),
    });
    const browser = h("div", { hidden: true });
    const toggle = h("button", {
      class: "btn", type: "button", disabled: readOnly, "aria-expanded": "false",
      onclick: () => {
        const open = browser.hidden;
        browser.hidden = !open;
        toggle.setAttribute("aria-expanded", String(open));
        if (open) browse(browser, info.kind, input.value, (stored) => {
          input.value = stored;
          save({ paths: { [key]: stored } }, note, input, key);
        });
      },
    }, icon("folder"), "Durchsuchen");
    return h("div", { class: "field" },
      h("label", { for: id }, info.label),
      h("div", { class: "field-row" }, input, toggle, h("span", { class: "saved", "data-saved": key, role: "status" })),
      note, browser);
  }

  async function browse(container, kind, start, choose) {
    let listing;
    try {
      listing = await api("POST", "/api/fs/list", { path: start });
    } catch (error) {
      container.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
      return;
    }
    const go = (path) => browse(container, kind, path, choose);
    const rows = [];
    if (listing.parent) {
      rows.push(h("li", null, h("button", { type: "button", onclick: () => go(listing.parent) },
        icon("up"), "Übergeordneter Ordner")));
    }
    for (const dir of listing.dirs) {
      rows.push(h("li", null, h("button", { type: "button", onclick: () => go(dir.path) }, icon("folder"), dir.name)));
    }
    if (kind === "file") {
      for (const file of listing.files) {
        rows.push(h("li", null, h("button", { type: "button", onclick: () => choose(file.stored) },
          icon("file"), file.name)));
      }
    }
    const hasContent = listing.dirs.length || (kind === "file" && listing.files.length);
    container.replaceChildren(h("div", { class: "browser" },
      h("div", { class: "browser-head" },
        h("span", { class: "browser-path" }, listing.path),
        kind === "dir"
          ? h("button", { class: "btn", type: "button", onclick: () => choose(listing.stored) }, "Diesen Ordner wählen")
          : null),
      h("ul", { class: "browser-list" }, rows,
        hasContent ? null : h("li", null, emptyState(kind === "file"
          ? "Keine Unterordner und keine .xlsx-Dateien in diesem Ordner."
          : "Keine Unterordner in diesem Ordner.")),
        listing.note ? h("li", null, h("p", { class: "field-note bad" }, listing.note)) : null)));
    const first = container.querySelector("button");
    if (first) first.focus();
  }

  function publishRow() {
    if (!settings.configured) return null;
    const note = h("p", { class: "field-note", role: "status" });
    if (settings.defaults_published) {
      note.className = "field-note ok";
      note.append(icon("check"), h("span", null, "Diese Pfade sind als Vorgabe für die Vertretung hinterlegt."));
      return note;
    }
    if (!settings.can_publish_defaults) {
      note.append(icon("dash"), h("span", null, "Als Vorgabe für die Vertretung lassen sich nur relative Pfade bei fehlerfreier standort.json hinterlegen."));
      return note;
    }
    const button = h("button", {
      class: "btn", type: "button", disabled: readOnly,
      onclick: async () => {
        try {
          settings = await api("POST", "/api/settings/publish-paths");
          draw();
        } catch (error) {
          note.className = "field-note bad";
          note.replaceChildren(icon("alert"), h("span", null, error.message));
        }
      },
    }, "Als Vorgabe für die Vertretung hinterlegen");
    note.append(h("span", null, "Schreibt die drei relativen Pfade in standort.json; die Vertretung muss dann nichts einrichten."));
    return h("div", { class: "field" }, h("div", { class: "field-row" }, button), note);
  }

  function numberField(focusKey, name, label, unit, min, max, hint) {
    const id = `setting-${name}`;
    const note = h("p", { class: "field-note", id: `${id}-note`, role: "status" }, h("span", null, hint));
    const input = h("input", {
      type: "number", id, min: String(min), max: String(max), step: "1", value: String(settings[name]),
      disabled: readOnly, "data-focus": focusKey, "aria-describedby": `${id}-note`,
      onchange: () => save({ [name]: Number(input.value) }, note, input, focusKey),
    });
    return h("div", { class: "field" },
      h("label", { for: id }, label),
      h("div", { class: "field-row" }, input, h("span", null, unit),
        h("span", { class: "saved", "data-saved": focusKey, role: "status" })),
      note);
  }

  function testModeField() {
    const id = "setting-test-mode";
    const note = h("p", { class: "field-note", id: `${id}-note`, role: "status" },
      h("span", null, `Arbeitet auf einer eigenen Datenbank mit erfundenen Beispieldaten unter ${settings.test_dir}. Die echte Datenbank und die echten Quellen werden im Testmodus nicht geöffnet.`));
    const input = h("input", {
      type: "checkbox", id, checked: settings.test_mode, "data-focus": "test", "aria-describedby": `${id}-note`,
      onchange: () => save({ test_mode: input.checked }, note, input, "test"),
    });
    return h("div", { class: "field" },
      h("div", { class: "checkline" }, input, h("label", { for: id }, "Testmodus"),
        h("span", { class: "saved", "data-saved": "test", role: "status" })),
      note);
  }

  function siteSection() {
    const site = settings.site;
    const rows = [
      ...site.errors.map((text) => h("li", null,
        h("span", { class: "check-error" }, icon("alert", "Fehler")), h("span", null, `Fehler: ${text}`))),
      ...site.open.map((text) => h("li", null,
        h("span", { class: "check-open" }, icon("circle", "Offen")), h("span", null, `Offen: ${text}`))),
    ];
    return h("section", { class: "panel" },
      h("h2", null, "Standortkonfiguration",
        h("span", { class: "count" }, `(${site.errors.length} Fehler, ${site.open.length} offen)`)),
      h("p", { class: "muted" }, "Wertelisten, Spaltenzuordnung, Stichtag und Bezeichnungen stehen in ",
        h("code", null, "standort.json"), " im Programmordner. Wie die Datei angepasst wird, beschreibt ",
        h("code", null, "ANPASSUNG.md"), ". Die Bearbeitung in dieser Oberfläche folgt in Phase 5."),
      rows.length ? h("ul", { class: "check-list" }, rows)
        : emptyState("Die Standortkonfiguration ist vollständig und fehlerfrei."));
  }
}
