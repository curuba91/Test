"""Tests Phase 4: Vorabcheck – jedes der sieben Ergebnisse, Platzhalter-Kennzeichnung, Prompt."""

import copy
import json
import unittest

from tests.helpers import PROGRAM_DIR, HubTestCase

from hub import validation

RULES, ERRORS = validation.load_rules(PROGRAM_DIR)
PFAD_A = {"reguliert": "ja", "art": "enterprise_tool", "eingebettet": "nein", "selbst_gewaehlt": "ja",
          "geschulte_person": "ja", "freigabe_dokumentiert": "ja"}
PFAD_B = {"reguliert": "ja", "art": "eigene_anwendung", "eingebettet": "ja", "direkter_bezug": "nein"}


def result(answers, rules=RULES):
    return validation.evaluate(rules, answers)["result"]


class DecisionTest(unittest.TestCase):
    def test_shipped_rules_are_valid(self):
        self.assertEqual(ERRORS, [])
        self.assertEqual(len(RULES["questions"]), 11)

    def test_each_of_the_seven_results_is_reachable(self):
        cases = {
            "keine_ki": {"reguliert": "ja", "art": "keine_ki"},
            "ausserhalb": {"reguliert": "nein", "art": "enterprise_tool"},
            "klaerung": {"reguliert": "ja", "art": "unklar"},
            "pfad_a_erfuellt": PFAD_A,
            "pfad_a_nicht_erfuellt": dict(PFAD_A, geschulte_person="nein"),
            "pfad_b": PFAD_B,
            "pfad_b_direkt": dict(PFAD_B, direkter_bezug="ja"),
        }
        self.assertEqual(set(cases), set(RULES["results"]))
        for expected, answers in cases.items():
            self.assertEqual(result(answers), expected, expected)

    def test_order_and_unclear_answers(self):
        self.assertEqual(result({"reguliert": "nein", "art": "keine_ki"}), "keine_ki")       # Frage 2 vor Frage 1
        self.assertEqual(result({}), "klaerung")                                               # unbeantwortet
        self.assertEqual(result(dict(PFAD_A, freigabe_dokumentiert="unklar")), "klaerung")
        self.assertEqual(result({k: v for k, v in PFAD_B.items() if k != "direkter_bezug"}), "klaerung")
        self.assertEqual(result(dict(PFAD_A, eingebettet="ja", direkter_bezug="nein")), "pfad_b")  # eingebettet -> Pfad B
        self.assertEqual(result(dict(PFAD_A, zweitpruefung="unklar")), "pfad_a_erfuellt")      # Frage 9 entscheidet nicht

    def test_questions_disappear_when_no_longer_relevant(self):
        visible = validation.evaluate(RULES, {"reguliert": "ja", "art": "keine_ki", "eingebettet": "ja"})
        self.assertEqual(visible["visible"], ["reguliert", "art"])
        self.assertNotIn("eingebettet", visible["answers"])
        self.assertEqual(len(validation.evaluate(RULES, {"reguliert": "ja"})["visible"]), 11)

    def test_placeholder_rules_are_marked_incomplete_and_nothing_is_invented(self):
        answers = dict(PFAD_B, entscheidungsfolge="hoch", modelleinfluss="mittel", faehigkeiten=["chat", "extraktion"])
        evaluation = validation.evaluate(RULES, answers)
        self.assertTrue(evaluation["incomplete"])
        self.assertEqual(evaluation["incomplete_parts"], ["Entscheidungslogik", "Risikomatrix", "Kontrollen"])
        self.assertEqual((evaluation["risk"], evaluation["controls"]), (None, []))

    def test_filled_rules_deliver_risk_and_controls(self):
        rules = copy.deepcopy(RULES)
        for part in ("decision", "risk_matrix", "controls"):
            rules[part]["status"] = "FEST"
        rules["risk_matrix"]["values"]["hoch"]["mittel"] = "hoch"
        rules["controls"]["by_capability"].update(chat=["Kontrolle 1", "Kontrolle 2"], extraktion=["Kontrolle 2", "Kontrolle 3"])
        self.assertEqual(validation.check_rules(rules), [])
        answers = dict(PFAD_B, entscheidungsfolge="hoch", modelleinfluss="mittel", faehigkeiten=["chat", "extraktion"])
        evaluation = validation.evaluate(rules, answers)
        self.assertEqual((evaluation["incomplete"], evaluation["risk"]), (False, "hoch"))
        self.assertEqual(evaluation["controls"], ["Kontrolle 1", "Kontrolle 2", "Kontrolle 3"])

    def test_broken_rules_are_reported(self):
        rules = copy.deepcopy(RULES)
        rules["decision"]["rules"][0]["result"] = "gibtsnicht"
        rules["decision"]["rules"][1]["if"] = {"reguliert": ["vielleicht"]}
        rules["decision"]["rules"][-1]["if"] = {"art": ["keine_ki"]}
        errors = "\n".join(validation.check_rules(rules))
        for text in ("decision.rules[0]", "unbekannte Antwort", "letzte Regel"):
            self.assertIn(text, errors)

    def test_prompt_demands_no_invented_facts_and_marks_assumptions(self):
        evaluation = validation.evaluate(RULES, PFAD_A)
        usecase = {"id": "UC-001", "title": "Protokolle", "description": "", "benefit": "spart Zeit"}
        german = validation.build_prompt(RULES, usecase, evaluation, "de")
        for text in ("Erfinde keine Fakten", "ANNAHME:", "Abschnittsverweis", "offener Fragen an die Qualitätsfunktion",
                     "ersetzt keine Freigabe", "UC-001: Protokolle", "(nicht angegeben)", "Pfad A – Bedingungen erfüllt",
                     "2. Art der Lösung – freigegebenes Enterprise-GenAI-Tool"):
            self.assertIn(text, german)
        english = validation.build_prompt(RULES, usecase, evaluation, "en")
        for text in ("Do not invent facts", "ASSUMPTION:", "section reference", "Path A – conditions met", "approved enterprise GenAI tool"):
            self.assertIn(text, english)
        self.assertNotIn("{", german + english)


class ValidationApiTest(HubTestCase):
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

    def test_preview_save_and_latest_run_counts(self):
        rules = self.call("GET", "/api/validation")
        self.assertEqual(rules["incomplete_parts"], ["Entscheidungslogik", "Risikomatrix", "Kontrollen"])
        self.assertIn("ersetzt keine Freigabe", rules["notice"]["de"])
        self.assertEqual(self.call("POST", "/api/validation/preview", {"answers": PFAD_B})["result"], "pfad_b")

        detail = self.call("POST", "/api/usecases/UC-001/validations", {"answers": PFAD_B, "lang": "de"})
        run = detail["validations"][0]
        self.assertEqual((run["label"], run["incomplete_parts"][0], run["rules_version"]),
                         ("Pfad B – formales Risiko-Assessment", "Entscheidungslogik", "0.1"))
        self.assertIn("UC-001", run["prompt_text"])
        self.assertEqual((detail["usecase"]["reg_status"], detail["usecase"]["reg_result"]),
                         ("Vorabcheck erfolgt", "Pfad B – formales Risiko-Assessment"))
        self.assertEqual({s["key"]: s["state"] for s in detail["stepper"]["steps"]}["eingeordnet"], "teil")

        detail = self.call("POST", "/api/usecases/UC-001/validations", {"answers": PFAD_A, "lang": "en"})
        self.assertEqual([r["result"] for r in detail["validations"]], ["pfad_a_erfuellt", "pfad_b"])
        self.assertEqual(detail["validations"][0]["prompt_lang"], "en")
        self.assertEqual(detail["usecase"]["reg_result"], "Pfad A – Bedingungen erfüllt")

    def test_confirmed_classification_is_not_touched(self):
        self.call("PATCH", "/api/usecases/UC-001", {"field": "reg_status", "value": "bestätigt"})
        self.call("PATCH", "/api/usecases/UC-001", {"field": "reg_result", "value": "Pfad B laut QA"})
        detail = self.call("POST", "/api/usecases/UC-001/validations", {"answers": PFAD_A})
        self.assertEqual((detail["usecase"]["reg_status"], detail["usecase"]["reg_result"]), ("bestätigt", "Pfad B laut QA"))

    def test_broken_rules_file_is_reported(self):
        path = self.program / "validation_rules.json"
        rules = json.loads(path.read_text(encoding="utf-8"))
        del rules["results"]["pfad_b"]
        path.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
        result = self.call("POST", "/api/validation/preview", {"answers": {}}, expect=409)
        self.assertIn("Regelwerk", result["error"]["message"])
        self.call("GET", "/api/usecases/UC-001")  # Detailseite bleibt nutzbar
        self.call("POST", "/api/usecases/UC-404/validations", {"answers": {}}, expect=409)


if __name__ == "__main__":
    unittest.main()
