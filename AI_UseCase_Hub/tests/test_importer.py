"""Tests für hub/importer.py – Regeln S1 bis S7 und Konflikte."""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests.helpers import PROGRAM_DIR  # noqa: F401 - setzt den Suchpfad

import openpyxl

from hub import db as dbm
from hub import importer

UC_FIELDS = {
    "id": "ID", "title": "Titel Use Case", "benefit": "Erwarteter Nutzen (Input Melder)",
    "folder_link": "Link zu Ordner", "description": None, "area": None, "reporter": None,
    "reporter_email": None, "submitted_at": None,
}
UC_HEADER = ["ID", "Titel Use Case", "Link zu Ordner", "Erwarteter Nutzen (Input Melder)", "Status Use Case"]
T_FIELDS = {
    "id": "ID", "title": "Titel", "description": "Beschreibung", "affected_tool_raw": "Betroffenes Tool",
    "reporter": "Melder:in", "submitted_at": "Gemeldet am",
}
T_HEADER = ["ID", "Titel", "Beschreibung", "Betroffenes Tool", "Melder:in", "Gemeldet am"]


def write_xlsx(path, header, rows, lead_rows=0, sheet_title="Tabelle1"):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = sheet_title
    for _ in range(lead_rows):
        sheet.append([])
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    # Änderungsdatum sicher verändern, auch auf Dateisystemen mit grober Auflösung
    stamp = time.time() + write_xlsx.counter
    write_xlsx.counter += 2
    os.utime(path, (stamp, stamp))


write_xlsx.counter = 0


class ImporterCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hubimp_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.db = dbm.open_database(self.tmp / "hub.db")
        self.addCleanup(self.db.close)
        self.uc_path = self.tmp / "UseCases.xlsx"
        self.t_path = self.tmp / "Tickets.xlsx"
        self.paths = {"usecases": self.uc_path, "tickets": self.t_path}
        self.columns = {
            "usecases": {"id_prefix": "UC-", "fields": dict(UC_FIELDS)},
            "tickets": {"id_prefix": "T-", "fields": dict(T_FIELDS)},
        }
        self.errors = []
        self.imp = importer.Importer(
            self.db, columns=lambda: self.columns, path_for=lambda key: self.paths[key],
            tmp_dir=self.tmp / "tmp", user="tester", machine="pc", log_error=self.errors.append, retry_pause=0)

    def usecases(self, rows, **kwargs):
        write_xlsx(self.uc_path, UC_HEADER, rows, **kwargs)

    def run_uc(self):
        return self.imp.run("usecases")[0]

    def row(self, entity, entity_id):
        with self.db.read() as conn:
            found = conn.execute(f"SELECT * FROM {entity} WHERE id = ?", (entity_id,)).fetchone()
        return dict(found) if found else None

    def count(self, table, where="1=1"):
        with self.db.read() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]

    def edit(self, entity, entity_id, field, value):
        with self.db.write(user="tester", machine="pc") as tx:
            dbm.update_field(tx, entity, entity_id, field, value)

    def revision(self):
        return self.db.meta()["revision"]


class NewAndDuplicateTest(ImporterCase):
    def test_new_id_creates_usecase_in_phase_eingang(self):  # S3
        self.usecases([[1, "Protokolle zusammenfassen", "https://x/1", "spart Zeit", "Neu"]])
        summary = self.run_uc()
        self.assertEqual((summary["status"], summary["added"], summary["row_count"]), ("ok", 1, 1))
        row = self.row("usecases", "UC-001")
        self.assertEqual(row["title"], "Protokolle zusammenfassen")
        self.assertEqual(row["title_src"], "Protokolle zusammenfassen")
        self.assertEqual(row["benefit"], "spart Zeit")
        self.assertEqual(row["folder_link"], "https://x/1")
        self.assertEqual((row["phase"], row["in_source"]), ("Eingang", 1))
        self.assertEqual(self.count("audit", "entity_id = 'UC-001' AND source = 'import'"), 1)
        self.assertEqual(self.revision(), 1)

    def test_new_ticket_has_status_neu(self):  # S3
        write_xlsx(self.t_path, T_HEADER, [[7, "Antwort falsch", "Details", "UC-001 – Protokolle", "A. B.", "2026-11-03"]])
        summary = self.imp.run("tickets")[0]
        self.assertEqual(summary["added"], 1)
        row = self.row("tickets", "T-007")
        self.assertEqual((row["status"], row["affected_tool_raw"], row["submitted_at"]),
                         ("Neu", "UC-001 – Protokolle", "2026-11-03"))

    def test_duplicate_id_first_row_wins_and_is_counted(self):  # S3
        self.usecases([[1, "Erste Zeile", "", "", ""], [1, "Flow-Wiederholung", "", "", ""], [2, "Zweiter", "", "", ""]])
        summary = self.run_uc()
        self.assertEqual((summary["added"], summary["duplicates"], summary["row_count"]), (2, 1, 3))
        self.assertEqual(self.row("usecases", "UC-001")["title"], "Erste Zeile")
        with self.db.read() as conn:
            log = conn.execute("SELECT * FROM import_log ORDER BY id DESC").fetchone()
        self.assertEqual(log["duplicates"], 1)
        self.assertIn("UC-001", log["message"])

    def test_rows_without_id_are_skipped_and_reported(self):
        self.usecases([[None, "Ohne ID", "", "", ""], [3, "Mit ID", "", "", ""], [None, None, None, None, None]])
        summary = self.run_uc()
        self.assertEqual((summary["added"], summary["missing_id"], summary["row_count"]), (1, 1, 2))
        self.assertEqual(self.imp.state["usecases"]["missing_id"], 1)
        self.assertEqual(self.count("usecases"), 1)

    def test_id_spellings_are_normalized(self):
        self.assertEqual(importer.normalize_id(7, "UC-"), "UC-007")
        self.assertEqual(importer.normalize_id(7.0, "UC-"), "UC-007")
        self.assertEqual(importer.normalize_id(" 12 ", "UC-"), "UC-012")
        self.assertEqual(importer.normalize_id("uc-7", "UC-"), "UC-007")
        self.assertEqual(importer.normalize_id("UC-1234", "UC-"), "UC-1234")
        self.assertEqual(importer.normalize_id("ALT-3", "UC-"), "ALT-3")
        self.assertIsNone(importer.normalize_id("  ", "UC-"))
        self.assertIsNone(importer.normalize_id(None, "UC-"))

    def test_header_is_found_despite_spaces_case_and_leading_rows(self):
        write_xlsx(self.uc_path, [" id", "TITEL  use case ", "Link zu Ordner ", "Erwarteter Nutzen (Input Melder)"],
                   [[5, "Fünf", "", "n"]], lead_rows=2)
        self.assertEqual(self.run_uc()["added"], 1)
        self.assertEqual(self.row("usecases", "UC-005")["benefit"], "n")

    def test_second_import_without_changes_writes_nothing(self):
        self.usecases([[1, "A", "", "", ""]])
        self.run_uc()
        revision, audits = self.revision(), self.count("audit")
        summary = self.run_uc()
        self.assertEqual((summary["added"], summary["changed"], summary["conflicts"]), (0, 0, 0))
        self.assertEqual((self.revision(), self.count("audit")), (revision, audits))


class ChangedSourceFieldTest(ImporterCase):
    def setUp(self):
        super().setUp()
        self.usecases([[1, "Alter Titel", "", "alter Nutzen", ""]])
        self.run_uc()

    def test_changed_source_field_without_hub_change_is_taken_over(self):  # S4
        self.usecases([[1, "Neuer Titel", "", "alter Nutzen", ""]])
        summary = self.run_uc()
        self.assertEqual((summary["changed"], summary["conflicts"]), (1, 0))
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["title"], row["title_src"]), ("Neuer Titel", "Neuer Titel"))
        with self.db.read() as conn:
            entry = conn.execute("SELECT * FROM audit WHERE field = 'title' ORDER BY id DESC").fetchone()
        self.assertEqual((entry["old_value"], entry["new_value"], entry["source"]), ("Alter Titel", "Neuer Titel", "import"))

    def test_changed_source_field_with_hub_change_creates_conflict(self):  # S5
        self.edit("usecases", "UC-001", "title", "Titel aus dem Hub")
        self.usecases([[1, "Titel aus der Quelle", "", "alter Nutzen", ""]])
        summary = self.run_uc()
        self.assertEqual((summary["changed"], summary["conflicts"]), (0, 1))
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["title"], row["title_src"]), ("Titel aus dem Hub", "Alter Titel"))  # nie still überschreiben
        with self.db.read() as conn:
            conflict = dict(conn.execute("SELECT * FROM conflicts").fetchone())
        self.assertEqual((conflict["hub_value"], conflict["old_src_value"], conflict["new_src_value"], conflict["status"]),
                         ("Titel aus dem Hub", "Alter Titel", "Titel aus der Quelle", "offen"))

    def test_conflict_is_not_duplicated_by_repeated_imports(self):
        self.edit("usecases", "UC-001", "title", "Hub")
        self.usecases([[1, "Quelle", "", "alter Nutzen", ""]])
        self.run_uc()
        revision = self.revision()
        self.assertEqual(self.run_uc()["conflicts"], 0)
        self.assertEqual(self.count("conflicts"), 1)
        self.assertEqual(self.revision(), revision)
        # Die Quelle ändert sich erneut: derselbe Konflikt zeigt den neuesten Quellwert.
        self.usecases([[1, "Quelle 2", "", "alter Nutzen", ""]])
        self.run_uc()
        self.assertEqual(self.count("conflicts"), 1)
        with self.db.read() as conn:
            self.assertEqual(conn.execute("SELECT new_src_value FROM conflicts").fetchone()[0], "Quelle 2")

    def test_resolve_take_source(self):  # S5
        self.edit("usecases", "UC-001", "title", "Hub")
        self.usecases([[1, "Quelle", "", "alter Nutzen", ""]])
        self.run_uc()
        importer.resolve_conflict(self.db, 1, "quelle", "tester", "pc")
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["title"], row["title_src"]), ("Quelle", "Quelle"))
        self.assertEqual(self.count("conflicts", "status = 'entschieden' AND resolution = 'Quelle übernommen'"), 1)
        self.assertEqual(self.run_uc()["conflicts"], 0)
        with self.assertRaises(ValueError):
            importer.resolve_conflict(self.db, 1, "hub", "tester", "pc")

    def test_resolve_keep_hub_sets_src_to_new_source_value(self):  # S5
        self.edit("usecases", "UC-001", "title", "Hub")
        self.usecases([[1, "Quelle", "", "alter Nutzen", ""]])
        self.run_uc()
        importer.resolve_conflict(self.db, 1, "hub", "tester", "pc")
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["title"], row["title_src"]), ("Hub", "Quelle"))
        self.assertEqual(self.run_uc()["conflicts"], 0)
        self.assertEqual(self.count("conflicts", "status = 'offen'"), 0)
        self.assertGreaterEqual(self.count("audit", "field = 'title' AND source = 'oberfläche'"), 2)

    def test_conflict_disappears_when_source_goes_back_or_matches_hub(self):
        self.edit("usecases", "UC-001", "title", "Hub")
        self.usecases([[1, "Quelle", "", "alter Nutzen", ""]])
        self.run_uc()
        self.usecases([[1, "Alter Titel", "", "alter Nutzen", ""]])  # Quelle wieder wie vorher
        self.run_uc()
        self.assertEqual(self.count("conflicts", "status = 'offen'"), 0)
        self.assertEqual(self.row("usecases", "UC-001")["title"], "Hub")
        self.usecases([[1, "Hub", "", "alter Nutzen", ""]])  # Quelle zieht mit dem Hub gleich
        summary = self.run_uc()
        self.assertEqual(summary["conflicts"], 0)
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["title"], row["title_src"]), ("Hub", "Hub"))

    def test_care_fields_are_never_touched_by_import(self):  # S6
        self.edit("usecases", "UC-001", "phase", "In Bearbeitung")
        self.edit("usecases", "UC-001", "owner", "Person A")
        self.usecases([[1, "Neuer Titel", "", "neuer Nutzen", "Abgeschlossen"]])
        self.run_uc()
        row = self.row("usecases", "UC-001")
        self.assertEqual((row["phase"], row["owner"]), ("In Bearbeitung", "Person A"))

    def test_unmapped_fields_stay_untouched(self):
        self.edit("usecases", "UC-001", "description", "im Hub ergänzt")
        self.usecases([[1, "Alter Titel", "", "alter Nutzen", ""]])
        self.assertEqual(self.run_uc()["conflicts"], 0)
        self.assertEqual(self.row("usecases", "UC-001")["description"], "im Hub ergänzt")

    def test_vanished_id_is_kept_and_reported_once(self):  # S7
        self.usecases([[1, "Alter Titel", "", "alter Nutzen", ""], [2, "Zwei", "", "", ""]])
        self.run_uc()
        self.usecases([[2, "Zwei", "", "", ""]])
        summary = self.run_uc()
        self.assertIn("UC-001", summary["message"])
        self.assertEqual(self.row("usecases", "UC-001")["in_source"], 0)
        self.assertEqual(self.count("usecases"), 2)
        self.assertNotIn("UC-001", self.run_uc()["message"])
        self.usecases([[1, "Alter Titel", "", "alter Nutzen", ""], [2, "Zwei", "", "", ""]])
        self.run_uc()
        self.assertEqual(self.row("usecases", "UC-001")["in_source"], 1)


class UnreadableSourceTest(ImporterCase):
    def setUp(self):
        super().setUp()
        self.usecases([[1, "A", "", "", ""]])
        self.run_uc()

    def test_missing_column_aborts_with_clear_message(self):
        write_xlsx(self.uc_path, ["ID", "Titel Use Case", "Link zu Ordner"], [[1, "B", ""], [2, "C", ""]])
        summary = self.run_uc()
        self.assertEqual(summary["status"], "fehler")
        self.assertIn("Spalte ‚Erwarteter Nutzen (Input Melder)‘ in Quelle 1 nicht gefunden", summary["message"])
        self.assertIn("Einstellungen", summary["message"])
        self.assertEqual(self.imp.state["usecases"]["state"], "spalte_fehlt")
        self.assertEqual(self.count("usecases"), 1)  # kein Teilimport
        self.assertEqual(self.row("usecases", "UC-001")["title"], "A")

    def test_missing_id_column(self):
        write_xlsx(self.uc_path, UC_HEADER[1:], [["B", "", "", ""]])
        summary = self.run_uc()
        self.assertIn("Spalte ‚ID‘ in Quelle 1 nicht gefunden", summary["message"])

    def test_unmapped_required_field(self):
        self.columns["tickets"]["fields"]["id"] = None
        write_xlsx(self.t_path, T_HEADER, [])
        summary = self.imp.run("tickets")[0]
        self.assertEqual((summary["status"], self.imp.state["tickets"]["state"]), ("fehler", "zuordnung_fehlt"))

    def test_locked_file_is_retried_three_times(self):  # S2
        calls = []

        def locked(src, dst):
            calls.append(1)
            raise PermissionError(13, "Der Prozess kann nicht auf die Datei zugreifen")

        self.imp.copy = locked
        self.usecases([[1, "B", "", "", ""], [2, "C", "", "", ""]])
        summary = self.run_uc()
        self.assertEqual(len(calls), 3)
        self.assertEqual((summary["status"], self.imp.state["usecases"]["state"]), ("fehler", "nicht_lesbar"))
        self.assertIn("Quelle 1 konnte nicht gelesen werden", summary["message"])
        self.assertEqual(self.count("usecases"), 1)
        self.assertEqual(self.row("usecases", "UC-001")["title"], "A")
        self.assertEqual(list((self.tmp / "tmp").iterdir()), [])

    def test_locked_file_succeeds_on_later_attempt(self):  # S2
        calls = []

        def flaky(src, dst):
            calls.append(1)
            if len(calls) < 3:
                raise PermissionError(13, "gesperrt")
            shutil.copyfile(src, dst)

        self.imp.copy = flaky
        self.usecases([[1, "B", "", "", ""], [2, "C", "", "", ""]])
        summary = self.run_uc()
        self.assertEqual((summary["status"], summary["added"], summary["changed"]), ("ok", 1, 1))

    def test_half_synced_file_does_not_crash(self):  # S2
        full = self.uc_path.read_bytes()
        self.uc_path.write_bytes(full[: len(full) // 2])
        summary = self.run_uc()
        self.assertEqual(summary["status"], "fehler")
        self.assertEqual(self.imp.state["usecases"]["state"], "nicht_lesbar")
        self.assertEqual(self.count("usecases"), 1)

    def test_missing_file_and_unconfigured_path(self):
        self.uc_path.unlink()
        self.assertEqual(self.run_uc()["status"], "fehler")
        self.paths["usecases"] = None
        self.run_uc()
        self.assertEqual(self.imp.state["usecases"]["state"], "nicht_eingerichtet")

    def test_repeated_identical_error_is_logged_once(self):
        self.uc_path.unlink()
        self.imp.check()
        self.imp.check()
        self.imp.check()
        self.assertEqual(self.count("import_log", "status = 'fehler' AND source = 'usecases'"), 1)


class WatcherTest(ImporterCase):
    def test_check_imports_only_when_file_changed(self):  # S1
        self.usecases([[1, "A", "", "", ""]])
        write_xlsx(self.t_path, T_HEADER, [])
        self.assertEqual(len(self.imp.check()), 2)   # Import beim Start
        self.assertEqual(self.imp.check(), [])        # unverändert
        self.usecases([[1, "A", "", "", ""], [2, "B", "", "", ""]])
        runs = self.imp.check()
        self.assertEqual([(r["source"], r["added"]) for r in runs], [("usecases", 1)])
        self.assertEqual(self.imp.state["usecases"]["state"], "ok")
        self.assertTrue(self.imp.state["usecases"]["last_success"])

    def test_failed_source_is_retried_on_next_check(self):
        self.usecases([[1, "A", "", "", ""]])
        write_xlsx(self.t_path, T_HEADER, [])
        original = self.imp.copy
        self.imp.copy = lambda src, dst: (_ for _ in ()).throw(PermissionError(13, "gesperrt"))
        self.imp.check()
        self.assertEqual(self.count("usecases"), 0)
        self.imp.copy = original
        self.imp.check()
        self.assertEqual(self.count("usecases"), 1)

    def test_background_thread_picks_up_changes(self):
        self.usecases([[1, "A", "", "", ""]])
        write_xlsx(self.t_path, T_HEADER, [])
        self.imp.start(interval=0.05)
        self.addCleanup(self.imp.stop)
        deadline = time.time() + 5
        while time.time() < deadline and self.count("usecases") < 1:
            time.sleep(0.05)
        self.usecases([[1, "A", "", "", ""], [2, "B", "", "", ""]])
        while time.time() < deadline and self.count("usecases") < 2:
            time.sleep(0.05)
        self.assertEqual(self.count("usecases"), 2)


if __name__ == "__main__":
    unittest.main()
