"""Tests Phase 3: S8 (automatische Zuordnung), S9 (Buchung der Fix-Version), Ticket-API."""

import unittest

from tests.helpers import HubTestCase

from hub import rules


class TicketCase(HubTestCase):
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

    def patch(self, ticket_id, field, value, expect=200, **extra):
        return self.call("PATCH", f"/api/tickets/{ticket_id}", dict(field=field, value=value, **extra), expect)

    def usecase(self, usecase_id="UC-001"):
        return self.call("GET", f"/api/usecases/{usecase_id}")


class AssignmentTest(TicketCase):
    def test_s8_ticket_with_known_id_is_assigned_automatically(self):
        tickets = {t["id"]: t for t in self.call("GET", "/api/tickets")["items"]}
        self.assertEqual(tickets["T-001"]["usecase_id"], "UC-001")
        self.assertEqual(tickets["T-002"]["usecase_title"], "Suche in Arbeitsanweisungen")
        self.assertIsNone(tickets["T-005"]["usecase_id"])  # „Chat-Assistent allgemein“
        detail = self.call("GET", "/api/tickets/T-001")
        self.assertEqual((detail["history"][0]["field"], detail["history"][0]["source"]), ("usecase_id", "regel"))
        actions = self.call("GET", "/api/actions")
        self.assertEqual([i["id"] for i in actions["new"]["items"] if i["action"] == "Zuordnen"], ["T-005"])
        self.assertEqual(len(self.usecase()["tickets"]), 3)

    def test_manual_assignment_and_validation(self):
        detail = self.patch("T-005", "usecase_id", "UC-003", expected=None)
        self.assertEqual(detail["ticket"]["usecase_id"], "UC-003")
        self.patch("T-005", "usecase_id", "UC-404", expect=422)
        self.patch("T-005", "usecase_id", "UC-001", expected=None, expect=409)
        self.assertIsNone(self.patch("T-005", "usecase_id", "")["ticket"]["usecase_id"])

    def test_h02_and_manual_ticket(self):
        self.patch("T-001", "severity", "hoch")
        self.assertIn(("H02", "T-001"), [(a["rule"], a["subject"]) for a in self.call("GET", "/api/actions")["blocking"]])
        self.assertIn("H02", [a["rule"] for a in self.usecase()["actions"]])
        created = self.call("POST", "/api/tickets", {"title": "Telefonisch gemeldet"})
        self.assertEqual((created["ticket"]["id"], created["ticket"]["status"]), ("TM-001", "Neu"))
        self.patch("T-001", "severity", "dringend", expect=422)
        self.patch("T-001", "status", "Erledigt", expect=422)
        self.call("GET", "/api/tickets/T-999", expect=404)


class BookingTest(TicketCase):
    def test_s9_books_exactly_once_also_from_geloest_to_geschlossen(self):
        self.call("PATCH", "/api/usecases/UC-001", {"field": "version", "value": "1.0"})
        self.patch("T-001", "fix_version", "1.1")
        result = self.patch("T-001", "status", "Gelöst", expected="Neu")
        self.assertEqual((result["booking"]["booked"], result["booking"]["version_raised"],
                          result["booking"]["old_version"]), (True, True, "1.0"))
        self.assertTrue(result["ticket"]["resolved_at"])
        usecase = self.usecase()
        self.assertEqual((usecase["usecase"]["version"], len(usecase["releases"])), ("1.1", 1))
        self.assertEqual(usecase["releases"][0]["ticket_id"], "T-001")
        again = self.patch("T-001", "status", "Geschlossen", expected="Gelöst")
        self.assertIsNone(again["booking"])
        self.assertTrue(again["ticket"]["closed_at"])
        self.patch("T-001", "status", "In Analyse")
        self.assertIsNone(self.patch("T-001", "status", "Gelöst")["booking"])
        self.assertEqual(len(self.usecase()["releases"]), 1)

    def test_s9_without_fix_version_or_usecase(self):
        self.assertIsNone(self.patch("T-001", "status", "Gelöst")["booking"])
        self.assertEqual(self.usecase()["releases"], [])
        self.patch("T-005", "fix_version", "2.0")
        booking = self.patch("T-005", "status", "Geschlossen")["booking"]
        self.assertEqual(booking["booked"], False)
        self.assertIn("keinem Use Case", booking["hint"])

    def test_s9_version_is_only_raised_when_higher(self):
        self.call("PATCH", "/api/usecases/UC-001", {"field": "version", "value": "2.0"})
        self.patch("T-001", "fix_version", "1.9.5")
        booking = self.patch("T-001", "status", "Gelöst")["booking"]
        self.assertEqual((booking["booked"], booking["version_raised"]), (True, False))
        self.assertEqual(self.usecase()["usecase"]["version"], "2.0")

    def test_s9_unreadable_version_changes_nothing_and_gives_a_hint(self):
        self.call("PATCH", "/api/usecases/UC-001", {"field": "version", "value": "Frühjahr"})
        self.patch("T-001", "fix_version", "1.1")
        booking = self.patch("T-001", "status", "Gelöst")["booking"]
        self.assertEqual((booking["booked"], booking["version_raised"]), (True, False))
        self.assertIn("Haupt.Neben", booking["hint"])
        self.assertEqual(self.usecase()["usecase"]["version"], "Frühjahr")

    def test_undo_removes_booking_and_it_is_not_booked_again(self):
        self.call("PATCH", "/api/usecases/UC-001", {"field": "version", "value": "1.0"})
        self.patch("T-001", "fix_version", "1.1")
        booking = self.patch("T-001", "status", "Gelöst")["booking"]
        self.call("POST", "/api/tickets/T-001/undo-booking", {"old_version": booking["old_version"]})
        usecase = self.usecase()
        self.assertEqual((usecase["usecase"]["version"], usecase["releases"]), ("1.0", []))
        self.assertIsNone(self.patch("T-001", "status", "Geschlossen")["booking"])
        self.assertEqual(self.usecase()["releases"], [])
        self.call("POST", "/api/tickets/T-001/undo-booking", {}, expect=404)


class VersionTest(unittest.TestCase):
    def test_compare(self):
        self.assertTrue(rules.version_higher("1.10", "1.9"))
        self.assertTrue(rules.version_higher("1.2.1", "1.2"))
        self.assertFalse(rules.version_higher("1.2", "1.2.0"))
        self.assertTrue(rules.version_higher("1.0", ""))
        self.assertIsNone(rules.version_higher("v2", "1.0"))
        self.assertIsNone(rules.version_higher("2.0", "1"))


if __name__ == "__main__":
    unittest.main()
