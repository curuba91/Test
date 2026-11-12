// Use Case – Detailseite (Konzept 9.4): Kopf mit genau einer Hauptaktion,
// Schrittleiste, offene Punkte und fünf Abschnitte. Alle Regeln kommen vom Server.

import { api } from "../api.js";
import { h, icon, emptyState, formatDate, formatTs, table, status } from "../dom.js";
import { field, cell, flashSaved, keepFocus } from "../fields.js";

const SECTIONS = [["ueberblick", "Überblick"], ["planung", "Planung"], ["governance", "Governance"],
  ["betrieb", "Betrieb"], ["verlauf", "Verlauf"]];
const DEFAULT_SECTION = { eingang: "ueberblick", umsetzung: "planung", governance: "governance", betrieb: "betrieb", archiv: "ueberblick" };
const STEP_STATE = {
  erfuellt: ["ok", "check", "erfüllt"], offen: ["open", "circle", "offen"],
  teil: ["open", "circle", "Teilstand"], entfaellt: ["none", "dash", "entfällt"],
};
const STAGE_TEXT = { erledigt: "erledigt", offen: "offen" };

let meta = null;
// Hinweis mit „Rückgängig“; bleibt stehen, wenn die Hauptaktion in den nächsten Abschnitt springt.
let carried = null;

export async function renderUsecase(view, id, section, app) {
  if (!meta) meta = await api("GET", "/api/meta");
  let detail = await api("GET", `/api/usecases/${encodeURIComponent(id)}`);
  if (!SECTIONS.some(([key]) => key === section)) {
    location.replace(`#/usecases/${encodeURIComponent(id)}/${DEFAULT_SECTION[detail.stepper.stage]}`);
    return;
  }
  const readOnly = app.state.mode === "nur-lesen";
  const base = `#/usecases/${encodeURIComponent(id)}`;
  const url = `/api/usecases/${encodeURIComponent(id)}`;
  const frame = h("div", { class: "stack" });
  const toast = h("div", { role: "status" });
  const body = h("div", { class: "stack" });
  let others = null; // andere Use Cases für „Zusammenführen mit …“
  const check = { open: false, rules: null, answers: {}, evaluation: null, lang: "de", error: "" }; // Vorabcheck
  const root = h("div", { class: "stack" }, frame, toast, body);
  view.append(root);

  // --- Daten ändern ---------------------------------------------------------------

  function apply(next, savedKey) {
    detail = next;
    carried = null;
    toast.replaceChildren();
    keepFocus(root, draw);
    flashSaved(root, savedKey);
    app.refreshState();
  }

  function showCarried() {
    if (!carried || carried.id !== id) {
      carried = null;
      return;
    }
    const { text, undo } = carried;
    toast.replaceChildren(h("p", { class: "field-note ok" }, icon("check"), h("span", null, text),
      undo ? h("button", { class: "btn", type: "button", onclick: async () => {
        carried = null;
        try {
          await undo();
        } catch (error) {
          fail(error);
          return;
        }
        window.dispatchEvent(new Event("hashchange")); // Seite mit dem wiederhergestellten Stand neu aufbauen
      } }, "Rückgängig") : null));
  }

  function notify(text, undo) {
    carried = { id, text, undo };
    showCarried();
  }

  function fail(error) {
    toast.replaceChildren(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, error.message)));
  }

  async function reloadAfterStale(error) {
    if (error.code === "stale") apply(await api("GET", url));
    throw error;
  }

  function saver(name) {
    return async (value, expected) => {
      try {
        apply(await api("PATCH", url, { field: name, value, expected }), name);
      } catch (error) {
        await reloadAfterStale(error);
      }
    };
  }

  async function setPhase(phase, mergedInto, message) {
    const before = { phase: detail.usecase.phase, merged: detail.usecase.merged_into };
    try {
      apply(await api("PATCH", url, { field: "phase", value: phase, merged_into: mergedInto, expected: before.phase }));
    } catch (error) {
      fail(error);
      return false;
    }
    notify(message, () => api("PATCH", url, { field: "phase", value: before.phase, merged_into: before.merged }));
    return true;
  }

  function f(name, extra) {
    const differs = detail.differs.includes(name);
    return field({
      key: name, label: meta.field_labels[name] || name, kind: "text", value: detail.usecase[name], disabled: readOnly,
      save: saver(name),
      warn: differs ? `Weicht von der Meldung ab. In der Meldung: ${detail.src[name] === "" ? "(leer)" : `„${detail.src[name]}“`}` : null,
      ...extra,
    });
  }

  function options(listName, allowEmpty) {
    const list = meta.lists[listName].map((entry) => ({ key: entry.key, label: entry.label }));
    return allowEmpty ? [{ key: "", label: "– bitte wählen –" }, ...list] : list;
  }

  // --- Rahmen: Kopf, Schrittleiste, offene Punkte, Abschnitte ------------------------

  function draw() {
    const uc = detail.usecase;
    const steps = detail.stepper;
    frame.replaceChildren(
      h("a", { class: "back", href: "#/usecases" }, "← Use Cases"),
      h("div", { class: "page-head" },
        h("div", null,
          h("h1", null, h("span", { class: "num muted" }, `${uc.id}  `), uc.title || "(ohne Titel)"),
          h("p", null, `Owner: ${uc.owner || "noch keiner"} · ${steps.stage_label}${uc.merged_into ? ` · zusammengeführt mit ${uc.merged_into}` : ""}`)),
        mainAction()),
      stepper(),
      openPoints(),
      h("nav", { class: "subnav", "aria-label": "Abschnitte" }, SECTIONS.map(([key, label]) =>
        h("a", { href: `${base}/${key}`, "aria-current": key === section ? "page" : null }, label))));
    body.replaceChildren(...[RENDER[section]()].flat());
  }

  function mainAction() {
    const next = detail.stepper.next;
    if (!next || readOnly) return null;
    let run = () => { location.hash = `${base}/${next.section}`; };
    if (next.key === "geplant" && detail.usecase.phase === "Eingang") {
      run = async () => { if (await setPhase("In Bearbeitung", null, "Umsetzung gestartet.")) location.hash = `${base}/planung`; };
    } else if (next.key === "umgesetzt") {
      run = async () => { if (await setPhase("Abgeschlossen", null, "Als umgesetzt markiert. Es folgt die Governance.")) location.hash = `${base}/governance`; };
    }
    return h("button", { class: "btn btn-primary", type: "button", onclick: run }, next.action, icon("arrow"));
  }

  function stepper() {
    const steps = detail.stepper;
    if (steps.stage === "archiv") {
      return h("section", { class: "panel" }, h("p", null, status("none", "dash", `Archiv: ${detail.usecase.phase}`),
        " – erzeugt keinen Handlungsbedarf. Wiederaufnahme im Abschnitt Überblick."));
    }
    return h("section", { class: "panel" },
      h("ol", { class: "stepper" }, steps.stages.map((stage, index) => {
        let text = STAGE_TEXT[stage.state] || "";
        if (stage.state === "aktiv") text = stage.total_steps ? `aktiv: ${stage.done_steps} von ${stage.total_steps}` : "aktiv";
        if (stage.state === "luecke") text = `${stage.open_steps} ${stage.open_steps === 1 ? "Schritt" : "Schritte"} offen`;
        const own = steps.steps.filter((s) => s.stage === stage.key);
        return h("li", { class: `stage stage-${stage.state}`, "aria-current": stage.state === "aktiv" ? "step" : null },
          h("div", { class: "stage-head" }, h("span", { class: "stage-no" }, stage.state === "erledigt" ? icon("check") : String(index + 1)),
            h("span", { class: "stage-label" }, stage.label)),
          h("p", { class: "stage-text" }, text),
          (stage.state === "aktiv" || stage.state === "luecke") && own.length
            ? h("ul", { class: "step-list" }, own.map((s) => h("li", null, status(...STEP_STATE[s.state].slice(0, 2), s.label),
                s.state === "erfuellt" ? null : h("span", { class: "muted" }, ` ${STEP_STATE[s.state][2]}`))))
            : null);
      })));
  }

  function openPoints() {
    if (detail.stepper.stage === "archiv") return null;
    return h("section", { class: "panel" },
      h("h2", null, "Offene Punkte", h("span", { class: "count" }, `(${detail.actions.length})`)),
      detail.actions.length ? h("ul", { class: "action-list" }, detail.actions.map((a) => {
        const blocking = a.level === "blockierend";
        return h("li", null, h("a", { href: a.target },
          h("span", { class: blocking ? "level-blocking" : "level-open" }, icon(blocking ? "alert" : "circle")),
          h("span", { class: "action-subject" }, blocking ? "Blockierend" : "Offen"),
          h("span", { class: "action-text" }, a.text), icon("arrow")));
      })) : emptyState("Keine offenen Punkte. Alle Schritte sind erfüllt oder entfallen."));
  }

  // --- Validierungs-Vorabcheck (Konzept 10) -------------------------------------------------

  async function preview() {
    try {
      check.evaluation = await api("POST", "/api/validation/preview", { answers: check.answers });
      check.answers = check.evaluation.answers;
      check.error = "";
    } catch (error) {
      check.error = error.message;
    }
    keepFocus(root, draw);
  }

  async function openCheck() {
    try {
      check.rules = await api("GET", "/api/validation");
    } catch (error) {
      check.error = error.message;
      draw();
      return;
    }
    check.answers = detail.validations.length ? { ...detail.validations[0].answers } : {};
    check.open = true;
    await preview();
  }

  function incompleteNote(parts) {
    return parts.length ? h("p", { class: "field-note bad" }, icon("alert"),
      h("span", null, `Regelwerk unvollständig (${parts.join(", ")} sind Platzhalter). Das Ergebnis ist nur eine Orientierung.`)) : null;
  }

  function precheck() {
    const last = detail.validations[0];
    const notice = "Der Check ersetzt keine Freigabe. Die verbindliche Entscheidung trifft die zuständige Qualitäts- bzw. Validierungsfunktion; das freigegebene Assessment liegt im kontrollierten Dokumentensystem, der Hub speichert nur den Verweis.";
    const parts = [h("p", { class: "field-note warn" }, icon("alert"), h("span", null, notice))];
    if (check.error) parts.push(h("p", { class: "field-note bad" }, icon("alert"), h("span", null, check.error)));
    if (last && !check.open) {
      const prompt = h("textarea", { rows: "8", readonly: true, "aria-label": "Prompt zum Kopieren", "data-key": "vc-prompt" });
      prompt.value = last.prompt_text;
      const copied = h("span", { class: "saved", role: "status" });
      parts.push(
        h("dl", { class: "kv" },
          h("dt", null, "Letzter Vorabcheck"), h("dd", null, `${formatTs(last.created_at)} durch ${last.created_by || "unbekannt"}, Regelwerk ${last.rules_version}`),
          h("dt", null, "Ergebnis"), h("dd", null, h("strong", null, last.label), ` – ${last.text}`),
          h("dt", null, "Gesamtrisiko"), h("dd", null, last.risk || "nicht ermittelt"),
          h("dt", null, "Kontrollen"), h("dd", null, last.controls.length ? h("ul", { class: "check-list" }, last.controls.map((c) => h("li", null, c))) : "keine ermittelt")),
        incompleteNote(last.incomplete_parts),
        h("div", { class: "field wide" },
          h("label", null, `Prompt (${last.prompt_lang === "en" ? "Englisch" : "Deutsch"}) – manuell im freigegebenen GenAI-Tool zusammen mit den Richtliniendokumenten ausführen`),
          prompt,
          h("div", { class: "toolbar" }, h("button", { class: "btn", type: "button", onclick: async () => {
            try {
              await navigator.clipboard.writeText(last.prompt_text);
            } catch (error) {
              prompt.select();
              document.execCommand("copy");
            }
            copied.replaceChildren(icon("check"), "Kopiert");
          } }, "Prompt kopieren"), copied)));
    }
    if (!check.open) {
      parts.push(h("div", { class: "toolbar" }, h("button", { class: "btn", type: "button", disabled: readOnly, onclick: openCheck },
        last ? "Vorabcheck wiederholen" : "Vorabcheck durchführen"),
        detail.validations.length > 1 ? h("span", { class: "muted" }, `${detail.validations.length} Durchläufe gespeichert, der neueste gilt.`) : null));
      return h("div", { class: "stack-tight wide" }, parts);
    }
    const unclear = check.rules.unclear;
    const visible = check.evaluation ? check.evaluation.visible : check.rules.questions.map((q) => q.key);
    for (const question of check.rules.questions.filter((q) => visible.includes(q.key))) {
      const current = check.answers[question.key];
      const choices = question.multiple ? question.options : [...question.options, unclear];
      parts.push(h("fieldset", { class: "question" },
        h("legend", null, `${question.nr}. ${question.text}`),
        choices.map((option) => {
          const id = `vc-${question.key}-${option.key}`;
          const input = h("input", {
            type: question.multiple ? "checkbox" : "radio", name: `vc-${question.key}`, id, "data-key": id,
            checked: question.multiple ? (current || []).includes(option.key) : current === option.key,
            onchange: () => {
              if (question.multiple) {
                const set = new Set(check.answers[question.key] || []);
                if (input.checked) set.add(option.key); else set.delete(option.key);
                check.answers[question.key] = [...set];
              } else {
                check.answers[question.key] = option.key;
              }
              preview();
            },
          });
          return h("span", { class: "checkline" }, input, h("label", { for: id }, option.label));
        })));
    }
    const lang = h("select", { "aria-label": "Sprache des Prompts", "data-key": "vc-lang", onchange: () => { check.lang = lang.value; } },
      h("option", { value: "de", selected: check.lang === "de" }, "Prompt auf Deutsch"),
      h("option", { value: "en", selected: check.lang === "en" }, "Prompt auf Englisch"));
    if (check.evaluation) {
      parts.push(h("div", { class: "result-box" },
        h("p", null, "Ergebnis nach den bisherigen Antworten: ", h("strong", null, check.evaluation.label)),
        h("p", { class: "muted" }, check.evaluation.text),
        incompleteNote(check.evaluation.incomplete_parts)));
    }
    parts.push(h("div", { class: "toolbar" }, lang,
      h("button", { class: "btn", type: "button", onclick: async () => {
        try {
          const next = await api("POST", `${url}/validations`, { answers: check.answers, lang: check.lang });
          check.open = false;
          apply(next);
        } catch (error) {
          fail(error);
        }
      } }, "Vorabcheck speichern"),
      h("button", { class: "btn btn-quiet", type: "button", onclick: () => { check.open = false; draw(); } }, "Abbrechen")));
    return h("div", { class: "stack-tight wide" }, parts);
  }

  // --- Unterlisten -----------------------------------------------------------------------

  function sublist(name, columns, addLabel, emptyText) {
    const rows = detail[name];
    const draft = {};
    const addRow = h("tr", null, columns.map((c) => h("td", null, (() => {
      const input = h("input", { type: c.kind === "date" ? "date" : "text", "aria-label": `${c.label} (neu)`, placeholder: c.label,
        "data-key": `${name}-new-${c.field}`, disabled: readOnly, autocomplete: "off" });
      input.addEventListener("input", () => { draft[c.field] = input.value; });
      input.addEventListener("keydown", (event) => { if (event.key === "Enter") add(); });
      return input;
    })())), h("td", null, h("button", { class: "btn", type: "button", disabled: readOnly, onclick: add }, icon("plus"), addLabel)));

    async function add() {
      try {
        apply(await api("POST", `${url}/${name}`, { values: draft }));
        const first = root.querySelector(`[data-key="${name}-new-${columns[0].field}"]`);
        if (first) first.focus();
      } catch (error) {
        fail(error);
      }
    }

    async function remove(row) {
      const values = Object.fromEntries(columns.map((c) => [c.field, row[c.field]]));
      try {
        apply(await api("DELETE", `/api/${name}/${row.id}`));
      } catch (error) {
        fail(error);
        return;
      }
      notify("Zeile gelöscht.", () => api("POST", `${url}/${name}`, { values }));
    }

    return h("div", { class: "table-wrap" },
      rows.length ? null : emptyState(emptyText),
      h("table", { class: "table edit-table" },
        h("thead", null, h("tr", null, columns.map((c) => h("th", { scope: "col" }, c.label)), h("th", { scope: "col" }, ""))),
        h("tbody", null,
          rows.map((row) => h("tr", { class: row.overdue ? "row-overdue" : null },
            columns.map((c) => h("td", null, cell({
              key: `${name}-${row.id}-${c.field}`, label: c.label, kind: c.kind, value: row[c.field], disabled: readOnly,
              onError: fail,
              save: async (value, expected) => {
                try {
                  apply(await api("PATCH", `/api/${name}/${row.id}`, { field: c.field, value, expected }));
                } catch (error) {
                  await reloadAfterStale(error);
                }
              },
            }))),
            h("td", { class: "nowrap" },
              row.overdue ? status("bad", "alert", "überfällig") : null,
              h("button", { class: "btn btn-quiet", type: "button", disabled: readOnly, "aria-label": "Zeile löschen",
                title: "Zeile löschen", onclick: () => remove(row) }, icon("x"))))),
          addRow)));
  }

  // --- Abschnitte --------------------------------------------------------------------------

  const RENDER = {
    ueberblick() {
      const uc = detail.usecase;
      const link = /^https?:\/\//i.test(uc.folder_link)
        ? h("a", { class: "btn", href: uc.folder_link, target: "_blank", rel: "noopener noreferrer" }, "Öffnen") : null;
      const scoreMode = meta.score.mode;
      return [
        h("section", { class: "panel" },
          h("h2", null, "Meldung"),
          h("div", { class: "form-grid" },
            f("title", { wide: true }),
            f("description", { kind: "textarea", wide: true }),
            f("benefit", { kind: "textarea", wide: true }),
            f("area", { suggestions: "list-area" }),
            f("reporter"),
            f("folder_link", { wide: true, after: link })),
          h("datalist", { id: "list-area" }, meta.lists.area.map((v) => h("option", { value: v }))),
          h("dl", { class: "kv" },
            h("dt", null, "Eingegangen am"), h("dd", null, formatDate(uc.submitted_at || uc.created_at)),
            h("dt", null, "Herkunft des Eintrags"),
            h("dd", null, detail.from_source ? (uc.in_source ? "aus dem Formular (Quelle 1)" : "aus dem Formular – in Quelle 1 nicht mehr vorhanden") : "manuell im Hub angelegt"),
            uc.reporter_email ? [h("dt", null, "E-Mail (nur intern)"), h("dd", null, uc.reporter_email)] : null,
            detail.merged_from.length ? [h("dt", null, "Hierher zusammengeführt"),
              h("dd", null, detail.merged_from.map((other, i) => [i ? ", " : "", h("a", { href: `#/usecases/${encodeURIComponent(other)}` }, other)]))] : null)),
        h("section", { class: "panel" },
          h("h2", null, "Bewertung"),
          h("div", { class: "form-grid" },
            f("owner"),
            f("type", { suggestions: "list-type" }),
            f("origin", { kind: "select", options: options("origin", true),
              hint: "Bei „übernommen“ entfallen Sponsor und Gremium." }),
            f("score", { kind: "number", disabled: readOnly || scoreMode === "gewichtet",
              hint: scoreMode === "gewichtet" ? "Wird aus den Einzelscores berechnet (gewichtet)." : "Gesamtscore, manuell eingegeben." })),
          h("datalist", { id: "list-type" }, meta.lists.usecase_type.map((v) => h("option", { value: v }))),
          meta.score.criteria.length ? h("div", { class: "form-grid five" }, meta.score.criteria.map((c) => field({
            key: `score-${c.key}`, label: c.label, kind: "number", value: detail.scores[c.key], disabled: readOnly,
            save: async (value) => { apply(await api("PUT", `${url}/scores`, { criterion: c.key, value }), `score-${c.key}`); },
          }))) : null),
        h("section", { class: "panel" },
          h("h2", null, "Links"),
          sublist("links", [{ field: "label", label: "Bezeichnung" }, { field: "url", label: "Adresse (https://…)" }],
            "Link hinzufügen", "Noch keine Links. Bezeichnung und Adresse in die Zeile unten eintragen.")),
        h("section", { class: "panel" },
          h("h2", null, "Notizen und Hilfe"),
          h("div", { class: "form-grid" },
            f("notes", { kind: "textarea", wide: true }),
            f("needs_help", { kind: "checkbox", hint: "Erscheint als blockierender Punkt auf der Startseite." }),
            f("help_note", { hint: "Wobei wird Hilfe gebraucht?" }))),
        phasePanel(),
      ];
    },

    planung() {
      return h("section", { class: "panel" },
        h("h2", null, "Meilensteine", h("span", { class: "count" }, `(${detail.milestones.length})`)),
        sublist("milestones", [{ field: "title", label: "Titel" }, { field: "planned_date", label: "geplant", kind: "date" },
          { field: "done_date", label: "erledigt am", kind: "date" }],
        "Meilenstein hinzufügen", "Noch keine Meilensteine. Titel und Plandatum in die Zeile unten eintragen."));
    },

    governance() {
      const uc = detail.usecase;
      const state = Object.fromEntries(detail.stepper.steps.map((s) => [s.key, s.state]));
      const adopted = uc.origin === "übernommen";
      const card = (key, title, hint, ...content) => h("section", { class: "panel step-card" },
        h("h2", null, title, status(...STEP_STATE[state[key]].slice(0, 2), STEP_STATE[state[key]][2])),
        hint ? h("p", { class: "muted" }, hint) : null, h("div", { class: "form-grid" }, content));
      const missing = [["lc_owner", "Life-Cycle-Owner"], ["version", "Version"], ["next_review", "nächstes Review"]]
        .filter(([name]) => !uc[name]).map(([, label]) => label);
      return [
        card("betriebsbereit", "1 · Betriebsbereit",
          missing.length ? `Es fehlen: ${missing.join(", ")}.` : "Life-Cycle-Owner, Version und nächstes Review sind gesetzt.",
          h("div", { class: "field wide" }, h("div", null, h("a", { class: "btn", href: `${base}/betrieb` }, "Zum Abschnitt Betrieb", icon("arrow"))))),
        card("eingeordnet", "2 · Eingeordnet",
          `Regulatorische Einordnung nach ${meta.labels.guideline || "der Richtlinie"}.`,
          precheck(),
          f("reg_status", { kind: "select", options: options("reg_status") }),
          f("reg_confirmed_at", { kind: "date" }),
          f("reg_result", { hint: "Zum Beispiel: Pfad A, Pfad B, außerhalb des Geltungsbereichs." }),
          f("reg_reference", { hint: "Dokumentnummer oder Link im kontrollierten Dokumentensystem." })),
        card("sponsor", `3 · ${meta.labels.sponsor || "Sponsor"}`,
          adopted ? "Entfällt, weil die Herkunft „übernommen“ ist." : null,
          f("sponsor_status", { kind: "select", options: options("sponsor_status") }),
          f("sponsor_date", { kind: "date" })),
        card("gremium", `4 · ${meta.labels.board || "Gremium"}`,
          adopted ? "Entfällt, weil die Herkunft „übernommen“ ist." : null,
          f("board_status", { kind: "select", options: options("board_status") }),
          f("board_date", { kind: "date" }),
          f("board_note", { kind: "textarea", wide: true, rows: 3 })),
        card("portal", `5 · ${meta.labels.portal || "Portal"}`, null,
          f("portal_status", { kind: "select", options: options("portal_status") }),
          f("portal_link")),
        card("kommuniziert", "6 · Kommuniziert",
          meta.labels.comm_platform ? `Bekanntgabe über ${meta.labels.comm_platform}.` : null,
          f("comm_status", { kind: "select", options: options("comm_status") }),
          f("comm_date", { kind: "date" })),
      ];
    },

    betrieb() {
      return [
        h("section", { class: "panel" },
          h("h2", null, "Life Cycle"),
          h("div", { class: "form-grid" },
            f("lc_owner"),
            f("version", { hint: "Format Haupt.Neben[.Patch], zum Beispiel 1.2 oder 1.2.3." }),
            f("next_review", { kind: "date" }),
            f("last_review", { kind: "date" }))),
        h("section", { class: "panel" },
          h("h2", null, "Updatehistorie", h("span", { class: "count" }, `(${detail.releases.length})`)),
          sublist("releases", [{ field: "date", label: "Datum", kind: "date" }, { field: "version", label: "Version" },
            { field: "change", label: "Änderung" }, { field: "released_by", label: "durch" }],
          "Update hinzufügen", "Noch keine Updates. Jede freigegebene Änderung der Lösung gehört in diese Liste.")),
        h("section", { class: "panel" },
          h("h2", null, "Tickets", h("span", { class: "count" }, `(${detail.tickets.length})`)),
          detail.tickets.length ? table([
            { label: "ID", value: (t) => h("a", { href: `#/tickets/${encodeURIComponent(t.id)}` }, t.id) },
            { label: "Titel", value: (t) => t.title },
            { label: "Status", value: (t) => t.status },
            { label: "Schwere", value: (t) => t.severity || "–" },
          ], detail.tickets) : emptyState("Keine Tickets zu diesem Use Case. Tickets kommen über das Formular „Problem mit AI-Tool melden“ und werden über die ID im Feld „Betroffenes Tool“ zugeordnet.")),
      ];
    },

    verlauf() {
      return h("section", { class: "panel" },
        h("h2", null, "Verlauf", h("span", { class: "count" }, `(${detail.history.length})`)),
        table([
          { label: "Zeit", value: (r) => formatTs(r.ts) },
          { label: "Wer", value: (r) => (r.user ? `${r.user} an ${r.machine}` : "–") },
          { label: "Feld", value: (r) => r.field_label },
          { label: "Alt", value: (r) => r.old_value },
          { label: "Neu", value: (r) => r.new_value },
          { label: "Herkunft", value: (r) => r.source },
        ], detail.history, "Neueste zuerst"));
    },
  };

  function phasePanel() {
    const uc = detail.usecase;
    const ended = detail.stepper.stage === "archiv";
    const target = h("input", { type: "text", list: "list-usecases", placeholder: "ID, z. B. UC-001", "aria-label": "Zusammenführen mit",
      "data-key": "merge-target", disabled: readOnly, autocomplete: "off" });
    const datalist = h("datalist", { id: "list-usecases" });
    if (!ended && !others) {
      api("GET", "/api/usecases").then((data) => {
        others = data.items.filter((row) => row.id !== uc.id && row.stage !== "archiv");
        datalist.replaceChildren(...others.map((row) => h("option", { value: row.id }, row.title)));
      }).catch(() => {});
    } else if (others) {
      datalist.replaceChildren(...others.map((row) => h("option", { value: row.id }, row.title)));
    }
    // Rückfragen nur bei Endzuständen (Konzept 9.7).
    const merge = async () => {
      const other = target.value.trim();
      if (!other) { fail(new Error("Bitte die ID des Use Cases angeben, mit dem zusammengeführt wird.")); return; }
      if (window.confirm(`${uc.id} mit ${other} zusammenführen? ${uc.id} wandert ins Archiv und erzeugt keinen Handlungsbedarf mehr. Nichts wird gelöscht.`)) {
        await setPhase("Zusammengeführt", other, `Zusammengeführt mit ${other}.`);
      }
    };
    const discontinue = async () => {
      if (window.confirm(`${uc.id} als „Discontinued“ ins Archiv verschieben? Der Datensatz bleibt erhalten.`)) {
        await setPhase("Discontinued", null, "Als Discontinued archiviert.");
      }
    };
    return h("section", { class: "panel" },
      h("h2", null, "Phase"),
      ended
        ? h("div", { class: "toolbar" },
            h("span", null, uc.phase, uc.merged_into ? [" mit ", h("a", { href: `#/usecases/${encodeURIComponent(uc.merged_into)}` }, uc.merged_into)] : null),
            h("button", { class: "btn", type: "button", disabled: readOnly, onclick: () => setPhase("Eingang", null, "Wieder aufgenommen (Phase Eingang).") }, "Wieder aufnehmen"))
        : [
            h("div", { class: "form-grid" }, field({
              key: "phase", label: "Phase", kind: "select", value: uc.phase, disabled: readOnly,
              options: options("phase").filter((o) => !["Zusammengeführt", "Discontinued"].includes(o.key)),
              hint: "Eingang → In Bearbeitung → Abgeschlossen. Die Reihenfolge ist eine Empfehlung.",
              save: async (value, expected) => {
                try {
                  apply(await api("PATCH", url, { field: "phase", value, expected }), "phase");
                } catch (error) {
                  await reloadAfterStale(error);
                }
              },
            })),
            h("div", { class: "toolbar" }, target, datalist,
              h("button", { class: "btn", type: "button", disabled: readOnly, onclick: merge }, "Zusammenführen mit …"),
              h("button", { class: "btn", type: "button", disabled: readOnly, onclick: discontinue }, "Discontinued")),
          ]);
  }

  draw();
  showCarried();
}
