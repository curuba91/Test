"""Tests Phase 6: einmalige Migration der Pflegeinformationen über IDs."""

import json
import unittest

from tests.helpers import HubTestCase


class MigrationTest(HubTestCase):
    def setUp(self):
        super().setUp()
        cfg = self.make_config()
        cfg.local["test_mode"] = True
        self.app, _ = self.start(cfg, data=True)
        self.app.importer.run()

    def call(self, method, path, body=None, expect=200):
        status, data, _ = self.request(self.app, method, path, body)
        self.assertEqual(status, expect, data)
        return data

    def alias(self):
        path = self.program / "standort.json"
        site = json.loads(path.read_text(encoding="utf-8"))
        site["value_lists"]["phase"]["entries"][0]["aliases"] = ["Neu"]
        path.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
        self.app.cfg.reload_site()

    def test_report_lists_applicable_unassignable_and_contradicting_rows_without_writing(self):
        self.call("PATCH", "/api/usecases/UC-002", {"field": "owner", "value": "Person X"})
        revision = self.app.db.meta()["revision"]
        report = self.call("GET", "/api/migration/preview")
        self.assertEqual(report["rows"], 11)
        self.assertEqual(len(report["apply"]), 10)
        self.assertEqual([c for c in report["conflicts"] if c["id"] == "UC-002"],
                         [{"id": "UC-002", "label": "Owner", "hub": "Person X", "source": "Person B"}])
        reasons = [u["reason"] for u in report["unassigned"]]
        self.assertTrue(any("Status „Neu“" in r for r in reasons))        # Alias fehlt noch
        first = {c["label"]: c["value"] for c in report["apply"][0]["changes"]}
        self.assertEqual((first["Owner"], first["Phase"], first["Score"]), ("Person A", "Abgeschlossen", 2.8))
        self.assertEqual(self.app.db.meta()["revision"], revision)         # nichts geschrieben
        self.assertEqual(self.call("GET", "/api/usecases/UC-001")["usecase"]["owner"], "")

    def test_apply_writes_only_after_confirmation_and_is_repeatable(self):
        self.alias()
        self.call("PATCH", "/api/usecases/UC-002", {"field": "owner", "value": "Person X"})
        result = self.call("POST", "/api/migration/apply")
        self.assertEqual((result["usecases"], result["conflicts"]), (10, 1))
        detail = self.call("GET", "/api/usecases/UC-001")
        usecase = detail["usecase"]
        self.assertEqual((usecase["owner"], usecase["phase"], usecase["score"]), ("Person A", "Abgeschlossen", 2.8))
        self.assertEqual(detail["scores"]["rft"], 2.0)
        self.assertIn("Life Cycle erforderlich nach Implementierung: nein", usecase["notes"])
        self.assertTrue(usecase["description"].startswith("Kurzfassung"))
        self.assertEqual(detail["history"][0]["source"], "import")
        self.assertEqual(self.call("GET", "/api/usecases/UC-002")["usecase"]["owner"], "Person X")  # Widerspruch bleibt
        again = self.call("GET", "/api/migration/preview")
        self.assertEqual((again["apply"], again["unchanged"]), ([], 10))
        self.assertEqual(len(again["conflicts"]), 1)

    def test_unknown_id_and_missing_column(self):
        with self.app.db.write() as tx:
            tx.execute("DELETE FROM usecases WHERE id = 'UC-010'")
        report = self.call("GET", "/api/migration/preview")
        self.assertIn({"id": "UC-010", "reason": "ID im Hub nicht vorhanden – zuerst importieren"}, report["unassigned"])
        path = self.program / "standort.json"
        site = json.loads(path.read_text(encoding="utf-8"))
        site["migration"]["columns"]["owner"] = "Gibt es nicht"
        path.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
        self.app.cfg.reload_site()
        result = self.call("GET", "/api/migration/preview", expect=409)
        self.assertIn("Spalte ‚Gibt es nicht‘", result["error"]["message"])


if __name__ == "__main__":
    unittest.main()
