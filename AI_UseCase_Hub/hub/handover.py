"""Sperre, Übergabestand, Backups.

Phase 1 enthält die Backups (Kapitel 6.1 und 5.3). Sperre und Übergabestand
folgen in Phase 5.
"""

import os
import re
import sqlite3
import time
from pathlib import Path

BACKUP_KEEP = 30
_NAME = re.compile(r"^hub_(\d{8}-\d{6})(?:-(\d+))?_([a-z]+)\.db$")
LABELS = {"start": "Start", "migration": "vor Migration", "uebernahme": "vor Übernahme",
          "wiederherstellung": "vor Wiederherstellung"}


def _open_read_only(path):
    # as_uri() liefert die von SQLite dokumentierte Form (file:///C:/...) und
    # maskiert Leerzeichen und Sonderzeichen im Pfad.
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def is_valid(path) -> bool:
    """Lässt sich die Datei öffnen und besteht sie die Integritätsprüfung?"""
    try:
        conn = _open_read_only(path)
    except (sqlite3.Error, ValueError):
        return False
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        return len(rows) == 1 and rows[0][0] == "ok"
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def create_backup(database, folder, label="start", keep=BACKUP_KEEP) -> Path:
    """Kopie mit Zeitstempel über die SQLite-Backup-Funktion; die letzten ``keep`` je Anlass bleiben."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = folder / f"hub_{stamp}_{label}.db"
    counter = 1
    while target.exists():
        counter += 1
        target = folder / f"hub_{stamp}-{counter}_{label}.db"
    tmp = target.with_suffix(".tmp")
    try:
        database.backup_to(tmp)
        if not is_valid(tmp):
            raise RuntimeError("Das Backup hat die Integritätsprüfung nicht bestanden.")
        os.replace(tmp, target)
    finally:
        if tmp.exists():
            tmp.unlink()
    for old in [b for b in list_backups(folder) if b["label_key"] == label][keep:]:
        try:
            Path(old["path"]).unlink()
        except OSError:
            pass
    return target


def list_backups(folder) -> list:
    """Backups, neueste zuerst."""
    folder = Path(folder)
    items = []
    if not folder.is_dir():
        return items
    for path in folder.iterdir():
        match = _NAME.match(path.name)
        if not match:
            continue
        stamp, counter, label = match.groups()
        items.append({
            "order": (stamp, int(counter or 1)),
            "name": path.name,
            "path": str(path),
            "ts": f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}",
            "label_key": label,
            "label": LABELS.get(label, label),
            "size": path.stat().st_size,
        })
    items.sort(key=lambda item: item.pop("order"), reverse=True)
    return items


def latest_valid_backup(folder):
    for item in list_backups(folder):
        if is_valid(item["path"]):
            return item
    return None


def restore_backup(backup_path, db_path) -> Path:
    """Ersetzt die (geschlossene) Datenbank durch ein Backup.

    Die bisherige Datei bleibt unter neuem Namen erhalten. Rückgabe: deren Pfad
    (oder None, wenn es keine gab).
    """
    backup_path, db_path = Path(backup_path), Path(db_path)
    if not is_valid(backup_path):
        raise ValueError("Das gewählte Backup ist nicht lesbar oder beschädigt.")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    kept = None
    tmp = db_path.with_name(db_path.name + ".neu")
    source = _open_read_only(backup_path)
    try:
        target = sqlite3.connect(str(tmp))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    if db_path.exists():
        kept = db_path.with_name(f"{db_path.stem}.ersetzt-{stamp}{db_path.suffix}")
        os.replace(db_path, kept)
    # Ein liegengebliebenes Journal der alten Datei darf nicht auf die neue angewendet werden.
    journal = db_path.with_name(db_path.name + "-journal")
    if journal.exists():
        os.replace(journal, journal.with_name(f"{db_path.stem}.ersetzt-{stamp}.journal"))
    os.replace(tmp, db_path)
    return kept


# --- Sperre und Übergabestand (Kapitel 6.2 und 6.3) ---------------------------------------

import json
import shutil
import uuid

HANDOVER_DIR = "Hub_Uebergabe"
STAND_FILE = "stand.db"
STAND_INFO = "stand.json"
LOCK_FILE = "aktiv.lock"
USERS_FILE = "berechtigte.json"
LOCK_EXPIRY_SECONDS = 300
LOCK_BEAT_SECONDS = 60
LABELS["fremd"] = "fremder Stand (aufgehoben)"


def _write_json(path, data) -> None:
    tmp = Path(str(path) + f".{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def lock_state(folder, user, machine, now=None):
    """Rückgabe: ("frei" | "eigene" | "fremd", Inhalt der Sperrdatei oder None).

    Die Sperre verfällt 5 Minuten nach dem letzten Lebenszeichen. Wegen der
    Synchronisationsverzögerung ist sie nur ein Hinweis; die eigentliche
    Absicherung ist die Erkennung „auseinandergelaufen“ (check_start).
    """
    lock = _read_json(Path(folder) / LOCK_FILE)
    now = time.time() if now is None else now
    if not lock or now - float(lock.get("heartbeat", 0) or 0) > LOCK_EXPIRY_SECONDS:
        return "frei", lock
    if lock.get("user") == user and lock.get("machine") == machine:
        return "eigene", lock
    return "fremd", lock


def write_lock(folder, user, machine, started, instance, now=None) -> None:
    Path(folder).mkdir(parents=True, exist_ok=True)
    _write_json(Path(folder) / LOCK_FILE, {"user": user, "machine": machine, "started": started,
                                           "heartbeat": time.time() if now is None else now, "instance": instance})


def release_lock(folder, instance) -> None:
    path = Path(folder) / LOCK_FILE
    lock = _read_json(path)
    if lock and lock.get("instance") == instance:
        try:
            path.unlink()
        except OSError:
            pass


def authorized_users(folder, user) -> list:
    """Liste der berechtigten Benutzer. Beim ersten Start wird sie mit dem aktuellen Benutzer angelegt."""
    path = Path(folder) / USERS_FILE
    data = _read_json(path)
    if data is None or not isinstance(data.get("users"), list):
        Path(folder).mkdir(parents=True, exist_ok=True)
        data = {"_hinweis": "Benutzer, die im Hub schreiben dürfen (Hauptperson und Vertretung). Alle anderen "
                            "sehen den Hub nur lesend. Pflege unter Verwaltung → Übergabe & Backups.",
                "users": [user]}
        _write_json(path, data)
    return [str(u) for u in data["users"] if str(u).strip()]


def set_authorized_users(folder, users, current_user) -> list:
    clean = []
    for name in users:
        name = str(name).strip()
        if name and name.casefold() not in [c.casefold() for c in clean]:
            clean.append(name)
    if current_user.casefold() not in [c.casefold() for c in clean]:
        raise ValueError("Der eigene Benutzer muss in der Liste bleiben, sonst sperrt sich der Hub selbst aus.")
    data = _read_json(Path(folder) / USERS_FILE) or {}
    data["users"] = clean
    _write_json(Path(folder) / USERS_FILE, data)
    return clean


def is_authorized(users, user) -> bool:
    return user.casefold() in [u.casefold() for u in users]


def publish(database, folder, user="", machine="") -> str:
    """Veröffentlicht einen konsistenten Übergabestand als ``stand.db``.

    Die neue ``stand_id`` wird zuerst in die Kopie geschrieben und erst nach
    erfolgreichem Ersetzen in die lokale Datenbank – so passt die lokale
    Kennung immer zu einer Datei, die tatsächlich im Übergabe-Ordner liegt.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stand_id = uuid.uuid4().hex
    tmp = folder / f"stand.{os.getpid()}.tmp"
    try:
        database.backup_to(tmp)
        copy = sqlite3.connect(str(tmp))
        try:
            copy.execute("PRAGMA journal_mode=DELETE")
            copy.execute("UPDATE meta SET stand_id_published = ?, revision_published = revision", (stand_id,))
            copy.commit()
            revision = copy.execute("SELECT revision FROM meta").fetchone()[0]
        finally:
            copy.close()
        if not is_valid(tmp):
            raise RuntimeError("Der Übergabestand hat die Integritätsprüfung nicht bestanden.")
        os.replace(tmp, folder / STAND_FILE)
    finally:
        if tmp.exists():
            tmp.unlink()
    with database.write() as tx:
        tx.execute("UPDATE meta SET stand_id_published = ?, revision_published = ?", (stand_id, revision))
        tx.bump = False
    _write_json(folder / STAND_INFO, {"stand_id": stand_id, "user": user, "machine": machine,
                                      "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "revision": revision})
    return stand_id


def inspect_shared(folder, tmp_dir, attempts=3, pause=0.5):
    """Liest eine Temp-Kopie von ``stand.db``. Rückgabe: None (kein Stand) oder Angaben zum Stand."""
    source = Path(folder) / STAND_FILE
    if not source.exists():
        return None
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)
    target = Path(tmp_dir) / "stand_pruefung.db"
    info = _read_json(Path(folder) / STAND_INFO) or {}
    for attempt in range(attempts):
        try:
            shutil.copyfile(source, target)
            if is_valid(target):
                conn = _open_read_only(target)
                try:
                    row = conn.execute("SELECT schema_version, revision, stand_id_published FROM meta").fetchone()
                finally:
                    conn.close()
                same = info.get("stand_id") == row[2]
                return {"valid": True, "path": str(target), "schema_version": row[0], "revision": row[1],
                        "stand_id": row[2], "user": info.get("user", "") if same else "",
                        "machine": info.get("machine", "") if same else "", "ts": info.get("ts", "") if same else ""}
        except (OSError, sqlite3.Error, TypeError):
            pass
        if attempt + 1 < attempts and pause:
            time.sleep(pause)
    return {"valid": False, "path": str(target)}


def check_start(local_meta, shared, program_schema) -> str:
    """Die fünf Situationen aus Kapitel 6.2 (plus „unlesbar“ für eine halb synchronisierte Datei)."""
    if shared is None:
        return "kein_stand"
    if not shared["valid"]:
        return "unlesbar"
    if shared["schema_version"] > program_schema:
        return "schema_neuer"
    if shared["stand_id"] == local_meta["stand_id_published"]:
        return "gleich"
    if local_meta["revision"] == local_meta["revision_published"]:
        return "fremd_neuer"
    return "auseinander"


def keep_foreign_copy(shared_path, backup_folder) -> Path:
    """Hebt den nicht übernommenen fremden Stand als Backup auf."""
    backup_folder = Path(backup_folder)
    backup_folder.mkdir(parents=True, exist_ok=True)
    target = backup_folder / f"hub_{time.strftime('%Y%m%d-%H%M%S')}_fremd.db"
    shutil.copyfile(shared_path, target)
    return target
