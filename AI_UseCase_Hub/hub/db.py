"""Verbindung, Schema, Migrationen (Kapitel 5)."""

import contextlib
import datetime
import sqlite3
import threading
from pathlib import Path

# Quellfelder: kommen aus der Quell-Excel, haben je ein ``<feld>_src`` (Regeln S4/S5).
SOURCE_FIELDS = {
    "usecases": ["title", "description", "area", "reporter", "benefit", "folder_link"],
    "tickets": ["title", "description", "reporter", "affected_tool_raw"],
}
# Nur intern: kommen aus der Quelle, werden im Hub nicht geändert und nie exportiert.
INTERNAL_FIELDS = {
    "usecases": ["reporter_email", "submitted_at"],
    "tickets": ["submitted_at"],
}
# Pflegefelder: gehören ausschließlich dem Hub (Regel S6).
CARE_FIELDS = {
    "usecases": [
        "phase", "merged_into", "owner", "type", "origin", "score",
        "reg_status", "reg_result", "reg_reference", "reg_confirmed_at",
        "sponsor_status", "sponsor_date",
        "board_status", "board_date", "board_note",
        "portal_status", "portal_link", "comm_status", "comm_date",
        "lc_owner", "version", "next_review", "last_review",
        "needs_help", "help_note", "notes",
    ],
    "tickets": [
        "usecase_id", "type", "severity", "status", "assignee", "fix_version",
        "cause", "solution", "resolved_at", "closed_at",
    ],
}
ID_PREFIX_MANUAL = {"usecases": "M-", "tickets": "TM-"}

FIELD_LABELS = {
    "title": "Titel", "description": "Beschreibung", "area": "Bereich", "reporter": "Melder:in",
    "benefit": "Nutzen", "folder_link": "Link zum Ordner", "affected_tool_raw": "Betroffenes Tool",
    "reporter_email": "E-Mail", "submitted_at": "Eingangsdatum", "phase": "Phase",
    "merged_into": "Zusammengeführt mit", "owner": "Owner", "type": "Typ", "origin": "Herkunft",
    "score": "Score", "reg_status": "Einordnung", "reg_result": "Ergebnis der Einordnung",
    "reg_reference": "Verweis auf Assessment", "reg_confirmed_at": "Einordnung bestätigt am",
    "sponsor_status": "Sponsor", "sponsor_date": "Sponsor-Abstimmung am", "board_status": "Gremium",
    "board_date": "Gremium am", "board_note": "Notiz des Gremiums", "portal_status": "Portal",
    "portal_link": "Link im Portal", "comm_status": "Kommunikation", "comm_date": "Kommuniziert am",
    "lc_owner": "Life-Cycle-Owner", "version": "Version", "next_review": "Nächstes Review",
    "last_review": "Letztes Review", "needs_help": "Hilfe angefordert", "help_note": "Hilfe-Notiz",
    "notes": "Notizen", "usecase_id": "Use Case", "severity": "Schwere", "status": "Status",
    "assignee": "Zuständig", "fix_version": "Fix-Version", "cause": "Ursache", "solution": "Lösung",
    "resolved_at": "Gelöst am", "closed_at": "Geschlossen am", "angelegt": "Angelegt",
}
ENTITY_LABELS = {"usecases": "Use Case", "tickets": "Ticket"}


def now_ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def today() -> str:
    return datetime.date.today().isoformat()


class DatabaseCorrupt(Exception):
    """Die Datenbankdatei ist beschädigt oder keine SQLite-Datei."""


class SchemaTooNew(Exception):
    """Die Datenbank stammt von einer neueren Programmversion."""


class StaleValue(Exception):
    """Der erwartete alte Wert stimmt nicht mehr (z. B. Änderung in einem zweiten Tab)."""

    def __init__(self, current):
        super().__init__("Der Wert wurde inzwischen geändert.")
        self.current = current


def _text(name, default=""):
    return f"{name} TEXT NOT NULL DEFAULT '{default}'"


def _source_columns(entity):
    columns = []
    for field in SOURCE_FIELDS[entity]:
        columns += [_text(field), _text(f"{field}_src")]
    return columns


_USECASE_COLUMNS = (
    ["id TEXT PRIMARY KEY"]
    + _source_columns("usecases")
    + [_text("reporter_email"), _text("submitted_at"), "in_source INTEGER"]
    + [
        _text("phase", "Eingang"), "merged_into TEXT REFERENCES usecases(id)",
        _text("owner"), _text("type"), _text("origin"), "score REAL",
        _text("reg_status", "offen"), _text("reg_result"), _text("reg_reference"), _text("reg_confirmed_at"),
        _text("sponsor_status", "offen"), _text("sponsor_date"),
        _text("board_status", "offen"), _text("board_date"), _text("board_note"),
        _text("portal_status", "offen"), _text("portal_link"),
        _text("comm_status", "offen"), _text("comm_date"),
        _text("lc_owner"), _text("version"), _text("next_review"), _text("last_review"),
        "needs_help INTEGER NOT NULL DEFAULT 0", _text("help_note"), _text("notes"),
        "created_at TEXT NOT NULL", "updated_at TEXT NOT NULL",
    ]
)
_TICKET_COLUMNS = (
    ["id TEXT PRIMARY KEY"]
    + _source_columns("tickets")
    + [_text("submitted_at"), "in_source INTEGER"]
    + [
        "usecase_id TEXT REFERENCES usecases(id)",
        _text("type"), _text("severity"), _text("status", "Neu"), _text("assignee"), _text("fix_version"),
        _text("cause"), _text("solution"),
        "created_at TEXT NOT NULL", _text("resolved_at"), _text("closed_at"), "updated_at TEXT NOT NULL",
    ]
)

# Nummerierte Migrationen. Eine ausgelieferte Migration wird nie mehr geändert;
# Schemaänderungen kommen als neue Nummer ans Ende.
MIGRATIONS = [
    (1, [
        "CREATE TABLE meta (id INTEGER PRIMARY KEY CHECK (id = 1), schema_version INTEGER NOT NULL, "
        "revision INTEGER NOT NULL DEFAULT 0, stand_id_published TEXT NOT NULL DEFAULT '', "
        "revision_published INTEGER NOT NULL DEFAULT 0)",
        "INSERT INTO meta (id, schema_version) VALUES (1, 0)",
        f"CREATE TABLE usecases ({', '.join(_USECASE_COLUMNS)})",
        "CREATE TABLE usecase_scores (usecase_id TEXT NOT NULL REFERENCES usecases(id), "
        "criterion TEXT NOT NULL, value REAL, PRIMARY KEY (usecase_id, criterion))",
        "CREATE TABLE milestones (id INTEGER PRIMARY KEY, usecase_id TEXT NOT NULL REFERENCES usecases(id), "
        "title TEXT NOT NULL DEFAULT '', planned_date TEXT NOT NULL DEFAULT '', "
        "done_date TEXT NOT NULL DEFAULT '', sort_order INTEGER NOT NULL DEFAULT 0)",
        "CREATE INDEX idx_milestones_usecase ON milestones(usecase_id)",
        f"CREATE TABLE tickets ({', '.join(_TICKET_COLUMNS)})",
        "CREATE INDEX idx_tickets_usecase ON tickets(usecase_id)",
        "CREATE TABLE releases (id INTEGER PRIMARY KEY, usecase_id TEXT NOT NULL REFERENCES usecases(id), "
        "date TEXT NOT NULL DEFAULT '', version TEXT NOT NULL DEFAULT '', change TEXT NOT NULL DEFAULT '', "
        "released_by TEXT NOT NULL DEFAULT '', ticket_id TEXT UNIQUE REFERENCES tickets(id))",
        "CREATE INDEX idx_releases_usecase ON releases(usecase_id)",
        "CREATE TABLE links (id INTEGER PRIMARY KEY, usecase_id TEXT NOT NULL REFERENCES usecases(id), "
        "label TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '')",
        "CREATE INDEX idx_links_usecase ON links(usecase_id)",
        "CREATE TABLE validations (id INTEGER PRIMARY KEY, usecase_id TEXT NOT NULL REFERENCES usecases(id), "
        "created_at TEXT NOT NULL, created_by TEXT NOT NULL DEFAULT '', answers_json TEXT NOT NULL DEFAULT '{}', "
        "result TEXT NOT NULL DEFAULT '', risk TEXT NOT NULL DEFAULT '', controls_json TEXT NOT NULL DEFAULT '[]', "
        "prompt_text TEXT NOT NULL DEFAULT '', prompt_lang TEXT NOT NULL DEFAULT '', "
        "rules_version TEXT NOT NULL DEFAULT '')",
        "CREATE INDEX idx_validations_usecase ON validations(usecase_id)",
        "CREATE TABLE audit (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, user TEXT NOT NULL DEFAULT '', "
        "machine TEXT NOT NULL DEFAULT '', entity TEXT NOT NULL, entity_id TEXT NOT NULL, "
        "field TEXT NOT NULL DEFAULT '', old_value TEXT NOT NULL DEFAULT '', new_value TEXT NOT NULL DEFAULT '', "
        "source TEXT NOT NULL)",
        "CREATE INDEX idx_audit_entity ON audit(entity, entity_id)",
        "CREATE TABLE import_log (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, source TEXT NOT NULL, "
        "status TEXT NOT NULL, row_count INTEGER NOT NULL DEFAULT 0, added INTEGER NOT NULL DEFAULT 0, "
        "changed INTEGER NOT NULL DEFAULT 0, conflicts INTEGER NOT NULL DEFAULT 0, "
        "duplicates INTEGER NOT NULL DEFAULT 0, missing_id INTEGER NOT NULL DEFAULT 0, "
        "message TEXT NOT NULL DEFAULT '')",
        "CREATE TABLE conflicts (id INTEGER PRIMARY KEY, entity TEXT NOT NULL, entity_id TEXT NOT NULL, "
        "field TEXT NOT NULL, hub_value TEXT NOT NULL DEFAULT '', old_src_value TEXT NOT NULL DEFAULT '', "
        "new_src_value TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'offen', "
        "created_at TEXT NOT NULL, resolved_at TEXT NOT NULL DEFAULT '', resolution TEXT NOT NULL DEFAULT '')",
        "CREATE INDEX idx_conflicts_status ON conflicts(status)",
    ]),
]


def latest_version() -> int:
    return MIGRATIONS[-1][0]


class Tx:
    """Eine laufende Schreibtransaktion."""

    def __init__(self, conn, user, machine, source):
        self.conn = conn
        self.user = user
        self.machine = machine
        self.source = source
        self.bump = True  # False: nur Protokoll geschrieben, kein inhaltlicher Stand

    def execute(self, sql, params=()):
        return self.conn.execute(sql, params)

    def audit(self, entity, entity_id, field, old, new, source=None):
        self.conn.execute(
            "INSERT INTO audit (ts, user, machine, entity, entity_id, field, old_value, new_value, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now_ts(), self.user, self.machine, entity, entity_id, field,
             _as_text(old), _as_text(new), source or self.source),
        )


def _as_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class Database:
    """Eine Verbindung für alle Threads, durch eine Sperre geschützt."""

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.conn = sqlite3.connect(str(self.path), isolation_level=None, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            # Technische Vorgaben (5.3): kein WAL, volle Synchronisation, Fremdschlüssel aktiv.
            self.conn.execute("PRAGMA journal_mode=DELETE")
            self.conn.execute("PRAGMA synchronous=FULL")
            self.conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError as exc:
            self._close_quietly()
            raise DatabaseCorrupt(str(exc)) from None

    def _close_quietly(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def close(self):
        with self._lock:
            self._close_quietly()

    def integrity_ok(self) -> bool:
        with self._lock:
            try:
                rows = self.conn.execute("PRAGMA integrity_check").fetchall()
            except sqlite3.DatabaseError:
                return False
        return len(rows) == 1 and rows[0][0] == "ok"

    def schema_version(self) -> int:
        with self._lock:
            has_meta = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'").fetchone()
            if not has_meta:
                return 0
            return self.conn.execute("SELECT schema_version FROM meta").fetchone()[0]

    def meta(self) -> dict:
        with self._lock:
            return dict(self.conn.execute("SELECT * FROM meta").fetchone())

    @contextlib.contextmanager
    def read(self):
        with self._lock:
            yield self.conn

    @contextlib.contextmanager
    def write(self, user="", machine="", source="oberfläche"):
        """Genau eine Transaktion; erhöht ``meta.revision`` um 1 (5.3)."""
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            tx = Tx(self.conn, user, machine, source)
            try:
                yield tx
                if tx.bump:
                    self.conn.execute("UPDATE meta SET revision = revision + 1")
                self.conn.execute("COMMIT")
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise

    def backup_to(self, target) -> None:
        """Konsistente Kopie über die SQLite-Backup-Funktion (keine Dateikopie)."""
        with self._lock:
            copy = sqlite3.connect(str(target))
            try:
                self.conn.backup(copy)
            finally:
                copy.close()

    def migrate(self, before_migration=None) -> list:
        """Führt ausstehende Migrationen aus. Vor jeder entsteht ein Backup (Rückruf)."""
        done = []
        current = self.schema_version()
        if current > latest_version():
            raise SchemaTooNew(
                f"Die Datenbank hat Schema-Version {current}, das Programm kennt nur {latest_version()}.")
        for version, statements in MIGRATIONS:
            if version <= current:
                continue
            if current > 0 and before_migration is not None:
                before_migration(self, version)
            with self._lock:
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    for statement in statements:
                        self.conn.execute(statement)
                    self.conn.execute("UPDATE meta SET schema_version = ?", (version,))
                    self.conn.execute("COMMIT")
                except BaseException:
                    self.conn.execute("ROLLBACK")
                    raise
            current = version
            done.append(version)
        return done


def open_database(path, before_migration=None) -> Database:
    """Öffnet die Datenbank, prüft die Integrität und bringt das Schema auf Stand."""
    database = Database(path)
    try:
        if not database.integrity_ok():
            raise DatabaseCorrupt("Die Integritätsprüfung der Datenbank ist fehlgeschlagen.")
        database.migrate(before_migration)
    except BaseException:
        database.close()
        raise
    return database


def editable_fields(entity) -> list:
    return SOURCE_FIELDS[entity] + CARE_FIELDS[entity]


_MISSING = object()


def update_field(tx, entity, entity_id, field, new, expected=_MISSING):
    """Ändert genau ein Feld mit Audit-Eintrag.

    ``expected`` ist der Wert, den die Oberfläche zuletzt gesehen hat. Weicht er
    vom Stand der Datenbank ab, wird nichts geschrieben (StaleValue).
    Rückgabe: True, wenn sich der Wert geändert hat.
    """
    if entity not in SOURCE_FIELDS or field not in editable_fields(entity):
        raise KeyError(f"Feld nicht änderbar: {entity}.{field}")
    row = tx.execute(f"SELECT {field} FROM {entity} WHERE id = ?", (entity_id,)).fetchone()
    if row is None:
        raise LookupError(f"{ENTITY_LABELS[entity]} {entity_id} nicht gefunden.")
    old = row[0]
    if expected is not _MISSING and _as_text(expected) != _as_text(old):
        raise StaleValue(old)
    if _as_text(new) == _as_text(old):
        tx.bump = False
        return False
    tx.execute(f"UPDATE {entity} SET {field} = ?, updated_at = ? WHERE id = ?", (new, now_ts(), entity_id))
    tx.audit(entity, entity_id, field, old, new)
    return True
