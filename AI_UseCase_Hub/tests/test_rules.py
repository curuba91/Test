"""Tests für hub/rules.py: Schrittleiste (8.1) und Handlungsbedarf H01 bis H12 (8.2)."""

import datetime
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import PROGRAM_DIR  # noqa: F401 - setzt den Suchpfad

from hub import db as dbm
from hub import rules

TODAY = datetime.date(2026, 11, 12)
NO_DEADLINE = {"date": None, "lead_days": 60}


def uc(**over):
    """Ein Use Case mit den Standardwerten der Datenbank."""
    base = {
        "id": "UC-001", "title": "Titel", "phase": "Eingang", "merged_into": None,
        "owner": "", "type": "", "origin": "", "score": None,
        "reg_status": "offen", "sponsor_status": "offen", "board_status": "offen",
        "portal_status": "offen", "comm_status": "offen",
        "lc_owner": "", "version": "", "next_review": "", "last_review": "",
        "needs_help": 0, "help_note": "",
    }
    base.update(over)
    return base


def rated(**over):
    values = dict(owner="Person A", type="Prompt", origin="lokal entwickelt", score=3.0)
    values.update(over)
    return uc(**values)


def in_operation(**over):
    values = dict(phase="Abgeschlossen", lc_owner="Person B", version="1.0", next_review="2027-01-01",
                  reg_status="bestätigt", sponsor_status="besprochen", board_status="freigegeben",
                  portal_status="veröffentlicht", comm_status="kommuniziert")
    values.update(over)
    return rated(**values)


def ms(title="Pilot", planned="2026-12-01", done=""):
    return {"id": 1, "title": title, "planned_date": planned, "done_date": done}


def ticket(**over):
    base = {"id": "T-001", "title": "Problem", "status": "Neu", "severity": "", "usecase_id": "UC-001",
            "submitted_at": "2026-11-08", "created_at": "2026-11-09T08:00:00"}
    base.update(over)
    return base


def actions_for(usecase, milestones=(), releases=1, deadline=NO_DEADLINE):
    return rules.usecase_actions(usecase, list(milestones), releases, TODAY, deadline)


def rule_ids(actions):
    return [a["rule"] for a in actions]


def state_of(usecase, key, milestones=()):
    return {s["key"]: s["state"] for s in rules.stepper(usecase, list(milestones))["steps"]}[key]


class StepperTest(unittest.TestCase):
    def test_new_usecase_is_reported_and_next_step_is_rating(self):
        result = rules.stepper(uc(), [])
        self.assertEqual(result["stage"], "eingang")
        self.assertEqual(state_of(uc(), "gemeldet"), "erfuellt")
        self.assertEqual(result["next"]["key"], "bewertet")

    def test_rated_needs_score_owner_type_and_origin(self):
        self.assertEqual(state_of(rated(), "bewertet"), "erfuellt")
        for missing in ("owner", "type", "origin"):
            self.assertEqual(state_of(rated(**{missing: ""}), "bewertet"), "offen", missing)
        self.assertEqual(state_of(rated(score=None), "bewertet"), "offen")
        self.assertEqual(state_of(rated(score=0), "bewertet"), "erfuellt")  # Score 0 ist ein Wert

    def test_planned_needs_a_milestone_with_plan_date(self):
        self.assertEqual(state_of(rated(), "geplant"), "offen")
        self.assertEqual(state_of(rated(), "geplant", [ms(planned="")]), "offen")
        self.assertEqual(state_of(rated(), "geplant", [ms()]), "erfuellt")

    def test_next_step_follows_the_order(self):
        self.assertEqual(rules.stepper(rated(), [])["next"]["key"], "geplant")
        self.assertEqual(rules.stepper(rated(phase="In Bearbeitung"), [ms()])["next"]["key"], "umgesetzt")
        done = rated(phase="Abgeschlossen")
        self.assertEqual(rules.stepper(done, [ms()])["next"]["key"], "betriebsbereit")

    def test_stage_follows_the_phase(self):
        self.assertEqual(rules.stepper(rated(phase="In Bearbeitung"), [])["stage"], "umsetzung")
        self.assertEqual(rules.stepper(rated(phase="Abgeschlossen"), [])["stage"], "governance")
        self.assertEqual(rules.stepper(in_operation(), [ms()])["stage"], "betrieb")
        for phase in ("Zusammengeführt", "Discontinued"):
            result = rules.stepper(rated(phase=phase), [])
            self.assertEqual((result["stage"], result["next"]), ("archiv", None))

    def test_governance_steps(self):
        base = rated(phase="Abgeschlossen")
        self.assertEqual(state_of(base, "betriebsbereit"), "offen")
        self.assertEqual(state_of(rated(phase="Abgeschlossen", lc_owner="B", version="1.0"), "betriebsbereit"), "offen")
        self.assertEqual(state_of(in_operation(), "betriebsbereit"), "erfuellt")
        self.assertEqual(state_of(rated(reg_status="Vorabcheck erfolgt"), "eingeordnet"), "teil")
        self.assertEqual(state_of(rated(reg_status="bestätigt"), "eingeordnet"), "erfuellt")
        self.assertEqual(state_of(rated(sponsor_status="besprochen"), "sponsor"), "erfuellt")
        self.assertEqual(state_of(rated(board_status="vorgelegt"), "gremium"), "offen")
        self.assertEqual(state_of(rated(board_status="freigegeben"), "gremium"), "erfuellt")
        self.assertEqual(state_of(rated(portal_status="veröffentlicht"), "portal"), "erfuellt")
        self.assertEqual(state_of(rated(comm_status="kommuniziert"), "kommuniziert"), "erfuellt")

    def test_sponsor_and_board_do_not_apply_to_adopted_solutions(self):
        adopted = rated(origin="übernommen", phase="Abgeschlossen")
        self.assertEqual(state_of(adopted, "sponsor"), "entfaellt")
        self.assertEqual(state_of(adopted, "gremium"), "entfaellt")
        self.assertEqual(state_of(rated(sponsor_status="nicht erforderlich"), "sponsor"), "entfaellt")
        self.assertEqual(state_of(rated(board_status="nicht erforderlich"), "gremium"), "entfaellt")
        operating = in_operation(origin="übernommen", sponsor_status="offen", board_status="offen")
        result = rules.stepper(operating, [ms()])
        self.assertEqual((result["stage"], result["next"]), ("betrieb", None))
        self.assertEqual((result["gov_done"], result["gov_total"]), (4, 4))

    def test_governance_progress(self):
        result = rules.stepper(in_operation(portal_status="offen", comm_status="offen", board_status="vorgelegt"), [ms()])
        self.assertEqual((result["stage"], result["gov_done"], result["gov_total"]), ("governance", 3, 6))
        self.assertEqual(result["next"]["key"], "gremium")

    def test_stage_overview(self):
        result = rules.stepper(rated(phase="Abgeschlossen", score=None), [ms()])
        stages = {s["key"]: s["state"] for s in result["stages"]}
        self.assertEqual(stages, {"eingang": "luecke", "umsetzung": "erledigt", "governance": "aktiv", "betrieb": "offen"})
        self.assertEqual(result["next"]["key"], "bewertet")  # Reihenfolge ist Empfehlung, Lücken bleiben sichtbar


class UsecaseRulesTest(unittest.TestCase):
    def test_h01_overdue_milestone(self):
        usecase = rated(phase="In Bearbeitung")
        found = actions_for(usecase, [ms("Pilot", "2026-11-03"), ms("Rollout", "2026-12-01"), ms("Kickoff", "2026-10-01", "2026-10-02")])
        h01 = [a for a in found if a["rule"] == "H01"]
        self.assertEqual(len(h01), 1)
        self.assertEqual((h01[0]["level"], h01[0]["text"], h01[0]["target"]),
                         ("blockierend", "Meilenstein ‚Pilot‘ seit 9 Tagen überfällig", "#/usecases/UC-001/planung"))
        self.assertEqual([a for a in actions_for(usecase, [ms("Heute", "2026-11-12")]) if a["rule"] == "H01"], [])
        one_day = [a for a in actions_for(usecase, [ms("Gestern", "2026-11-11")]) if a["rule"] == "H01"]
        self.assertIn("seit 1 Tag überfällig", one_day[0]["text"])

    def test_h03_overdue_review(self):
        found = actions_for(in_operation(next_review="2026-11-01"), [ms()])
        self.assertEqual([(a["rule"], a["level"], a["text"], a["target"]) for a in found],
                         [("H03", "blockierend", "Review seit 11 Tagen überfällig", "#/usecases/UC-001/betrieb")])
        self.assertEqual(actions_for(in_operation(next_review="2026-11-12"), [ms()]), [])

    def test_h04_board_demands_rework(self):
        found = actions_for(in_operation(board_status="Nachschärfen gefordert"), [ms()])
        self.assertEqual([(a["rule"], a["level"], a["target"]) for a in found],
                         [("H04", "blockierend", "#/usecases/UC-001/governance")])  # H10 „Gremium“ entfällt

    def test_h05_help_requested(self):
        found = actions_for(uc(needs_help=1, help_note="Fachlicher Ansprechpartner fehlt"))
        h05 = [a for a in found if a["rule"] == "H05"][0]
        self.assertEqual((h05["level"], h05["text"], h05["target"]),
                         ("blockierend", "Hilfe angefordert: Fachlicher Ansprechpartner fehlt", "#/usecases/UC-001/ueberblick"))

    def test_h06_no_lifecycle_owner_replaces_h10(self):
        found = actions_for(rated(phase="Abgeschlossen", reg_status="bestätigt"), [ms()])
        self.assertEqual(rule_ids(found), ["H06"])
        self.assertEqual((found[0]["level"], found[0]["text"], found[0]["target"]),
                         ("blockierend", "Kein Life-Cycle-Owner", "#/usecases/UC-001/betrieb"))
        self.assertNotIn("H06", rule_ids(actions_for(rated(phase="In Bearbeitung"), [ms()])))

    def test_h09_open_without_deadline(self):
        found = actions_for(in_operation(reg_status="offen"), [ms()])
        self.assertEqual([(a["rule"], a["level"], a["text"]) for a in found],
                         [("H09", "offen", "Regulatorische Einordnung fehlt")])
        self.assertEqual(found[0]["target"], "#/usecases/UC-001/governance")

    def test_h09_becomes_blocking_within_lead_time(self):
        usecase = in_operation(reg_status="Vorabcheck erfolgt")
        far = actions_for(usecase, [ms()], deadline={"date": "2027-02-01", "lead_days": 60})
        self.assertEqual((far[0]["level"], far[0]["text"]), ("offen", "Regulatorische Einordnung fehlt (Stichtag in 81 Tagen)"))
        edge = actions_for(usecase, [ms()], deadline={"date": "2027-01-11", "lead_days": 60})
        self.assertEqual((edge[0]["level"], edge[0]["text"]), ("blockierend", "Regulatorische Einordnung fehlt (Stichtag in 60 Tagen)"))
        past = actions_for(usecase, [ms()], deadline={"date": "2026-11-02", "lead_days": 60})
        self.assertEqual((past[0]["level"], past[0]["text"]),
                         ("blockierend", "Regulatorische Einordnung fehlt (Stichtag seit 10 Tagen überschritten)"))
        self.assertNotIn("H09", rule_ids(actions_for(rated(phase="In Bearbeitung"), [ms()])))

    def test_h10_exactly_one_next_step(self):
        found = actions_for(uc())
        self.assertEqual([(a["rule"], a["level"], a["text"], a["target"]) for a in found],
                         [("H10", "offen", "Nächster Schritt: Bewerten", "#/usecases/UC-001/ueberblick")])
        planning = actions_for(rated(phase="In Bearbeitung"))
        self.assertEqual([(a["rule"], a["target"]) for a in planning], [("H10", "#/usecases/UC-001/planung")])
        governance = actions_for(in_operation(sponsor_status="offen", portal_status="offen"), [ms()])
        self.assertEqual([(a["rule"], a["text"]) for a in governance], [("H10", "Nächster Schritt: Sponsor-Abstimmung")])

    def test_h10_is_dropped_when_another_rule_reports_the_same_step(self):
        found = actions_for(rated(phase="Abgeschlossen", lc_owner="B", version="1.0", next_review="2027-01-01"), [ms()])
        self.assertEqual(rule_ids(found), ["H09"])  # nächster Schritt wäre „Eingeordnet“
        both = actions_for(rated(phase="Abgeschlossen"), [ms()])
        self.assertEqual(rule_ids(both), ["H06", "H09"])  # nächster Schritt „Betriebsbereit“ steckt in H06

    def test_h12_no_update_history(self):
        found = actions_for(in_operation(), [ms()], releases=0)
        self.assertEqual([(a["rule"], a["level"], a["text"], a["target"]) for a in found],
                         [("H12", "offen", "Keine Updatehistorie", "#/usecases/UC-001/betrieb")])
        self.assertNotIn("H12", rule_ids(actions_for(rated(phase="In Bearbeitung"), [ms()], releases=0)))

    def test_end_states_create_no_actions(self):
        for phase in ("Zusammengeführt", "Discontinued"):
            usecase = rated(phase=phase, needs_help=1, next_review="2020-01-01", board_status="Nachschärfen gefordert")
            self.assertEqual(actions_for(usecase, [ms("Alt", "2020-01-01")], releases=0), [])


class TicketRulesTest(unittest.TestCase):
    def test_h02_open_ticket_with_high_severity(self):
        tickets = [ticket(severity="hoch"), ticket(id="T-002", severity="hoch", status="Gelöst"),
                   ticket(id="T-003", severity="mittel"), ticket(id="T-004", severity="hoch", status="In Umsetzung",
                                                                 submitted_at="", created_at="2026-11-10T09:00:00")]
        found = [a for a in rules.ticket_actions(tickets, TODAY) if a["rule"] == "H02"]
        self.assertEqual([(a["subject"], a["level"], a["text"], a["target"]) for a in found], [
            ("T-001", "blockierend", "Ticket mit Schwere hoch seit 4 Tagen offen", "#/tickets/T-001"),
            ("T-004", "blockierend", "Ticket mit Schwere hoch seit 2 Tagen offen", "#/tickets/T-004"),
        ])

    def test_h11_new_ticket_without_usecase(self):
        tickets = [ticket(usecase_id=None), ticket(id="T-002"), ticket(id="T-003", usecase_id=None, status="In Analyse")]
        found = [a for a in rules.ticket_actions(tickets, TODAY) if a["rule"] == "H11"]
        self.assertEqual([(a["subject"], a["level"], a["text"], a["target"]) for a in found],
                         [("T-001", "offen", "Ticket zuordnen", "#/tickets/T-001")])


class StartSelectionTest(unittest.TestCase):
    def test_only_one_open_entry_per_usecase_but_all_blocking(self):
        usecase = in_operation(reg_status="offen", version="", next_review="2026-11-01")
        found = rules.usecase_actions(usecase, [ms("Alt", "2026-11-01")], 0, TODAY, NO_DEADLINE)
        self.assertEqual(sorted(rule_ids(found)), ["H01", "H03", "H09", "H10", "H12"])
        start = rules.start_selection(found + rules.ticket_actions([ticket(usecase_id=None)], TODAY))
        self.assertEqual(sorted(rule_ids(start)), ["H01", "H03", "H10", "H11"])

    def test_h09_is_shown_when_it_replaces_h10(self):
        found = actions_for(in_operation(reg_status="offen"), [ms()], releases=0)
        self.assertEqual(rule_ids(rules.start_selection(found)), ["H09"])
        only_history = actions_for(in_operation(), [ms()], releases=0)
        self.assertEqual(rule_ids(rules.start_selection(only_history)), ["H12"])

    def test_new_arrivals_are_not_repeated_as_open_entries(self):
        found = actions_for(uc()) + actions_for(uc(id="UC-002", needs_help=1))
        found += rules.ticket_actions([ticket(usecase_id=None), ticket(id="T-002", usecase_id=None, severity="hoch")], TODAY)
        start = rules.start_selection(found, new_ids=["UC-001", "UC-002", "T-001", "T-002"])
        self.assertEqual([(a["rule"], a["subject"]) for a in start], [("H05", "UC-002"), ("H02", "T-002")])

    def test_no_fact_appears_twice(self):
        for usecase, milestones in ((uc(), []), (rated(phase="Abgeschlossen"), [ms()]),
                                    (in_operation(board_status="Nachschärfen gefordert"), [ms()])):
            found = actions_for(usecase, milestones)
            texts = [a["text"] for a in found]
            self.assertEqual(len(texts), len(set(texts)))


class DatabaseRulesTest(unittest.TestCase):
    """Dieselben Regeln über die Datenbank, wie sie Oberfläche, Export und Druck verwenden (E7)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hubrules_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = dbm.open_database(self.tmp / "hub.db")
        self.addCleanup(self.db.close)
        with self.db.write() as tx:
            for usecase_id, phase in (("UC-001", "Eingang"), ("UC-002", "In Bearbeitung"), ("UC-003", "Abgeschlossen"),
                                      ("UC-004", "Discontinued")):
                tx.execute("INSERT INTO usecases (id, title, phase, created_at, updated_at) VALUES (?, ?, ?, 'x', 'x')",
                           (usecase_id, f"Titel {usecase_id}", phase))
            tx.execute("INSERT INTO milestones (usecase_id, title, planned_date) VALUES ('UC-002', 'Pilot', '2026-11-03')")
            tx.execute("INSERT INTO milestones (usecase_id, title, planned_date) VALUES ('UC-004', 'Alt', '2020-01-01')")
            tx.execute("INSERT INTO tickets (id, title, status, severity, usecase_id, submitted_at, created_at, updated_at) "
                       "VALUES ('T-001', 'Problem', 'Neu', 'hoch', 'UC-003', '2026-11-08', 'x', 'x')")
            tx.execute("INSERT INTO tickets (id, title, status, created_at, updated_at) VALUES ('T-002', 'Frage', 'Neu', 'x', 'x')")
            tx.execute("INSERT INTO conflicts (entity, entity_id, field, created_at) VALUES ('usecases', 'UC-001', 'title', 'x')")

    def test_all_rules_from_the_database(self):
        with self.db.read() as conn:
            found = rules.data_actions(conn, NO_DEADLINE, TODAY)
        by_rule = {}
        for action in found:
            by_rule.setdefault(action["rule"], []).append(action["subject"])
        self.assertEqual(by_rule, {
            "H01": ["UC-002"], "H02": ["T-001"], "H06": ["UC-003"], "H07": ["UC-001"], "H09": ["UC-003"],
            "H10": ["UC-001", "UC-002", "UC-003"], "H11": ["T-002"], "H12": ["UC-003"],
        })
        self.assertEqual({a["title"] for a in found if a["subject"] == "UC-002"}, {"Titel UC-002"})

    def test_counts_by_stage(self):
        with self.db.read() as conn:
            counts = rules.counts(conn)
        self.assertEqual((counts["eingang"], counts["umsetzung"], counts["governance"], counts["betrieb"],
                          counts["archiv"], counts["tickets_open"]), (1, 1, 1, 0, 1, 2))
        self.assertEqual((counts["reg_confirmed"], counts["reg_total"]), (0, 1))

    def test_overview_rows_carry_stage_next_step_and_status(self):
        with self.db.read() as conn:
            rows = {row["id"]: row for row in rules.overview(conn, NO_DEADLINE, TODAY)}
        self.assertEqual((rows["UC-001"]["stage"], rows["UC-001"]["next_step"], rows["UC-001"]["attention"]),
                         ("eingang", "Bewerten", "blockierend"))  # offener Konflikt (H07)
        self.assertEqual((rows["UC-002"]["attention"], rows["UC-002"]["next_milestone"]["title"]), ("blockierend", "Pilot"))
        self.assertEqual((rows["UC-003"]["gov_done"], rows["UC-003"]["gov_total"], rows["UC-003"]["open_tickets"]), (0, 6, 1))
        self.assertEqual((rows["UC-004"]["stage"], rows["UC-004"]["attention"], rows["UC-004"]["next_step"]),
                         ("archiv", "keiner", ""))


class WeightedScoreTest(unittest.TestCase):
    CRITERIA = [{"key": "a", "label": "A", "weight": 2}, {"key": "b", "label": "B", "weight": 1}]

    def test_manual_mode_computes_nothing(self):
        self.assertIsNone(rules.weighted_score({"mode": "manuell", "criteria": self.CRITERIA}, {"a": 4, "b": 1}))

    def test_weighted_average(self):
        config = {"mode": "gewichtet", "criteria": self.CRITERIA}
        self.assertEqual(rules.weighted_score(config, {"a": 4, "b": 1}), 3.0)
        self.assertIsNone(rules.weighted_score(config, {"a": 4}))  # unvollständig: kein Gesamtscore


if __name__ == "__main__":
    unittest.main()
