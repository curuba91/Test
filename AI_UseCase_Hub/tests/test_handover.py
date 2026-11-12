"""Tests Phase 5: Sperre, Berechtigung, die fünf Übergabe-Situationen (6.2), Reporting-Excel."""

import json
import sqlite3
import time
import unittest

from tests.helpers import HubTestCase

import openpyxl

from hub import export, handover, server
from hub import db as dbm
from hub.config import Config


class HandoverCase(HubTestCase):
    """Zwei Rechner (A und B) mit eigenem lokalem Datenordner und gemeinsamem Team-Ordner."""

    def setUp(self):
        super().setUp()
        self.folder = self.team / handover.HANDOVER_DIR
        self.opened = []

    def machine(self, name):
        app = server.HubApp(Config(program_dir=self.program, data_dir=self.tmp / f"local_{name}"))
        app.autostart_import = False
        app.retry_pause = 0
        app.machine = f"pc-{name}"
        app.open_data()
        self.opened.append(app)
        self.addCleanup(app.close_data)
        return app

    def add(self, app, usecase_id):
        with app.db.write(user="u", machine=app.machine) as tx:
            tx.execute("INSERT INTO usecases (id, title, created_at, updated_at) VALUES (?, ?, 'x', 'x')",
                       (usecase_id, f"Titel {usecase_id}"))

    def ids(self, app):
        with app.db.read() as conn:
            return [r[0] for r in conn.execute("SELECT id FROM usecases ORDER BY id")]

    def crash(self, app):
        """Rechner fällt aus: nichts wird veröffentlicht, die Sperre bleibt nicht gültig."""
        app._holds_lock = False
        app.close_data()
        (self.folder / handover.LOCK_FILE).unlink(missing_ok=True)


class StandTest(HandoverCase):
    def test_1_no_shared_stand_starts_normally(self):
        a = self.machine("a")
        self.assertEqual((a.read_only, a.handover_pending), (False, None))
        self.assertTrue((self.folder / handover.LOCK_FILE).exists())

    def test_2_nobody_else_worked(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.close_data()                                   # veröffentlicht beim Beenden und gibt die Sperre frei
        self.assertTrue((self.folder / handover.STAND_FILE).exists())
        self.assertFalse((self.folder / handover.LOCK_FILE).exists())
        a.open_data()
        self.assertEqual((a.read_only, a.handover_pending, self.ids(a)), (False, None, ["UC-001"]))
        self.assertIsNone(a._dirty_since)                # nichts Unveröffentlichtes

    def test_3_newer_foreign_stand_is_taken_over_after_confirmation(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.close_data()
        b = self.machine("b")
        self.assertTrue(b.read_only)
        self.assertEqual((b.handover_pending["situation"], b.handover_pending["machine"]), ("fremd_neuer", "pc-a"))
        self.assertEqual(self.ids(b), [])                # vor der Bestätigung wird nichts übernommen
        with self.assertRaises(server.ApiError):
            server.api_handover_decide(b, {"choice": "egal"})
        server.api_handover_decide(b, {"choice": "uebernehmen"})
        self.assertEqual((b.read_only, b.handover_pending, self.ids(b)), (False, None, ["UC-001"]))
        self.assertIn("uebernahme", [x["label_key"] for x in handover.list_backups(b.backup_dir)])  # vorher gesichert
        b.close_data()
        a.open_data()                                     # B hat nichts geändert: für A ist es derselbe Stand
        self.assertEqual((a.read_only, a.handover_pending), (False, None))

    def test_4_diverged_stands_are_never_merged(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.publish_outputs()
        self.add(a, "UC-002")                             # A ändert weiter und fällt aus, bevor veröffentlicht wird
        self.crash(a)
        b = self.machine("b")
        server.api_handover_decide(b, {"choice": "uebernehmen"})
        self.add(b, "UC-003")
        b.close_data()

        a.open_data()
        self.assertEqual((a.read_only, a.handover_pending["situation"], a.handover_pending["local_unpublished"]),
                         (True, "auseinander", 1))
        self.assertEqual(self.ids(a), ["UC-001", "UC-002"])
        revision = a.db.meta()["revision"]
        server.api_handover_decide(a, {"choice": "behalten"})       # eigenen Stand behalten und veröffentlichen
        self.assertEqual((a.read_only, self.ids(a), a.db.meta()["revision"]), (False, ["UC-001", "UC-002"], revision))
        kept = [x for x in handover.list_backups(a.backup_dir) if x["label_key"] == "fremd"]
        self.assertEqual(len(kept), 1)                    # der andere Stand bleibt als Backup erhalten
        other = sqlite3.connect(kept[0]["path"])
        self.assertEqual([r[0] for r in other.execute("SELECT id FROM usecases ORDER BY id")], ["UC-001", "UC-003"])
        other.close()
        a.publish_outputs()
        shared = handover.inspect_shared(self.folder, self.tmp / "check", pause=0)
        self.assertEqual(shared["stand_id"], a.db.meta()["stand_id_published"])

    def test_4b_diverged_take_shared_keeps_own_stand_as_backup(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.publish_outputs()
        self.add(a, "UC-002")
        self.crash(a)
        b = self.machine("b")
        server.api_handover_decide(b, {"choice": "uebernehmen"})
        self.add(b, "UC-003")
        b.close_data()
        a.open_data()
        server.api_handover_decide(a, {"choice": "uebernehmen"})
        self.assertEqual(self.ids(a), ["UC-001", "UC-003"])
        backup = [x for x in handover.list_backups(a.backup_dir) if x["label_key"] == "uebernahme"][0]
        own = sqlite3.connect(backup["path"])
        self.assertEqual([r[0] for r in own.execute("SELECT id FROM usecases ORDER BY id")], ["UC-001", "UC-002"])
        own.close()

    def test_5_newer_schema_in_shared_stand_means_read_only(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.close_data()
        conn = sqlite3.connect(self.folder / handover.STAND_FILE)
        conn.execute("UPDATE meta SET schema_version = 99, stand_id_published = 'neuer'")
        conn.commit()
        conn.close()
        a.open_data()
        self.assertTrue(a.read_only)
        self.assertIn("neueren Programmversion", a.read_only_reason)
        self.assertIsNone(a.handover_pending)

    def test_half_synced_stand_is_not_taken_over(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        a.close_data()
        (self.folder / handover.STAND_FILE).write_bytes(b"halb")
        a.open_data()
        self.assertFalse(a.read_only)
        self.assertTrue(any("nicht lesbar" in n for n in a.notices))

    def test_check_start_matrix(self):
        local = {"stand_id_published": "x", "revision": 5, "revision_published": 5}
        shared = {"valid": True, "schema_version": 1, "stand_id": "x", "revision": 5}
        self.assertEqual(handover.check_start(local, None, 2), "kein_stand")
        self.assertEqual(handover.check_start(local, shared, 2), "gleich")
        self.assertEqual(handover.check_start(local, dict(shared, stand_id="y"), 2), "fremd_neuer")
        self.assertEqual(handover.check_start(dict(local, revision=6), dict(shared, stand_id="y"), 2), "auseinander")
        self.assertEqual(handover.check_start(local, dict(shared, schema_version=3), 2), "schema_neuer")
        self.assertEqual(handover.check_start(local, {"valid": False}, 2), "unlesbar")


class LockTest(HandoverCase):
    def foreign_lock(self, age=0):
        self.folder.mkdir(parents=True, exist_ok=True)
        handover.write_lock(self.folder, "kollegin", "pc-x", "2026-11-12T08:05:00", "fremd", now=time.time() - age)

    def test_valid_foreign_lock_means_read_only(self):
        self.foreign_lock()
        a = self.machine("a")
        self.assertTrue(a.read_only)
        self.assertIn("kollegin arbeitet gerade an pc-x (seit 08:05 Uhr)", a.read_only_reason)
        a.close_data()
        self.assertEqual(json.loads((self.folder / handover.LOCK_FILE).read_text())["user"], "kollegin")  # bleibt

    def test_lock_expires_five_minutes_after_last_heartbeat(self):
        self.foreign_lock(age=handover.LOCK_EXPIRY_SECONDS + 5)
        a = self.machine("a")
        self.assertFalse(a.read_only)
        self.assertEqual(json.loads((self.folder / handover.LOCK_FILE).read_text())["machine"], "pc-a")
        self.assertEqual(handover.lock_state(self.folder, a.user, "pc-a")[0], "eigene")
        self.assertEqual(handover.lock_state(self.folder, a.user, "pc-b")[0], "fremd")

    def test_unknown_user_gets_read_only_and_list_keeps_own_user(self):
        a = self.machine("a")
        self.assertEqual(a.users, [a.user])               # erste Person wird eingetragen
        with self.assertRaises(ValueError):
            handover.set_authorized_users(self.folder, ["jemand"], a.user)
        self.assertEqual(handover.set_authorized_users(self.folder, [a.user, "vertretung", "Vertretung", " "], a.user),
                         [a.user, "vertretung"])
        a.close_data()
        (self.folder / handover.USERS_FILE).write_text(json.dumps({"users": ["hauptperson"]}), encoding="utf-8")
        a.open_data()
        self.assertTrue(a.read_only)
        self.assertIn("nicht berechtigt", a.read_only_reason)


class OutputTest(HandoverCase):
    def test_reporting_excel_opens_and_has_stable_columns(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        with a.db.write() as tx:
            tx.execute("UPDATE usecases SET reporter_email = 'a@b.invalid', notes = 'intern', phase = 'Abgeschlossen'")
            tx.execute("INSERT INTO milestones (usecase_id, title, planned_date) VALUES ('UC-001', 'Pilot', '2020-01-01')")
        outputs = a.publish_outputs()
        self.assertTrue(outputs["reporting"]["ok"] and outputs["handover"]["ok"])
        path = self.team / export.REPORTING_DIR / export.REPORTING_FILE
        workbook = openpyxl.load_workbook(path)
        self.assertEqual(workbook.sheetnames, list(export.SCHEMA))
        for name, columns in export.SCHEMA.items():
            sheet = workbook[name]
            self.assertEqual([c.value for c in sheet[1]], columns, name)
            self.assertEqual(list(sheet.tables), [name])          # genau eine Tabelle mit festem Namen
        everything = json.dumps([[c.value for c in row] for sheet in workbook for row in sheet.iter_rows()], default=str)
        self.assertNotIn("a@b.invalid", everything)
        self.assertNotIn("intern", everything)
        row = dict(zip(export.SCHEMA["tbl_usecases"], [c.value for c in workbook["tbl_usecases"][2]]))
        self.assertEqual((row["id"], row["stage"], row["next_step"]), ("UC-001", "Governance", "Bewerten"))
        rules_found = {r[0].value for r in workbook["tbl_handlungsbedarf"].iter_rows(min_row=2)}
        self.assertLessEqual({"H01", "H06", "H09"}, rules_found)
        self.assertEqual(export.SCHEMA["tbl_usecases"][:4], ["id", "title", "area", "type"])  # Reihenfolge ist fest

    def test_open_target_file_is_retried_in_the_next_cycle(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        original = export.write_reporting
        export.write_reporting = lambda *args, **kwargs: (_ for _ in ()).throw(PermissionError(13, "geöffnet"))
        try:
            outputs = a.publish_outputs()
        finally:
            export.write_reporting = original
        self.assertEqual((outputs["handover"]["ok"], outputs["reporting"]["ok"]), (True, False))
        self.assertIn("geöffnet", outputs["reporting"]["message"])
        self.assertIsNotNone(a._dirty_since)              # bleibt vorgemerkt
        self.assertTrue(a.publish_outputs()["reporting"]["ok"])
        self.assertIsNone(a._dirty_since)

    def test_background_publishes_after_change(self):
        a = self.machine("a")
        a.close_data()
        a.autostart_import, a.publish_delay, a.output_tick = True, 0, 0.05
        a.open_data()
        self.add(a, "UC-009")
        deadline = time.time() + 5
        while time.time() < deadline and not (a.outputs.get("reporting") or {}).get("ok"):
            time.sleep(0.05)
        self.assertTrue(a.outputs["reporting"]["ok"])
        shared = handover.inspect_shared(self.folder, self.tmp / "check", pause=0)
        self.assertEqual(shared["stand_id"], a.db.meta()["stand_id_published"])

    def test_full_export_contains_audit_but_no_email(self):
        a = self.machine("a")
        self.add(a, "UC-001")
        path = export.write_full(a.db, self.tmp / "voll")
        workbook = openpyxl.load_workbook(path)
        self.assertIn("tbl_audit", workbook.sheetnames)
        self.assertNotIn("reporter_email", [c.value for c in workbook["tbl_usecases"][1]])
        with a.db.read() as conn:
            self.assertEqual(export.tool_list(conn), [])
        with a.db.write() as tx:
            tx.execute("UPDATE usecases SET phase = 'Abgeschlossen'")
        with a.db.read() as conn:
            self.assertEqual(export.tool_list(conn), ["UC-001 – Titel UC-001"])


class ApiTest(HubTestCase):
    def test_pending_decision_blocks_writes_except_the_decision(self):
        first = server.HubApp(Config(program_dir=self.program, data_dir=self.tmp / "local_a"))
        first.autostart_import, first.retry_pause = False, 0
        first.open_data()
        with first.db.write() as tx:
            tx.execute("INSERT INTO usecases (id, title, created_at, updated_at) VALUES ('UC-001', 'A', 'x', 'x')")
        first.close_data()
        app, _ = self.start(data=True)
        state = self.request(app, "GET", "/api/state")[1]
        self.assertEqual((state["mode"], state["handover_pending"]["situation"]), ("nur-lesen", "fremd_neuer"))
        self.assertEqual(self.request(app, "POST", "/api/usecases", {"title": "x"})[0], 403)
        status, data, _ = self.request(app, "POST", "/api/handover/decide", {"choice": "uebernehmen"})
        self.assertEqual((status, data["mode"]), (200, "schreiben"))
        self.assertEqual(self.request(app, "GET", "/api/state")[1]["counts"]["usecases_total"], 1)
        self.assertEqual(self.request(app, "POST", "/api/handover/decide", {"choice": "behalten"})[0], 409)
        info = self.request(app, "GET", "/api/handover")[1]
        self.assertEqual((info["holds_lock"], info["lock_state"]), (True, "eigene"))
        self.assertEqual(self.request(app, "POST", "/api/handover/users", {"users": ["fremd"]})[0], 422)
        self.assertEqual(self.request(app, "GET", "/api/report/status")[1]["counts"]["usecases_total"], 1)

    def test_site_files_are_only_saved_when_valid(self):
        app, _ = self.start(data=True)
        current = self.request(app, "GET", "/api/sitefile?file=standort")[1]
        site = json.loads(current["text"])
        site["deadline"]["date"] = "2027-06-30"
        status, _, _ = self.request(app, "PUT", "/api/sitefile", {"file": "standort", "text": json.dumps(site)})
        self.assertEqual(status, 200)
        self.assertEqual(self.request(app, "GET", "/api/state")[1]["deadline"]["date"], "2027-06-30")
        site["deadline"]["date"] = "30.06.2027"
        status, data, _ = self.request(app, "PUT", "/api/sitefile", {"file": "standort", "text": json.dumps(site)})
        self.assertEqual(status, 422)
        self.assertIn("deadline.date", data["error"]["message"])
        self.assertEqual(self.request(app, "PUT", "/api/sitefile", {"file": "regeln", "text": "{kaputt"})[0], 422)
        self.assertEqual(self.request(app, "PUT", "/api/sitefile", {"file": "hub.db", "text": "{}"})[0], 400)
        self.assertEqual(app.cfg.site["deadline"]["date"], "2027-06-30")


if __name__ == "__main__":
    unittest.main()
