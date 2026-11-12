import socket
import time
import unittest

from tests.helpers import HubTestCase

from hub import APP_ID, server


class SecurityTest(HubTestCase):
    def setUp(self):
        super().setUp()
        self.app, _ = self.start()

    def test_ping_identifies_the_hub(self):
        status, data, _ = self.request(self.app, "GET", "/api/ping")
        self.assertEqual(status, 200)
        self.assertEqual(data["app"], APP_ID)

    def test_foreign_host_header_is_rejected(self):
        for host in ("evil.example", f"evil.example:{self.app.port}", "127.0.0.1", f"127.0.0.1:{self.app.port + 1}"):
            for path in ("/", "/api/ping", "/static/app.css"):
                status, data, _ = self.request(self.app, "GET", path, host=host)
                self.assertEqual(status, 403, (host, path))
                self.assertEqual(data["error"]["code"], "host")

    def test_localhost_host_header_is_accepted(self):
        status, _, _ = self.request(self.app, "GET", "/api/ping", host=f"localhost:{self.app.port}")
        self.assertEqual(status, 200)

    def test_write_without_token_is_rejected(self):
        status, data, _ = self.request(self.app, "POST", "/api/heartbeat", auth=False,
                                       headers={"Origin": f"http://127.0.0.1:{self.app.port}"})
        self.assertEqual((status, data["error"]["code"]), (403, "token"))
        status, data, _ = self.request(self.app, "POST", "/api/heartbeat", headers={"X-Hub-Token": "falsch"})
        self.assertEqual((status, data["error"]["code"]), (403, "token"))

    def test_write_with_foreign_or_missing_origin_is_rejected(self):
        for origin in ("http://evil.example", "null", None, f"https://127.0.0.1:{self.app.port}"):
            status, data, _ = self.request(self.app, "POST", "/api/heartbeat", headers={"Origin": origin})
            self.assertEqual((status, data["error"]["code"]), (403, "origin"), origin)

    def test_write_needs_json_content_type(self):
        status, data, _ = self.request(self.app, "POST", "/api/heartbeat", headers={"Content-Type": "text/plain"})
        self.assertEqual((status, data["error"]["code"]), (415, "content_type"))

    def test_valid_write_passes(self):
        status, data, _ = self.request(self.app, "POST", "/api/heartbeat")
        self.assertEqual((status, data), (200, {"ok": True}))

    def test_token_is_only_in_the_delivered_page(self):
        status, html, response = self.request(self.app, "GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(self.app.token, html)
        self.assertNotIn("{{HUB_TOKEN}}", html)
        self.assertIn("default-src 'none'", response.getheader("Content-Security-Policy"))
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        for path in ("/api/state", "/api/ping", "/api/settings", "/static/js/main.js", "/static/js/api.js"):
            _, payload, _ = self.request(self.app, "GET", path)
            self.assertNotIn(self.app.token, str(payload), path)

    def test_static_files_and_path_traversal(self):
        status, _, response = self.request(self.app, "GET", "/static/js/main.js")
        self.assertEqual(status, 200)
        self.assertTrue(response.getheader("Content-Type").startswith("text/javascript"))
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        for path in ("/static/../standort.json", "/static/%2e%2e/standort.json", "/static/..%2fhub/server.py",
                     "/static/index.html", "/standort.json", "/hub/server.py", "/static/gibtsnicht.js"):
            status, _, _ = self.request(self.app, "GET", path)
            self.assertEqual(status, 404, path)

    def test_unknown_api_and_wrong_method(self):
        self.assertEqual(self.request(self.app, "GET", "/api/gibtsnicht")[0], 404)
        self.assertEqual(self.request(self.app, "GET", "/api/shutdown")[0], 405)
        self.assertEqual(self.request(self.app, "DELETE", "/api/settings")[0], 405)

    def test_broken_json_is_a_clean_error(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.app.port, timeout=5)
        conn.request("PUT", "/api/settings", body=b"{kaputt", headers={
            "Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.app.port}",
            "X-Hub-Token": self.app.token})
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        conn.close()

    def test_read_only_mode_rejects_writes_but_allows_shutdown_and_heartbeat(self):
        self.app.read_only = True
        self.app.read_only_reason = "Test"
        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"auto_shutdown_minutes": 5})
        self.assertEqual((status, data["error"]["code"]), (403, "read_only"))
        self.assertEqual(self.app.cfg.local["auto_shutdown_minutes"], 10)
        self.assertEqual(self.request(self.app, "POST", "/api/heartbeat")[0], 200)
        self.assertEqual(self.request(self.app, "GET", "/api/state")[1]["mode"], "nur-lesen")

    def test_internal_error_is_logged_and_does_not_kill_the_server(self):
        original = server.ROUTES[0]
        server.ROUTES[0] = (original[0], original[1], lambda app, body: 1 / 0)
        try:
            status, data, _ = self.request(self.app, "GET", "/api/ping")
        finally:
            server.ROUTES[0] = original
        self.assertEqual((status, data["error"]["code"]), (500, "internal"))
        self.assertIn("ZeroDivisionError", (self.data / server.ERROR_LOG).read_text(encoding="utf-8"))
        self.assertEqual(self.request(self.app, "GET", "/api/ping")[0], 200)


class SettingsTest(HubTestCase):
    def setUp(self):
        super().setUp()
        self.app, _ = self.start()
        for name in ("UseCases.xlsx", "Tickets.xlsx"):
            (self.team / name).write_bytes(b"")

    def test_setup_flow(self):
        state = self.request(self.app, "GET", "/api/state")[1]
        self.assertFalse(state["configured"])
        actions = self.request(self.app, "GET", "/api/actions")[1]
        self.assertEqual(len(actions["blocking"]), 2)  # zwei Quellen fehlen, Team-Ordner kommt aus der Vorgabe
        self.assertTrue(all(a["rule"] == "H08" and a["target"] == "#/verwaltung/einstellungen"
                            for a in actions["blocking"]))

        status, data, _ = self.request(self.app, "PUT", "/api/settings",
                                       {"paths": {"source_usecases": str(self.team / "UseCases.xlsx")}})
        self.assertEqual(status, 200)
        self.assertEqual(data["paths"]["source_usecases"]["stored"], "../UseCases.xlsx")
        self.assertIsNone(data["paths"]["source_usecases"]["error"])

        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"paths": {"source_tickets": "../fehlt.xlsx"}})
        self.assertEqual(status, 422)
        self.assertIn("nicht gefunden", data["error"]["fields"]["source_tickets"])

        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"paths": {"source_tickets": "../Tickets.xlsx"}})
        self.assertTrue(data["configured"])
        self.assertTrue(data["can_publish_defaults"])
        self.assertEqual(self.request(self.app, "GET", "/api/actions")[1]["blocking"], [])

        status, data, _ = self.request(self.app, "POST", "/api/settings/publish-paths")
        self.assertEqual(status, 200)
        self.assertTrue(data["defaults_published"])

    def test_invalid_values_are_not_saved(self):
        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"auto_shutdown_minutes": -1})
        self.assertEqual(status, 422)
        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"paths": {"fremd": "x"}})
        self.assertEqual(status, 400)
        self.assertEqual(self.make_config().local["auto_shutdown_minutes"], 10)

    def test_folder_listing_shows_only_folders_and_xlsx(self):
        (self.team / "notiz.txt").write_text("x", encoding="utf-8")
        (self.team / "~$UseCases.xlsx").write_bytes(b"")
        status, data, _ = self.request(self.app, "POST", "/api/fs/list", {"path": ""})
        self.assertEqual(status, 200)
        self.assertEqual(data["path"], str(self.team))
        self.assertEqual([d["name"] for d in data["dirs"]], ["AI_UseCase_Hub"])
        self.assertEqual([f["name"] for f in data["files"]], ["Tickets.xlsx", "UseCases.xlsx"])
        self.assertEqual(data["files"][0]["stored"], "../Tickets.xlsx")
        missing = self.request(self.app, "POST", "/api/fs/list", {"path": "../gibt/es/nicht"})[1]
        self.assertEqual(missing["path"], str(self.team))
        self.assertEqual(self.request(self.app, "POST", "/api/fs/list", {"path": ""}, auth=False)[0], 403)


class StartTest(HubTestCase):
    def test_second_start_finds_running_hub_and_creates_no_second_server(self):
        first, _ = self.start()
        self.assertEqual(first.port, self.base_port)
        second, running = self.start()
        self.assertIsNone(second)
        self.assertEqual(running, first.port)
        self.assertEqual(len(self.apps), 1)

    def test_foreign_program_on_port_is_skipped(self):
        blocker = socket.socket()
        blocker.bind(("127.0.0.1", self.base_port))
        blocker.listen(1)
        self.addCleanup(blocker.close)
        app, _ = self.start()
        self.assertEqual(app.port, self.base_port + 1)
        # Ein weiterer Start überspringt den fremden Port und findet den Hub dahinter.
        second, running = self.start()
        self.assertIsNone(second)
        self.assertEqual(running, self.base_port + 1)

    def test_no_free_port_gives_clear_error(self):
        blockers = []
        for port in range(self.base_port, self.base_port + server.PORT_ATTEMPTS):
            sock = socket.socket()
            sock.bind(("127.0.0.1", port))
            blockers.append(sock)
            self.addCleanup(sock.close)
        with self.assertRaisesRegex(RuntimeError, "Kein freier Port"):
            server.bind(self.make_config(), self.base_port)

    def test_find_hub_ignores_closed_port(self):
        self.assertIsNone(server.find_hub(self.base_port))

    def test_shutdown_request_stops_server_and_runs_hooks(self):
        app, _ = self.start()
        done = []
        app.shutdown_hooks.append(lambda: done.append("hook"))
        self.assertEqual(self.request(app, "POST", "/api/shutdown")[0], 200)
        self.apps[0][1].join(timeout=5)
        self.assertFalse(self.apps[0][1].is_alive())
        self.assertEqual(done, ["hook"])
        self.assertEqual(app.shutdown_reason, "benutzer")
        self.assertIsNone(server.find_hub(app.port))

    def test_auto_shutdown_without_heartbeat(self):
        cfg = self.make_config()
        cfg.local["auto_shutdown_minutes"] = 0.5 / 60  # eine halbe Sekunde
        app, _ = server.bind(cfg, self.base_port)
        app.watch_interval = 0.1
        import threading
        thread = threading.Thread(target=app.serve, daemon=True)
        thread.start()
        self.addCleanup(self.stop, app, thread)
        # Lebenszeichen halten den Hub am Laufen ...
        for _ in range(8):
            time.sleep(0.15)
            self.assertEqual(self.request(app, "POST", "/api/heartbeat")[0], 200)
        self.assertTrue(thread.is_alive())
        # ... ohne Lebenszeichen beendet er sich.
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(app.shutdown_reason, "auto")

    def test_auto_shutdown_can_be_switched_off(self):
        cfg = self.make_config()
        cfg.local["auto_shutdown_minutes"] = 0
        app, _ = self.start(cfg)
        app.watch_interval = 0.05
        app._last_beat -= 100000
        time.sleep(0.4)
        self.assertEqual(self.request(app, "GET", "/api/ping")[0], 200)


if __name__ == "__main__":
    unittest.main()
