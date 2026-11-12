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
