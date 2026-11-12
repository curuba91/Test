"""Testmodus: erfundene Beispieldaten in eigenen Test-Quellen (Kapitel 6.1).

Die Test-Quellen liegen im lokalen Datenordner unter ``test/`` und haben
dieselben Spalten wie die echten Quellen laut ``standort.json`` (inklusive der
Pflegespalten für die Migration). Die echten Quell-Excels werden hier nie
berührt.
"""

import datetime
from pathlib import Path

from . import db as dbm

FILES = {"usecases": "Quelle1_UseCases.xlsx", "tickets": "Quelle2_Tickets.xlsx"}

# Ersatznamen, falls ein Feld in standort.json (noch) keiner Spalte zugeordnet ist.
FALLBACK_COLUMNS = {
    "usecases": {"id": "ID", "title": "Titel Use Case"},
    "tickets": {"id": "ID", "title": "Titel"},
}

USECASES = [
    # Titel, Nutzen, Verantwortlich, fünf Einzelscores, Life Cycle, Gesamtscore, Status
    ("Besprechungsprotokolle zusammenfassen", "Weniger Nacharbeit nach Terminen, einheitliche Protokolle", "Person A", (2, 1, 4, 2, 5), "nein", 2.8, "Abgeschlossen"),
    ("Abweichungsberichte vorformulieren", "Schnellere Erstfassung, weniger Rückfragen", "Person B", (5, 3, 4, 3, 3), "ja", 3.6, "In Bearbeitung"),
    ("Suche in Arbeitsanweisungen", "Antworten in Sekunden statt Suche in Ordnern", "Person A", (4, 2, 4, 2, 5), "ja", 3.4, "Abgeschlossen"),
    ("Schichtübergabe strukturieren", "Keine vergessenen Punkte bei der Übergabe", "Person C", (4, 1, 3, 2, 4), "ja", 2.8, "In Bearbeitung"),
    ("Trendanalyse Reklamationen", "Häufungen früher erkennen", "Person B", (4, 5, 2, 3, 2), "ja", 3.2, "Neu"),
    ("Schulungsunterlagen übersetzen", "Unterlagen schneller in weiteren Sprachen", "", (1, 1, 4, 3, 3), "", None, "Neu"),
    ("Chargendokumentation auf Vollständigkeit prüfen", "Fehlende Einträge vor der Freigabe finden", "Person C", (5, 3, 3, 3, 2), "ja", 3.2, "Neu"),
    ("Wartungsberichte klassifizieren", "Auswertung nach Ursache ohne Handarbeit", "", (2, 3, 3, 3, 2), "", None, "Neu"),
    ("CAPA-Maßnahmen entwerfen", "Vorschläge aus ähnlichen früheren Fällen", "Person B", (3, 5, 3, 2, 2), "ja", 3.0, "Neu"),
    ("FAQ-Assistent zum Qualitätshandbuch", "Entlastung der Qualitätsabteilung bei Standardfragen", "", (2, 1, 3, 2, 5), "", None, "Neu"),
]

TICKETS = [
    # Titel, Beschreibung, Use-Case-Nummer oder Freitext, Melder:in, Tage zurück
    ("Zusammenfassung lässt Beschlüsse aus", "Bei langen Protokollen fehlen die Beschlüsse am Ende.", 1, "Person D", 4),
    ("Suche findet neue Version der Anweisung nicht", "Es wird noch die abgelöste Fassung angezeigt.", 3, "Person E", 9),
    ("Wunsch: Export als Word", "Die Zusammenfassung soll als Word-Datei speicherbar sein.", 1, "Person F", 15),
    ("Antwort ohne Quellenangabe", "Bei manchen Antworten fehlt der Verweis auf den Abschnitt.", 3, "Person D", 2),
    ("Wie melde ich mich an?", "Der Link aus der Schulung funktioniert nicht.", "Chat-Assistent allgemein", "Person G", 1),
    ("Falsche Sprache in der Ausgabe", "Die Zusammenfassung kam auf Englisch.", 1, "Person E", 21),
]


def source_paths(root) -> dict:
    return {key: Path(root) / name for key, name in FILES.items()}


def _columns(site, key) -> dict:
    """Feld -> Spaltenname laut Standortkonfiguration (nur zugeordnete Felder)."""
    columns = site.get("columns") if isinstance(site.get("columns"), dict) else {}
    entry = columns.get(key) if isinstance(columns.get(key), dict) else {}
    fields = entry.get("fields") if isinstance(entry.get("fields"), dict) else {}
    mapped = {f: c for f, c in fields.items() if isinstance(c, str) and c.strip()}
    for field, column in FALLBACK_COLUMNS[key].items():
        mapped.setdefault(field, column)
    return mapped


def _migration_columns(site) -> dict:
    migration = site.get("migration") if isinstance(site.get("migration"), dict) else {}
    columns = migration.get("columns") if isinstance(migration.get("columns"), dict) else {}
    return {f: c for f, c in columns.items() if isinstance(c, str) and c.strip()}


def _usecase_title(number) -> str:
    return USECASES[number - 1][0]


def _usecase_record(number) -> dict:
    title, benefit, owner, scores, lifecycle, total, status = USECASES[number - 1]
    return {
        "id": number, "title": title, "benefit": benefit,
        "folder_link": f"https://beispiel.invalid/ordner/uc-{number:03d}",
        "description": f"Beispielbeschreibung zu „{title}“.", "area": ["Produktion", "Qualität", "Technik"][number % 3],
        "reporter": f"Person {'DEFG'[number % 4]}", "reporter_email": f"person{number}@beispiel.invalid",
        "submitted_at": (datetime.date.today() - datetime.timedelta(days=10 * (len(USECASES) - number) + 3)).isoformat(),
        # Pflegespalten der bisherigen Excel (nur für die Migration, Phase 6)
        "internal_title": title, "summary": f"Kurzfassung: {benefit}.", "owner": owner,
        "score_rft": scores[0], "score_capa": scores[1], "score_time": scores[2], "score_cost": scores[3],
        "score_users": scores[4], "lifecycle_required": lifecycle, "score": total, "phase": status,
    }


def _ticket_record(number) -> dict:
    title, description, tool, reporter, days = TICKETS[number - 1]
    if isinstance(tool, int):
        tool = f"UC-{tool:03d} – {_usecase_title(tool)}"
    return {
        "id": number, "title": title, "description": description, "affected_tool_raw": tool, "reporter": reporter,
        "submitted_at": (datetime.date.today() - datetime.timedelta(days=days)).isoformat(),
    }


def ensure_sources(site, root) -> dict:
    """Legt die Test-Quellen an, falls sie fehlen."""
    import openpyxl

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    paths = source_paths(root)
    if not paths["usecases"].exists():
        columns = dict(_columns(site, "usecases"))
        for field, column in _migration_columns(site).items():
            columns.setdefault(field, column)
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Use Cases"
        sheet.append(list(columns.values()))
        for number in range(1, len(USECASES) + 1):
            record = _usecase_record(number)
            sheet.append([record.get(field) for field in columns])
            if number == 4:  # Flow-Wiederholung: dieselbe ID ein zweites Mal (S3)
                sheet.append([record.get(field) for field in columns])
        workbook.save(paths["usecases"])
    if not paths["tickets"].exists():
        columns = _columns(site, "tickets")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Tickets"
        sheet.append(list(columns.values()))
        for number in range(1, len(TICKETS) + 1):
            record = _ticket_record(number)
            sheet.append([record.get(field) for field in columns])
        workbook.save(paths["tickets"])
    return paths


def simulate(site, root, database, user, machine) -> list:
    """Verändert die Test-Quellen so, als wären neue Meldungen eingegangen.

    Erzeugt eine neue Meldung je Quelle, eine stille Übernahme (S4) und – beim
    ersten Aufruf – einen Konflikt (S5). Rückgabe: Klartext der Schritte.
    """
    import openpyxl

    paths = ensure_sources(site, root)
    steps = []

    uc_columns = _columns(site, "usecases")
    workbook = openpyxl.load_workbook(paths["usecases"])
    sheet = workbook.active
    header = [cell.value for cell in sheet[1]]
    position = {field: header.index(column) + 1 for field, column in uc_columns.items() if column in header}
    ids = [row[position["id"] - 1].value for row in sheet.iter_rows(min_row=2) if row[position["id"] - 1].value]
    next_id = max(int(i) for i in ids if str(i).isdigit()) + 1

    def find_row(number):
        for row in sheet.iter_rows(min_row=2):
            if row[position["id"] - 1].value == number:
                return row
        return None

    new_row = [None] * len(header)
    new_row[position["id"] - 1] = next_id
    new_row[position["title"] - 1] = f"Neue Meldung {next_id} aus dem Formular"
    if "benefit" in position:
        new_row[position["benefit"] - 1] = "Im Testmodus simulierte Meldung"
    sheet.append(new_row)
    steps.append(f"Quelle 1: neue Zeile mit ID {next_id} angehängt.")

    if "benefit" in position and find_row(2) is not None:
        cell = find_row(2)[position["benefit"] - 1]
        cell.value = f"{str(cell.value or '').split(' (geändert')[0]} (geändert am {dbm.now_ts()[11:19]})"
        steps.append("Quelle 1: Nutzen von UC-002 geändert – im Hub unverändert, wird still übernommen (S4).")

    with database.read() as conn:
        current = conn.execute("SELECT title, title_src FROM usecases WHERE id = 'UC-004'").fetchone()
    if current is not None and current["title"] == current["title_src"] and find_row(4) is not None:
        with database.write(user=user, machine=machine, source="oberfläche") as tx:
            dbm.update_field(tx, "usecases", "UC-004", "title", "Schichtübergabe (im Hub umbenannt)")
        for row in sheet.iter_rows(min_row=2):
            if row[position["id"] - 1].value == 4:
                row[position["title"] - 1].value = "Schichtübergabe digital strukturieren"
        steps.append("UC-004: Titel im Hub und in Quelle 1 unterschiedlich geändert – ergibt einen Konflikt (S5).")
    workbook.save(paths["usecases"])

    t_columns = _columns(site, "tickets")
    workbook = openpyxl.load_workbook(paths["tickets"])
    sheet = workbook.active
    header = [cell.value for cell in sheet[1]]
    position = {field: header.index(column) + 1 for field, column in t_columns.items() if column in header}
    numbers = [row[position["id"] - 1].value for row in sheet.iter_rows(min_row=2) if row[position["id"] - 1].value]
    next_ticket = max(int(i) for i in numbers if str(i).isdigit()) + 1
    new_row = [None] * len(header)
    new_row[position["id"] - 1] = next_ticket
    new_row[position["title"] - 1] = f"Simuliertes Problem {next_ticket}"
    for field, value in (("description", "Im Testmodus simulierte Meldung."),
                         ("affected_tool_raw", f"UC-003 – {_usecase_title(3)}"),
                         ("reporter", "Person H"), ("submitted_at", dbm.today())):
        if field in position:
            new_row[position[field] - 1] = value
    sheet.append(new_row)
    workbook.save(paths["tickets"])
    steps.append(f"Quelle 2: neue Zeile mit ID {next_ticket} angehängt.")
    return steps
