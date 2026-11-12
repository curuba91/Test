"""Tests für die Datenschicht im Server: Testmodus, Import, Konflikte, Protokoll, beschädigte Datenbank."""

import sqlite3
import unittest
from urllib.parse import quote

from tests.helpers import HubTestCase

import openpyxl

from hub import handover, rules, testdata


class TestModeCase(HubTestCase):
    def setUp(self):
        super().setUp()
        cfg = self.make_config()
        cfg.local["test_mode"] = True
        self.app, _ = self.start(cfg, data=True)

    def get(self, path):
        status, data, _ = self.request(self.app, "GET", path)
        self.assertEqual(status, 200, data)
        return data

    def post(self, path, body=None, expect=200):
        status, data, _ = self.request(self.app, "POST", path, body)
        self.assertEqual(status, expect, data)
        return data


class TestModeTest(TestModeCase):
    def test_test_mode_uses_own_database_and_sources(self):
        self.assertEqual(self.app.db_path, self.data / "test" / "hub_test.db")
        self.assertFalse((self.data / "hub.db").exists())  # echte Datenbank wird nie geöffnet
        self.assertTrue((self.data / "test" / "Quelle1_UseCases.xlsx").exists())
        state = self.get("/api/state")
        self.assertTrue(state["test_mode"])
        self.assertTrue(state["configured"])
        self.assertEqual(state["db_state"], "ok")

    def test_test_sources_follow_the_column_mapping(self):
        sheet = openpyxl.load_workbook(self.data / "test" / "Quelle1_UseCases.xlsx").active
        header = [cell.value for cell in sheet[1]]
        for column in ("ID", "Titel Use Case", "Erwarteter Nutzen (Input Melder)", "Link zu Ordner",
                       "Verantwortliche Person", "Gewichteter Gesamtscore", "Status Use Case"):
            self.assertIn(column, header)
        self.assertNotIn("reporter_email", header)

    def test_import_of_sample_data(self):
        runs = self.post("/api/import/run")["runs"]
        by_source = {run["source"]: run for run in runs}
        self.assertEqual((by_source["usecases"]["status"], by_source["usecases"]["added"]), ("ok", 10))
        self.assertEqual(by_source["usecases"]["duplicates"], 1)
        self.assertEqual(by_source["tickets"]["added"], 6)
        state = self.get("/api/state")
        self.assertEqual(state["counts"]["eingang"], 10)
        self.assertEqual(state["counts"]["tickets_open"], 6)
        self.assertTrue(state["last_import"])
        actions = self.get("/api/actions")
        self.assertEqual(actions["blocking"], [])
        self.assertEqual(actions["new"]["total"], 16)
        self.assertEqual(len(actions["new"]["items"]), 16)
        self.assertEqual(actions["open"], [])  # Neueingänge stehen nicht zusätzlich im Handlungsbedarf
        log = self.get("/api/import/log")
        self.assertEqual(len(log["items"]), 2)
        self.assertEqual({s["state"] for s in log["sources"]}, {"ok"})

    def test_simulation_produces_new_rows_silent_update_and_conflict(self):
        self.post("/api/import/run")
        result = self.post("/api/import/simulate")
        self.assertEqual(len(result["steps"]), 4)
        by_source = {run["source"]: run for run in result["runs"]}
        self.assertEqual((by_source["usecases"]["added"], by_source["usecases"]["changed"],
                          by_source["usecases"]["conflicts"]), (1, 1, 1))
        self.assertEqual(by_source["tickets"]["added"], 1)

        conflicts = self.get("/api/conflicts")
        self.assertEqual(len(conflicts["open"]), 1)
        conflict = conflicts["open"][0]
        self.assertEqual((conflict["entity_id"], conflict["field_label"]), ("UC-004", "Titel"))

        actions = self.get("/api/actions")  # H07
        h07 = [a for a in actions["blocking"] if a["rule"] == "H07"]
        self.assertEqual(len(h07), 1)
        self.assertEqual((h07[0]["subject"], h07[0]["target"]), ("UC-004", "#/verwaltung/konflikte"))
        self.assertIn("Feld Titel", h07[0]["text"])

        status, data, _ = self.request(self.app, "POST", f"/api/conflicts/{conflict['id']}/resolve", {"choice": "x"})
        self.assertEqual(status, 409)
        self.post(f"/api/conflicts/{conflict['id']}/resolve", {"choice": "quelle"})
        after = self.get("/api/conflicts")
        self.assertEqual((len(after["open"]), after["decided"][0]["resolution"]), (0, "Quelle übernommen"))
        self.assertEqual([a for a in self.get("/api/actions")["blocking"] if a["rule"] == "H07"], [])
        self.post(f"/api/conflicts/{conflict['id']}/resolve", {"choice": "hub"}, expect=409)
        self.post("/api/conflicts/999/resolve", {"choice": "hub"}, expect=404)

        audit = self.get("/api/audit?entity_id=UC-004")
        self.assertGreaterEqual(audit["total"], 3)  # angelegt, im Hub geändert, Quelle übernommen
        self.assertEqual(self.get("/api/audit?q=umbenannt&source=" + quote("oberfläche"))["total"], 2)

        # Eine zweite Simulation erzeugt keinen zweiten Konflikt, nur neue Zeilen.
        again = {run["source"]: run for run in self.post("/api/import/simulate")["runs"]}
        self.assertEqual((again["usecases"]["added"], again["usecases"]["conflicts"]), (1, 0))

    def test_switching_modes_reopens_the_other_database(self):
        self.post("/api/import/run")
        status, data, _ = self.request(self.app, "PUT", "/api/settings", {"test_mode": False})
        self.assertEqual(status, 200)
        self.assertFalse(self.app.test_mode)
        self.assertEqual(self.app.db_path, self.data / "hub.db")
        state = self.get("/api/state")
        self.assertEqual(state["counts"]["usecases_total"], 0)
        self.assertFalse(state["configured"])
        self.post("/api/import/simulate", expect=409)
        self.request(self.app, "PUT", "/api/settings", {"test_mode": True})
        self.assertEqual(self.get("/api/state")["counts"]["usecases_total"], 10)

    def test_start_creates_backup(self):
        backups = self.get("/api/backups")["items"]
        self.assertEqual([b["label_key"] for b in backups], ["start"])

    def test_error_log_endpoint(self):
        self.app.log_error("Beispiel-Fehler")
        lines = self.get("/api/errors")["lines"]
        self.assertIn("Beispiel-Fehler", lines[-1])


class SourceProblemTest(TestModeCase):
    def test_h08_for_unreadable_source_and_missing_ids(self):
        self.post("/api/import/run")
        path = testdata.source_paths(self.data / "test")["usecases"]
        workbook = openpyxl.load_workbook(path)
        workbook.active.append([None, "Meldung ohne ID"])
        workbook.save(path)
        self.post("/api/import/run")
        h08 = [a for a in self.get("/api/actions")["blocking"] if a["rule"] == "H08"]
        self.assertEqual(len(h08), 1)
        self.assertIn("1 Zeile ohne ID", h08[0]["text"])
        self.assertEqual(h08[0]["target"], "#/verwaltung/quellen")

        path.write_bytes(b"halb synchronisiert")
        runs = self.post("/api/import/run")["runs"]
        self.assertEqual(runs[0]["status"], "fehler")
        h08 = [a for a in self.get("/api/actions")["blocking"] if a["rule"] == "H08"]
        self.assertIn("Quelle 1 konnte nicht gelesen werden", h08[0]["text"])
        self.assertEqual(self.get("/api/state")["counts"]["usecases_total"], 10)  # Stand bleibt

    def test_rules_are_computed_without_database(self):
        actions = rules.handlungsbedarf(None, self.app.cfg, [], test_mode=False)
        self.assertEqual({a["rule"] for a in actions}, {"H08"})
        self.assertEqual(len(actions), 2)  # zwei Quellen nicht eingerichtet


class CorruptDatabaseTest(HubTestCase):
    def test_corrupt_database_blocks_writes_and_can_be_restored(self):
        app, _ = self.start(data=True)
        with app.db.write(user="u", machine="m") as tx:
            tx.execute("INSERT INTO usecases (id, title, created_at, updated_at) VALUES ('UC-001', 'A', 'x', 'x')")
        handover.create_backup(app.db, app.backup_dir, "start")
        app.close_data()
        (self.data / "hub.db").write_bytes(b"kaputt" * 500)

        app.open_data()
        self.assertEqual(app.db_state, "defekt")
        state = self.request(app, "GET", "/api/state")[1]
        self.assertEqual((state["mode"], state["db_state"]), ("nur-lesen", "defekt"))
        self.assertIn("beschädigt", state["read_only_reason"])
        status, data, _ = self.request(app, "POST", "/api/import/run")
        self.assertEqual((status, data["error"]["code"]), (403, "read_only"))
        self.assertEqual(self.request(app, "GET", "/api/conflicts")[0], 503)
        self.assertEqual((self.data / "hub.db").read_bytes()[:6], b"kaputt")  # nichts geschrieben

        status, data, _ = self.request(app, "POST", "/api/backups/restore")
        self.assertEqual((status, data["db_state"]), (200, "ok"))
        state = self.request(app, "GET", "/api/state")[1]
        self.assertEqual((state["mode"], state["counts"]["usecases_total"]), ("schreiben", 1))
        self.assertTrue([p for p in self.data.iterdir() if p.name.startswith("hub.ersetzt-")])

    def test_restore_without_backup(self):
        app, _ = self.start(data=True)
        app.close_data()
        for path in (self.data / "backups").iterdir():
            path.unlink()
        (self.data / "hub.db").write_bytes(b"kaputt" * 500)
        app.open_data()
        status, data, _ = self.request(app, "POST", "/api/backups/restore")
        self.assertEqual(status, 404)

    def test_newer_schema_is_read_only(self):
        app, _ = self.start(data=True)
        app.close_data()
        conn = sqlite3.connect(self.data / "hub.db")
        conn.execute("UPDATE meta SET schema_version = 99")
        conn.commit()
        conn.close()
        app.open_data()
        state = self.request(app, "GET", "/api/state")[1]
        self.assertEqual((state["mode"], state["db_state"]), ("nur-lesen", "schema_neuer"))
        self.assertIn("aktualisieren", state["read_only_reason"])
        self.assertEqual(self.request(app, "POST", "/api/backups/restore")[0], 403)


if __name__ == "__main__":
    unittest.main()
