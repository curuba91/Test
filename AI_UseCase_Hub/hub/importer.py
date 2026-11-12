"""Quellen lesen, Abgleich, Konflikte – Regeln S1 bis S7 (Kapitel 7).

Die Quell-Excels werden nie geöffnet oder verändert: Gelesen wird immer eine
temporäre Kopie im lokalen Datenordner (S2, X9).
"""

import datetime
import re
import shutil
import threading
import time
from pathlib import Path

from . import db as dbm

ATTEMPTS = 3
HEADER_SCAN_ROWS = 20

SOURCES = {
    "usecases": {"short": "Quelle 1", "label": "Quelle 1 – Use-Case-Excel", "path_key": "source_usecases",
                 "prefix": "UC-", "new_state": ("phase", "Eingang")},
    "tickets": {"short": "Quelle 2", "label": "Quelle 2 – Ticket-Excel", "path_key": "source_tickets",
                "prefix": "T-", "new_state": ("status", "Neu")},
}
STATE_TEXT = {
    "ausstehend": "Noch nicht gelesen",
    "ok": "Gelesen",
    "nicht_eingerichtet": "Nicht eingerichtet",
    "nicht_lesbar": "Quelle nicht lesbar",
    "spalte_fehlt": "Spalte fehlt",
    "zuordnung_fehlt": "Spaltenzuordnung unvollständig",
}


# S8: „Betroffenes Tool“ beginnt mit einer ID, gefolgt von einem Gedankenstrich und dem Titel.
_TOOL_ID = re.compile(r"^\s*([^\s–—-]+-[^\s–—-]+)\s*[–—-]\s*\S")


class SourceError(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


class SourceData:
    def __init__(self):
        self.rows = []          # je Zeile: {"id": ..., <feld>: <text>}
        self.row_count = 0      # Zeilen mit Inhalt
        self.duplicates = []    # IDs, die mehrfach vorkamen (erste Zeile gilt)
        self.missing_id = 0     # Zeilen mit Inhalt, aber ohne ID


def norm_header(value) -> str:
    return " ".join(str(value).split()).casefold() if value is not None else ""


def normalize_id(raw, prefix):
    """Formular-ID in die Hub-Schreibweise bringen: 7 -> UC-007, 'uc-7' -> UC-007."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, float) and raw.is_integer():
        raw = int(raw)
    text = str(raw).strip()
    if not text:
        return None
    if text.casefold().startswith(prefix.casefold()) and text[len(prefix):].isdigit():
        text = text[len(prefix):]
    if text.isdigit():
        return f"{prefix}{int(text):03d}"
    return text


_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
_GERMAN_DATE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})")


def _date_text(value) -> str:
    """Datum als JJJJ-MM-TT; nicht lesbare Angaben ergeben einen leeren Wert."""
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = str(value).strip()
    match = _ISO_DATE.match(text)
    if match:
        year, month, day = match.groups()
    else:
        match = _GERMAN_DATE.match(text)
        if not match:
            return ""
        day, month, year = match.groups()
    try:
        return datetime.date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return ""


def cell_text(value, field) -> str:
    if value is None:
        return ""
    if field == "submitted_at":
        return _date_text(value)
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, datetime.datetime):
        if value.time() == datetime.time(0, 0):
            return value.date().isoformat()
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def parse_workbook(path, wanted, prefix, short) -> SourceData:
    """Liest die Tabelle mit der Kopfzeile, die die ID-Spalte enthält."""
    import openpyxl

    wanted_norm = {field: norm_header(column) for field, column in wanted.items()}
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            sheet.reset_dimensions()  # veraltete Größenangaben in der Datei ignorieren
            rows = sheet.iter_rows(values_only=True)
            columns = None
            for index, row in enumerate(rows):
                if index >= HEADER_SCAN_ROWS:
                    break
                header = [norm_header(cell) for cell in row]
                if wanted_norm["id"] in header:
                    columns = {}
                    for field, name in wanted_norm.items():
                        if name not in header:
                            raise SourceError(
                                "spalte_fehlt",
                                f"Spalte ‚{wanted[field]}‘ in {short} nicht gefunden. "
                                "Zuordnung unter Verwaltung → Einstellungen prüfen (standort.json, Abschnitt columns).")
                        columns[field] = header.index(name)
                    break
            if columns is None:
                continue
            data = SourceData()
            seen = set()
            for row in rows:
                record = {}
                for field, position in columns.items():
                    value = row[position] if position < len(row) else None
                    record[field] = value if field == "id" else cell_text(value, field)
                raw_id = record["id"]
                if all(not record[f] for f in record if f != "id") and normalize_id(raw_id, prefix) is None:
                    continue  # leere Zeile
                data.row_count += 1
                record["id"] = normalize_id(raw_id, prefix)
                if record["id"] is None:
                    data.missing_id += 1
                elif record["id"] in seen:
                    data.duplicates.append(record["id"])
                else:
                    seen.add(record["id"])
                    data.rows.append(record)
            return data
    finally:
        workbook.close()
    raise SourceError(
        "spalte_fehlt",
        f"Spalte ‚{wanted['id']}‘ in {short} nicht gefunden. "
        "Zuordnung unter Verwaltung → Einstellungen prüfen (standort.json, Abschnitt columns).")


def _describe(exc) -> str:
    if isinstance(exc, FileNotFoundError):
        return "Datei nicht gefunden"
    if isinstance(exc, PermissionError):
        return "Datei ist gesperrt"
    return f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__


def _list_ids(ids, limit=8) -> str:
    ids = sorted(set(ids))
    return ", ".join(ids[:limit]) + (f" und {len(ids) - limit} weitere" if len(ids) > limit else "")


def apply(database, key, data, mapped, user, machine) -> dict:
    """Gleicht die gelesenen Zeilen in einer Transaktion mit dem Hub ab (S3 bis S7)."""
    entity = key
    source_fields = [f for f in dbm.SOURCE_FIELDS[entity] if f in mapped]
    internal_fields = [f for f in dbm.INTERNAL_FIELDS[entity] if f in mapped]
    state_field, state_value = SOURCES[key]["new_state"]
    summary = {"added": 0, "changed": 0, "conflicts": 0}
    notes = []
    now = dbm.now_ts()
    with database.write(user=user, machine=machine, source="import") as tx:
        touched = False
        existing = {row["id"]: row for row in tx.execute(f"SELECT * FROM {entity}")}
        open_conflicts = {
            (row["entity_id"], row["field"]): row
            for row in tx.execute("SELECT * FROM conflicts WHERE entity = ? AND status = 'offen'", (entity,))
        }

        def close_conflict(conflict):
            tx.execute("UPDATE conflicts SET status = 'entschieden', resolved_at = ?, resolution = ? WHERE id = ?",
                       (now, "entfallen (Quelle und Hub stimmen wieder überein)", conflict["id"]))

        for record in data.rows:
            current = existing.get(record["id"])
            if current is None:  # S3: neue ID
                names = ["id", state_field, "in_source", "created_at", "updated_at"]
                values = [record["id"], state_value, 1, now, now]
                for field in source_fields:
                    names += [field, f"{field}_src"]
                    values += [record[field], record[field]]
                for field in internal_fields:
                    names.append(field)
                    values.append(record[field])
                tx.execute(f"INSERT INTO {entity} ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})", values)
                tx.audit(entity, record["id"], "angelegt", "", record.get("title", ""))
                summary["added"] += 1
                continue
            updates = {}
            record_changed = False
            for field in source_fields:
                hub_value, old_src, new_src = current[field], current[f"{field}_src"], record[field]
                conflict = open_conflicts.get((record["id"], field))
                if new_src == old_src:
                    if conflict is not None:  # Quelle ist zum alten Wert zurückgekehrt
                        close_conflict(conflict)
                        touched = True
                elif hub_value == old_src:  # S4: im Hub unverändert, Quelle gilt
                    updates[field] = new_src
                    updates[f"{field}_src"] = new_src
                    tx.audit(entity, record["id"], field, hub_value, new_src)
                    record_changed = True
                elif new_src == hub_value:  # Quelle hat denselben Wert wie der Hub bekommen
                    updates[f"{field}_src"] = new_src
                    if conflict is not None:
                        close_conflict(conflict)
                elif conflict is None:  # S5: nie still überschreiben
                    tx.execute(
                        "INSERT INTO conflicts (entity, entity_id, field, hub_value, old_src_value, new_src_value, "
                        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (entity, record["id"], field, hub_value, old_src, new_src, now))
                    summary["conflicts"] += 1
                elif conflict["new_src_value"] != new_src or conflict["hub_value"] != hub_value:
                    tx.execute("UPDATE conflicts SET new_src_value = ?, hub_value = ? WHERE id = ?",
                               (new_src, hub_value, conflict["id"]))
                    if conflict["new_src_value"] != new_src:
                        summary["conflicts"] += 1
                    touched = True
            for field in internal_fields:
                if record[field] != current[field]:
                    updates[field] = record[field]
            if current["in_source"] == 0:
                updates["in_source"] = 1
            if updates:
                updates["updated_at"] = now
                assignments = ", ".join(f"{name} = ?" for name in updates)
                tx.execute(f"UPDATE {entity} SET {assignments} WHERE id = ?", list(updates.values()) + [record["id"]])
                touched = True
            if record_changed:
                summary["changed"] += 1

        if entity == "tickets":  # S8: „UC-xxx – Titel“ ordnet ein neues Ticket automatisch zu
            known = {row[0].casefold(): row[0] for row in tx.execute("SELECT id FROM usecases")}
            assigned = 0
            for row in tx.execute("SELECT id, affected_tool_raw FROM tickets WHERE usecase_id IS NULL "
                                  "AND status = 'Neu'").fetchall():
                match = _TOOL_ID.match(row["affected_tool_raw"])
                usecase_id = known.get(match.group(1).casefold()) if match else None
                if usecase_id:
                    tx.execute("UPDATE tickets SET usecase_id = ?, updated_at = ? WHERE id = ?",
                               (usecase_id, now, row["id"]))
                    tx.audit("tickets", row["id"], "usecase_id", "", usecase_id, "regel")
                    assigned += 1
            if assigned:
                touched = True
                notes.append(f"{assigned} {'Ticket' if assigned == 1 else 'Tickets'} automatisch zugeordnet")

        # S7: Datensätze werden nie gelöscht; eine verschwundene ID wird nur vermerkt.
        present = {record["id"] for record in data.rows}
        vanished = [i for i, row in existing.items() if row["in_source"] == 1 and i not in present]
        for entity_id in vanished:
            tx.execute(f"UPDATE {entity} SET in_source = 0 WHERE id = ?", (entity_id,))
        if vanished:
            notes.append(f"Nicht mehr in der Quelle (Datensatz bleibt erhalten): {_list_ids(vanished)}")
        if data.duplicates:
            count = len(data.duplicates)
            notes.append(f"{count} {'Dublette' if count == 1 else 'Dubletten'} übersprungen, "
                         f"erste Zeile gilt: {_list_ids(data.duplicates)}")
        if data.missing_id:
            count = data.missing_id
            notes.append(f"{count} {'Zeile' if count == 1 else 'Zeilen'} ohne ID nicht importiert")
        summary.update(
            source=key, status="ok", ts=now, row_count=data.row_count, duplicates=len(data.duplicates),
            missing_id=data.missing_id, message=". ".join(notes))
        _write_log(tx, summary)
        tx.bump = bool(summary["added"] or summary["changed"] or summary["conflicts"] or vanished or touched)
    return summary


def _write_log(tx, summary) -> None:
    tx.execute(
        "INSERT INTO import_log (ts, source, status, row_count, added, changed, conflicts, duplicates, missing_id, "
        "message) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (summary["ts"], summary["source"], summary["status"], summary["row_count"], summary["added"],
         summary["changed"], summary["conflicts"], summary["duplicates"], summary["missing_id"], summary["message"]))


def resolve_conflict(database, conflict_id, choice, user, machine) -> dict:
    """S5: Quelle übernehmen oder Hub-Wert behalten. ``<feld>_src`` wird in beiden Fällen der neue Quellwert."""
    if choice not in ("quelle", "hub"):
        raise ValueError("Unbekannte Entscheidung.")
    with database.write(user=user, machine=machine, source="oberfläche") as tx:
        conflict = tx.execute("SELECT * FROM conflicts WHERE id = ?", (conflict_id,)).fetchone()
        if conflict is None:
            raise LookupError("Konflikt nicht gefunden.")
        if conflict["status"] != "offen":
            raise ValueError("Dieser Konflikt ist bereits entschieden.")
        entity, entity_id, field = conflict["entity"], conflict["entity_id"], conflict["field"]
        new_src = conflict["new_src_value"]
        hub_value = tx.execute(f"SELECT {field} FROM {entity} WHERE id = ?", (entity_id,)).fetchone()[0]
        now = dbm.now_ts()
        if choice == "quelle":
            resolution = "Quelle übernommen"
            tx.execute(f"UPDATE {entity} SET {field} = ?, {field}_src = ?, updated_at = ? WHERE id = ?",
                       (new_src, new_src, now, entity_id))
            tx.audit(entity, entity_id, field, hub_value, new_src)
        else:
            resolution = "Hub-Wert behalten"
            tx.execute(f"UPDATE {entity} SET {field}_src = ?, updated_at = ? WHERE id = ?", (new_src, now, entity_id))
            tx.audit(entity, entity_id, field, f"Quelle: {new_src}", f"Hub-Wert behalten: {hub_value}")
        tx.execute("UPDATE conflicts SET status = 'entschieden', resolved_at = ?, resolution = ? WHERE id = ?",
                   (now, resolution, conflict_id))
        return {"id": conflict_id, "resolution": resolution}


class Importer:
    """Liest beide Quellen, hält ihren Zustand und prüft regelmäßig auf Änderungen (S1)."""

    def __init__(self, database, columns, path_for, tmp_dir, user="", machine="", log_error=None, retry_pause=0.5):
        self.db = database
        self.columns = columns      # Aufruf liefert den Abschnitt "columns" der Standortkonfiguration
        self.path_for = path_for    # Aufruf liefert den Pfad einer Quelle oder None
        self.tmp_dir = Path(tmp_dir)
        self.user = user
        self.machine = machine
        self.log_error = log_error or (lambda text: None)
        self.retry_pause = retry_pause
        self.copy = shutil.copyfile
        self.state = {key: {
            "key": key, "label": spec["label"], "short": spec["short"], "state": "ausstehend",
            "state_text": STATE_TEXT["ausstehend"], "message": "", "last_attempt": "", "last_success": "",
            "row_count": 0, "missing_id": 0, "duplicates": 0,
        } for key, spec in SOURCES.items()}
        self._signature = {key: None for key in SOURCES}
        self._last_logged_error = {key: None for key in SOURCES}
        self._run_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    # --- Lesen (S2) -------------------------------------------------------------

    def _mapping(self, key):
        columns = self.columns() or {}
        entry = columns.get(key) if isinstance(columns.get(key), dict) else {}
        fields = entry.get("fields") if isinstance(entry.get("fields"), dict) else {}
        wanted = {field: column for field, column in fields.items() if isinstance(column, str) and column.strip()}
        return wanted, entry.get("id_prefix") or SOURCES[key]["prefix"]

    def read(self, key) -> tuple:
        spec = SOURCES[key]
        path = self.path_for(key)
        if path is None:
            raise SourceError("nicht_eingerichtet", f"{spec['short']} ist nicht eingerichtet (Verwaltung → Einstellungen).")
        wanted, prefix = self._mapping(key)
        for required in ("id", "title"):
            if required not in wanted:
                raise SourceError(
                    "zuordnung_fehlt",
                    f"{spec['short']}: Dem Feld ‚{dbm.FIELD_LABELS.get(required, required.upper())}‘ ({required}) ist "
                    "keine Spalte zugeordnet (standort.json, Abschnitt columns).")
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        last_error = None
        for attempt in range(ATTEMPTS):
            tmp = self.tmp_dir / f"quelle_{key}_{threading.get_ident()}_{attempt}.xlsx"
            try:
                self.copy(str(path), str(tmp))
                return parse_workbook(tmp, wanted, prefix, spec["short"]), set(wanted)
            except SourceError:
                raise
            except Exception as exc:  # gesperrt, halb synchronisiert, keine gültige Arbeitsmappe
                last_error = exc
            finally:
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt + 1 < ATTEMPTS and self.retry_pause:
                time.sleep(self.retry_pause)
        raise SourceError(
            "nicht_lesbar",
            f"{spec['short']} konnte nicht gelesen werden ({ATTEMPTS} Versuche): {_describe(last_error)}. "
            "Der bisherige Stand bleibt unverändert.")

    def _file_signature(self, key):
        path = self.path_for(key)
        if path is None:
            return None
        try:
            stat = Path(path).stat()
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    # --- Läufe --------------------------------------------------------------------

    def run(self, key=None, log_repeated_errors=True) -> list:
        """Importiert eine oder beide Quellen. Kein Absturz, kein Teilimport."""
        with self._run_lock:
            return [self._run_one(k, log_repeated_errors) for k in ([key] if key else list(SOURCES))]

    def _run_one(self, key, log_repeated_errors) -> dict:
        state = self.state[key]
        signature = self._file_signature(key)
        now = dbm.now_ts()
        state["last_attempt"] = now
        try:
            data, mapped = self.read(key)
            summary = apply(self.db, key, data, mapped, self.user, self.machine)
        except SourceError as exc:
            summary = self._failed(key, exc.kind, str(exc), now, log_repeated_errors)
        except Exception as exc:  # unerwartet: protokollieren, weiterlaufen
            self.log_error(f"Import {key}: {type(exc).__name__}: {exc}")
            summary = self._failed(key, "nicht_lesbar", f"{SOURCES[key]['short']}: unerwarteter Fehler beim Import "
                                   f"({type(exc).__name__}). Details im Fehlerprotokoll.", now, log_repeated_errors)
        else:
            self._signature[key] = signature
            self._last_logged_error[key] = None
            state.update(state="ok", state_text=STATE_TEXT["ok"], message=summary["message"], last_success=now,
                         row_count=summary["row_count"], missing_id=summary["missing_id"],
                         duplicates=summary["duplicates"])
        return summary

    def _failed(self, key, kind, message, now, log_repeated_errors) -> dict:
        self._signature[key] = None  # beim nächsten Prüfen erneut versuchen
        self.state[key].update(state=kind, state_text=STATE_TEXT[kind], message=message)
        summary = {"source": key, "status": "fehler", "ts": now, "row_count": 0, "added": 0, "changed": 0,
                   "conflicts": 0, "duplicates": 0, "missing_id": 0, "message": message}
        if log_repeated_errors or self._last_logged_error[key] != message:
            with self.db.write(user=self.user, machine=self.machine, source="import") as tx:
                _write_log(tx, summary)
                tx.bump = False
            self._last_logged_error[key] = message
        return summary

    def check(self) -> list:
        """S1: importiert Quellen, deren Datei sich geändert hat oder die zuletzt nicht lesbar waren."""
        runs = []
        with self._run_lock:
            for key in SOURCES:
                signature = self._file_signature(key)
                if self.state[key]["state"] == "ok" and signature == self._signature[key]:
                    continue
                runs.append(self._run_one(key, log_repeated_errors=False))
        return runs

    def start(self, interval) -> None:
        def loop():
            while not self._stop.is_set():
                try:
                    self.check()
                except Exception as exc:
                    self.log_error(f"Import-Prüfung: {type(exc).__name__}: {exc}")
                self._stop.wait(interval)

        self._stop.clear()
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def states(self) -> list:
        return [dict(self.state[key], path=str(self.path_for(key) or "")) for key in SOURCES]


# --- Einmalige Migration der bisherigen Pflegeinformationen (Phase 6) -------------------------
# Liest die Pflegespalten der bisherigen Excel (standort.json, Abschnitt migration) über die ID.
# Der Abgleichsbericht schreibt nichts; geschrieben wird erst mit migration_apply.

_SCORE_PREFIX = "score_"


def _phase_lookup(site) -> dict:
    lists = site.get("value_lists") if isinstance(site.get("value_lists"), dict) else {}
    entries = (lists.get("phase") or {}).get("entries") if isinstance(lists.get("phase"), dict) else []
    lookup = {}
    for entry in entries or []:
        if isinstance(entry, dict) and entry.get("key"):
            for name in [entry["key"], entry.get("label", "")] + list(entry.get("aliases") or []):
                if isinstance(name, str) and name.strip():
                    lookup[name.strip().casefold()] = entry["key"]
    return lookup


def migration_report(database, site, path, tmp_dir, copy=shutil.copyfile) -> dict:
    """Abgleichsbericht: übernehmbare, nicht zuordenbare und widersprüchliche Angaben."""
    columns = site.get("columns") if isinstance(site.get("columns"), dict) else {}
    usecases = columns.get("usecases") if isinstance(columns.get("usecases"), dict) else {}
    id_column = (usecases.get("fields") or {}).get("id")
    migration = site.get("migration") if isinstance(site.get("migration"), dict) else {}
    wanted = {f: c for f, c in (migration.get("columns") or {}).items() if isinstance(c, str) and c.strip()}
    if path is None:
        raise SourceError("nicht_eingerichtet", "Quelle 1 ist nicht eingerichtet (Verwaltung → Einstellungen).")
    if not id_column or not wanted:
        raise SourceError("zuordnung_fehlt", "In standort.json fehlen die ID-Spalte (columns.usecases) oder die "
                          "Pflegespalten (migration.columns).")
    wanted = dict(wanted, id=id_column)
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    tmp = Path(tmp_dir) / f"migration_{threading.get_ident()}.xlsx"
    try:
        copy(str(path), str(tmp))
        data = parse_workbook(tmp, wanted, usecases.get("id_prefix") or "UC-", "Quelle 1")
    except SourceError:
        raise
    except Exception as exc:
        raise SourceError("nicht_lesbar", f"Quelle 1 konnte für die Migration nicht gelesen werden: {_describe(exc)}.") from None
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass

    phases = _phase_lookup(site)
    labels = {c["key"]: c.get("label", c["key"]) for c in (site.get("score") or {}).get("criteria", [])
              if isinstance(c, dict) and c.get("key")}
    report = {"rows": data.row_count, "apply": [], "unassigned": [], "conflicts": [], "unchanged": 0}
    if data.missing_id:
        report["unassigned"].append({"id": "", "reason": f"{data.missing_id} Zeile(n) ohne ID"})
    with database.read() as conn:
        hub = {row["id"]: row for row in conn.execute("SELECT * FROM usecases")}
        scores = {}
        for row in conn.execute("SELECT usecase_id, criterion, value FROM usecase_scores"):
            scores.setdefault(row["usecase_id"], {})[row["criterion"]] = row["value"]
    for record in data.rows:
        current = hub.get(record["id"])
        if current is None:
            report["unassigned"].append({"id": record["id"], "reason": "ID im Hub nicht vorhanden – zuerst importieren"})
            continue
        changes = []

        def offer(target, label, value, hub_value, kind="field"):
            """Leere Hub-Felder werden gefüllt; abweichende Werte sind ein Widerspruch und bleiben unangetastet."""
            if value in ("", None):
                return
            if hub_value in ("", None):
                changes.append({"target": target, "label": label, "value": value, "kind": kind})
            elif str(hub_value) != str(value) and not (kind != "field" and float(hub_value) == float(value)):
                report["conflicts"].append({"id": record["id"], "label": label, "hub": hub_value, "source": value})

        def number(text, label):
            try:
                return dbm.clean_number(text)
            except ValueError:
                report["unassigned"].append({"id": record["id"], "reason": f"{label}: „{text}“ ist keine Zahl"})
                return None

        offer("owner", "Owner", record.get("owner", ""), current["owner"])
        if record.get("summary"):
            offer("description", "Beschreibung (aus AI Summary)", record["summary"], current["description"])
        if record.get("score"):
            value = number(record["score"], "Gesamtscore")
            if value is not None and (current["score"] is None or float(current["score"]) != value):
                offer("score", "Score", value, current["score"], "number")
        for field, text in record.items():
            if field.startswith(_SCORE_PREFIX) and text:
                key = field[len(_SCORE_PREFIX):]
                value = number(text, labels.get(key, key))
                have = scores.get(record["id"], {}).get(key)
                if value is not None and (have is None or float(have) != value):
                    offer(key, f"Score {labels.get(key, key)}", value, have, "criterion")
        status = record.get("phase", "")
        if status:
            mapped = phases.get(status.casefold())
            if mapped is None:
                report["unassigned"].append({"id": record["id"], "reason": f"Status „{status}“ ist keiner Phase "
                                             "zugeordnet (Alias in standort.json, value_lists.phase, ergänzen)"})
            elif mapped != current["phase"]:
                if current["phase"] == "Eingang":
                    changes.append({"target": "phase", "label": "Phase", "value": mapped, "kind": "field"})
                else:
                    report["conflicts"].append({"id": record["id"], "label": "Phase", "hub": current["phase"], "source": mapped})
        extra = []
        if record.get("internal_title") and record["internal_title"] != current["title"]:
            extra.append(f"Interner Titel: {record['internal_title']}")
        if record.get("lifecycle_required"):
            extra.append(f"Life Cycle erforderlich nach Implementierung: {record['lifecycle_required']}")
        line = "Aus der bisherigen Excel – " + "; ".join(extra) if extra else ""
        if line and line not in current["notes"]:
            changes.append({"target": "notes", "label": "Notizen", "kind": "field",
                            "value": f"{current['notes']}\n{line}".strip()})
        if changes:
            report["apply"].append({"id": record["id"], "title": current["title"], "changes": changes})
        else:
            report["unchanged"] += 1
    return report


def migration_apply(database, report, user, machine) -> dict:
    """Schreibt die übernehmbaren Angaben aus dem Bericht – in einer Transaktion, mit Audit."""
    written = 0
    with database.write(user=user, machine=machine, source="import") as tx:
        for entry in report["apply"]:
            for change in entry["changes"]:
                if change["kind"] == "criterion":
                    dbm.set_criterion_score(tx, entry["id"], change["target"], change["label"].replace("Score ", ""), change["value"])
                else:
                    dbm.update_field(tx, "usecases", entry["id"], change["target"], change["value"])
                written += 1
        tx.bump = written > 0
    return {"usecases": len(report["apply"]), "values": written}
