"""Konfiguration laden/speichern und Ersteinrichtung.

Zwei Ebenen:

* Lokale Konfiguration (``config.json`` im lokalen Datenordner, pro Benutzer):
  Port, Pfade, Betriebsoptionen. Pfade werden relativ zum Programmordner
  gespeichert, sobald das möglich ist.
* Standortkonfiguration (``standort.json`` im Programmordner, für alle gleich):
  Bezeichnungen, Wertelisten, Spaltenzuordnung, Stichtag, Score-Regel.
  Die Datei wird von Hand oder per KI gepflegt (siehe ANPASSUNG.md) und beim
  Start geprüft.

Prüfung der Standortkonfiguration ohne Hub-Start::

    python -B -m hub.config
"""

import copy
import datetime
import json
import os
import sys
import time
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent.parent
SITE_FILE = "standort.json"
LOCAL_FILE = "config.json"
ENV_DATA_DIR = "AI_USECASE_HUB_DATA"
SITE_CONFIG_VERSION = 1

PATH_KEYS = {
    "source_usecases": {"label": "Quelle 1 – Use-Case-Excel", "kind": "file"},
    "source_tickets": {"label": "Quelle 2 – Ticket-Excel", "kind": "file"},
    "team_folder": {"label": "Team-Ordner", "kind": "dir"},
}

DEFAULT_LOCAL = {
    "config_version": 1,
    "port": 8765,
    "paths": {key: "" for key in PATH_KEYS},
    "auto_shutdown_minutes": 10,
    "import_interval_seconds": 20,
    "test_mode": False,
}

# Wertelisten, an denen Geschäftsregeln hängen. Die Schlüssel sind fest (sie
# stehen so in der Datenbank und in hub/rules.py); anpassbar sind nur die
# Anzeige (label) und die Alias-Werte für Import und Migration.
LOGIC_LISTS = {
    "phase": ["Eingang", "In Bearbeitung", "Abgeschlossen", "Zusammengeführt", "Discontinued"],
    "origin": ["lokal entwickelt", "übernommen"],
    "reg_status": ["offen", "Vorabcheck erfolgt", "bestätigt"],
    "sponsor_status": ["offen", "besprochen", "nicht erforderlich"],
    "board_status": ["offen", "vorgelegt", "freigegeben", "Nachschärfen gefordert", "nicht erforderlich"],
    "portal_status": ["offen", "veröffentlicht"],
    "comm_status": ["offen", "kommuniziert"],
    "ticket_status": ["Neu", "In Analyse", "In Umsetzung", "Gelöst", "Geschlossen", "Abgelehnt"],
    "ticket_severity": ["hoch", "mittel", "niedrig"],
}
FREE_LISTS = ["usecase_type", "ticket_type", "area"]
PLACEHOLDER = "PLATZHALTER"


def default_data_dir() -> Path:
    """Lokaler, nicht synchronisierter Datenordner (Kapitel 4.2)."""
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        return Path(override)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "AI_UseCase_Hub"
    return Path.home() / ".local" / "share" / "AI_UseCase_Hub"


def write_json_atomic(path: Path, data) -> None:
    """Erst in eine temporäre Datei schreiben, dann ersetzen (kein halber Stand)."""
    path = Path(path)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _is_iso_date(value) -> bool:
    try:
        datetime.date.fromisoformat(value)
        return isinstance(value, str) and len(value) == 10
    except (TypeError, ValueError):
        return False


def check_site(site) -> dict:
    """Prüft die Standortkonfiguration.

    Rückgabe: ``{"errors": [...], "open": [...]}``. ``errors`` machen die Datei
    unbrauchbar, ``open`` sind noch nicht bestätigte Platzhalter.
    """
    errors, open_items = [], []
    if not isinstance(site, dict):
        return {"errors": ["Die Datei muss ein JSON-Objekt enthalten."], "open": []}

    if site.get("config_version") != SITE_CONFIG_VERSION:
        errors.append(f"config_version muss {SITE_CONFIG_VERSION} sein.")

    labels = site.get("labels")
    if not isinstance(labels, dict):
        errors.append("labels fehlt oder ist kein Objekt.")
    else:
        pending = []
        for key, value in labels.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f"labels.{key} muss ein nicht leerer Text sein.")
            elif value.startswith("<") and value.endswith(">"):
                pending.append(key)
        if pending:
            open_items.append(f"labels: Platzhalter noch nicht ersetzt bei {', '.join(pending)}.")

    defaults = site.get("default_paths", {})
    if not isinstance(defaults, dict) or any(not isinstance(v, str) for v in defaults.values()):
        errors.append("default_paths muss ein Objekt mit Texten sein.")
    else:
        for key in defaults:
            if key not in PATH_KEYS:
                errors.append(f"default_paths.{key} ist unbekannt (erlaubt: {', '.join(PATH_KEYS)}).")

    deadline = site.get("deadline")
    if not isinstance(deadline, dict):
        errors.append("deadline fehlt oder ist kein Objekt.")
    else:
        date = deadline.get("date")
        if date is None:
            open_items.append("deadline.date: Stichtag der Richtlinie ist nicht festgelegt (Regel H09 bleibt ohne Frist).")
        elif not _is_iso_date(date):
            errors.append("deadline.date muss null oder ein Datum im Format JJJJ-MM-TT sein.")
        lead = deadline.get("lead_days")
        if isinstance(lead, bool) or not isinstance(lead, int) or lead < 0:
            errors.append("deadline.lead_days muss eine ganze Zahl ab 0 sein.")

    _check_score(site.get("score"), errors, open_items)
    _check_value_lists(site.get("value_lists"), errors, open_items)
    _check_columns(site.get("columns"), errors, open_items)
    return {"errors": errors, "open": open_items}


def _check_score(score, errors, open_items) -> None:
    if not isinstance(score, dict):
        errors.append("score fehlt oder ist kein Objekt.")
        return
    mode = score.get("mode")
    if mode not in ("manuell", "gewichtet"):
        errors.append('score.mode muss "manuell" oder "gewichtet" sein.')
    criteria = score.get("criteria")
    if not isinstance(criteria, list):
        errors.append("score.criteria muss eine Liste sein.")
        return
    seen = set()
    for index, item in enumerate(criteria):
        where = f"score.criteria[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("key"), str) or not item.get("key"):
            errors.append(f"{where}: key fehlt.")
            continue
        if item["key"] in seen:
            errors.append(f"{where}: key '{item['key']}' kommt mehrfach vor.")
        seen.add(item["key"])
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            errors.append(f"{where}: label fehlt.")
        weight = item.get("weight")
        weight_ok = isinstance(weight, (int, float)) and not isinstance(weight, bool) and weight > 0
        if weight is not None and not weight_ok:
            errors.append(f"{where}: weight muss null oder eine Zahl größer 0 sein.")
        if mode == "gewichtet" and not weight_ok:
            errors.append(f"{where}: bei score.mode = gewichtet braucht jedes Kriterium ein weight.")
    if mode == "manuell":
        open_items.append("score: Gesamtscore wird manuell eingegeben; Gewichte der Kriterien sind nicht hinterlegt.")


def _check_value_lists(lists, errors, open_items) -> None:
    if not isinstance(lists, dict):
        errors.append("value_lists fehlt oder ist kein Objekt.")
        return
    pending_logic = []
    for name, required in LOGIC_LISTS.items():
        where = f"value_lists.{name}"
        entry = lists.get(name)
        entries = entry.get("entries") if isinstance(entry, dict) else None
        if not isinstance(entries, list):
            errors.append(f"{where}.entries fehlt.")
            continue
        keys = [item.get("key") if isinstance(item, dict) else None for item in entries]
        if keys != required:
            errors.append(
                f"{where}: Die Schlüssel sind fest und müssen genau lauten: {', '.join(required)}. "
                "Anpassbar sind nur label und aliases."
            )
            continue
        aliases_seen = {}
        for item in entries:
            if not isinstance(item.get("label"), str) or not item["label"].strip():
                errors.append(f"{where}: Eintrag '{item['key']}' braucht ein label.")
            aliases = item.get("aliases", [])
            if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
                errors.append(f"{where}: aliases von '{item['key']}' muss eine Liste von Texten sein.")
                continue
            for alias in aliases:
                folded = alias.strip().casefold()
                if folded in aliases_seen and aliases_seen[folded] != item["key"]:
                    errors.append(f"{where}: Alias '{alias}' ist zwei Schlüsseln zugeordnet.")
                aliases_seen[folded] = item["key"]
        if entry.get("status") == PLACEHOLDER:
            pending_logic.append(name)
    if pending_logic:
        open_items.append(
            "value_lists: Anzeige-Texte und Alias-Werte nicht bestätigt bei " + ", ".join(pending_logic) + "."
        )
    for name in FREE_LISTS:
        where = f"value_lists.{name}"
        entry = lists.get(name)
        values = entry.get("values") if isinstance(entry, dict) else None
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            errors.append(f"{where}.values muss eine Liste von Texten sein.")
            continue
        if len({v.strip().casefold() for v in values}) != len(values):
            errors.append(f"{where}: Werte kommen mehrfach vor.")
        if entry.get("status") == PLACEHOLDER:
            open_items.append(f"{where}: Werte sind nicht bestätigt (bis dahin freie Texteingabe).")
    for name in lists:
        if name.startswith("_"):  # Hinweistexte
            continue
        if name not in LOGIC_LISTS and name not in FREE_LISTS:
            errors.append(f"value_lists.{name} ist unbekannt.")


def _check_columns(columns, errors, open_items) -> None:
    if not isinstance(columns, dict):
        errors.append("columns fehlt oder ist kein Objekt.")
        return
    for source, required in (("usecases", ("id", "title")), ("tickets", ("id", "title"))):
        mapping = columns.get(source)
        where = f"columns.{source}"
        if not isinstance(mapping, dict) or not isinstance(mapping.get("fields"), dict):
            errors.append(f"{where}.fields fehlt.")
            continue
        fields = mapping["fields"]
        used = {}
        for field, column in fields.items():
            if column is not None and (not isinstance(column, str) or not column.strip()):
                errors.append(f"{where}.fields.{field} muss null oder ein Spaltenname sein.")
            elif column is not None:
                folded = " ".join(column.split()).casefold()
                if folded in used:
                    errors.append(f"{where}: Spalte '{column}' ist {used[folded]} und {field} zugeordnet.")
                used[folded] = field
        for field in required:
            if field not in fields:
                errors.append(f"{where}.fields.{field} fehlt.")
            elif fields[field] is None:
                open_items.append(f"{where}.fields.{field}: Pflichtspalte ist nicht zugeordnet – Import nicht möglich.")
        missing = sorted(f for f, c in fields.items() if c is None and f not in required)
        if missing:
            open_items.append(f"{where}: ohne Spalte in der Quelle: {', '.join(missing)}.")
        if mapping.get("status") == PLACEHOLDER:
            open_items.append(f"{where}: Spaltenzuordnung ist nicht bestätigt.")


def load_site(program_dir: Path):
    """Liest ``standort.json``. Rückgabe: (Inhalt oder {}, Prüfergebnis)."""
    path = Path(program_dir) / SITE_FILE
    try:
        with open(path, encoding="utf-8-sig") as handle:
            site = json.load(handle)
    except FileNotFoundError:
        return {}, {"errors": [f"{SITE_FILE} fehlt im Programmordner."], "open": []}
    except json.JSONDecodeError as exc:
        message = f"{SITE_FILE} ist kein gültiges JSON (Zeile {exc.lineno}, Spalte {exc.colno}): {exc.msg}"
        return {}, {"errors": [message], "open": []}
    except OSError as exc:
        return {}, {"errors": [f"{SITE_FILE} ist nicht lesbar: {exc}"], "open": []}
    result = check_site(site)
    return (site if isinstance(site, dict) else {}), result


class Config:
    """Lokale Konfiguration plus Standortkonfiguration."""

    def __init__(self, program_dir=None, data_dir=None):
        self.program_dir = Path(program_dir) if program_dir else PROGRAM_DIR
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.warnings = []
        self.local = self._load_local()
        self.site, self.site_check = load_site(self.program_dir)
        self._apply_default_paths()

    # --- lokale Konfiguration -------------------------------------------------

    @property
    def local_path(self) -> Path:
        return self.data_dir / LOCAL_FILE

    def _load_local(self) -> dict:
        local = copy.deepcopy(DEFAULT_LOCAL)
        try:
            with open(self.local_path, encoding="utf-8") as handle:
                stored = json.load(handle)
            if not isinstance(stored, dict):
                raise ValueError("kein JSON-Objekt")
        except FileNotFoundError:
            return local
        except (OSError, ValueError) as exc:
            # Defekte Datei aufheben, mit Standardwerten weiterarbeiten.
            keep = self.local_path.with_name(f"config.defekt-{time.strftime('%Y%m%d-%H%M%S')}.json")
            try:
                os.replace(self.local_path, keep)
            except OSError:
                pass
            self.warnings.append(f"Lokale Konfiguration war nicht lesbar ({exc}) und wurde zurückgesetzt.")
            return local
        for key, default in DEFAULT_LOCAL.items():
            value = stored.get(key, default)
            if key == "paths":
                value = value if isinstance(value, dict) else {}
                local["paths"] = {k: value.get(k, "") if isinstance(value.get(k, ""), str) else "" for k in PATH_KEYS}
            elif type(value) is type(default) or (isinstance(default, int) and isinstance(value, (int, float))):
                local[key] = value
        return local

    def save_local(self) -> None:
        write_json_atomic(self.local_path, self.local)

    def _apply_default_paths(self) -> None:
        """Leere lokale Pfade aus ``default_paths`` füllen, wenn das Ziel existiert.

        So muss die Vertretung nichts einrichten, wenn der Team-Ordner bei ihr
        genauso synchronisiert ist.
        """
        defaults = self.site.get("default_paths")
        if not isinstance(defaults, dict):
            return
        changed = False
        for key in PATH_KEYS:
            candidate = defaults.get(key)
            if self.local["paths"][key] or not isinstance(candidate, str) or not candidate.strip():
                continue
            stored = self.to_stored(candidate)
            if self.check_path(key, stored) is None:
                self.local["paths"][key] = stored
                changed = True
        if changed:
            self.save_local()

    # --- Pfade ----------------------------------------------------------------

    def to_stored(self, raw: str) -> str:
        """Eingabe in die Speicherform bringen: relativ zum Programmordner, wenn möglich."""
        raw = (raw or "").strip().strip('"').strip()
        if not raw:
            return ""
        path = Path(os.path.expandvars(raw)).expanduser()
        if not path.is_absolute():
            path = self.program_dir / path
        normalized = os.path.normpath(str(path))
        try:
            relative = os.path.relpath(normalized, str(self.program_dir))
        except ValueError:  # anderes Laufwerk unter Windows
            return normalized
        return relative.replace("\\", "/")

    def resolve(self, stored: str):
        """Speicherform in einen absoluten Pfad auflösen (None bei leerem Wert)."""
        if not stored:
            return None
        path = Path(stored)
        if not path.is_absolute():
            path = self.program_dir / path
        return Path(os.path.normpath(str(path)))

    @staticmethod
    def is_relative(stored: str) -> bool:
        return bool(stored) and not Path(stored).is_absolute()

    def check_path(self, key: str, stored: str):
        """Klartext-Fehler für einen Pfad oder None, wenn er in Ordnung ist."""
        spec = PATH_KEYS[key]
        target = self.resolve(stored)
        if target is None:
            return "Noch nicht angegeben."
        if spec["kind"] == "file":
            if target.suffix.lower() != ".xlsx":
                return "Erwartet wird eine Excel-Datei mit der Endung .xlsx."
            if target.name.startswith("~$"):
                return "Das ist eine temporäre Sperrdatei von Excel, nicht die Arbeitsmappe."
            if not target.is_file():
                return f"Datei nicht gefunden: {target}"
        else:
            if not target.is_dir():
                return f"Ordner nicht gefunden: {target}"
            if self._inside(target, self.data_dir) or self._inside(self.data_dir, target):
                return "Der Team-Ordner darf nicht der lokale Datenordner sein (die Datenbank bleibt lokal)."
        return None

    @staticmethod
    def _inside(child: Path, parent: Path) -> bool:
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except (OSError, ValueError):
            return False

    def is_configured(self) -> bool:
        return all(self.check_path(key, self.local["paths"][key]) is None for key in PATH_KEYS)

    def path_report(self) -> dict:
        report = {}
        for key, spec in PATH_KEYS.items():
            stored = self.local["paths"][key]
            target = self.resolve(stored)
            report[key] = {
                "label": spec["label"],
                "kind": spec["kind"],
                "stored": stored,
                "resolved": str(target) if target else "",
                "relative": self.is_relative(stored),
                "error": self.check_path(key, stored),
            }
        return report

    # --- Standortkonfiguration ------------------------------------------------

    def reload_site(self) -> None:
        self.site, self.site_check = load_site(self.program_dir)

    def publish_default_paths(self) -> None:
        """Die eigenen relativen Pfade als Vorgabe für andere Rechner hinterlegen."""
        if self.site_check["errors"]:
            raise ValueError(f"{SITE_FILE} enthält Fehler und wird deshalb nicht verändert.")
        paths = self.local["paths"]
        if not self.is_configured():
            raise ValueError("Erst alle drei Pfade einrichten.")
        if not all(self.is_relative(paths[key]) for key in PATH_KEYS):
            raise ValueError("Nur relative Pfade lassen sich als Vorgabe hinterlegen (gleiches Laufwerk wie der Programmordner).")
        site = copy.deepcopy(self.site)
        site["default_paths"] = {key: paths[key] for key in PATH_KEYS}
        write_json_atomic(self.program_dir / SITE_FILE, site)
        self.reload_site()

    def label(self, key: str) -> str:
        labels = self.site.get("labels") if isinstance(self.site.get("labels"), dict) else {}
        return labels.get(key) or f"<{key}>"


def main(argv=None) -> int:
    """Prüft standort.json und gibt das Ergebnis aus."""
    argv = sys.argv[1:] if argv is None else argv
    program_dir = Path(argv[0]) if argv else PROGRAM_DIR
    _, result = load_site(program_dir)
    print(f"Prüfung von {program_dir / SITE_FILE}")
    for text in result["errors"]:
        print(f"  FEHLER  {text}")
    for text in result["open"]:
        print(f"  OFFEN   {text}")
    if result["errors"]:
        print(f"Ergebnis: {len(result['errors'])} Fehler – der Hub startet damit nur eingeschränkt.")
        return 1
    print(f"Ergebnis: gültig, {len(result['open'])} offene Punkte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
