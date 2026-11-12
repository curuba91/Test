"""Tests für die Use-Case-API der Phase 2: Liste, Detail, Feldänderung, Unterlisten, Score, Suche."""

import json
import unittest
from urllib.parse import quote

from tests.helpers import HubTestCase


class UsecaseApiCase(HubTestCase):
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

    def patch(self, usecase_id, field, value, expect=200, **extra):
        return self.call("PATCH", f"/api/usecases/{usecase_id}", dict(field=field, value=value, **extra), expect)


class ListAndDetailTest(UsecaseApiCase):
    def test_list_has_stage_next_step_and_status(self):
        rows = {r["id"]: r for r in self.call("GET", "/api/usecases")["items"]}
        self.assertEqual(len(rows), 10)
        row = rows["UC-001"]
        self.assertEqual((row["stage"], row["next_step"], row["attention"], row["open_tickets"]),
                         ("eingang", "Bewerten", "offen", 0))  # Tickets werden erst in Phase 3 zugeordnet (S8)
        self.assertEqual(row["next_target"], "#/usecases/UC-001/ueberblick")

    def test_detail_contains_everything_the_page_needs(self):
        detail = self.call("GET", "/api/usecases/UC-003")
        self.assertEqual(detail["usecase"]["title"], "Suche in Arbeitsanweisungen")
        self.assertEqual(detail["stepper"]["next"]["key"], "bewertet")
        self.assertEqual([a["rule"] for a in detail["actions"]], ["H10"])
        self.assertEqual([t["id"] for t in detail["tickets"]], [])  # Zuordnung der Tickets folgt in Phase 3 (S8)
        self.assertEqual(detail["history"][0]["field"], "angelegt")
        self.assertEqual((detail["from_source"], detail["differs"]), (True, []))
        self.assertNotIn("title_src", detail["usecase"])
        self.call("GET", "/api/usecases/UC-999", expect=404)

    def test_meta_delivers_value_lists_and_score_config(self):
        meta = self.call("GET", "/api/meta")
        self.assertEqual([e["key"] for e in meta["lists"]["origin"]], ["lokal entwickelt", "übernommen"])
        self.assertEqual(meta["lists"]["ticket_type"], ["Fehler", "Verbesserung", "Frage"])
        self.assertEqual((meta["score"]["mode"], len(meta["score"]["criteria"])), ("manuell", 5))

    def test_search_by_id_title_and_reporter(self):
        self.assertEqual([i["id"] for i in self.call("GET", "/api/search?q=uc-003")["items"]], ["UC-003"])
        hits = self.call("GET", "/api/search?q=" + quote("Zusammenfassung"))["items"]
        self.assertEqual({i["kind"] for i in hits}, {"Ticket"})
        self.assertTrue(self.call("GET", "/api/search?q=" + quote("Person D"))["items"])
        self.assertEqual(self.call("GET", "/api/search?q=")["items"], [])


class FieldEditTest(UsecaseApiCase):
    def test_rating_moves_the_next_step(self):
        self.patch("UC-001", "owner", "Person A", expected="")
        self.patch("UC-001", "type", "Prompt")
        self.patch("UC-001", "origin", "lokal entwickelt")
        detail = self.patch("UC-001", "score", "3,5")
        self.assertEqual(detail["usecase"]["score"], 3.5)
        self.assertEqual(detail["stepper"]["next"], {"key": "geplant", "label": "Meilenstein planen",
                                                     "action": "Umsetzung starten", "section": "planung"})
        self.assertEqual([h["field"] for h in detail["history"][:4]], ["score", "origin", "type", "owner"])

    def test_stale_value_is_rejected_like_a_second_tab(self):
        self.patch("UC-001", "owner", "Person A", expected="")
        result = self.patch("UC-001", "owner", "Person B", expected="", expect=409)
        self.assertEqual((result["error"]["code"], result["error"]["current"]), ("stale", "Person A"))
        self.assertEqual(self.call("GET", "/api/usecases/UC-001")["usecase"]["owner"], "Person A")

    def test_invalid_values_get_plain_messages(self):
        for field, value, text in (("origin", "gekauft", "Erlaubt"), ("next_review", "31.12.2026", "Datum"),
                                   ("score", "viel", "Zahl"), ("title", "  ", "Titel"), ("board_status", "", "Erlaubt")):
            result = self.patch("UC-001", field, value, expect=422)
            self.assertIn(text, result["error"]["message"], field)
        self.patch("UC-001", "title_src", "x", expect=400)
        self.patch("UC-001", "merged_into", "UC-002", expect=400)
        self.patch("UC-999", "owner", "x", expect=404)

    def test_changed_source_field_is_marked_as_different_from_report(self):
        detail = self.patch("UC-002", "title", "Abweichungsberichte (Hub)")
        self.assertEqual(detail["differs"], ["title"])
        self.assertEqual(detail["src"]["title"], "Abweichungsberichte vorformulieren")

    def test_phase_changes_and_merge(self):
        detail = self.patch("UC-001", "phase", "In Bearbeitung", expected="Eingang")
        self.assertEqual(detail["stepper"]["stage"], "umsetzung")
        self.patch("UC-002", "phase", "Zusammengeführt", expect=422)                      # Ziel fehlt
        self.patch("UC-002", "phase", "Zusammengeführt", merged_into="UC-002", expect=422)  # mit sich selbst
        self.patch("UC-002", "phase", "Zusammengeführt", merged_into="UC-404", expect=422)
        detail = self.patch("UC-002", "phase", "Zusammengeführt", merged_into="UC-001")
        self.assertEqual((detail["usecase"]["merged_into"], detail["stepper"]["stage"], detail["actions"]),
                         ("UC-001", "archiv", []))
        self.assertEqual(self.call("GET", "/api/usecases/UC-001")["merged_from"], ["UC-002"])
        self.patch("UC-003", "phase", "Zusammengeführt", merged_into="UC-002", expect=422)  # Ziel ist selbst zusammengeführt
        detail = self.patch("UC-002", "phase", "Eingang")                                    # zurückholen
        self.assertIsNone(detail["usecase"]["merged_into"])
        self.patch("UC-003", "phase", "Discontinued")
        rows = {r["id"]: r for r in self.call("GET", "/api/usecases")["items"]}
        self.assertEqual((rows["UC-003"]["stage"], rows["UC-003"]["attention"]), ("archiv", "keiner"))

    def test_manual_usecase_gets_m_id(self):
        first = self.call("POST", "/api/usecases", {"title": "Idee aus dem Gespräch"})
        second = self.call("POST", "/api/usecases", {"title": "Noch eine"})
        self.assertEqual((first["usecase"]["id"], second["usecase"]["id"]), ("M-001", "M-002"))
        self.assertEqual((first["from_source"], first["differs"]), (False, []))
        self.call("POST", "/api/usecases", {"title": " "}, expect=422)

    def test_read_only_mode_blocks_every_change(self):
        self.app.read_only = True
        self.patch("UC-001", "owner", "x", expect=403)
        self.call("POST", "/api/usecases", {"title": "x"}, expect=403)
        self.call("POST", "/api/usecases/UC-001/milestones", {"values": {"title": "x"}}, expect=403)
        self.call("GET", "/api/usecases/UC-001")


class SublistTest(UsecaseApiCase):
    def test_milestones_add_edit_delete_with_audit(self):
        detail = self.call("POST", "/api/usecases/UC-001/milestones",
                           {"values": {"title": "Pilot", "planned_date": "2020-01-01"}})
        milestone = detail["milestones"][0]
        self.assertEqual((milestone["title"], milestone["overdue"]), ("Pilot", True))
        self.assertIn("H01", [a["rule"] for a in detail["actions"]])
        detail = self.call("PATCH", f"/api/milestones/{milestone['id']}",
                           {"field": "done_date", "value": "2020-01-02", "expected": ""})
        self.assertFalse(detail["milestones"][0]["overdue"])
        self.assertNotIn("H01", [a["rule"] for a in detail["actions"]])
        self.assertIn("Meilenstein ‚Pilot‘: erledigt am", detail["history"][0]["field"])
        self.call("PATCH", f"/api/milestones/{milestone['id']}",
                  {"field": "done_date", "value": "2020-01-03", "expected": ""}, expect=409)
        self.call("PATCH", f"/api/milestones/{milestone['id']}", {"field": "planned_date", "value": "bald"}, expect=422)
        self.call("PATCH", f"/api/milestones/{milestone['id']}", {"field": "usecase_id", "value": "UC-002"}, expect=400)
        detail = self.call("DELETE", f"/api/milestones/{milestone['id']}")
        self.assertEqual(detail["milestones"], [])
        self.assertEqual(detail["history"][0]["new_value"], "gelöscht")
        self.call("DELETE", f"/api/milestones/{milestone['id']}", expect=404)
        self.call("POST", "/api/usecases/UC-001/milestones", {"values": {}}, expect=422)
        self.call("POST", "/api/usecases/UC-404/milestones", {"values": {"title": "x"}}, expect=404)

    def test_releases_and_links(self):
        detail = self.call("POST", "/api/usecases/UC-001/releases",
                           {"values": {"date": "2026-10-01", "version": "1.0", "change": "Erstfreigabe", "released_by": "A"}})
        self.assertEqual(detail["releases"][0]["version"], "1.0")
        detail = self.call("POST", "/api/usecases/UC-001/links", {"values": {"label": "Anleitung", "url": "https://x.invalid/a"}})
        self.assertEqual(detail["links"][0]["label"], "Anleitung")
        result = self.call("POST", "/api/usecases/UC-001/links", {"values": {"label": "Böse", "url": "javascript:alert(1)"}},
                           expect=422)
        self.assertIn("http", result["error"]["message"])
        self.call("POST", "/api/usecases/UC-001/tickets", {"values": {"title": "x"}}, expect=404)


class ScoreTest(UsecaseApiCase):
    def test_manual_mode_stores_criteria_without_touching_the_total(self):
        detail = self.call("PUT", "/api/usecases/UC-001/scores", {"criterion": "rft", "value": 4})
        self.assertEqual((detail["scores"], detail["usecase"]["score"]), ({"rft": 4.0}, None))
        self.call("PUT", "/api/usecases/UC-001/scores", {"criterion": "gibtsnicht", "value": 4}, expect=400)
        self.call("PUT", "/api/usecases/UC-001/scores", {"criterion": "rft", "value": "viel"}, expect=422)

    def test_weighted_mode_computes_the_total_as_a_rule(self):
        path = self.program / "standort.json"
        site = json.loads(path.read_text(encoding="utf-8"))
        site["score"]["mode"] = "gewichtet"
        for index, criterion in enumerate(site["score"]["criteria"]):
            criterion["weight"] = 2 if index == 0 else 1
        path.write_text(json.dumps(site, ensure_ascii=False), encoding="utf-8")
        self.app.cfg.reload_site()
        self.assertEqual(self.app.cfg.site_check["errors"], [])
        for key in ("rft", "capa", "time", "cost"):
            detail = self.call("PUT", "/api/usecases/UC-001/scores", {"criterion": key, "value": 3})
        self.assertIsNone(detail["usecase"]["score"])  # unvollständig
        detail = self.call("PUT", "/api/usecases/UC-001/scores", {"criterion": "users", "value": 5})
        self.assertEqual(detail["usecase"]["score"], round((3 * 2 + 3 + 3 + 3 + 5) / 6, 2))
        self.assertEqual((detail["history"][0]["field"], detail["history"][0]["source"]), ("score", "regel"))


class StartPageTest(UsecaseApiCase):
    def test_every_start_entry_has_a_target_and_open_entries_are_limited(self):
        self.patch("UC-001", "phase", "Abgeschlossen")
        actions = self.call("GET", "/api/actions")
        subjects = [a["subject"] for a in actions["open"]]
        self.assertEqual(len(subjects), len(set(subjects)))  # je Use Case höchstens ein Eintrag „Offen“
        self.assertEqual([a["rule"] for a in actions["blocking"] if a["subject"] == "UC-001"], ["H06"])
        self.assertGreater(actions["total"], len(actions["blocking"]) + len(actions["open"]))
        for action in actions["blocking"] + actions["open"]:
            self.assertRegex(action["target"], r"^#/(usecases|tickets|verwaltung)/")
        state = self.call("GET", "/api/state")
        self.assertEqual((state["counts"]["eingang"], state["counts"]["governance"], state["counts"]["reg_total"]), (9, 1, 1))


if __name__ == "__main__":
    unittest.main()
