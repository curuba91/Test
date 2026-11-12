"""HTTP-Server, API und Sicherheitsprüfungen (Kapitel 6.1, 6.4 und 12)."""

import argparse
import getpass
import json
import os
import platform
import re
import secrets
import socket
import threading
import time
import traceback
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from . import APP_ID, APP_VERSION, audit, export, handover, importer, rules, testdata, validation
from . import db as dbm
from .config import FREE_LISTS, LOGIC_LISTS, PATH_KEYS, SITE_FILE, Config, check_site, write_json_atomic

PORT_ATTEMPTS = 10
MAX_BODY_BYTES = 1_000_000
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# Diese Aufrufe verändern keine Daten und bleiben im Nur-Lese-Modus erlaubt.
ALLOWED_WHEN_READ_ONLY = ("/api/heartbeat", "/api/shutdown", "/api/fs/list", "/api/validation/preview")
ERROR_LOG = "hub_fehler.log"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


class ApiError(Exception):
    """Fehler mit HTTP-Status und Klartext für die Oberfläche."""

    def __init__(self, status, code, message, **extra):
        super().__init__(message)
        self.status = status
        self.payload = {"error": {"code": code, "message": message, **extra}}


class HubApp:
    """Zustand eines laufenden Hubs."""

    autostart_import = True  # Tests schalten den Hintergrund-Import ab

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.token = secrets.token_urlsafe(32)
        self.instance = secrets.token_hex(8)
        self.port = None
        self.httpd = None
        self.read_only = False
        self.read_only_reason = ""
        self.shutdown_hooks = []  # Phase 5: Übergabestand veröffentlichen, Sperre freigeben
        self.shutdown_reason = ""
        self.watch_interval = 2.0
        self._last_beat = time.monotonic()
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._data_lock = threading.RLock()
        self.data_ready = threading.Event()  # gelöscht, solange die Datenbank beim Start geöffnet wird
        self.data_ready.set()
        try:
            self.user = getpass.getuser()
        except Exception:  # kein Benutzername ermittelbar
            self.user = "unbekannt"
        self.machine = platform.node() or "unbekannt"
        # Datenschicht (open_data)
        self.db = None
        self.importer = None
        self.db_state = "geschlossen"
        self.db_message = ""
        self.test_mode = False
        self.data_root = cfg.data_dir
        self.db_path = None
        self.backup_dir = None
        self.notices = []
        # Übergabe und Ausgabe (Phase 5)
        self.handover_dir = None
        self.reporting_dir = None
        self.handover_pending = None
        self.lock_info = None
        self.users = []
        self.outputs = {}
        self.publish_delay = 60     # Sekunden nach der letzten Änderung
        self.output_tick = 5
        self.retry_pause = 0.5
        self._holds_lock = False
        self._lock_started = ""
        self._seen_revision = None
        self._dirty_since = None
        self._publish_lock = threading.Lock()
        self._outputs_stop = threading.Event()
        self._outputs_thread = None

    @property
    def static_dir(self) -> Path:
        return self.cfg.program_dir / "static"

    def log_error(self, text: str) -> None:
        try:
            with open(self.cfg.data_dir / ERROR_LOG, "a", encoding="utf-8") as handle:
                handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text.rstrip()}\n")
        except OSError:
            pass

    # --- Datenschicht -----------------------------------------------------------

    def open_data(self, stand_decided=False) -> None:
        """Öffnet Datenbank und Import für den aktuellen Modus (echt oder Testmodus).

        Im Testmodus wird die echte Datenbank nie geöffnet (Kapitel 6.1).
        """
        with self._data_lock:
            self.close_data()
            cfg = self.cfg
            self.test_mode = bool(cfg.local.get("test_mode"))
            self.data_root = cfg.data_dir / "test" if self.test_mode else cfg.data_dir
            self.db_path = self.data_root / ("hub_test.db" if self.test_mode else "hub.db")
            self.backup_dir = self.data_root / "backups"
            self.read_only, self.read_only_reason = False, ""
            self.db_state, self.db_message, self.notices = "ok", "", []
            try:
                if self.test_mode:
                    testdata.ensure_sources(cfg.site, self.data_root)
                self.db = dbm.open_database(
                    self.db_path,
                    before_migration=lambda database, version: handover.create_backup(
                        database, self.backup_dir, "migration"))
            except dbm.DatabaseCorrupt as exc:
                self._data_failed("defekt", f"Die Datenbank ist beschädigt ({exc}). Es wird nichts geschrieben.")
                return
            except dbm.SchemaTooNew as exc:
                self._data_failed("schema_neuer", f"{exc} Bitte das Programm aktualisieren.")
                return
            except Exception:
                self.log_error("Datenbank konnte nicht geöffnet werden:\n" + traceback.format_exc())
                self._data_failed("fehler", f"Die Datenbank konnte nicht geöffnet werden. Details in {ERROR_LOG}.")
                return
            try:
                handover.create_backup(self.db, self.backup_dir, "start")
            except Exception as exc:
                self.log_error(f"Start-Backup fehlgeschlagen: {exc}")
                self.notices.append("Das Backup beim Start ist fehlgeschlagen. Details im Fehlerprotokoll.")
            self.importer = importer.Importer(
                self.db, columns=lambda: self.cfg.site.get("columns"), path_for=self.source_path,
                tmp_dir=self.data_root / "tmp", user=self.user, machine=self.machine, log_error=self.log_error)
            # Erst die Übergabe prüfen, dann importieren: Ein Import vor der Prüfung würde den
            # lokalen Stand verändern und fälschlich als „auseinandergelaufen“ erscheinen.
            self._setup_team(stand_decided)
            if self.read_only:
                return
            if self.autostart_import:
                self.importer.start(self._import_interval())
            if self.handover_dir is not None and self.autostart_import:
                self._outputs_stop = threading.Event()
                self._outputs_thread = threading.Thread(target=self._outputs_loop, args=(self._outputs_stop,), daemon=True)
                self._outputs_thread.start()

    def _set_read_only(self, reason) -> None:
        self.read_only, self.read_only_reason = True, reason

    def _team_folder(self):
        if self.test_mode:
            return self.data_root  # der Testmodus schreibt nie in den echten Team-Ordner
        stored = self.cfg.local["paths"]["team_folder"]
        return self.cfg.resolve(stored) if self.cfg.check_path("team_folder", stored) is None else None

    def _setup_team(self, stand_decided) -> None:
        """Berechtigung, Sperre und Übergabestand prüfen (Kapitel 6.2 und 6.3)."""
        team = self._team_folder()
        self.handover_dir = team / handover.HANDOVER_DIR if team else None
        self.reporting_dir = team / export.REPORTING_DIR if team else None
        self.handover_pending, self.lock_info, self.users, self._holds_lock = None, None, [], False
        self.outputs = {}
        if self.handover_dir is None:
            return
        try:
            self.users = handover.authorized_users(self.handover_dir, self.user)
            if not handover.is_authorized(self.users, self.user):
                self._set_read_only(f"Benutzer {self.user} ist für diesen Hub nicht berechtigt (berechtigt: "
                                    f"{', '.join(self.users)}). Eintragen kann das eine berechtigte Person unter "
                                    "Verwaltung → Übergabe & Backups.")
                return
            state, lock = handover.lock_state(self.handover_dir, self.user, self.machine)
            if state == "fremd":
                self.lock_info = lock
                self._set_read_only(f"{lock.get('user')} arbeitet gerade an {lock.get('machine')} (seit "
                                    f"{str(lock.get('started', ''))[11:16]} Uhr). Der angezeigte Stand kann veraltet sein.")
                return
            meta = self.db.meta()
            shared = handover.inspect_shared(self.handover_dir, self.data_root / "tmp", pause=self.retry_pause)
            situation = "gleich" if stand_decided else handover.check_start(meta, shared, dbm.latest_version())
            if situation == "schema_neuer":
                self._set_read_only("Der geteilte Übergabestand stammt von einer neueren Programmversion. "
                                    "Bitte das Programm aktualisieren.")
                return
            if situation == "unlesbar":
                self.notices.append("Der geteilte Übergabestand ist gerade nicht lesbar (läuft die Synchronisation?). "
                                    "Es wird mit dem lokalen Stand gearbeitet.")
            if situation in ("fremd_neuer", "auseinander"):
                self.handover_pending = dict(shared, situation=situation, local_revision=meta["revision"],
                                             local_unpublished=meta["revision"] - meta["revision_published"])
                self._set_read_only("Im Team-Ordner liegt ein anderer Stand. Bis zur Entscheidung wird nichts geschrieben.")
                return
            self._lock_started = dbm.now_ts()
            handover.write_lock(self.handover_dir, self.user, self.machine, self._lock_started, self.instance)
            self._holds_lock = True
            self._seen_revision = meta["revision"]
            unpublished = meta["revision"] != meta["revision_published"] or shared is None
            self._dirty_since = time.monotonic() if unpublished else None
        except OSError as exc:
            self.log_error(f"Übergabe-Ordner nicht nutzbar: {exc}")
            self.notices.append("Der Übergabe-Ordner im Team-Ordner ist nicht erreichbar. Übergabestand und Sperre "
                                "sind in dieser Sitzung nicht aktiv.")
            self.handover_dir = None

    def _outputs_loop(self, stop) -> None:
        """Lebenszeichen der Sperre; Übergabestand und Reporting 60 Sekunden nach der letzten Änderung."""
        last_beat = time.monotonic()
        while not stop.wait(self.output_tick):
            try:
                now = time.monotonic()
                if now - last_beat >= handover.LOCK_BEAT_SECONDS:
                    handover.write_lock(self.handover_dir, self.user, self.machine, self._lock_started, self.instance)
                    last_beat = now
                revision = self.db.meta()["revision"]
                if revision != self._seen_revision:
                    self._seen_revision, self._dirty_since = revision, now
                if self._dirty_since is not None and now - self._dirty_since >= self.publish_delay:
                    self.publish_outputs()
            except Exception:
                self.log_error("Fehler beim Veröffentlichen:\n" + traceback.format_exc())

    def publish_outputs(self, only=None) -> dict:
        """Schreibt Übergabestand und Reporting-Excel jetzt. Ist eine Zieldatei geöffnet, folgt ein neuer Versuch."""
        with self._publish_lock:
            if self.db is None or self.read_only or self.handover_dir is None:
                return self.outputs
            steps = {
                "handover": lambda: handover.publish(self.db, self.handover_dir, self.user, self.machine),
                "reporting": lambda: export.write_reporting(self.db, self.cfg, self.reporting_dir,
                                                            self.source_states(), self.test_mode),
            }
            failed = False
            for key, step in steps.items():
                if only and key != only:
                    continue
                entry = {"ok": True, "ts": dbm.now_ts(), "message": ""}
                try:
                    result = step()
                    entry["path"] = str(result if key == "reporting" else self.handover_dir / handover.STAND_FILE)
                except PermissionError:
                    entry.update(ok=False, message="Die Zieldatei ist geöffnet oder gesperrt. Neuer Versuch im nächsten Zyklus.")
                except Exception as exc:
                    self.log_error(f"Veröffentlichen ({key}) fehlgeschlagen:\n{traceback.format_exc()}")
                    entry.update(ok=False, message=f"{type(exc).__name__}: {exc}")
                failed = failed or not entry["ok"]
                self.outputs[key] = entry
            if not only:
                self._seen_revision = self.db.meta()["revision"]
                self._dirty_since = time.monotonic() if failed else None
            return self.outputs

    def _data_failed(self, state, message) -> None:
        self.db = None
        self.importer = None
        self.db_state, self.db_message = state, message
        self.read_only, self.read_only_reason = True, message

    def close_data(self) -> None:
        with self._data_lock:
            if self._outputs_thread is not None:
                self._outputs_stop.set()
                self._outputs_thread.join(timeout=30)
                self._outputs_thread = None
            if self.importer is not None:
                self.importer.stop()
                self.importer = None
            if self.db is not None and self._holds_lock:
                # Beim Ende: Übergabestand veröffentlichen (falls etwas offen ist), Sperre freigeben.
                try:
                    if self.db.meta()["revision"] != self._seen_revision or self._dirty_since is not None:
                        self.publish_outputs()
                    handover.release_lock(self.handover_dir, self.instance)
                except Exception:
                    self.log_error("Fehler beim Abschluss der Übergabe:\n" + traceback.format_exc())
                self._holds_lock = False
            if self.db is not None:
                self.db.close()
                self.db = None
            self.db_state = "geschlossen"

    def _import_interval(self) -> float:
        value = self.cfg.local.get("import_interval_seconds", 20)
        return value if isinstance(value, (int, float)) and value >= 1 else 20

    def source_path(self, key):
        """Pfad einer Quelle im aktuellen Modus oder None, wenn keiner angegeben ist."""
        if self.test_mode:
            return testdata.source_paths(self.data_root)[key]
        return self.cfg.resolve(self.cfg.local["paths"][importer.SOURCES[key]["path_key"]])

    def configured(self) -> bool:
        if self.test_mode:
            return self.cfg.check_path("team_folder", self.cfg.local["paths"]["team_folder"]) is None
        return self.cfg.is_configured()

    def require_db(self):
        if self.db is None:
            raise ApiError(503, "db", self.db_message or "Die Datenbank ist nicht geöffnet.")
        return self.db

    def source_states(self) -> list:
        return self.importer.states() if self.importer is not None else []

    # --- Lebenszyklus -------------------------------------------------------------

    def beat(self) -> None:
        self._last_beat = time.monotonic()

    def request_shutdown(self, reason: str) -> None:
        with self._lock:
            if self._stop.is_set():
                return
            self._stop.set()
            self.shutdown_reason = reason
        if self.httpd is not None:
            threading.Thread(target=self.httpd.shutdown, daemon=True).start()

    def _watchdog(self) -> None:
        """Beendet den Hub, wenn lange kein Browser-Tab ein Lebenszeichen sendet."""
        while not self._stop.wait(self.watch_interval):
            minutes = self.cfg.local.get("auto_shutdown_minutes", 0)
            if minutes and time.monotonic() - self._last_beat > minutes * 60:
                self.request_shutdown("auto")
                return

    def serve(self) -> None:
        """Blockiert bis zum Beenden; führt danach die Abschlussarbeiten aus."""
        self.beat()
        threading.Thread(target=self._watchdog, daemon=True).start()
        try:
            self.httpd.serve_forever(poll_interval=0.25)
        finally:
            self._stop.set()
            for hook in self.shutdown_hooks:
                try:
                    hook()
                except Exception:
                    self.log_error("Fehler beim Beenden:\n" + traceback.format_exc())
            try:
                self.close_data()
            except Exception:
                self.log_error("Fehler beim Schließen der Datenbank:\n" + traceback.format_exc())
            self.httpd.server_close()


class HubHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # Unter Windows würde SO_REUSEADDR einem zweiten Prozess erlauben, denselben
    # Port zu belegen. Dort stattdessen exklusiv binden.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


# --- API ----------------------------------------------------------------------
# Jede Funktion erhält (app, params, *Gruppen aus dem Pfad). ``params`` ist bei
# schreibenden Aufrufen der JSON-Körper, sonst die Parameter der Adresse.


def _int(params, name, default, low, high):
    try:
        return max(low, min(high, int(params.get(name, default))))
    except (TypeError, ValueError):
        return default


def api_ping(app, _params):
    return {"app": APP_ID, "version": APP_VERSION, "instance": app.instance}


def api_state(app, _params):
    cfg = app.cfg
    deadline = cfg.site.get("deadline") if isinstance(cfg.site.get("deadline"), dict) else {}
    sources = app.source_states()
    counts, revision = None, None
    if app.db is not None:
        with app.db.read() as conn:
            counts = rules.counts(conn)
        revision = app.db.meta()["revision"]
    return {
        "app": APP_ID,
        "version": APP_VERSION,
        "mode": "nur-lesen" if app.read_only else "schreiben",
        "read_only_reason": app.read_only_reason,
        "user": app.user,
        "machine": app.machine,
        "configured": app.configured(),
        "test_mode": app.test_mode,
        "auto_shutdown_minutes": cfg.local.get("auto_shutdown_minutes", 0),
        "db_state": app.db_state,
        "revision": revision,
        "sources": sources,
        "last_import": max((s["last_success"] for s in sources), default="") or None,
        "counts": counts,
        "deadline": {"date": deadline.get("date"), "lead_days": deadline.get("lead_days")},
        "labels": cfg.site.get("labels") if isinstance(cfg.site.get("labels"), dict) else {},
        "site_errors": len(cfg.site_check["errors"]),
        "warnings": list(cfg.warnings) + list(app.notices),
        "handover_pending": app.handover_pending and {
            k: app.handover_pending.get(k) for k in ("situation", "user", "machine", "ts", "revision", "local_unpublished")},
    }


def api_actions(app, _params):
    new = {"total": 0, "items": []}
    if app.db is not None:
        with app.db.read() as conn:
            items = rules.handlungsbedarf(conn, app.cfg, app.source_states(), app.test_mode)
            new = rules.new_items(conn)
    else:
        items = rules.handlungsbedarf(None, app.cfg, [], app.test_mode)
    # Je Use Case höchstens ein Eintrag „Offen“; Neueingänge stehen nur unter „Neu eingegangen“.
    shown = rules.start_selection(items, [item["id"] for item in new["items"]])
    return {
        "blocking": [a for a in shown if a["level"] == rules.LEVEL_BLOCKING],
        "open": [a for a in shown if a["level"] == rules.LEVEL_OPEN],
        "total": len(items),
        "new": new,
    }


def api_settings_get(app, _params):
    cfg = app.cfg
    cfg.reload_site()
    paths = cfg.local["paths"]
    return {
        "program_dir": str(cfg.program_dir),
        "data_dir": str(cfg.data_dir),
        "paths": cfg.path_report(),
        "configured": cfg.is_configured(),
        "auto_shutdown_minutes": cfg.local.get("auto_shutdown_minutes", 0),
        "import_interval_seconds": cfg.local.get("import_interval_seconds", 20),
        "test_mode": bool(cfg.local.get("test_mode")),
        "test_dir": str(cfg.data_dir / "test"),
        "can_publish_defaults": (
            cfg.is_configured()
            and not cfg.site_check["errors"]
            and all(cfg.is_relative(paths[key]) for key in PATH_KEYS)
        ),
        "defaults_published": cfg.site.get("default_paths") == paths,
        "site": cfg.site_check,
    }


def _whole_number(body, name, low, high, errors, text):
    value = body[name]
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        errors[name] = text
        return None
    return value


def api_settings_put(app, body):
    cfg = app.cfg
    errors = {}
    new_paths = dict(cfg.local["paths"])
    paths = body.get("paths", {})
    if not isinstance(paths, dict):
        raise ApiError(400, "format", "paths muss ein Objekt sein.")
    for key, raw in paths.items():
        if key not in PATH_KEYS or not isinstance(raw, str):
            raise ApiError(400, "format", f"Unbekannter Pfad: {key}")
        stored = cfg.to_stored(raw)
        error = cfg.check_path(key, stored) if stored else None
        if error:
            errors[key] = error
        else:
            new_paths[key] = stored
    updates = {}
    if "auto_shutdown_minutes" in body:
        updates["auto_shutdown_minutes"] = _whole_number(
            body, "auto_shutdown_minutes", 0, 240, errors, "Erwartet wird eine ganze Zahl von 0 (aus) bis 240.")
    if "import_interval_seconds" in body:
        updates["import_interval_seconds"] = _whole_number(
            body, "import_interval_seconds", 5, 3600, errors, "Erwartet wird eine ganze Zahl von 5 bis 3600.")
    if "test_mode" in body:
        if not isinstance(body["test_mode"], bool):
            errors["test_mode"] = "Erwartet wird wahr oder falsch."
        else:
            updates["test_mode"] = body["test_mode"]
    if errors:
        raise ApiError(422, "validation", "Eingabe nicht gespeichert.", fields=errors)
    paths_changed = new_paths != cfg.local["paths"]
    mode_changed = "test_mode" in updates and updates["test_mode"] != bool(cfg.local.get("test_mode"))
    interval_changed = ("import_interval_seconds" in updates
                        and updates["import_interval_seconds"] != cfg.local.get("import_interval_seconds"))
    cfg.local["paths"] = new_paths
    cfg.local.update(updates)
    cfg.save_local()
    if mode_changed or interval_changed:
        app.open_data()  # anderer Modus: andere Datenbank und andere Quellen
    elif paths_changed and app.importer is not None and app.autostart_import:
        threading.Thread(target=app.importer.check, daemon=True).start()
    return api_settings_get(app, None)


def api_settings_publish_paths(app, _params):
    try:
        app.cfg.publish_default_paths()
    except ValueError as exc:
        raise ApiError(409, "not_possible", str(exc)) from None
    return api_settings_get(app, None)


def api_fs_list(app, body):
    """Ordnerinhalt für die Pfadauswahl der Einrichtung (nur Ordner und .xlsx)."""
    cfg = app.cfg
    raw = body.get("path", "")
    if not isinstance(raw, str):
        raise ApiError(400, "format", "path muss ein Text sein.")
    base = cfg.resolve(cfg.to_stored(raw)) if raw.strip() else cfg.program_dir.parent
    while not base.is_dir() and base.parent != base:
        base = base.parent
    dirs, files, note = [], [], ""
    try:
        with os.scandir(base) as scan:
            for entry in scan:
                name = entry.name
                if name.startswith((".", "~$")):
                    continue
                try:
                    if entry.is_dir():
                        dirs.append(name)
                    elif name.lower().endswith(".xlsx"):
                        files.append(name)
                except OSError:
                    continue
    except OSError as exc:
        note = f"Ordner nicht lesbar: {exc.strerror or exc}"
    limit = 500
    if len(dirs) + len(files) > limit:
        note = f"Es werden nur die ersten {limit} Einträge angezeigt."
    dirs.sort(key=str.casefold)
    files.sort(key=str.casefold)

    def item(name):
        full = str(base / name)
        return {"name": name, "path": full, "stored": cfg.to_stored(full)}

    return {
        "path": str(base),
        "stored": cfg.to_stored(str(base)),
        "parent": str(base.parent) if base.parent != base else None,
        "dirs": [item(n) for n in dirs[:limit]],
        "files": [item(n) for n in files[: max(0, limit - len(dirs))]],
        "note": note,
    }


def api_import_log(app, params):
    database = app.require_db()
    with database.read() as conn:
        rows = conn.execute("SELECT * FROM import_log ORDER BY id DESC LIMIT ?",
                            (_int(params, "limit", 30, 1, 500),)).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["source_label"] = importer.SOURCES.get(row["source"], {}).get("short", row["source"])
        items.append(item)
    return {"sources": app.source_states(), "items": items}


def api_import_run(app, _body):
    app.require_db()
    if app.importer is None:
        raise ApiError(503, "db", "Der Import ist nicht verfügbar.")
    return {"runs": app.importer.run(), "sources": app.source_states()}


def api_import_simulate(app, _body):
    database = app.require_db()
    if not app.test_mode:
        raise ApiError(409, "not_possible", "Meldungen lassen sich nur im Testmodus simulieren.")
    steps = testdata.simulate(app.cfg.site, app.data_root, database, app.user, app.machine)
    return {"steps": steps, "runs": app.importer.run(), "sources": app.source_states()}


def _conflict_view(row):
    item = dict(row)
    item["field_label"] = dbm.FIELD_LABELS.get(row["field"], row["field"])
    item["entity_label"] = dbm.ENTITY_LABELS.get(row["entity"], row["entity"])
    return item


def api_conflicts(app, _params):
    database = app.require_db()
    with database.read() as conn:
        open_rows = conn.execute("SELECT * FROM conflicts WHERE status = 'offen' ORDER BY id").fetchall()
        decided = conn.execute(
            "SELECT * FROM conflicts WHERE status = 'entschieden' ORDER BY resolved_at DESC, id DESC LIMIT 20"
        ).fetchall()
    return {"open": [_conflict_view(r) for r in open_rows], "decided": [_conflict_view(r) for r in decided]}


def api_conflict_resolve(app, body, conflict_id):
    database = app.require_db()
    try:
        result = importer.resolve_conflict(database, int(conflict_id), body.get("choice"), app.user, app.machine)
    except LookupError as exc:
        raise ApiError(404, "not_found", str(exc)) from None
    except ValueError as exc:
        raise ApiError(409, "not_possible", str(exc)) from None
    return result


def api_audit(app, params):
    database = app.require_db()
    with database.read() as conn:
        return audit.query(
            conn, entity=params.get("entity") or None, entity_id=params.get("entity_id") or None,
            source=params.get("source") or None, text=params.get("q") or None,
            limit=_int(params, "limit", 100, 1, 1000), offset=_int(params, "offset", 0, 0, 10**9))


def api_errors(app, _params):
    """Die letzten Einträge des Fehlerprotokolls."""
    path = app.cfg.data_dir / ERROR_LOG
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()[-200:]
    except OSError:
        lines = []
    return {"path": str(path), "lines": lines}


def api_backups(app, _params):
    return {"items": handover.list_backups(app.backup_dir) if app.backup_dir else []}


def api_backup_restore(app, body):
    """Stellt ein Backup wieder her (ohne Angabe: das jüngste gültige)."""
    name = body.get("name")
    with app._data_lock:
        if name:
            match = [b for b in handover.list_backups(app.backup_dir) if b["name"] == name]
            backup = match[0] if match else None
        else:
            backup = handover.latest_valid_backup(app.backup_dir)
        if backup is None:
            raise ApiError(404, "not_found", "Es gibt kein gültiges Backup.")
        if app.db is not None:
            handover.create_backup(app.db, app.backup_dir, "wiederherstellung")
        app.close_data()
        try:
            handover.restore_backup(backup["path"], app.db_path)
        except ValueError as exc:
            app.open_data()
            raise ApiError(409, "not_possible", str(exc)) from None
        # Bewusst wiederhergestellt: Dieser Stand gilt und wird als neuer Übergabestand veröffentlicht.
        app.open_data(stand_decided=True)
        if app._holds_lock:
            app._dirty_since = time.monotonic() - app.publish_delay
    return {"restored": backup["name"], "db_state": app.db_state}


# --- Use Cases (Phase 2) -------------------------------------------------------------


def _value_lists(cfg) -> dict:
    """Wertelisten für Auswahlfelder: feste Schlüssel, Anzeige aus standort.json."""
    lists = cfg.site.get("value_lists") if isinstance(cfg.site.get("value_lists"), dict) else {}
    result = {}
    for name, keys in LOGIC_LISTS.items():
        entries = (lists.get(name) or {}).get("entries") if isinstance(lists.get(name), dict) else None
        labels = {e.get("key"): e.get("label") for e in entries or [] if isinstance(e, dict)}
        result[name] = [{"key": key, "label": labels.get(key) or key} for key in keys]
    for name in FREE_LISTS:
        values = (lists.get(name) or {}).get("values") if isinstance(lists.get(name), dict) else None
        result[name] = [v for v in values or [] if isinstance(v, str)]
    return result


def _score_config(cfg) -> dict:
    score = cfg.site.get("score") if isinstance(cfg.site.get("score"), dict) else {}
    criteria = [c for c in score.get("criteria", []) if isinstance(c, dict) and c.get("key")]
    return {"mode": score.get("mode", "manuell"), "criteria": criteria}


def api_meta(app, _params):
    cfg = app.cfg
    return {
        "lists": _value_lists(cfg),
        "score": _score_config(cfg),
        "labels": cfg.site.get("labels") if isinstance(cfg.site.get("labels"), dict) else {},
        "field_labels": dbm.FIELD_LABELS,
        "stages": [{"key": key, "label": label} for key, label in rules.STAGES] + [{"key": "archiv", "label": "Archiv"}],
    }


def api_usecases(app, _params):
    database = app.require_db()
    with database.read() as conn:
        rows = rules.overview(conn, rules.deadline_of(app.cfg))
    return {"items": rows}


def _usecase_detail(app, conn, usecase_id) -> dict:
    row = conn.execute("SELECT * FROM usecases WHERE id = ?", (usecase_id,)).fetchone()
    if row is None:
        raise ApiError(404, "not_found", f"Use Case {usecase_id} nicht gefunden.")
    usecase = dict(row)
    today = time.strftime("%Y-%m-%d")
    milestones = dbm.sub_list(conn, "milestones", usecase_id)
    for milestone in milestones:
        milestone["overdue"] = bool(milestone["planned_date"]) and milestone["planned_date"] < today \
            and not milestone["done_date"]
    releases = dbm.sub_list(conn, "releases", usecase_id)
    tickets = [dict(r) for r in conn.execute("SELECT * FROM tickets WHERE usecase_id = ? ORDER BY id", (usecase_id,))]
    steps = rules.stepper(usecase, milestones)
    source_fields = dbm.SOURCE_FIELDS["usecases"]
    from_source = usecase["in_source"] is not None
    return {
        "usecase": {k: v for k, v in usecase.items() if not k.endswith("_src")},
        "from_source": from_source,
        "src": {f: usecase[f"{f}_src"] for f in source_fields},
        "differs": [f for f in source_fields if from_source and usecase[f] != usecase[f"{f}_src"]],
        "stepper": steps,
        "actions": rules.usecase_detail_actions(conn, usecase, milestones, len(releases), tickets,
                                                rules.deadline_of(app.cfg)),
        "milestones": milestones,
        "releases": releases,
        "links": dbm.sub_list(conn, "links", usecase_id),
        "tickets": [{"id": t["id"], "title": t["title"], "status": t["status"], "severity": t["severity"]}
                    for t in tickets],
        "scores": dict(conn.execute("SELECT criterion, value FROM usecase_scores WHERE usecase_id = ?",
                                    (usecase_id,)).fetchall()),
        "merged_from": [r[0] for r in conn.execute("SELECT id FROM usecases WHERE merged_into = ? ORDER BY id",
                                                   (usecase_id,))],
        "validations": _validation_list(app, conn, usecase_id),
        "history": audit.query(conn, entity="usecases", entity_id=usecase_id, limit=300)["items"],
    }


def _detail(app, usecase_id) -> dict:
    with app.db.read() as conn:
        return _usecase_detail(app, conn, usecase_id)


def _data_errors(func):
    """Übersetzt Fehler der Datenschicht in Antworten mit Klartext."""
    def wrapper(app, params, *groups):
        try:
            return func(app, params, *groups)
        except dbm.StaleValue as exc:
            raise ApiError(409, "stale", "Der Wert wurde inzwischen an anderer Stelle geändert. Die Seite zeigt "
                           "jetzt den aktuellen Stand.", current=exc.current) from None
        except KeyError as exc:  # vor LookupError prüfen: KeyError ist davon abgeleitet
            raise ApiError(400, "format", str(exc.args[0]) if exc.args else "Unbekanntes Feld.") from None
        except LookupError as exc:
            raise ApiError(404, "not_found", str(exc)) from None
        except ValueError as exc:
            raise ApiError(422, "validation", str(exc)) from None
    return wrapper


def _expected(body):
    return {"expected": body["expected"]} if "expected" in body else {}


@_data_errors
def api_usecase_get(app, _params, usecase_id):
    app.require_db()
    return _detail(app, usecase_id)


@_data_errors
def api_usecase_create(app, body):
    database = app.require_db()
    with database.write(user=app.user, machine=app.machine) as tx:
        usecase_id = dbm.create_manual(tx, "usecases", body.get("title"))
    return _detail(app, usecase_id)


@_data_errors
def api_usecase_patch(app, body, usecase_id):
    """Ändert genau ein Feld; ``expected`` ist der Wert, den die Oberfläche zuletzt gezeigt hat."""
    database = app.require_db()
    field = body.get("field")
    if not isinstance(field, str):
        raise ApiError(400, "format", "field fehlt.")
    with database.write(user=app.user, machine=app.machine) as tx:
        if field == "phase":
            dbm.set_phase(tx, usecase_id, body.get("value"), body.get("merged_into"), **_expected(body))
        else:
            value = dbm.clean_value("usecases", field, body.get("value"))
            dbm.update_field(tx, "usecases", usecase_id, field, value, **_expected(body))
    return _detail(app, usecase_id)


@_data_errors
def api_usecase_score(app, body, usecase_id):
    """Einzelscore speichern; bei score.mode = gewichtet folgt der Gesamtscore als Regel."""
    database = app.require_db()
    config = _score_config(app.cfg)
    criterion = {c["key"]: c for c in config["criteria"]}.get(body.get("criterion"))
    if criterion is None:
        raise ApiError(400, "format", "Unbekanntes Kriterium.")
    with database.write(user=app.user, machine=app.machine) as tx:
        dbm.set_criterion_score(tx, usecase_id, criterion["key"], criterion.get("label", criterion["key"]),
                                body.get("value"))
        changed = tx.bump
        values = dict(tx.execute("SELECT criterion, value FROM usecase_scores WHERE usecase_id = ?", (usecase_id,)))
        total = rules.weighted_score(config, values)
        if config["mode"] == "gewichtet":
            changed = dbm.update_field(tx, "usecases", usecase_id, "score", total, source="regel") or changed
        tx.bump = changed
    return _detail(app, usecase_id)


@_data_errors
def api_sub_add(app, body, usecase_id, table):
    database = app.require_db()
    with database.write(user=app.user, machine=app.machine) as tx:
        dbm.sub_add(tx, table, usecase_id, body.get("values"))
    return _detail(app, usecase_id)


@_data_errors
def api_sub_patch(app, body, table, row_id):
    database = app.require_db()
    field = body.get("field")
    if not isinstance(field, str):
        raise ApiError(400, "format", "field fehlt.")
    with database.write(user=app.user, machine=app.machine) as tx:
        usecase_id = dbm.sub_update(tx, table, int(row_id), field, body.get("value"), **_expected(body))
    return _detail(app, usecase_id)


@_data_errors
def api_sub_delete(app, _body, table, row_id):
    database = app.require_db()
    with database.write(user=app.user, machine=app.machine) as tx:
        usecase_id = dbm.sub_delete(tx, table, int(row_id))
    return _detail(app, usecase_id)


# --- Vorabcheck (Phase 4) ----------------------------------------------------------------


def _validation_rules(app):
    rules_data, errors = validation.load_rules(app.cfg.program_dir)
    if errors:
        raise ApiError(409, "rules", "Das Regelwerk des Vorabchecks ist fehlerhaft: " + " ".join(errors), errors=errors)
    return rules_data


def api_validation_rules(app, _params):
    rules_data = _validation_rules(app)
    return {"rules_version": rules_data["rules_version"], "notice": rules_data.get("notice", {}),
            "unclear": rules_data.get("unclear", {"key": "unklar", "label": "unklar"}),
            "questions": rules_data["questions"], "incomplete_parts": validation.incomplete_parts(rules_data)}


def api_validation_preview(app, body):
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise ApiError(400, "format", "answers fehlt.")
    return validation.evaluate(_validation_rules(app), answers)


def _validation_list(app, conn, usecase_id) -> list:
    rules_data, _errors = validation.load_rules(app.cfg.program_dir)
    results = rules_data.get("results", {})
    items = []
    for row in conn.execute("SELECT * FROM validations WHERE usecase_id = ? ORDER BY id DESC", (usecase_id,)):
        extra = json.loads(row["controls_json"] or "{}")
        entry = results.get(row["result"], {})
        items.append({
            "id": row["id"], "created_at": row["created_at"], "created_by": row["created_by"],
            "result": row["result"], "label": entry.get("label", row["result"]), "text": entry.get("text", ""),
            "risk": row["risk"], "controls": extra.get("controls", []),
            "incomplete_parts": extra.get("incomplete_parts", []), "answers": json.loads(row["answers_json"] or "{}"),
            "prompt_text": row["prompt_text"], "prompt_lang": row["prompt_lang"], "rules_version": row["rules_version"],
        })
    return items


@_data_errors
def api_validation_save(app, body, usecase_id):
    """Speichert einen Durchlauf; der neueste gilt. Der Check ersetzt keine Freigabe."""
    database = app.require_db()
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise ApiError(400, "format", "answers fehlt.")
    rules_data = _validation_rules(app)
    evaluation = validation.evaluate(rules_data, answers)
    lang = "en" if body.get("lang") == "en" else "de"
    with database.write(user=app.user, machine=app.machine) as tx:
        usecase = tx.execute("SELECT * FROM usecases WHERE id = ?", (usecase_id,)).fetchone()
        if usecase is None:
            raise LookupError(f"Use Case {usecase_id} nicht gefunden.")
        prompt = validation.build_prompt(rules_data, dict(usecase), evaluation, lang)
        extra = {"controls": evaluation["controls"], "incomplete_parts": evaluation["incomplete_parts"]}
        tx.execute(
            "INSERT INTO validations (usecase_id, created_at, created_by, answers_json, result, risk, controls_json, "
            "prompt_text, prompt_lang, rules_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (usecase_id, dbm.now_ts(), app.user, json.dumps(evaluation["answers"], ensure_ascii=False),
             evaluation["result"], evaluation["risk"] or "", json.dumps(extra, ensure_ascii=False), prompt, lang,
             evaluation["rules_version"]))
        tx.audit("usecases", usecase_id, "Vorabcheck", "", f"{evaluation['label']} (Regelwerk {evaluation['rules_version']})")
        if usecase["reg_status"] != "bestätigt":  # eine bestätigte Einordnung fasst der Vorabcheck nicht an
            if usecase["reg_status"] == "offen":
                dbm.update_field(tx, "usecases", usecase_id, "reg_status", "Vorabcheck erfolgt", source="regel")
            dbm.update_field(tx, "usecases", usecase_id, "reg_result", evaluation["label"], source="regel")
        tx.bump = True
    return _detail(app, usecase_id)


# --- Tickets (Phase 3) -----------------------------------------------------------------


def _ticket_view(row, titles, today):
    ticket = {k: v for k, v in dict(row).items() if not k.endswith("_src")}
    ticket["usecase_title"] = titles.get(row["usecase_id"], "")
    ticket["age_days"] = rules.ticket_age(row, today)
    return ticket


def api_tickets(app, _params):
    database = app.require_db()
    import datetime
    today = datetime.date.today()
    with database.read() as conn:
        titles = dict(conn.execute("SELECT id, title FROM usecases").fetchall())
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
    return {"items": [_ticket_view(row, titles, today) for row in rows],
            "lists": {k: v for k, v in _value_lists(app.cfg).items() if k.startswith("ticket_")}}


def _ticket_detail(app, ticket_id) -> dict:
    import datetime
    with app.db.read() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            raise ApiError(404, "not_found", f"Ticket {ticket_id} nicht gefunden.")
        titles = dict(conn.execute("SELECT id, title FROM usecases").fetchall())
        fields = dbm.SOURCE_FIELDS["tickets"]
        from_source = row["in_source"] is not None
        return {
            "ticket": _ticket_view(row, titles, datetime.date.today()),
            "from_source": from_source,
            "src": {f: row[f"{f}_src"] for f in fields},
            "differs": [f for f in fields if from_source and row[f] != row[f"{f}_src"]],
            "history": audit.query(conn, entity="tickets", entity_id=ticket_id, limit=200)["items"],
        }


@_data_errors
def api_ticket_get(app, _params, ticket_id):
    app.require_db()
    return _ticket_detail(app, ticket_id)


@_data_errors
def api_ticket_create(app, body):
    database = app.require_db()
    with database.write(user=app.user, machine=app.machine) as tx:
        ticket_id = dbm.create_manual(tx, "tickets", body.get("title"))
    return _ticket_detail(app, ticket_id)


@_data_errors
def api_ticket_patch(app, body, ticket_id):
    database = app.require_db()
    field = body.get("field")
    if not isinstance(field, str):
        raise ApiError(400, "format", "field fehlt.")
    booking = None
    with database.write(user=app.user, machine=app.machine) as tx:
        if field == "status":
            booking = dbm.set_ticket_status(tx, ticket_id, body.get("value"), **_expected(body))
        elif field == "usecase_id":
            dbm.set_ticket_usecase(tx, ticket_id, body.get("value"), **_expected(body))
        else:
            value = dbm.clean_value("tickets", field, body.get("value"))
            dbm.update_field(tx, "tickets", ticket_id, field, value, **_expected(body))
    return dict(_ticket_detail(app, ticket_id), booking=booking)


@_data_errors
def api_ticket_undo_booking(app, body, ticket_id):
    database = app.require_db()
    with database.write(user=app.user, machine=app.machine) as tx:
        dbm.undo_ticket_booking(tx, ticket_id, body.get("old_version"))
    return _ticket_detail(app, ticket_id)


def api_search(app, params):
    """Globale Suche über ID, Titel und Melder:in."""
    database = app.require_db()
    text = (params.get("q") or "").strip()
    if not text:
        return {"q": "", "items": []}
    like = f"%{text}%"
    items = []
    with database.read() as conn:
        for row in conn.execute("SELECT id, title, phase FROM usecases WHERE id LIKE ? OR title LIKE ? OR reporter LIKE ? "
                                "ORDER BY id LIMIT 50", (like, like, like)):
            items.append({"kind": "Use Case", "id": row["id"], "title": row["title"], "state": row["phase"],
                          "target": f"#/usecases/{row['id']}"})
        for row in conn.execute("SELECT id, title, status FROM tickets WHERE id LIKE ? OR title LIKE ? OR reporter LIKE ? "
                                "ORDER BY id LIMIT 50", (like, like, like)):
            items.append({"kind": "Ticket", "id": row["id"], "title": row["title"], "state": row["status"],
                          "target": f"#/tickets/{row['id']}"})
    return {"q": text, "items": items}


# --- Übergabe, Export, Bericht (Phase 5) ---------------------------------------------------


def api_handover(app, _params):
    meta = app.db.meta() if app.db is not None else {}
    lock_state, lock = ("", None)
    if app.handover_dir is not None:
        lock_state, lock = handover.lock_state(app.handover_dir, app.user, app.machine)
    return {
        "folder": str(app.handover_dir or ""), "reporting_folder": str(app.reporting_dir or ""),
        "user": app.user, "machine": app.machine, "users": app.users,
        "lock_state": lock_state, "lock": lock, "holds_lock": app._holds_lock,
        "pending": app.handover_pending, "outputs": app.outputs,
        "unpublished": bool(meta) and meta["revision"] != meta["revision_published"],
        "meta": meta, "backups": handover.list_backups(app.backup_dir) if app.backup_dir else [],
        "publish_delay": app.publish_delay,
    }


def api_handover_decide(app, body):
    """Geteilten Stand übernehmen oder eigenen behalten. Keine automatische Zusammenführung."""
    pending = app.handover_pending
    if not pending:
        raise ApiError(409, "not_possible", "Es steht keine Entscheidung zur Übergabe an.")
    choice = body.get("choice")
    with app._data_lock:
        if choice == "uebernehmen":
            handover.create_backup(app.db, app.backup_dir, "uebernahme")  # lokale Datenbank vorher sichern
            app.close_data()
            handover.restore_backup(pending["path"], app.db_path)
            app.open_data()
        elif choice == "behalten":
            handover.keep_foreign_copy(pending["path"], app.backup_dir)  # der andere Stand bleibt als Backup
            app.open_data(stand_decided=True)
            app._dirty_since = time.monotonic() - app.publish_delay  # eigenen Stand gleich veröffentlichen
        else:
            raise ApiError(400, "format", "Unbekannte Entscheidung.")
    return {"choice": choice, "mode": "nur-lesen" if app.read_only else "schreiben"}


def api_handover_users(app, body):
    if app.handover_dir is None:
        raise ApiError(409, "not_possible", "Der Team-Ordner ist nicht eingerichtet.")
    users = body.get("users")
    if not isinstance(users, list):
        raise ApiError(400, "format", "users muss eine Liste sein.")
    try:
        app.users = handover.set_authorized_users(app.handover_dir, users, app.user)
    except ValueError as exc:
        raise ApiError(422, "validation", str(exc)) from None
    return {"users": app.users}


def api_handover_publish(app, _body):
    app.require_db()
    if app.handover_dir is None:
        raise ApiError(409, "not_possible", "Der Team-Ordner ist nicht eingerichtet.")
    return {"outputs": app.publish_outputs()}


def api_export_reporting(app, _body):
    app.require_db()
    if app.reporting_dir is None:
        raise ApiError(409, "not_possible", "Der Team-Ordner ist nicht eingerichtet.")
    return {"outputs": app.publish_outputs(only="reporting")}


def api_export_full(app, _body):
    database = app.require_db()
    folder = app.reporting_dir or app.data_root
    try:
        return {"path": str(export.write_full(database, folder))}
    except PermissionError:
        raise ApiError(409, "not_possible", "Die Zieldatei ist geöffnet oder gesperrt.") from None


def api_export_toollist(app, _params):
    database = app.require_db()
    with database.read() as conn:
        return {"lines": export.tool_list(conn)}


def api_report_status(app, _params):
    """Daten des Statusberichts (Druckansicht); alle Werte kommen aus hub/rules.py."""
    database = app.require_db()
    with database.read() as conn:
        rows = rules.overview(conn, rules.deadline_of(app.cfg))
        actions = rules.handlungsbedarf(conn, app.cfg, app.source_states(), app.test_mode)
        counts = rules.counts(conn)
    return {
        "generated": dbm.now_ts(), "counts": counts, "deadline": rules.deadline_of(app.cfg),
        "labels": app.cfg.site.get("labels") if isinstance(app.cfg.site.get("labels"), dict) else {},
        "blocking": [a for a in actions if a["level"] == rules.LEVEL_BLOCKING],
        "governance": [r for r in rows if r["stage"] in ("governance", "betrieb")],
    }


SITE_FILES = {"standort": SITE_FILE, "regeln": validation.RULES_FILE}


def _site_file(params):
    name = params.get("file")
    if name not in SITE_FILES:
        raise ApiError(400, "format", "Unbekannte Datei.")
    return name


def api_sitefile_get(app, params):
    name = _site_file(params)
    path = app.cfg.program_dir / SITE_FILES[name]
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    return {"file": name, "name": SITE_FILES[name], "text": text}


def api_sitefile_put(app, body):
    """Speichert standort.json oder validation_rules.json – nur, wenn die Prüfung ohne Fehler ist."""
    name = _site_file(body)
    try:
        data = json.loads(body.get("text") or "")
    except ValueError as exc:
        raise ApiError(422, "validation", f"Kein gültiges JSON: {exc}", errors=[str(exc)]) from None
    errors = check_site(data)["errors"] if name == "standort" else validation.check_rules(data)
    if errors:
        raise ApiError(422, "validation", "Nicht gespeichert: " + " ".join(errors), errors=errors)
    write_json_atomic(app.cfg.program_dir / SITE_FILES[name], data)
    app.cfg.reload_site()
    return api_sitefile_get(app, {"file": name})


# --- Migration (Phase 6) -----------------------------------------------------------------


def _migration_report(app):
    database = app.require_db()
    try:
        return importer.migration_report(database, app.cfg.site, app.source_path("usecases"), app.data_root / "tmp")
    except importer.SourceError as exc:
        raise ApiError(409, "not_possible", str(exc)) from None


def api_migration_preview(app, _body):
    """Abgleichsbericht. Schreibt nichts."""
    return _migration_report(app)


def api_migration_apply(app, _body):
    report = _migration_report(app)
    result = importer.migration_apply(app.db, report, app.user, app.machine)
    return dict(result, conflicts=len(report["conflicts"]), unassigned=len(report["unassigned"]))


def api_heartbeat(app, _body):
    app.beat()
    return {"ok": True}


def api_shutdown(app, _body):
    # Erst antworten, dann beenden.
    threading.Timer(0.2, app.request_shutdown, args=("benutzer",)).start()
    return {"ok": True}


ROUTES = [
    ("GET", re.compile(r"^/api/ping$"), api_ping),
    ("GET", re.compile(r"^/api/state$"), api_state),
    ("GET", re.compile(r"^/api/actions$"), api_actions),
    ("GET", re.compile(r"^/api/settings$"), api_settings_get),
    ("PUT", re.compile(r"^/api/settings$"), api_settings_put),
    ("POST", re.compile(r"^/api/settings/publish-paths$"), api_settings_publish_paths),
    ("POST", re.compile(r"^/api/fs/list$"), api_fs_list),
    ("GET", re.compile(r"^/api/import/log$"), api_import_log),
    ("POST", re.compile(r"^/api/import/run$"), api_import_run),
    ("POST", re.compile(r"^/api/import/simulate$"), api_import_simulate),
    ("GET", re.compile(r"^/api/conflicts$"), api_conflicts),
    ("POST", re.compile(r"^/api/conflicts/(\d+)/resolve$"), api_conflict_resolve),
    ("GET", re.compile(r"^/api/audit$"), api_audit),
    ("GET", re.compile(r"^/api/errors$"), api_errors),
    ("GET", re.compile(r"^/api/backups$"), api_backups),
    ("POST", re.compile(r"^/api/backups/restore$"), api_backup_restore),
    ("GET", re.compile(r"^/api/meta$"), api_meta),
    ("GET", re.compile(r"^/api/search$"), api_search),
    ("GET", re.compile(r"^/api/usecases$"), api_usecases),
    ("POST", re.compile(r"^/api/usecases$"), api_usecase_create),
    ("GET", re.compile(r"^/api/usecases/([^/]+)$"), api_usecase_get),
    ("PATCH", re.compile(r"^/api/usecases/([^/]+)$"), api_usecase_patch),
    ("PUT", re.compile(r"^/api/usecases/([^/]+)/scores$"), api_usecase_score),
    ("POST", re.compile(r"^/api/usecases/([^/]+)/(milestones|releases|links)$"), api_sub_add),
    ("PATCH", re.compile(r"^/api/(milestones|releases|links)/(\d+)$"), api_sub_patch),
    ("DELETE", re.compile(r"^/api/(milestones|releases|links)/(\d+)$"), api_sub_delete),
    ("GET", re.compile(r"^/api/migration/preview$"), api_migration_preview),
    ("POST", re.compile(r"^/api/migration/apply$"), api_migration_apply),
    ("GET", re.compile(r"^/api/handover$"), api_handover),
    ("POST", re.compile(r"^/api/handover/decide$"), api_handover_decide),
    ("POST", re.compile(r"^/api/handover/users$"), api_handover_users),
    ("POST", re.compile(r"^/api/handover/publish$"), api_handover_publish),
    ("POST", re.compile(r"^/api/export/reporting$"), api_export_reporting),
    ("POST", re.compile(r"^/api/export/full$"), api_export_full),
    ("GET", re.compile(r"^/api/export/toollist$"), api_export_toollist),
    ("GET", re.compile(r"^/api/report/status$"), api_report_status),
    ("GET", re.compile(r"^/api/sitefile$"), api_sitefile_get),
    ("PUT", re.compile(r"^/api/sitefile$"), api_sitefile_put),
    ("GET", re.compile(r"^/api/validation$"), api_validation_rules),
    ("POST", re.compile(r"^/api/validation/preview$"), api_validation_preview),
    ("POST", re.compile(r"^/api/usecases/([^/]+)/validations$"), api_validation_save),
    ("GET", re.compile(r"^/api/tickets$"), api_tickets),
    ("POST", re.compile(r"^/api/tickets$"), api_ticket_create),
    ("GET", re.compile(r"^/api/tickets/([^/]+)$"), api_ticket_get),
    ("PATCH", re.compile(r"^/api/tickets/([^/]+)$"), api_ticket_patch),
    ("POST", re.compile(r"^/api/tickets/([^/]+)/undo-booking$"), api_ticket_undo_booking),
    ("POST", re.compile(r"^/api/heartbeat$"), api_heartbeat),
    ("POST", re.compile(r"^/api/shutdown$"), api_shutdown),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "AIUseCaseHub"
    sys_version = ""
    timeout = 15  # hängende Verbindungen blockieren keinen Thread auf Dauer

    def log_message(self, format, *args):  # noqa: A002 - Signatur der Basisklasse
        # Unter pythonw gibt es kein stderr; Zugriffe werden nicht protokolliert.
        return

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")

    # --- Ablauf -----------------------------------------------------------------

    def _handle(self, method):
        app = self.server.app
        try:
            self._check_host(app)
            parts = urlsplit(self.path)
            path = parts.path
            if path.startswith("/api/") and path != "/api/ping":
                app.data_ready.wait(30)  # Start: erst antworten, wenn die Datenbank geöffnet ist
            if method in WRITE_METHODS:
                self._check_write(app, path)
                params = self._read_json()
            else:
                params = {key: values[0] for key, values in parse_qs(parts.query).items()}
            if path.startswith("/api/"):
                for route_method, pattern, func in ROUTES:
                    match = pattern.match(path)
                    if match and route_method == method:
                        groups = [unquote(group) for group in match.groups()]
                        return self._send_json(200, func(app, params, *groups))
                if any(pattern.match(path) for _, pattern, _ in ROUTES):
                    raise ApiError(405, "method", "Methode für diese Adresse nicht erlaubt.")
                raise ApiError(404, "not_found", "Unbekannte API-Adresse.")
            if method != "GET":
                raise ApiError(405, "method", "Methode nicht erlaubt.")
            self._serve_static(app, path)
        except ApiError as exc:
            self._send_json(exc.status, exc.payload)
        except (BrokenPipeError, ConnectionError):
            return
        except Exception:
            app.log_error(f"{method} {self.path}\n{traceback.format_exc()}")
            self._send_json(500, {"error": {
                "code": "internal",
                "message": f"Interner Fehler. Details stehen in {ERROR_LOG} im lokalen Datenordner.",
            }})

    # --- Sicherheitsprüfungen (Kapitel 6.4) ---------------------------------------

    def _check_host(self, app):
        hosts = self.headers.get_all("Host") or []
        allowed = (f"127.0.0.1:{app.port}", f"localhost:{app.port}")
        if len(hosts) != 1 or hosts[0].strip().lower() not in allowed:
            raise ApiError(403, "host", "Anfrage abgelehnt: ungültige Host-Kopfzeile.")

    def _check_write(self, app, path):
        origin = (self.headers.get("Origin") or "").strip().lower()
        if origin not in (f"http://127.0.0.1:{app.port}", f"http://localhost:{app.port}"):
            raise ApiError(403, "origin", "Anfrage abgelehnt: ungültige Origin-Kopfzeile.")
        token = self.headers.get("X-Hub-Token") or ""
        if not secrets.compare_digest(token.encode("utf-8"), app.token.encode("utf-8")):
            raise ApiError(403, "token", "Sitzung ungültig. Seite neu laden.")
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise ApiError(415, "content_type", "Erwartet wird application/json.")
        if app.read_only and path not in ALLOWED_WHEN_READ_ONLY:
            # Einzige Ausnahme: eine beschädigte Datenbank aus dem Backup wiederherstellen.
            allowed = (path == "/api/backups/restore" and app.db_state == "defekt") or \
                (path == "/api/handover/decide" and app.handover_pending is not None)
            if not allowed:
                raise ApiError(403, "read_only", "Nur-Lese-Modus: Änderungen sind gesperrt.")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(400, "format", "Ungültige Content-Length.") from None
        if length < 0 or length > MAX_BODY_BYTES:
            raise ApiError(413, "too_large", "Anfrage zu groß.")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError(400, "format", "Anfrage ist kein gültiges JSON.") from None
        if not isinstance(body, dict):
            raise ApiError(400, "format", "Anfrage muss ein JSON-Objekt sein.")
        return body

    # --- Antworten ------------------------------------------------------------------

    def _send(self, status, content_type, data, html=False):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        if html:
            self.send_header("Content-Security-Policy", CSP)
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, MIME_TYPES[".json"], data)

    def _serve_static(self, app, path):
        static_dir = app.static_dir.resolve()
        if path in ("/", "/index.html"):
            # Das Sitzungs-Token wird nur in diese Seite eingebettet.
            html = (static_dir / "index.html").read_text(encoding="utf-8")
            html = html.replace("{{HUB_TOKEN}}", app.token)
            return self._send(200, MIME_TYPES[".html"], html.encode("utf-8"), html=True)
        if not path.startswith("/static/"):
            raise ApiError(404, "not_found", "Nicht gefunden.")
        target = (static_dir / unquote(path[len("/static/"):])).resolve()
        inside = static_dir in target.parents
        if not inside or target.suffix not in MIME_TYPES or target.name == "index.html" or not target.is_file():
            raise ApiError(404, "not_found", "Nicht gefunden.")
        self._send(200, MIME_TYPES[target.suffix], target.read_bytes())


# --- Start ------------------------------------------------------------------------


def find_hub(port: int, attempts: int = 1, pause: float = 0.2):
    """Prüft, ob auf dem Port bereits ein Hub antwortet (Zweitstart-Erkennung).

    ``attempts`` > 1 gibt einem Hub, der gerade hochfährt, Zeit zu antworten.
    """
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # nie über einen Proxy
    for attempt in range(attempts):
        refused = False
        try:
            with opener.open(f"http://127.0.0.1:{port}/api/ping", timeout=0.6) as response:
                data = json.loads(response.read(4096).decode("utf-8"))
            if isinstance(data, dict) and data.get("app") == APP_ID:
                return data
            return None  # Port gehört einem anderen Programm
        except (urllib.error.HTTPError, ValueError):
            return None
        except OSError as exc:
            reason = getattr(exc, "reason", exc)
            refused = isinstance(reason, ConnectionRefusedError)
        # Abgewiesen: dort lauscht niemand, ein einziger weiterer Versuch genügt.
        if attempt + 1 >= (2 if refused else attempts):
            return None
        time.sleep(pause)
    return None


def bind(cfg: Config, base_port=None):
    """Belegt den ersten freien Port.

    Rückgabe: ``(app, None)`` für einen neuen Hub oder ``(None, port)``, wenn
    auf einem der Ports bereits ein Hub läuft.
    """
    base = base_port or cfg.local.get("port") or 8765
    for port in range(base, base + PORT_ATTEMPTS):
        try:
            httpd = HubHTTPServer(("127.0.0.1", port), Handler)
        except OSError:
            # Belegt: Läuft dort schon ein Hub (oder fährt gerade hoch)?
            if find_hub(port, attempts=3):
                return None, port
            continue
        app = HubApp(cfg)
        app.port = port
        app.httpd = httpd
        httpd.app = app
        return app, None
    raise RuntimeError(
        f"Kein freier Port zwischen {base} und {base + PORT_ATTEMPTS - 1}. "
        "Anderes Programm beenden oder den Port in config.json ändern."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="AI_UseCase_Hub")
    parser.add_argument("--no-browser", action="store_true", help="Browser nicht öffnen")
    parser.add_argument("--port", type=int, help="Startport (Standard aus der Konfiguration)")
    args = parser.parse_args(argv)

    cfg = Config()
    app, running_port = bind(cfg, args.port)
    port = running_port if app is None else app.port
    url = f"http://127.0.0.1:{port}/"
    if app is None:  # Zweitstart: nur den Browser öffnen
        if not args.no_browser:
            webbrowser.open(url)
        return 0
    # Der Server antwortet sofort auf /api/ping (Zweitstart-Erkennung); die
    # Datenbank wird parallel geöffnet, alle anderen Aufrufe warten darauf.
    app.data_ready.clear()

    def open_data():
        try:
            app.open_data()
        except Exception:
            app.log_error("Start der Datenschicht fehlgeschlagen:\n" + traceback.format_exc())
            app._data_failed("fehler", f"Die Datenbank konnte nicht geöffnet werden. Details in {ERROR_LOG}.")
        finally:
            app.data_ready.set()

    threading.Thread(target=open_data, daemon=True).start()
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    app.serve()
    return 0
