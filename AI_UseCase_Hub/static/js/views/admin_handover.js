// Verwaltung → Übergabe & Backups: Übergabestand, Sperre, berechtigte Benutzer, Backups.

import { api } from "../api.js";
import { h, icon, emptyState, formatTs, table, status } from "../dom.js";

export async function renderHandover(box, app) {
  const readOnly = app.state.mode === "nur-lesen";
  let info = await api("GET", "/api/handover");
  const note = h("div", { role: "status" });
  const say = (ok, text) => note.replaceChildren(h("p", { class: `field-note ${ok ? "ok" : "bad"}` }, icon(ok ? "check" : "alert"), h("span", null, text)));
  draw();

  function draw() {
    const stand = info.outputs.handover;
    const lock = info.lock;
    const users = h("textarea", { rows: "3", "aria-label": "Berechtigte Benutzer", disabled: readOnly || !info.folder });
    users.value = info.users.join("\n");
    box.replaceChildren(
      h("section", { class: "panel" },
        h("h2", null, "Übergabestand"),
        h("dl", { class: "kv" },
          h("dt", null, "Ordner"), h("dd", null, info.folder || "Team-Ordner nicht eingerichtet"),
          h("dt", null, "Zuletzt veröffentlicht"), h("dd", null, stand ? (stand.ok ? formatTs(stand.ts) : stand.message) : "in dieser Sitzung noch nicht"),
          h("dt", null, "Lokaler Stand"), h("dd", null, info.unpublished ? status("open", "circle", "enthält unveröffentlichte Änderungen") : status("ok", "check", "veröffentlicht")),
          h("dt", null, "Sperre"), h("dd", null, info.holds_lock ? status("ok", "check", `gehalten von ${info.user} an ${info.machine}`)
            : (info.lock_state === "fremd" ? status("bad", "lock", `${lock.user} an ${lock.machine}`) : "keine"))),
        h("p", { class: "muted" }, `Die Datenbank bleibt lokal. Für die Vertretung wird ${info.publish_delay} Sekunden nach der letzten Änderung und beim Beenden eine geprüfte Kopie veröffentlicht. Laufen zwei Stände auseinander, entscheidet ein Mensch; zusammengeführt wird nie automatisch.`),
        note,
        h("div", { class: "toolbar" }, h("button", { class: "btn", type: "button", disabled: readOnly || !info.folder, onclick: async () => {
          try {
            const out = (await api("POST", "/api/handover/publish")).outputs.handover;
            info = await api("GET", "/api/handover");
            draw();
            say(out.ok, out.ok ? "Übergabestand veröffentlicht." : out.message);
          } catch (error) { say(false, error.message); }
        } }, icon("refresh"), "Jetzt veröffentlichen"))),
      h("section", { class: "panel" },
        h("h2", null, "Berechtigte Benutzer"),
        h("p", { class: "muted" }, "Ein Windows-Benutzername je Zeile (Hauptperson und Vertretung). Alle anderen sehen den Hub nur lesend. Das schützt vor versehentlichem Bearbeiten, nicht vor absichtlichem Zugriff auf den Ordner."),
        users,
        h("div", { class: "toolbar" }, h("button", { class: "btn", type: "button", disabled: readOnly || !info.folder, onclick: async () => {
          try {
            info.users = (await api("POST", "/api/handover/users", { users: users.value.split("\n") })).users;
            draw();
            say(true, "Liste gespeichert.");
          } catch (error) { say(false, error.message); }
        } }, "Liste speichern"))),
      h("section", { class: "panel" },
        h("h2", null, "Backups", h("span", { class: "count" }, `(${info.backups.length})`)),
        info.backups.length ? table([
          { label: "Zeit", value: (b) => formatTs(b.ts) },
          { label: "Anlass", value: (b) => b.label },
          { label: "Größe", num: true, value: (b) => `${Math.max(1, Math.round(b.size / 1024))} KB` },
          { label: "", value: (b) => h("button", { class: "btn", type: "button", disabled: readOnly, onclick: async () => {
            // Rückfrage ist hier vorgesehen: Ein Stand wird verworfen (Konzept 9.7).
            if (!window.confirm(`Den aktuellen Stand durch das Backup vom ${formatTs(b.ts)} ersetzen? Der aktuelle Stand wird vorher selbst als Backup gesichert.`)) return;
            try {
              await api("POST", "/api/backups/restore", { name: b.name });
              await app.refreshState();
              info = await api("GET", "/api/handover");
              draw();
              say(true, "Backup wiederhergestellt.");
            } catch (error) { say(false, error.message); }
          } }, "Wiederherstellen") },
        ], info.backups) : emptyState("Noch keine Backups. Bei jedem Start entsteht eines; die letzten 30 bleiben erhalten.")));
  }
}
