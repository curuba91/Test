"""Schrittleiste und Handlungsbedarf – die einzige Stelle für Geschäftsregeln (E7).

Oberfläche, Export und Druckansicht rechnen nichts selbst, sondern zeigen, was
dieses Modul liefert (Kapitel 8).

STICHTAG (Regel H09): Das Datum steht in ``standort.json`` unter
``deadline.date`` (Format JJJJ-MM-TT), die Vorlaufzeit unter
``deadline.lead_days``. Solange ``date`` null ist, bleibt H09 in der Stufe
„Offen“ und nennt keine Frist. Im Code ist dafür nichts zu ändern.
"""

import datetime

from .config import PATH_KEYS, SITE_FILE
from .db import FIELD_LABELS

LEVEL_BLOCKING = "blockierend"
LEVEL_OPEN = "offen"

END_PHASES = ("Zusammengeführt", "Discontinued")
OPEN_TICKET_STATUS = ("Neu", "In Analyse", "In Umsetzung")
SOURCE_PATH_KEYS = ("source_usecases", "source_tickets")

STAGES = [("eingang", "Eingang"), ("umsetzung", "Umsetzung"), ("governance", "Governance"), ("betrieb", "Betrieb")]
STAGE_LABELS = dict(STAGES, archiv="Archiv")
PHASE_STAGE = {"Eingang": "eingang", "In Bearbeitung": "umsetzung", "Abgeschlossen": "governance"}

# Schritt: (Kennung, Anzeige, Stufe, „Nächster Schritt: …“, Hauptaktion, Abschnitt der Detailseite)
STEPS = [
    ("gemeldet", "Gemeldet", "eingang", "", "", "ueberblick"),
    ("bewertet", "Bewertet", "eingang", "Bewerten", "Bewerten", "ueberblick"),
    ("geplant", "Geplant", "umsetzung", "Meilenstein planen", "Meilenstein planen", "planung"),
    ("umgesetzt", "Umgesetzt", "umsetzung", "Umsetzung abschließen", "Als umgesetzt markieren", "planung"),
    ("betriebsbereit", "Betriebsbereit", "governance", "Betrieb einrichten", "Betrieb einrichten", "betrieb"),
    ("eingeordnet", "Eingeordnet", "governance", "Einordnung", "Einordnung eintragen", "governance"),
    ("sponsor", "Sponsor", "governance", "Sponsor-Abstimmung", "Sponsor-Abstimmung eintragen", "governance"),
    ("gremium", "Gremium", "governance", "Gremium", "Gremium eintragen", "governance"),
    ("portal", "Portal", "governance", "Portal", "Portal-Eintrag eintragen", "governance"),
    ("kommuniziert", "Kommuniziert", "governance", "Kommunikation", "Kommunikation eintragen", "governance"),
]
GOVERNANCE_STEPS = [step[0] for step in STEPS if step[2] == "governance"]
# H10 entfällt, wenn derselbe Schritt schon durch diese Regel gemeldet wird.
STEP_COVERED_BY = {"betriebsbereit": "H06", "eingeordnet": "H09", "gremium": "H04"}
# Reihenfolge, in der die Startseite den einen „Offen“-Eintrag je Use Case wählt.
OPEN_PRIORITY = ("H10", "H09", "H12")


def _action(rule, level, subject, text, target, title=""):
    return {"rule": rule, "level": level, "subject": subject, "title": title, "text": text, "target": target}


def _days(count) -> str:
    return f"{count} Tag" if count == 1 else f"{count} Tagen"


def _date(value):
    try:
        return datetime.date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


# --- Schrittleiste (8.1) --------------------------------------------------------


def _step_states(uc, milestones) -> dict:
    adopted = uc["origin"] == "übernommen"
    done = uc["phase"] == "Abgeschlossen"

    def flag(value):
        return "erfuellt" if value else "offen"

    states = {
        "gemeldet": "erfuellt",
        "bewertet": flag(uc["score"] is not None and uc["owner"] and uc["type"] and uc["origin"]),
        "geplant": flag(any(m["planned_date"] for m in milestones)),
        "umgesetzt": flag(done),
        "betriebsbereit": flag(uc["lc_owner"] and uc["version"] and uc["next_review"]),
        "eingeordnet": "erfuellt" if uc["reg_status"] == "bestätigt"
        else ("teil" if uc["reg_status"] == "Vorabcheck erfolgt" else "offen"),
        "sponsor": "entfaellt" if adopted or uc["sponsor_status"] == "nicht erforderlich"
        else flag(uc["sponsor_status"] == "besprochen"),
        "gremium": "entfaellt" if adopted or uc["board_status"] == "nicht erforderlich"
        else flag(uc["board_status"] == "freigegeben"),
        "portal": flag(uc["portal_status"] == "veröffentlicht"),
        "kommuniziert": flag(uc["comm_status"] == "kommuniziert"),
    }
    return states


def stepper(uc, milestones) -> dict:
    """Stufe, Schritte und nächster Schritt eines Use Cases."""
    states = _step_states(uc, milestones)
    steps = [{"key": key, "label": label, "stage": stage, "state": states[key]}
             for key, label, stage, _next, _action_label, _section in STEPS]
    applicable = [key for key in GOVERNANCE_STEPS if states[key] != "entfaellt"]
    gov_done = sum(1 for key in applicable if states[key] == "erfuellt")
    archived = uc["phase"] in END_PHASES

    if archived:
        stage = "archiv"
    else:
        stage = PHASE_STAGE.get(uc["phase"], "eingang")
        if stage == "governance" and gov_done == len(applicable):
            stage = "betrieb"

    next_step = None
    if not archived:
        for key, label, _stage, next_label, action_label, section in STEPS:
            if states[key] in ("offen", "teil"):
                next_step = {"key": key, "label": next_label, "action": action_label, "section": section}
                # Der Wechsel in die Umsetzung ist ein Phasenwechsel und wird als Aktion angeboten.
                if key == "geplant" and uc["phase"] == "Eingang":
                    next_step["action"] = "Umsetzung starten"
                break

    order = [key for key, _label in STAGES]
    current = order.index(stage) if stage in order else len(order)
    stages = []
    for index, (key, label) in enumerate(STAGES):
        own = [s for s in steps if s["stage"] == key and s["state"] != "entfaellt"]
        open_steps = sum(1 for s in own if s["state"] != "erfuellt")
        if key == "betrieb":
            state = "aktiv" if stage == "betrieb" else "offen"
        elif index == current:
            state = "aktiv"
        elif index < current:
            state = "erledigt" if open_steps == 0 else "luecke"
        else:
            state = "offen"
        stages.append({"key": key, "label": label, "state": state, "open_steps": open_steps,
                       "done_steps": len(own) - open_steps, "total_steps": len(own)})
    return {
        "stage": stage, "stage_label": STAGE_LABELS[stage], "stages": stages, "steps": steps, "next": next_step,
        "gov_done": gov_done, "gov_total": len(applicable),
    }


# --- Handlungsbedarf (8.2) --------------------------------------------------------


def _h09(uc, today, deadline, base, title):
    date = _date((deadline or {}).get("date"))
    text, level = "Regulatorische Einordnung fehlt", LEVEL_OPEN
    if date is not None:
        left = (date - today).days
        lead = (deadline or {}).get("lead_days") or 0
        if left > 0:
            text += f" (Stichtag in {_days(left)})"
        elif left == 0:
            text += " (Stichtag heute)"
        else:
            text += f" (Stichtag seit {_days(-left)} überschritten)"
        if left <= lead:
            level = LEVEL_BLOCKING
    return _action("H09", level, uc["id"], text, f"{base}/governance", title)


def usecase_actions(uc, milestones, release_count, today, deadline) -> list:
    """H01, H03 bis H06, H09, H10 und H12 für einen Use Case."""
    if uc["phase"] in END_PHASES:
        return []  # Endzustände erzeugen keinen Handlungsbedarf
    base = f"#/usecases/{uc['id']}"
    title = uc.get("title", "")
    done = uc["phase"] == "Abgeschlossen"
    actions = []

    for milestone in milestones:  # H01
        planned = _date(milestone["planned_date"])
        if planned is not None and planned < today and not milestone["done_date"]:
            actions.append(_action(
                "H01", LEVEL_BLOCKING, uc["id"],
                f"Meilenstein ‚{milestone['title']}‘ seit {_days((today - planned).days)} überfällig",
                f"{base}/planung", title))
    review = _date(uc["next_review"])  # H03
    if review is not None and review < today:
        actions.append(_action("H03", LEVEL_BLOCKING, uc["id"],
                               f"Review seit {_days((today - review).days)} überfällig", f"{base}/betrieb", title))
    if uc["board_status"] == "Nachschärfen gefordert":  # H04
        actions.append(_action("H04", LEVEL_BLOCKING, uc["id"], "Gremium fordert Nachschärfen",
                               f"{base}/governance", title))
    if uc["needs_help"]:  # H05
        note = f": {uc['help_note']}" if uc["help_note"] else ""
        actions.append(_action("H05", LEVEL_BLOCKING, uc["id"], f"Hilfe angefordert{note}", f"{base}/ueberblick", title))
    if done and not uc["lc_owner"]:  # H06
        actions.append(_action("H06", LEVEL_BLOCKING, uc["id"], "Kein Life-Cycle-Owner", f"{base}/betrieb", title))
    if done and uc["reg_status"] != "bestätigt":  # H09
        actions.append(_h09(uc, today, deadline, base, title))

    next_step = stepper(uc, milestones)["next"]  # H10: genau ein Eintrag je Use Case
    if next_step is not None:
        covered = STEP_COVERED_BY.get(next_step["key"])
        if covered not in {a["rule"] for a in actions}:  # kein Sachverhalt erscheint doppelt
            actions.append(_action("H10", LEVEL_OPEN, uc["id"], f"Nächster Schritt: {next_step['label']}",
                                   f"{base}/{next_step['section']}", title))
    if done and not release_count:  # H12
        actions.append(_action("H12", LEVEL_OPEN, uc["id"], "Keine Updatehistorie", f"{base}/betrieb", title))
    return actions


def ticket_age(ticket, today) -> int:
    start = _date(ticket["submitted_at"]) or _date(ticket["created_at"]) or today
    return max(0, (today - start).days)


def ticket_actions(tickets, today) -> list:
    """H02 und H11."""
    actions = []
    for ticket in tickets:
        target = f"#/tickets/{ticket['id']}"
        if ticket["status"] in OPEN_TICKET_STATUS and ticket["severity"] == "hoch":
            actions.append(_action(
                "H02", LEVEL_BLOCKING, ticket["id"],
                f"Ticket mit Schwere hoch seit {_days(ticket_age(ticket, today))} offen", target, ticket["title"]))
        if ticket["status"] == "Neu" and not ticket["usecase_id"]:
            actions.append(_action("H11", LEVEL_OPEN, ticket["id"], "Ticket zuordnen", target, ticket["title"]))
    return actions


def conflict_actions(conn, entity=None, entity_id=None) -> list:
    """H07: offener Import-Konflikt."""
    sql, params = "SELECT entity, entity_id, field FROM conflicts WHERE status = 'offen'", []
    if entity_id is not None:
        sql += " AND entity = ? AND entity_id = ?"
        params = [entity, entity_id]
    actions = []
    for row in conn.execute(sql + " ORDER BY id", params):
        label = FIELD_LABELS.get(row["field"], row["field"])
        actions.append(_action("H07", LEVEL_BLOCKING, row["entity_id"],
                               f"Quelle und Hub weichen ab: Feld {label}", "#/verwaltung/konflikte"))
    return actions


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


# --- Daten laden --------------------------------------------------------------------


class Snapshot:
    """Alle Daten, die die Regeln brauchen, mit wenigen Abfragen geladen."""

    def __init__(self, conn):
        self.usecases = [dict(row) for row in conn.execute("SELECT * FROM usecases ORDER BY id")]
        self.milestones = {}
        for row in conn.execute("SELECT * FROM milestones ORDER BY sort_order, planned_date, id"):
            self.milestones.setdefault(row["usecase_id"], []).append(dict(row))
        self.releases = dict(conn.execute("SELECT usecase_id, COUNT(*) FROM releases GROUP BY usecase_id").fetchall())
        self.tickets = [dict(row) for row in conn.execute("SELECT * FROM tickets ORDER BY id")]
        self.tickets_by_usecase = {}
        for ticket in self.tickets:
            if ticket["usecase_id"]:
                self.tickets_by_usecase.setdefault(ticket["usecase_id"], []).append(ticket)
        self.conflicts = conflict_actions(conn)


def deadline_of(cfg) -> dict:
    deadline = cfg.site.get("deadline")
    return deadline if isinstance(deadline, dict) else {}


def data_actions(conn, deadline, today=None, snapshot=None) -> list:
    """Handlungsbedarf aus den Daten: H01 bis H07 und H09 bis H12, nach Regel sortiert."""
    today = today or datetime.date.today()
    snap = snapshot or Snapshot(conn)
    titles = {uc["id"]: uc["title"] for uc in snap.usecases}
    titles.update({t["id"]: t["title"] for t in snap.tickets})
    actions = []
    for uc in snap.usecases:
        actions += usecase_actions(uc, snap.milestones.get(uc["id"], []), snap.releases.get(uc["id"], 0),
                                   today, deadline)
    actions += ticket_actions(snap.tickets, today)
    for action in snap.conflicts:
        actions.append(dict(action, title=titles.get(action["subject"], "")))
    actions.sort(key=lambda a: a["rule"])  # stabil: innerhalb einer Regel nach ID
    return actions


def handlungsbedarf(conn, cfg, source_states, test_mode=False, today=None) -> list:
    """Alle Einträge des Handlungsbedarfs. ``conn`` ist None, wenn keine Datenbank offen ist."""
    actions = system_actions(cfg, test_mode) + source_actions(source_states)
    if conn is not None:
        actions += data_actions(conn, deadline_of(cfg), today)
    return actions


def start_selection(actions, new_ids=()) -> list:
    """Regel gegen Überladung: je Use Case höchstens ein Eintrag der Stufe „Offen“, alle blockierenden.

    Was unter „Neu eingegangen“ steht (``new_ids``), erscheint nicht noch einmal als
    „Nächster Schritt: Bewerten“ (H10) oder „Ticket zuordnen“ (H11).
    """
    new_ids = set(new_ids)
    actions = [a for a in actions if not (a["rule"] in ("H10", "H11") and a["subject"] in new_ids)]
    chosen = {}
    for action in actions:
        if action["level"] != LEVEL_OPEN or action["rule"] not in OPEN_PRIORITY:
            continue
        best = chosen.get(action["subject"])
        if best is None or OPEN_PRIORITY.index(action["rule"]) < OPEN_PRIORITY.index(best["rule"]):
            chosen[action["subject"]] = action
    return [a for a in actions
            if a["level"] != LEVEL_OPEN or a["rule"] not in OPEN_PRIORITY or chosen[a["subject"]] is a]


def usecase_detail_actions(conn, uc, milestones, release_count, tickets, deadline, today=None) -> list:
    """Alle offenen Punkte eines Use Cases für die Detailseite (vollständig, ohne Kürzung)."""
    today = today or datetime.date.today()
    if uc["phase"] in END_PHASES:
        return []
    actions = usecase_actions(uc, milestones, release_count, today, deadline)
    actions += [a for a in ticket_actions(tickets, today) if a["rule"] == "H02"]
    actions += conflict_actions(conn, "usecases", uc["id"])
    actions.sort(key=lambda a: (a["level"] != LEVEL_BLOCKING, a["rule"]))
    return actions


# --- Übersichten ----------------------------------------------------------------------


def overview(conn, deadline, today=None) -> list:
    """Eine Zeile je Use Case mit Stufe, nächstem Schritt und Status – Grundlage für Liste und Export."""
    today = today or datetime.date.today()
    snap = Snapshot(conn)
    conflict_ids = {a["subject"] for a in snap.conflicts}
    rows = []
    for uc in snap.usecases:
        milestones = snap.milestones.get(uc["id"], [])
        tickets = snap.tickets_by_usecase.get(uc["id"], [])
        steps = stepper(uc, milestones)
        actions = usecase_actions(uc, milestones, snap.releases.get(uc["id"], 0), today, deadline)
        if steps["stage"] != "archiv":
            actions += [a for a in ticket_actions(tickets, today) if a["rule"] == "H02"]
            if uc["id"] in conflict_ids:
                actions.append({"level": LEVEL_BLOCKING})
        if any(a["level"] == LEVEL_BLOCKING for a in actions):
            attention = LEVEL_BLOCKING
        else:
            attention = LEVEL_OPEN if actions else "keiner"
        upcoming = sorted((m for m in milestones if m["planned_date"] and not m["done_date"]),
                          key=lambda m: m["planned_date"])
        next_step = steps["next"]
        rows.append({
            "id": uc["id"], "title": uc["title"], "owner": uc["owner"], "area": uc["area"],
            "reporter": uc["reporter"], "type": uc["type"], "origin": uc["origin"], "score": uc["score"],
            "phase": uc["phase"], "stage": steps["stage"], "stage_label": steps["stage_label"],
            "next_step": next_step["label"] if next_step else "",
            "next_target": f"#/usecases/{uc['id']}/{next_step['section']}" if next_step else "",
            "attention": attention, "gov_done": steps["gov_done"], "gov_total": steps["gov_total"],
            "reg_status": uc["reg_status"],
            "next_milestone": ({"title": upcoming[0]["title"], "planned_date": upcoming[0]["planned_date"],
                                "overdue": upcoming[0]["planned_date"] < today.isoformat()} if upcoming else None),
            "version": uc["version"], "lc_owner": uc["lc_owner"], "next_review": uc["next_review"],
            "open_tickets": sum(1 for t in tickets if t["status"] in OPEN_TICKET_STATUS),
            "submitted": uc["submitted_at"] or uc["created_at"][:10], "updated_at": uc["updated_at"],
        })
    return rows


def counts(conn) -> dict:
    """Zähler der Startseite; jede Zahl ist über die gefilterte Liste auflösbar."""
    snap = Snapshot(conn)
    result = {key: 0 for key in ("eingang", "umsetzung", "governance", "betrieb", "archiv")}
    reg_total = reg_confirmed = 0
    for uc in snap.usecases:
        result[stepper(uc, snap.milestones.get(uc["id"], []))["stage"]] += 1
        if uc["phase"] == "Abgeschlossen":
            reg_total += 1
            reg_confirmed += uc["reg_status"] == "bestätigt"
    result.update(
        tickets_open=sum(1 for t in snap.tickets if t["status"] in OPEN_TICKET_STATUS),
        usecases_total=len(snap.usecases), conflicts_open=len(snap.conflicts),
        reg_confirmed=reg_confirmed, reg_total=reg_total)
    return result


def new_items(conn, limit=200) -> dict:
    """„Neu eingegangen“: noch unbewertete Use Cases und neue Tickets, neueste zuerst."""
    usecases = conn.execute(
        "SELECT id, title, created_at FROM usecases WHERE phase = 'Eingang' AND owner = '' AND type = '' "
        "AND origin = '' AND score IS NULL").fetchall()
    tickets = conn.execute("SELECT id, title, created_at, usecase_id FROM tickets WHERE status = 'Neu'").fetchall()
    items = [{"kind": "usecases", "id": r["id"], "title": r["title"], "created_at": r["created_at"],
              "action": "Bewerten", "target": f"#/usecases/{r['id']}/ueberblick"} for r in usecases]
    items += [{"kind": "tickets", "id": r["id"], "title": r["title"], "created_at": r["created_at"],
               "action": "Öffnen" if r["usecase_id"] else "Zuordnen", "target": f"#/tickets/{r['id']}"}
              for r in tickets]
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return {"total": len(items), "items": items[:limit]}


def weighted_score(score_config, values):
    """Gesamtscore aus den Einzelscores, wenn ``score.mode = gewichtet``; sonst None.

    Formel: Summe(Einzelscore x weight) / Summe(weight). Weitere Regeln lassen
    sich hier ergänzen, ohne die Oberfläche anzufassen.
    """
    if not isinstance(score_config, dict) or score_config.get("mode") != "gewichtet":
        return None
    total = weight_sum = 0.0
    for criterion in score_config.get("criteria", []):
        value, weight = values.get(criterion["key"]), criterion.get("weight")
        if value is None or not weight:
            return None  # unvollständig: kein Gesamtscore
        total += float(value) * float(weight)
        weight_sum += float(weight)
    return round(total / weight_sum, 2) if weight_sum else None
