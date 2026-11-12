import copy
import json
import os
import unittest

from tests.helpers import PROGRAM_DIR, HubTestCase

from hub import config
from hub.config import Config, check_site


def shipped_site():
    with open(PROGRAM_DIR / "standort.json", encoding="utf-8") as handle:
        return json.load(handle)


class SiteConfigTest(unittest.TestCase):
    def test_shipped_file_is_valid_and_lists_open_points(self):
        result = check_site(shipped_site())
        self.assertEqual(result["errors"], [])
        text = "\n".join(result["open"])
        self.assertIn("deadline.date", text)
        self.assertIn("columns.tickets.fields.id", text)
        self.assertIn("value_lists.usecase_type", text)
        self.assertIn("labels: Platzhalter", text)
        self.assertIn("nicht bestätigt bei phase, origin", text)

    def test_logic_list_keys_are_fixed(self):
        site = shipped_site()
        site["value_lists"]["phase"]["entries"][0]["key"] = "Neu gemeldet"
        errors = check_site(site)["errors"]
        self.assertTrue(any("value_lists.phase" in e and "fest" in e for e in errors), errors)

    def test_labels_and_aliases_are_adaptable(self):
        site = shipped_site()
        entry = site["value_lists"]["phase"]["entries"][2]
        entry["label"] = "Implementiert"
        entry["aliases"] = ["Done", "implementiert"]
        site["value_lists"]["usecase_type"] = {"status": "FEST", "values": ["Prompt", "Agent"]}
        self.assertEqual(check_site(site)["errors"], [])

    def test_alias_for_two_keys_is_rejected(self):
        site = shipped_site()
        entries = site["value_lists"]["phase"]["entries"]
        entries[0]["aliases"] = ["neu"]
        entries[1]["aliases"] = ["Neu"]
        self.assertTrue(any("Alias" in e for e in check_site(site)["errors"]))

    def test_weighted_score_needs_all_weights(self):
        site = shipped_site()
        site["score"]["mode"] = "gewichtet"
        self.assertTrue(any("weight" in e for e in check_site(site)["errors"]))
        for item in site["score"]["criteria"]:
            item["weight"] = 1
        self.assertEqual(check_site(site)["errors"], [])

    def test_bad_deadline_and_duplicate_column(self):
        site = shipped_site()
        site["deadline"]["date"] = "31.12.2026"
        site["columns"]["usecases"]["fields"]["description"] = " titel use case "
        errors = "\n".join(check_site(site)["errors"])
        self.assertIn("deadline.date", errors)
        self.assertIn("title und description", errors)

    def test_confirmed_deadline_is_no_longer_open(self):
        site = shipped_site()
        site["deadline"]["date"] = "2027-06-30"
        result = check_site(site)
        self.assertEqual(result["errors"], [])
        self.assertFalse(any("deadline" in o for o in result["open"]))


class LocalConfigTest(HubTestCase):
    def test_broken_site_file_is_reported_not_fatal(self):
        (self.program / "standort.json").write_text('{"config_version": 1,,}', encoding="utf-8")
        cfg = self.make_config()
        self.assertEqual(cfg.site, {})
        self.assertIn("Zeile 1", cfg.site_check["errors"][0])

    def test_paths_are_stored_relative_to_program_folder(self):
        cfg = self.make_config()
        source = self.team / "Quellen" / "UseCases.xlsx"
        source.parent.mkdir()
        source.write_bytes(b"")
        stored = cfg.to_stored(str(source))
        self.assertEqual(stored, "../Quellen/UseCases.xlsx")
        self.assertEqual(cfg.resolve(stored), source)
        self.assertEqual(cfg.to_stored('  "../Quellen/UseCases.xlsx" '), "../Quellen/UseCases.xlsx")
        self.assertIsNone(cfg.check_path("source_usecases", stored))

    def test_path_checks_give_plain_messages(self):
        cfg = self.make_config()
        self.assertIn("nicht gefunden", cfg.check_path("source_usecases", "../fehlt.xlsx"))
        self.assertIn(".xlsx", cfg.check_path("source_usecases", "../datei.csv"))
        self.assertIn("nicht gefunden", cfg.check_path("team_folder", "../gibt_es_nicht"))
        self.assertIn("lokale Datenordner", cfg.check_path("team_folder", cfg.to_stored(str(self.data))))
        self.assertFalse(cfg.is_configured())

    def test_default_team_folder_is_applied_and_saved(self):
        cfg = self.make_config()
        self.assertEqual(cfg.local["paths"]["team_folder"], "..")
        self.assertEqual(cfg.resolve(".."), self.team)
        self.assertEqual(self.make_config().local["paths"]["team_folder"], "..")

    def test_broken_local_config_is_reset_and_kept(self):
        self.data.mkdir(parents=True)
        (self.data / "config.json").write_text("{kaputt", encoding="utf-8")
        cfg = self.make_config()
        self.assertEqual(cfg.local["port"], 8765)
        self.assertTrue(cfg.warnings)
        self.assertTrue([n for n in os.listdir(self.data) if n.startswith("config.defekt-")])

    def test_publish_default_paths_writes_site_file(self):
        for name in ("UseCases.xlsx", "Tickets.xlsx"):
            (self.team / name).write_bytes(b"")
        cfg = self.make_config()
        with self.assertRaises(ValueError):
            cfg.publish_default_paths()
        cfg.local["paths"].update(source_usecases="../UseCases.xlsx", source_tickets="../Tickets.xlsx")
        cfg.save_local()
        before = copy.deepcopy(cfg.site)
        cfg.publish_default_paths()
        after = json.loads((self.program / "standort.json").read_text(encoding="utf-8"))
        self.assertEqual(after["default_paths"]["source_tickets"], "../Tickets.xlsx")
        before["default_paths"] = after["default_paths"]
        self.assertEqual(before, after)  # sonst nichts verändert
        # Ein zweiter Rechner (leerer lokaler Ordner) ist damit ohne Einrichtung fertig.
        other = Config(program_dir=self.program, data_dir=self.tmp / "local2")
        self.assertTrue(other.is_configured())

    def test_data_dir_prefers_env_then_localappdata(self):
        old = dict(os.environ)
        try:
            os.environ[config.ENV_DATA_DIR] = str(self.tmp / "x")
            self.assertEqual(config.default_data_dir(), self.tmp / "x")
            del os.environ[config.ENV_DATA_DIR]
            os.environ["LOCALAPPDATA"] = str(self.tmp / "lad")
            self.assertEqual(config.default_data_dir(), self.tmp / "lad" / "AI_UseCase_Hub")
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
