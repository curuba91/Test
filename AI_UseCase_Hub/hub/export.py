"""Reporting-Excel und Vollexport (Kapitel 11.1).

Die Reporting-Excel ist eine reine Ausgabedatei: Der Hub ist der einzige
Schreiber, sie wird nie zurückgelesen (kein Verstoß gegen X8/X9).

SCHEMA-STABILITÄT (FEST): Spaltennamen und -reihenfolge unten ändern sich nie;
neue Spalten kommen ans Ende. Keine E-Mail-Adressen, keine Notizfelder.
"""

import datetime
import os
import time
from pathlib import Path

from . import APP_VERSION, rules

REPORTING_DIR = "Hub_Reporting"
REPORTING_FILE = "AI_UseCase_Hub_Reporting.xlsx"

SCHEMA = {
    "tbl_usecases": ["id", "title", "area", "type", "origin", "owner", "score", "phase", "stage", "next_step",
                     "gov_done", "gov_total", "reg_status", "reg_result", "sponsor_status", "sponsor_date",
                     "board_status", "board_date", "portal_status", "comm_status", "comm_date", "lc_owner", "version",
                     "next_review", "last_review", "needs_help", "merged_into", "open_tickets", "attention",
                     "submitted_at", "created_at", "updated_at"],
    "tbl_milestones": ["id", "usecase_id", "title", "planned_date", "done_date", "overdue"],
    "tbl_releases": ["id", "usecase_id", "date", "version", "change", "released_by", "ticket_id"],
    "tbl_tickets": ["id", "title", "usecase_id", "type", "severity", "status", "assignee", "fix_version",
                    "submitted_at", "resolved_at", "closed_at", "age_days", "created_at", "updated_at"],
    "tbl_handlungsbedarf": ["rule", "level", "subject", "title", "text", "target"],
    "tbl_meta": ["key", "value"],
}
# Nie exportiert, auch nicht im Vollexport.
NEVER_EXPORTED = {"reporter_email"}


def build_tables(conn, cfg, source_states=(), test_mode=False) -> dict:
    """Inhalt der sechs Tabellen; Stufe, nächster Schritt und Handlungsbedarf kommen aus hub/rules.py (E7)."""
    today = datetime.date.today()
    deadline = rules.deadline_of(cfg)
    overview = {row["id"]: row for row in rules.overview(conn, deadline, today)}
    tables = {name: [] for name in SCHEMA}
    for uc in conn.execute("SELECT * FROM usecases ORDER BY id"):
        row = dict(uc)
        extra = overview[uc["id"]]
        row.update(stage=extra["stage_label"], next_step=extra["next_step"], gov_done=extra["gov_done"],
                   gov_total=extra["gov_total"], open_tickets=extra["open_tickets"], attention=extra["attention"],
                   submitted_at=extra["submitted"])
        tables["tbl_usecases"].append([row.get(column) for column in SCHEMA["tbl_usecases"]])
    for ms in conn.execute("SELECT * FROM milestones ORDER BY usecase_id, sort_order, planned_date, id"):
        row = dict(ms)
        row["overdue"] = int(bool(ms["planned_date"]) and ms["planned_date"] < today.isoformat() and not ms["done_date"])
        tables["tbl_milestones"].append([row.get(column) for column in SCHEMA["tbl_milestones"]])
    for release in conn.execute("SELECT * FROM releases ORDER BY usecase_id, date, id"):
        tables["tbl_releases"].append([release[column] for column in SCHEMA["tbl_releases"]])
    for ticket in conn.execute("SELECT * FROM tickets ORDER BY id"):
        row = dict(ticket)
        row["age_days"] = rules.ticket_age(ticket, today)
        tables["tbl_tickets"].append([row.get(column) for column in SCHEMA["tbl_tickets"]])
    for action in rules.handlungsbedarf(conn, cfg, list(source_states), test_mode, today):
        tables["tbl_handlungsbedarf"].append([action.get(column, "") for column in SCHEMA["tbl_handlungsbedarf"]])
    meta = conn.execute("SELECT * FROM meta").fetchone()
    tables["tbl_meta"] = [["exported_at", time.strftime("%Y-%m-%dT%H:%M:%S")], ["revision", meta["revision"]],
                          ["schema_version", meta["schema_version"]], ["app_version", APP_VERSION],
                          ["test_mode", int(bool(test_mode))]]
    return tables


def write_workbook(path, tables, columns) -> None:
    """Je Blatt genau eine formatierte Excel-Tabelle mit festem Namen; erst temporär, dann ersetzen."""
    import openpyxl
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, header in columns.items():
        sheet = workbook.create_sheet(title=name[:31])
        sheet.append(list(header))
        rows = tables.get(name) or [[None] * len(header)]  # eine Tabelle braucht mindestens eine Datenzeile
        for row in rows:
            sheet.append(["" if value is None else value for value in row])
        table = Table(displayName=name, ref=f"A1:{get_column_letter(len(header))}{len(rows) + 1}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        sheet.add_table(table)
        for index, title in enumerate(header, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = max(12, min(48, len(str(title)) + 4))
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp{path.suffix}")
    try:
        workbook.save(tmp)
        os.replace(tmp, path)  # schlägt fehl, solange die Zieldatei in Excel geöffnet ist
    finally:
        if tmp.exists():
            tmp.unlink()


def write_reporting(database, cfg, folder, source_states=(), test_mode=False) -> Path:
    with database.read() as conn:
        tables = build_tables(conn, cfg, source_states, test_mode)
    target = Path(folder) / REPORTING_FILE
    write_workbook(target, tables, SCHEMA)
    return target


def write_full(database, folder) -> Path:
    """Manueller Vollexport aller Tabellen inklusive Audit (ohne E-Mail-Adressen)."""
    tables, columns = {}, {}
    with database.read() as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        for name in names:
            header = [r[1] for r in conn.execute(f"PRAGMA table_info({name})") if r[1] not in NEVER_EXPORTED]
            columns[f"tbl_{name}"] = header
            tables[f"tbl_{name}"] = [list(row) for row in conn.execute(f"SELECT {', '.join(header)} FROM {name}")]
    target = Path(folder) / f"AI_UseCase_Hub_Vollexport_{time.strftime('%Y%m%d-%H%M%S')}.xlsx"
    write_workbook(target, tables, columns)
    return target


def tool_list(conn) -> list:
    """Auswahlliste für das Ticket-Formular: „UC-xxx – Titel“ der abgeschlossenen Lösungen (Regel S8)."""
    return [f"{row['id']} – {row['title']}" for row in
            conn.execute("SELECT id, title FROM usecases WHERE phase = 'Abgeschlossen' ORDER BY id")]
