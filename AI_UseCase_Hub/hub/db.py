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
    # S9: merkt, dass die Fix-Version eines Tickets bereits einmal gebucht wurde (auch nach „Rückgängig“).
    (2, ["ALTER TABLE tickets ADD COLUMN release_booked INTEGER NOT NULL DEFAULT 0"]),
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
        existed = current > 0  # eine neu angelegte Datenbank braucht kein Backup
        for version, statements in MIGRATIONS:
            if version <= current:
                continue
            if existed and before_migration is not None:
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


def update_field(tx, entity, entity_id, field, new, expected=_MISSING, source=None):
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
    tx.audit(entity, entity_id, field, old, new, source)
    return True


# --- Eingaben prüfen -------------------------------------------------------------

DATE_FIELDS = {"reg_confirmed_at", "sponsor_date", "board_date", "comm_date", "next_review", "last_review",
               "resolved_at", "closed_at", "planned_date", "done_date", "date"}
# Feld -> Werteliste mit festen Schlüsseln (hub/config.py, LOGIC_LISTS)
LIST_FIELDS = {
    "usecases": {"phase": "phase", "origin": "origin", "reg_status": "reg_status", "sponsor_status": "sponsor_status",
                 "board_status": "board_status", "portal_status": "portal_status", "comm_status": "comm_status"},
    "tickets": {"status": "ticket_status", "severity": "ticket_severity"},
}
MAY_BE_EMPTY = {"origin", "severity"}
MAX_TEXT = 20000


def clean_date(value) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    try:
        if len(text) != 10:
            raise ValueError
        return datetime.date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError("Kein gültiges Datum (erwartet: TT.MM.JJJJ).") from None


def clean_number(value):
    if value is None or isinstance(value, bool):
        if value is None:
            return None
        raise ValueError("Erwartet wird eine Zahl.")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise ValueError("Erwartet wird eine Zahl, zum Beispiel 3,5.") from None


def clean_text(value) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("Erwartet wird ein Text.")
    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(text) > MAX_TEXT:
        raise ValueError(f"Der Text ist zu lang (höchstens {MAX_TEXT} Zeichen).")
    return text


def clean_url(value) -> str:
    text = clean_text(value)
    if text and not text.lower().startswith(("http://", "https://")):
        raise ValueError("Die Adresse muss mit http:// oder https:// beginnen.")
    return text


def clean_value(entity, field, value):
    """Prüft und normalisiert eine Eingabe für ein Feld. Fehler als ValueError mit Klartext."""
    from .config import LOGIC_LISTS  # hier, um einen Importkreis zu vermeiden

    if field not in editable_fields(entity) or field in ("merged_into", "usecase_id"):
        raise KeyError(f"Feld nicht änderbar: {entity}.{field}")
    if field == "score":
        return clean_number(value)
    if field == "needs_help":
        if value in (True, 1, "1"):
            return 1
        if value in (False, 0, "0", None, ""):
            return 0
        raise ValueError("Erwartet wird ja oder nein.")
    if field in DATE_FIELDS:
        return clean_date(value)
    list_name = LIST_FIELDS[entity].get(field)
    if list_name:
        text = clean_text(value)
        if text == "" and field in MAY_BE_EMPTY:
            return ""
        if text not in LOGIC_LISTS[list_name]:
            raise ValueError(f"Unbekannter Wert. Erlaubt: {', '.join(LOGIC_LISTS[list_name])}.")
        return text
    text = clean_text(value)
    if field == "title" and not text:
        raise ValueError("Der Titel darf nicht leer sein.")
    return text


# --- Use Cases ---------------------------------------------------------------------


def create_manual(tx, entity, title) -> str:
    """Legt einen Datensatz von Hand an: M-xxx bzw. TM-xxx."""
    title = clean_text(title)
    if not title:
        raise ValueError("Der Titel darf nicht leer sein.")
    prefix = ID_PREFIX_MANUAL[entity]
    numbers = [int(row[0][len(prefix):]) for row in tx.execute(f"SELECT id FROM {entity} WHERE id LIKE ?", (prefix + "%",))
               if row[0][len(prefix):].isdigit()]
    new_id = f"{prefix}{max(numbers, default=0) + 1:03d}"
    now = now_ts()
    tx.execute(f"INSERT INTO {entity} (id, title, title_src, created_at, updated_at) VALUES (?, ?, '', ?, ?)",
               (new_id, title, now, now))
    tx.audit(entity, new_id, "angelegt", "", title)
    return new_id


def set_phase(tx, usecase_id, phase, merged_into=None, expected=_MISSING) -> None:
    """Phasenwechsel inklusive „Zusammenführen mit …“ (nichts wird gelöscht, Regel S7)."""
    phase = clean_value("usecases", "phase", phase)
    row = tx.execute("SELECT phase, merged_into FROM usecases WHERE id = ?", (usecase_id,)).fetchone()
    if row is None:
        raise LookupError(f"Use Case {usecase_id} nicht gefunden.")
    target = None
    if phase == "Zusammengeführt":
        target = clean_text(merged_into)
        if not target:
            raise ValueError("Bitte den Use Case angeben, mit dem zusammengeführt wird.")
        if target == usecase_id:
            raise ValueError("Ein Use Case kann nicht mit sich selbst zusammengeführt werden.")
        other = tx.execute("SELECT phase, merged_into FROM usecases WHERE id = ?", (target,)).fetchone()
        if other is None:
            raise ValueError(f"Use Case {target} nicht gefunden.")
        if other["phase"] == "Zusammengeführt":
            raise ValueError(f"{target} ist selbst zusammengeführt (mit {other['merged_into']}). Bitte dessen Ziel wählen.")
    changed = update_field(tx, "usecases", usecase_id, "phase", phase, expected)
    if row["merged_into"] != target:
        tx.execute("UPDATE usecases SET merged_into = ?, updated_at = ? WHERE id = ?", (target, now_ts(), usecase_id))
        tx.audit("usecases", usecase_id, "merged_into", row["merged_into"], target)
        changed = True
    tx.bump = changed


def set_criterion_score(tx, usecase_id, criterion, label, value) -> None:
    """Speichert einen Einzelscore (Kriterien aus standort.json, Abschnitt score)."""
    value = clean_number(value)
    if tx.execute("SELECT 1 FROM usecases WHERE id = ?", (usecase_id,)).fetchone() is None:
        raise LookupError(f"Use Case {usecase_id} nicht gefunden.")
    row = tx.execute("SELECT value FROM usecase_scores WHERE usecase_id = ? AND criterion = ?",
                     (usecase_id, criterion)).fetchone()
    old = row[0] if row else None
    if old == value:
        tx.bump = False
        return
    tx.execute("INSERT INTO usecase_scores (usecase_id, criterion, value) VALUES (?, ?, ?) "
               "ON CONFLICT (usecase_id, criterion) DO UPDATE SET value = excluded.value",
               (usecase_id, criterion, value))
    tx.execute("UPDATE usecases SET updated_at = ? WHERE id = ?", (now_ts(), usecase_id))
    tx.audit("usecases", usecase_id, f"Score {label}", old, value)


# --- Unterlisten eines Use Cases: Meilensteine, Updatehistorie, Links ---------------

SUBLISTS = {
    "milestones": {"label": "Meilenstein", "name": "title", "order": "sort_order, planned_date, id",
                   "fields": {"title": "Titel", "planned_date": "geplant", "done_date": "erledigt am"}},
    "releases": {"label": "Update", "name": "version", "order": "date DESC, id DESC",
                 "fields": {"date": "Datum", "version": "Version", "change": "Änderung", "released_by": "durch"}},
    "links": {"label": "Link", "name": "label", "order": "id",
              "fields": {"label": "Bezeichnung", "url": "Adresse"}},
}


def _clean_sub(table, field, value) -> str:
    if field not in SUBLISTS[table]["fields"]:
        raise KeyError(f"Feld nicht änderbar: {table}.{field}")
    if field in DATE_FIELDS:
        return clean_date(value)
    if field == "url":
        return clean_url(value)
    return clean_text(value)


def _describe_sub(table, row) -> str:
    parts = [f"{label}: {row[field]}" for field, label in SUBLISTS[table]["fields"].items() if row[field]]
    return "; ".join(parts) or "(leer)"


def sub_list(conn, table, usecase_id) -> list:
    spec = SUBLISTS[table]
    return [dict(row) for row in conn.execute(
        f"SELECT * FROM {table} WHERE usecase_id = ? ORDER BY {spec['order']}", (usecase_id,))]


def sub_add(tx, table, usecase_id, values) -> int:
    spec = SUBLISTS[table]
    if tx.execute("SELECT 1 FROM usecases WHERE id = ?", (usecase_id,)).fetchone() is None:
        raise LookupError(f"Use Case {usecase_id} nicht gefunden.")
    clean = {field: _clean_sub(table, field, (values or {}).get(field)) for field in spec["fields"]}
    if not any(clean.values()):
        raise ValueError("Bitte mindestens ein Feld ausfüllen.")
    names = ["usecase_id"] + list(clean)
    cursor = tx.execute(f"INSERT INTO {table} ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})",
                        [usecase_id] + list(clean.values()))
    tx.execute("UPDATE usecases SET updated_at = ? WHERE id = ?", (now_ts(), usecase_id))
    tx.audit("usecases", usecase_id, spec["label"], "", _describe_sub(table, clean))
    return cursor.lastrowid


def _sub_row(tx, table, row_id):
    if table not in SUBLISTS:
        raise KeyError(table)
    row = tx.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise LookupError(f"{SUBLISTS[table]['label']} nicht gefunden.")
    return row


def sub_update(tx, table, row_id, field, value, expected=_MISSING) -> str:
    """Ändert ein Feld einer Unterlisten-Zeile. Rückgabe: ID des Use Cases."""
    spec = SUBLISTS[table]
    row = _sub_row(tx, table, row_id)
    new = _clean_sub(table, field, value)
    old = row[field]
    if expected is not _MISSING and _as_text(expected) != _as_text(old):
        raise StaleValue(old)
    if new == old:
        tx.bump = False
        return row["usecase_id"]
    tx.execute(f"UPDATE {table} SET {field} = ? WHERE id = ?", (new, row_id))
    tx.execute("UPDATE usecases SET updated_at = ? WHERE id = ?", (now_ts(), row["usecase_id"]))
    name = row[spec["name"]] or f"Nr. {row_id}"
    tx.audit("usecases", row["usecase_id"], f"{spec['label']} ‚{name}‘: {spec['fields'][field]}", old, new)
    return row["usecase_id"]


def sub_delete(tx, table, row_id) -> str:
    spec = SUBLISTS[table]
    row = _sub_row(tx, table, row_id)
    tx.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
    tx.execute("UPDATE usecases SET updated_at = ? WHERE id = ?", (now_ts(), row["usecase_id"]))
    tx.audit("usecases", row["usecase_id"], spec["label"], _describe_sub(table, row), "gelöscht")
    return row["usecase_id"]


# --- Tickets (Phase 3) -----------------------------------------------------------------


def set_ticket_usecase(tx, ticket_id, usecase_id, expected=_MISSING, source=None) -> bool:
    """Ordnet ein Ticket einem Use Case zu (oder löst die Zuordnung mit einem leeren Wert)."""
    usecase_id = clean_text(usecase_id) or None
    row = tx.execute("SELECT usecase_id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise LookupError(f"Ticket {ticket_id} nicht gefunden.")
    if expected is not _MISSING and _as_text(expected) != _as_text(row[0]):
        raise StaleValue(row[0])
    if usecase_id and tx.execute("SELECT 1 FROM usecases WHERE id = ?", (usecase_id,)).fetchone() is None:
        raise ValueError(f"Use Case {usecase_id} nicht gefunden.")
    if usecase_id == row[0]:
        tx.bump = False
        return False
    tx.execute("UPDATE tickets SET usecase_id = ?, updated_at = ? WHERE id = ?", (usecase_id, now_ts(), ticket_id))
    tx.audit("tickets", ticket_id, "usecase_id", row[0], usecase_id, source)
    return True


def set_ticket_status(tx, ticket_id, status, expected=_MISSING):
    """Statuswechsel mit Regel S9: Fix-Version genau einmal in die Updatehistorie buchen.

    Rückgabe: None oder Angaben zur automatischen Buchung (für die Bestätigung mit „Rückgängig“).
    """
    from . import rules  # hier, um einen Importkreis zu vermeiden

    status = clean_value("tickets", "status", status)
    ticket = tx.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        raise LookupError(f"Ticket {ticket_id} nicht gefunden.")
    changed = update_field(tx, "tickets", ticket_id, "status", status, expected)
    tx.bump = changed
    if not changed or status not in ("Gelöst", "Geschlossen"):
        return None
    if not ticket["resolved_at"]:
        tx.execute("UPDATE tickets SET resolved_at = ? WHERE id = ?", (today(), ticket_id))
    if status == "Geschlossen" and not ticket["closed_at"]:
        tx.execute("UPDATE tickets SET closed_at = ? WHERE id = ?", (today(), ticket_id))
    fix = ticket["fix_version"]
    if not fix or ticket["release_booked"]:
        return None
    if not ticket["usecase_id"]:
        return {"booked": False, "hint": "Fix-Version nicht gebucht: Das Ticket ist keinem Use Case zugeordnet."}
    usecase_id = ticket["usecase_id"]
    current = tx.execute("SELECT version FROM usecases WHERE id = ?", (usecase_id,)).fetchone()[0]
    tx.execute("INSERT INTO releases (usecase_id, date, version, change, released_by, ticket_id) VALUES (?, ?, ?, ?, ?, ?)",
               (usecase_id, today(), fix, f"{ticket_id}: {ticket['title']}", tx.user, ticket_id))
    tx.execute("UPDATE tickets SET release_booked = 1 WHERE id = ?", (ticket_id,))
    tx.audit("usecases", usecase_id, "Update", "", f"Version {fix} aus {ticket_id}", "regel")
    higher = rules.version_higher(fix, current)
    hint = ""
    if higher is True:
        update_field(tx, "usecases", usecase_id, "version", fix, source="regel")
    elif higher is None:
        hint = (f"Version von {usecase_id} nicht automatisch geändert: „{fix}“ oder „{current}“ entspricht nicht "
                "dem Format Haupt.Neben[.Patch].")
    tx.bump = True
    return {"booked": True, "ticket_id": ticket_id, "usecase_id": usecase_id, "version": fix,
            "old_version": current, "version_raised": higher is True, "hint": hint}


def undo_ticket_booking(tx, ticket_id, old_version=None) -> None:
    """Nimmt die automatische Buchung aus S9 zurück. Sie wird danach nicht erneut ausgelöst."""
    release = tx.execute("SELECT * FROM releases WHERE ticket_id = ?", (ticket_id,)).fetchone()
    if release is None:
        raise LookupError("Zu diesem Ticket gibt es keine automatische Buchung.")
    usecase_id = release["usecase_id"]
    tx.execute("DELETE FROM releases WHERE id = ?", (release["id"],))
    tx.audit("usecases", usecase_id, "Update", f"Version {release['version']} aus {ticket_id}", "zurückgenommen", "regel")
    current = tx.execute("SELECT version FROM usecases WHERE id = ?", (usecase_id,)).fetchone()[0]
    if old_version is not None and current == release["version"] and old_version != current:
        update_field(tx, "usecases", usecase_id, "version", clean_text(old_version), source="regel")
