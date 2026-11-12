"""Schrittleiste und Handlungsbedarf – die einzige Stelle für Geschäftsregeln (E7).

Phase 0 enthält nur die Systemhinweise, die ohne Datenbank entstehen
(Einrichtung, Standortkonfiguration). Die Regeln H01 bis H12 folgen in Phase 2.
"""

from .config import PATH_KEYS, SITE_FILE

LEVEL_BLOCKING = "blockierend"
LEVEL_OPEN = "offen"


def system_actions(cfg) -> list:
    """Handlungsbedarf aus dem Zustand der Einrichtung (Vorstufe von H08)."""
    actions = []
    for text in cfg.site_check["errors"]:
        actions.append({
            "rule": "H08",
            "level": LEVEL_BLOCKING,
            "subject": SITE_FILE,
            "text": f"Standortkonfiguration fehlerhaft: {text}",
            "target": "#/verwaltung/einstellungen",
        })
    for key, spec in PATH_KEYS.items():
        error = cfg.check_path(key, cfg.local["paths"][key])
        if error is None:
            continue
        actions.append({
            "rule": "H08",
            "level": LEVEL_BLOCKING,
            "subject": spec["label"],
            "text": f"Nicht eingerichtet. {error}",
            "target": "#/verwaltung/einstellungen",
        })
    return actions
