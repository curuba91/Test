"""Änderungsprotokoll lesen. Geschrieben wird es über ``Tx.audit`` in hub/db.py,
damit jeder Eintrag in derselben Transaktion entsteht wie die Änderung selbst."""

from .db import ENTITY_LABELS, FIELD_LABELS

SOURCES = ("oberfläche", "import", "regel", "übergabe")


def query(conn, entity=None, entity_id=None, source=None, text=None, limit=200, offset=0) -> dict:
    """Audit-Einträge, neueste zuerst."""
    where, params = [], []
    if entity:
        where.append("entity = ?")
        params.append(entity)
    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)
    if source:
        where.append("source = ?")
        params.append(source)
    if text:
        like = f"%{text}%"
        where.append("(entity_id LIKE ? OR field LIKE ? OR old_value LIKE ? OR new_value LIKE ? OR user LIKE ?)")
        params += [like] * 5
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM audit {clause}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM audit {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [max(1, min(int(limit), 1000)), max(0, int(offset))],
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["field_label"] = FIELD_LABELS.get(row["field"], row["field"])
        item["entity_label"] = ENTITY_LABELS.get(row["entity"], row["entity"])
        items.append(item)
    return {"total": total, "items": items}
