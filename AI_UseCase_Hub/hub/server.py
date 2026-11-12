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
from urllib.parse import unquote, urlsplit

from . import APP_ID, APP_VERSION, rules
from .config import PATH_KEYS, Config

PORT_ATTEMPTS = 10
MAX_BODY_BYTES = 1_000_000
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# Diese Aufrufe verändern keine Daten und bleiben im Nur-Lese-Modus erlaubt.
ALLOWED_WHEN_READ_ONLY = ("/api/heartbeat", "/api/shutdown", "/api/fs/list")
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
        try:
            self.user = getpass.getuser()
        except Exception:  # kein Benutzername ermittelbar
            self.user = "unbekannt"
        self.machine = platform.node() or "unbekannt"

    @property
    def static_dir(self) -> Path:
        return self.cfg.program_dir / "static"

    def log_error(self, text: str) -> None:
        try:
            with open(self.cfg.data_dir / ERROR_LOG, "a", encoding="utf-8") as handle:
                handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {text.rstrip()}\n")
        except OSError:
            pass

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


def api_ping(app, _body):
    return {"app": APP_ID, "version": APP_VERSION, "instance": app.instance}


def api_state(app, _body):
    cfg = app.cfg
    deadline = cfg.site.get("deadline") if isinstance(cfg.site.get("deadline"), dict) else {}
    return {
        "app": APP_ID,
        "version": APP_VERSION,
        "mode": "nur-lesen" if app.read_only else "schreiben",
        "read_only_reason": app.read_only_reason,
        "user": app.user,
        "machine": app.machine,
        "configured": cfg.is_configured(),
        "test_mode": bool(cfg.local.get("test_mode")),
        "auto_shutdown_minutes": cfg.local.get("auto_shutdown_minutes", 0),
        "last_import": None,
        "counts": None,
        "deadline": {"date": deadline.get("date"), "lead_days": deadline.get("lead_days")},
        "labels": cfg.site.get("labels") if isinstance(cfg.site.get("labels"), dict) else {},
        "site_errors": len(cfg.site_check["errors"]),
        "warnings": list(cfg.warnings),
    }


def api_actions(app, _body):
    items = rules.system_actions(app.cfg)
    return {
        "blocking": [a for a in items if a["level"] == rules.LEVEL_BLOCKING],
        "open": [a for a in items if a["level"] == rules.LEVEL_OPEN],
        "new": [],
    }


def api_settings_get(app, _body):
    cfg = app.cfg
    cfg.reload_site()
    paths = cfg.local["paths"]
    return {
        "program_dir": str(cfg.program_dir),
        "data_dir": str(cfg.data_dir),
        "paths": cfg.path_report(),
        "configured": cfg.is_configured(),
        "auto_shutdown_minutes": cfg.local.get("auto_shutdown_minutes", 0),
        "can_publish_defaults": (
            cfg.is_configured()
            and not cfg.site_check["errors"]
            and all(cfg.is_relative(paths[key]) for key in PATH_KEYS)
        ),
        "defaults_published": cfg.site.get("default_paths") == paths,
        "site": cfg.site_check,
    }


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
    minutes = cfg.local.get("auto_shutdown_minutes", 0)
    if "auto_shutdown_minutes" in body:
        value = body["auto_shutdown_minutes"]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 240:
            errors["auto_shutdown_minutes"] = "Erwartet wird eine ganze Zahl von 0 (aus) bis 240."
        else:
            minutes = value
    if errors:
        raise ApiError(422, "validation", "Eingabe nicht gespeichert.", fields=errors)
    cfg.local["paths"] = new_paths
    cfg.local["auto_shutdown_minutes"] = minutes
    cfg.save_local()
    return api_settings_get(app, None)


def api_settings_publish_paths(app, _body):
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
            path = urlsplit(self.path).path
            body = None
            if method in WRITE_METHODS:
                self._check_write(app, path)
                body = self._read_json()
            if path.startswith("/api/"):
                for route_method, pattern, func in ROUTES:
                    match = pattern.match(path)
                    if match and route_method == method:
                        return self._send_json(200, func(app, body, *match.groups()))
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
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    app.serve()
    return 0
