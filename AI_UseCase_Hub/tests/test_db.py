"""Tests für hub/db.py und die Backups in hub/handover.py."""

import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.helpers import PROGRAM_DIR  # noqa: F401 - setzt den Suchpfad

from hub import audit, handover
from hub import db as dbm


class DbCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hubdb_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.path = self.tmp / "hub.db"

    def open(self, **kwargs):
        database = dbm.open_database(self.path, **kwargs)
        self.addCleanup(database.close)
        return database

    def add_usecase(self, database, usecase_id="UC-001", title="Titel"):
        with database.write(user="u", machine="m") as tx:
            tx.execute("INSERT INTO usecases (id, title, title_src, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                       (usecase_id, title, title, dbm.now_ts(), dbm.now_ts()))


class SchemaTest(DbCase):
    def test_new_database_has_schema_and_pragmas(self):
        database = self.open()
        self.assertEqual(database.schema_version(), dbm.latest_version())
        with database.read() as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "delete")  # kein WAL
            self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 2)          # FULL
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertLessEqual({"usecases", "milestones", "releases", "links", "tickets", "validations", "audit",
                              "import_log", "conflicts", "meta", "usecase_scores"}, tables)
        self.assertEqual(database.meta()["revision"], 0)

    def test_every_source_field_has_a_src_column(self):
        database = self.open()
        with database.read() as conn:
            for entity, fields in dbm.SOURCE_FIELDS.items():
                columns = {r[1] for r in conn.execute(f"PRAGMA table_info({entity})")}
                for field in fields:
                    self.assertIn(field, columns)
                    self.assertIn(f"{field}_src", columns)
                for field in dbm.CARE_FIELDS[entity] + dbm.INTERNAL_FIELDS[entity]:
                    self.assertIn(field, columns, f"{entity}.{field}")

    def test_write_is_one_transaction_and_bumps_revision(self):
        database = self.open()
        self.add_usecase(database)
        self.assertEqual(database.meta()["revision"], 1)
        with self.assertRaises(ZeroDivisionError):
            with database.write() as tx:
                tx.execute("UPDATE usecases SET title = 'halb'")
                1 / 0
        with database.read() as conn:
            self.assertEqual(conn.execute("SELECT title FROM usecases").fetchone()[0], "Titel")
        self.assertEqual(database.meta()["revision"], 1)

    def test_foreign_keys_are_enforced(self):
        database = self.open()
        with self.assertRaises(sqlite3.IntegrityError):
            with database.write() as tx:
                tx.execute("INSERT INTO milestones (usecase_id, title) VALUES ('UC-999', 'x')")

    def test_release_ticket_id_is_unique(self):  # Grundlage für S9
        database = self.open()
        self.add_usecase(database)
        with database.write() as tx:
            tx.execute("INSERT INTO tickets (id, created_at, updated_at) VALUES ('T-001', 'x', 'x')")
            tx.execute("INSERT INTO releases (usecase_id, ticket_id) VALUES ('UC-001', 'T-001')")
        with self.assertRaises(sqlite3.IntegrityError):
            with database.write() as tx:
                tx.execute("INSERT INTO releases (usecase_id, ticket_id) VALUES ('UC-001', 'T-001')")

    def test_reopen_keeps_data(self):
        database = self.open()
        self.add_usecase(database)
        database.close()
        again = self.open()
        with again.read() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM usecases").fetchone()[0], 1)


class UpdateFieldTest(DbCase):
    def setUp(self):
        super().setUp()
        self.db = self.open()
        self.add_usecase(self.db)

    def test_update_writes_audit_entry(self):
        with self.db.write(user="anna", machine="pc1") as tx:
            self.assertTrue(dbm.update_field(tx, "usecases", "UC-001", "owner", "Person A", expected=""))
        with self.db.read() as conn:
            result = audit.query(conn, entity="usecases", entity_id="UC-001")
        entry = result["items"][0]
        self.assertEqual((entry["field"], entry["old_value"], entry["new_value"], entry["user"], entry["machine"],
                          entry["source"], entry["field_label"]),
                         ("owner", "", "Person A", "anna", "pc1", "oberfläche", "Owner"))
        self.assertEqual(self.db.meta()["revision"], 2)

    def test_stale_expected_value_is_rejected(self):
        with self.db.write() as tx:
            dbm.update_field(tx, "usecases", "UC-001", "owner", "Person A")
        with self.assertRaises(dbm.StaleValue) as caught:
            with self.db.write() as tx:
                dbm.update_field(tx, "usecases", "UC-001", "owner", "Person B", expected="")
        self.assertEqual(caught.exception.current, "Person A")
        with self.db.read() as conn:
            self.assertEqual(conn.execute("SELECT owner FROM usecases").fetchone()[0], "Person A")

    def test_unchanged_value_writes_nothing(self):
        revision = self.db.meta()["revision"]
        with self.db.write() as tx:
            self.assertFalse(dbm.update_field(tx, "usecases", "UC-001", "title", "Titel"))
        self.assertEqual(self.db.meta()["revision"], revision)

    def test_unknown_field_or_record(self):
        with self.assertRaises(KeyError):
            with self.db.write() as tx:
                dbm.update_field(tx, "usecases", "UC-001", "title_src", "x")
        with self.assertRaises(KeyError):
            with self.db.write() as tx:
                dbm.update_field(tx, "usecases", "UC-001", "id = id; DROP TABLE usecases; --", "x")
        with self.assertRaises(LookupError):
            with self.db.write() as tx:
                dbm.update_field(tx, "usecases", "UC-404", "title", "x")

    def test_audit_query_filters(self):
        with self.db.write(user="anna") as tx:
            dbm.update_field(tx, "usecases", "UC-001", "owner", "Person A")
        with self.db.write(user="anna", source="import") as tx:
            dbm.update_field(tx, "usecases", "UC-001", "title", "Neu")
        with self.db.read() as conn:
            self.assertEqual(audit.query(conn)["total"], 2)
            self.assertEqual(audit.query(conn, source="import")["total"], 1)
            self.assertEqual(audit.query(conn, text="Person")["total"], 1)
            self.assertEqual(audit.query(conn, entity_id="UC-002")["total"], 0)
            self.assertEqual(audit.query(conn)["items"][0]["field"], "title")  # neueste zuerst


class IntegrityTest(DbCase):
    def test_garbage_file_is_reported_as_corrupt(self):
        self.path.write_bytes(b"das ist keine Datenbank" * 200)
        with self.assertRaises(dbm.DatabaseCorrupt):
            dbm.open_database(self.path)

    def test_damaged_pages_fail_integrity_check(self):
        database = self.open()
        for number in range(300):
            self.add_usecase(database, f"UC-{number:03d}", "Titel " * 50)
        database.close()
        raw = bytearray(self.path.read_bytes())
        for offset in range(8192, len(raw) - 4096, 4096):
            raw[offset:offset + 64] = b"\xff" * 64
        self.path.write_bytes(bytes(raw))
        with self.assertRaises(dbm.DatabaseCorrupt):
            dbm.open_database(self.path)

    def test_newer_schema_is_refused(self):
        database = self.open()
        with database.write() as tx:
            tx.execute("UPDATE meta SET schema_version = 99")
        database.close()
        with self.assertRaises(dbm.SchemaTooNew):
            dbm.open_database(self.path)


class MigrationTest(DbCase):
    def with_extra_migration(self, statements):
        original = list(dbm.MIGRATIONS)
        dbm.MIGRATIONS.append((original[-1][0] + 1, statements))
        self.addCleanup(lambda: dbm.MIGRATIONS.__setitem__(slice(None), original))

    def test_backup_is_created_before_each_migration(self):
        database = self.open()
        self.add_usecase(database)
        database.close()
        self.with_extra_migration(["ALTER TABLE usecases ADD COLUMN neu TEXT NOT NULL DEFAULT ''"])
        calls = []

        def before(db_obj, version):
            calls.append(version)
            return handover.create_backup(db_obj, self.tmp / "backups", "migration")

        database = self.open(before_migration=before)
        self.assertEqual(calls, [dbm.latest_version()])
        self.assertEqual(database.schema_version(), dbm.latest_version())
        backups = handover.list_backups(self.tmp / "backups")
        self.assertEqual(len(backups), 1)
        old = sqlite3.connect(backups[0]["path"])
        self.assertEqual(old.execute("SELECT schema_version FROM meta").fetchone()[0], dbm.latest_version() - 1)
        self.assertEqual(old.execute("SELECT COUNT(*) FROM usecases").fetchone()[0], 1)
        old.close()

    def test_new_database_needs_no_backup(self):
        calls = []
        self.open(before_migration=lambda db_obj, version: calls.append(version))
        self.assertEqual(calls, [])

    def test_failed_migration_is_rolled_back(self):
        self.open().close()
        self.with_extra_migration(["ALTER TABLE usecases ADD COLUMN neu TEXT", "DAS IST KEIN SQL"])
        with self.assertRaises(sqlite3.Error):
            dbm.open_database(self.path)
        dbm.MIGRATIONS.pop()
        database = self.open()
        self.assertEqual(database.schema_version(), dbm.latest_version())
        with database.read() as conn:
            self.assertNotIn("neu", {r[1] for r in conn.execute("PRAGMA table_info(usecases)")})


class BackupTest(DbCase):
    def setUp(self):
        super().setUp()
        self.db = self.open()
        self.add_usecase(self.db)
        self.folder = self.tmp / "backups"

    def test_backup_is_a_valid_copy(self):
        target = handover.create_backup(self.db, self.folder, "start")
        self.assertTrue(handover.is_valid(target))
        copy = sqlite3.connect(target)
        self.assertEqual(copy.execute("SELECT title FROM usecases").fetchone()[0], "Titel")
        copy.close()
        self.assertEqual([p.name for p in self.folder.iterdir()], [target.name])  # keine Reste

    def test_only_the_last_30_start_backups_are_kept(self):
        for _ in range(33):
            handover.create_backup(self.db, self.folder, "start")
        handover.create_backup(self.db, self.folder, "migration")
        backups = handover.list_backups(self.folder)
        self.assertEqual(len([b for b in backups if b["label_key"] == "start"]), 30)
        self.assertEqual(len([b for b in backups if b["label_key"] == "migration"]), 1)

    def test_backups_of_the_same_second_keep_their_order(self):
        names = [handover.create_backup(self.db, self.folder, "start").name for _ in range(12)]
        self.assertEqual([b["name"] for b in handover.list_backups(self.folder)], names[::-1])

    def test_latest_valid_backup_skips_damaged_files(self):
        good = handover.create_backup(self.db, self.folder, "start")
        bad = handover.create_backup(self.db, self.folder, "start")
        bad.write_bytes(b"kaputt" * 100)
        self.assertEqual(handover.latest_valid_backup(self.folder)["name"], good.name)
        self.assertIsNone(handover.latest_valid_backup(self.tmp / "leer"))

    def test_restore_replaces_database_and_keeps_the_old_file(self):
        backup = handover.create_backup(self.db, self.folder, "start")
        self.add_usecase(self.db, "UC-002")
        self.db.close()
        self.path.write_bytes(b"kaputt" * 100)
        (self.tmp / "hub.db-journal").write_bytes(b"altes journal")
        kept = handover.restore_backup(backup, self.path)
        self.assertTrue(kept.exists())
        self.assertFalse((self.tmp / "hub.db-journal").exists())
        restored = self.open()
        with restored.read() as conn:
            self.assertEqual([r[0] for r in conn.execute("SELECT id FROM usecases")], ["UC-001"])

    def test_restore_refuses_damaged_backup(self):
        bad = self.folder / "hub_20260101-000000_start.db"
        self.folder.mkdir()
        bad.write_bytes(b"kaputt" * 100)
        with self.assertRaises(ValueError):
            handover.restore_backup(bad, self.path)
        self.assertTrue(self.path.exists())


if __name__ == "__main__":
    unittest.main()
