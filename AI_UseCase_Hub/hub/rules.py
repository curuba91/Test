"""Schrittleiste und Handlungsbedarf – die einzige Stelle für Geschäftsregeln (E7).

Stand Phase 1: H07 (Import-Konflikt) und H08 (Quelle/Einrichtung), dazu die
Zähler der Startseite. Schrittleiste und H01 bis H06 sowie H09 bis H12 folgen
in Phase 2.

STICHTAG (Regel H09): Das Datum steht in ``standort.json`` unter
``deadline.date`` (Format JJJJ-MM-TT), die Vorlaufzeit unter
``deadline.lead_days``. Solange ``date`` null ist, bleibt H09 in der Stufe
„Offen“ und nennt keine Frist. Im Code ist dafür nichts zu ändern.
"""

from .config import PATH_KEYS, SITE_FILE
from .db import ENTITY_LABELS, FIELD_LABELS

LEVEL_BLOCKING = "blockierend"
LEVEL_OPEN = "offen"

OPEN_TICKET_STATUS = ("Neu", "In Analyse", "In Umsetzung")
SOURCE_PATH_KEYS = ("source_usecases", "source_tickets")


def _action(rule, level, subject, text, target):
    return {"rule": rule, "level": level, "subject": subject, "text": text, "target": target}


def system_actions(cfg, test_mode=False) -> list:
    """H08, Teil Einrichtung: fehlerhafte Standortkonfiguration, fehlende Pfade."""
    actions = []
    for text in cfg.site_check["errors"]:
        actions.append(_action("H08", LEVEL_BLOCKING, SITE_FILE, f"Standortkonfiguration fehlerhaft: {text}",
                               "#/verwaltung/einstellungen"))
    for key, spec in PATH_KEYS.items():
        if test_mode and key in SOURCE_PATH_KEYS:
            continue  # der Testmodus bringt eigene Quellen mit
        error = cfg.check_path(key, cfg.local["paths"][key])
        if error is not None:
            actions.append(_action("H08", LEVEL_BLOCKING, spec["label"], f"Nicht eingerichtet. {error}",
                                   "#/verwaltung/einstellungen"))
    return actions


def source_actions(states) -> list:
    """H08, Teil Import: Quelle nicht lesbar, Spalte fehlt, Zeilen ohne ID."""
    actions = []
    for state in states:
        if state["state"] in ("nicht_lesbar", "spalte_fehlt", "zuordnung_fehlt"):
            actions.append(_action("H08", LEVEL_BLOCKING, state["label"], state["message"], "#/verwaltung/quellen"))
        elif state["state"] == "ok" and state["missing_id"]:
            count = state["missing_id"]
            actions.append(_action(
                "H08", LEVEL_BLOCKING, state["label"],
                f"{count} {'Zeile' if count == 1 else 'Zeilen'} ohne ID – nicht importiert. "
                "Die ID-Spalte in der Quell-Excel ergänzen.", "#/verwaltung/quellen"))
    return actions


def conflict_actions(conn) -> list:
    """H07: offener Import-Konflikt."""
    actions = []
    rows = conn.execute("SELECT entity, entity_id, field FROM conflicts WHERE status = 'offen' ORDER BY id")
    for row in rows:
        label = FIELD_LABELS.get(row["field"], row["field"])
        actions.append(_action("H07", LEVEL_BLOCKING, row["entity_id"],
                               f"Quelle und Hub weichen ab: Feld {label}", "#/verwaltung/konflikte"))
    return actions


def handlungsbedarf(conn, cfg, source_states, test_mode=False) -> list:
    """Alle Einträge des Handlungsbedarfs. ``conn`` ist None, wenn keine Datenbank offen ist."""
    actions = system_actions(cfg, test_mode) + source_actions(source_states)
    if conn is not None:
        actions += conflict_actions(conn)
    return actions


def counts(conn) -> dict:
    """Zähler der Startseite. Governance und Betrieb hängen an der Schrittleiste (Phase 2)."""
    by_phase = dict(conn.execute("SELECT phase, COUNT(*) FROM usecases GROUP BY phase").fetchall())
    marks = ", ".join("?" * len(OPEN_TICKET_STATUS))
    tickets_open = conn.execute(
        f"SELECT COUNT(*) FROM tickets WHERE status IN ({marks})", OPEN_TICKET_STATUS).fetchone()[0]
    return {
        "eingang": by_phase.get("Eingang", 0),
        "umsetzung": by_phase.get("In Bearbeitung", 0),
        "governance": None,
        "betrieb": None,
        "tickets_open": tickets_open,
        "usecases_total": sum(by_phase.values()),
        "conflicts_open": conn.execute("SELECT COUNT(*) FROM conflicts WHERE status = 'offen'").fetchone()[0],
    }


def new_items(conn, limit=10) -> dict:
    """„Neu eingegangen“: noch unbewertete Use Cases und neue Tickets, neueste zuerst."""
    usecases = conn.execute(
        "SELECT id, title, created_at FROM usecases WHERE phase = 'Eingang' AND owner = '' AND type = '' "
        "AND origin = '' AND score IS NULL").fetchall()
    tickets = conn.execute("SELECT id, title, created_at FROM tickets WHERE status = 'Neu'").fetchall()
    items = [{"kind": "usecases", "kind_label": ENTITY_LABELS["usecases"], "id": r["id"], "title": r["title"],
              "created_at": r["created_at"], "target": f"#/usecases/{r['id']}"} for r in usecases]
    items += [{"kind": "tickets", "kind_label": ENTITY_LABELS["tickets"], "id": r["id"], "title": r["title"],
               "created_at": r["created_at"], "target": f"#/tickets/{r['id']}"} for r in tickets]
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return {"total": len(items), "items": items[:limit]}
