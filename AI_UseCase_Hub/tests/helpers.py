"""Gemeinsame Hilfen für die Tests (nur Standardbibliothek)."""

import http.client
import json
import shutil
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
PROGRAM_DIR = Path(__file__).resolve().parent.parent
if str(PROGRAM_DIR) not in sys.path:
    sys.path.insert(0, str(PROGRAM_DIR))

from hub import server  # noqa: E402
from hub.config import Config  # noqa: E402


def free_port_block(size=12) -> int:
    """Liefert einen Startport, ab dem ``size`` Ports frei sind."""
    for base in range(21000, 60000, 37):
        socks = []
        try:
            for port in range(base, base + size):
                sock = socket.socket()
                socks.append(sock)
                sock.bind(("127.0.0.1", port))
            return base
        except OSError:
            continue
        finally:
            for sock in socks:
                sock.close()
    raise RuntimeError("kein freier Portbereich")


class HubTestCase(unittest.TestCase):
    """Startet einen Hub mit eigenem Programm- und Datenordner."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hubtest_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        # Aufbau wie im Team-Ordner: <tmp>/team/AI_UseCase_Hub + lokaler Datenordner daneben
        self.team = self.tmp / "team"
        self.program = self.team / "AI_UseCase_Hub"
        self.program.mkdir(parents=True)
        shutil.copytree(PROGRAM_DIR / "static", self.program / "static")
        shutil.copy(PROGRAM_DIR / "standort.json", self.program / "standort.json")
        shutil.copy(PROGRAM_DIR / "validation_rules.json", self.program / "validation_rules.json")
        self.data = self.tmp / "local"
        self.base_port = free_port_block()
        self.apps = []

    def make_config(self) -> Config:
        return Config(program_dir=self.program, data_dir=self.data)

    def start(self, cfg=None, data=False):
        app, running = server.bind(cfg or self.make_config(), self.base_port)
        if app is None:
            return None, running
        if data:  # Datenbank öffnen; den Import stoßen die Tests selbst an
            app.autostart_import = False
            app.retry_pause = 0
            app.open_data()
        thread = threading.Thread(target=app.serve, daemon=True)
        thread.start()
        self.apps.append((app, thread))
        self.addCleanup(self.stop, app, thread)
        return app, None

    @staticmethod
    def stop(app, thread):
        app.request_shutdown("test")
        thread.join(timeout=5)

    def request(self, app, method, path, body=None, headers=None, host=None, auth=True):
        """Anfrage mit frei wählbaren Kopfzeilen (http.client setzt Host nicht selbst)."""
        conn = http.client.HTTPConnection("127.0.0.1", app.port, timeout=5)
        try:
            conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            conn.putheader("Host", host or f"127.0.0.1:{app.port}")
            send = {}
            data = b""
            if method != "GET":
                data = json.dumps(body or {}).encode("utf-8")
                send["Content-Type"] = "application/json"
                send["Content-Length"] = str(len(data))
                if auth:
                    send["Origin"] = f"http://127.0.0.1:{app.port}"
                    send["X-Hub-Token"] = app.token
            send.update(headers or {})
            for key, value in send.items():
                if value is not None:
                    conn.putheader(key, value)
            conn.endheaders(data)
            response = conn.getresponse()
            raw = response.read()
            content_type = response.getheader("Content-Type", "")
            payload = json.loads(raw) if "json" in content_type else raw.decode("utf-8")
            return response.status, payload, response
        finally:
            conn.close()
