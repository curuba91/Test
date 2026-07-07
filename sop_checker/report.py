"""Erzeugt einen eigenständigen HTML-Prüfbericht mit Abhak-Checkliste.

Der Bericht ist eine einzelne HTML-Datei ohne externe Abhängigkeiten.
Der Abhak-Status der Checkboxen wird im Browser (localStorage) gespeichert,
sodass die Prüfung unterbrochen und später fortgesetzt werden kann.
"""

from __future__ import annotations

import datetime
import html
from pathlib import Path

from .analysis import AnalysisResult, Finding
from .diffing import DiffResult

_CATEGORY_LABELS = {
    "alter_wortlaut": ("Alter Wortlaut gefunden", "cat-old"),
    "aehnliche_passage": ("Ähnliche Passage – prüfen", "cat-similar"),
    "sop_referenz": ("Verweis auf geänderte SOP", "cat-ref"),
    "suchbegriff": ("Suchbegriff gefunden", "cat-term"),
}

_CSS = """
:root { --old:#c0392b; --similar:#b9770e; --ref:#6c3483; --term:#1a5276;
        --ok:#1e8449; --bg:#f6f7f9; --card:#ffffff; --line:#dde1e6; }
* { box-sizing: border-box; }
body { font-family: 'Segoe UI', Arial, sans-serif; margin:0; background:var(--bg);
       color:#1c2833; line-height:1.5; }
header { background:#1c2833; color:#fff; padding:18px 28px; }
header h1 { margin:0 0 4px; font-size:1.35rem; }
header .meta { color:#aab7c4; font-size:.85rem; }
main { max-width:1100px; margin:0 auto; padding:20px 28px 60px; }
.summary { display:flex; gap:14px; flex-wrap:wrap; margin:18px 0; }
.tile { background:var(--card); border:1px solid var(--line); border-radius:8px;
        padding:12px 18px; min-width:150px; }
.tile b { display:block; font-size:1.5rem; }
h2 { margin:30px 0 10px; font-size:1.1rem; border-bottom:2px solid var(--line);
     padding-bottom:6px; }
h3 { margin:20px 0 8px; font-size:.98rem; }
.finding { background:var(--card); border:1px solid var(--line); border-left:5px solid #999;
           border-radius:6px; padding:10px 14px; margin:8px 0; display:flex; gap:12px; }
.finding.done { opacity:.55; }
.finding.done .para { text-decoration: line-through; }
.finding input[type=checkbox] { width:1.2em; height:1.2em; margin-top:3px; flex:none; }
.finding .body { min-width:0; }
.badge { display:inline-block; font-size:.72rem; font-weight:600; color:#fff;
         border-radius:4px; padding:2px 8px; margin-right:8px; }
.cat-old { border-left-color:var(--old); } .cat-old .badge { background:var(--old); }
.cat-similar { border-left-color:var(--similar);} .cat-similar .badge{background:var(--similar);}
.cat-ref { border-left-color:var(--ref); } .cat-ref .badge { background:var(--ref); }
.cat-term { border-left-color:var(--term); } .cat-term .badge { background:var(--term); }
.loc { color:#5d6d7e; font-size:.8rem; }
.para { margin:6px 0; overflow-wrap:anywhere; }
mark { background:#fdebd0; border-bottom:2px solid var(--old); padding:0 2px; }
.suggestion { font-size:.85rem; color:var(--ok); }
.detail { font-size:.8rem; color:#5d6d7e; }
table.diff { width:100%; border-collapse:collapse; background:var(--card);
             font-size:.85rem; }
table.diff th, table.diff td { border:1px solid var(--line); padding:6px 10px;
             vertical-align:top; text-align:left; overflow-wrap:anywhere; }
table.diff th { background:#eef1f4; }
td.k-geändert { color:var(--similar); font-weight:600; }
td.k-entfernt { color:var(--old); font-weight:600; }
td.k-hinzugefügt { color:var(--ok); font-weight:600; }
td.k-verschoben { color:#5d6d7e; font-weight:600; }
.ok-box { background:#eafaf1; border:1px solid #a9dfbf; color:var(--ok);
          border-radius:6px; padding:10px 14px; }
.err { color:var(--old); }
.progress { position:sticky; top:0; background:#fff; border-bottom:1px solid var(--line);
            padding:8px 28px; font-size:.85rem; z-index:5; }
.progress .bar { display:inline-block; width:220px; height:10px; background:#e5e8eb;
                 border-radius:5px; overflow:hidden; vertical-align:middle; margin:0 10px; }
.progress .bar i { display:block; height:100%; background:var(--ok); width:0; }
.table-wrap { overflow-x:auto; }
"""

_JS = """
(function () {
  var key = 'sop-report-' + document.body.dataset.reportId;
  var state = {};
  try { state = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) {}
  var boxes = document.querySelectorAll('.finding input[type=checkbox]');
  function refresh() {
    var done = 0;
    boxes.forEach(function (b) {
      b.closest('.finding').classList.toggle('done', b.checked);
      if (b.checked) done++;
    });
    var pct = boxes.length ? Math.round(100 * done / boxes.length) : 0;
    var bar = document.querySelector('.progress .bar i');
    var label = document.querySelector('.progress .label');
    if (bar) bar.style.width = pct + '%';
    if (label) label.textContent = done + ' von ' + boxes.length + ' Punkten erledigt (' + pct + '%)';
  }
  boxes.forEach(function (b) {
    if (state[b.id]) b.checked = true;
    b.addEventListener('change', function () {
      state[b.id] = b.checked;
      try { localStorage.setItem(key, JSON.stringify(state)); } catch (e) {}
      refresh();
    });
  });
  refresh();
})();
"""


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _shorten(text: str, limit: int = 320, center: int = -1) -> tuple[str, int]:
    """Kürzt einen Absatz um die Trefferposition herum. Gibt (Text, Offset) zurück."""
    if len(text) <= limit:
        return text, 0
    if center < 0:
        return text[:limit] + " …", 0
    start = max(0, center - limit // 2)
    end = min(len(text), start + limit)
    prefix = "… " if start > 0 else ""
    suffix = " …" if end < len(text) else ""
    return prefix + text[start:end] + suffix, start - len(prefix)


def _render_paragraph(f: Finding) -> str:
    """Rendert den Absatztext mit hervorgehobenem Treffer."""
    text, offset = _shorten(f.paragraph_text, center=max(f.match_start, 0))
    if f.match_start >= 0 and f.match_text:
        pos = f.match_start - offset
        if 0 <= pos <= len(text) - 1:
            before = text[:pos]
            match = text[pos:pos + len(f.match_text)]
            after = text[pos + len(f.match_text):]
            return f"{_esc(before)}<mark>{_esc(match)}</mark>{_esc(after)}"
    return _esc(text)


def _render_finding(f: Finding, uid: str) -> str:
    label, css = _CATEGORY_LABELS.get(f.category, (f.category, "cat-term"))
    parts = [
        f'<div class="finding {css}">',
        f'<input type="checkbox" id="{uid}" title="Als erledigt/geprüft markieren">',
        '<div class="body">',
        f'<span class="badge">{_esc(label)}</span>'
        f'<span class="loc">{_esc(f.document)} · Absatz {f.paragraph_index}</span>',
        f'<div class="para">{_render_paragraph(f)}</div>',
    ]
    if f.suggestion:
        parts.append(f'<div class="suggestion">Neuer Wortlaut: „{_esc(f.suggestion)}“</div>')
    if f.detail:
        parts.append(f'<div class="detail">{_esc(f.detail)}</div>')
    parts.append("</div></div>")
    return "".join(parts)


def _render_diff_table(diff: DiffResult) -> str:
    if not diff.changes:
        return '<div class="ok-box">Keine Unterschiede zwischen den beiden Versionen gefunden.</div>'
    rows = []
    for c in diff.changes:
        loc = []
        if c.old_index > 0:
            loc.append(f"alt: Abs. {c.old_index}")
        if c.new_index > 0:
            loc.append(f"neu: Abs. {c.new_index}")
        old_text, _ = _shorten(c.old_text)
        new_text, _ = _shorten(c.new_text)
        rows.append(
            f'<tr><td class="k-{c.kind}">{_esc(c.kind)}</td>'
            f'<td>{_esc(", ".join(loc))}</td>'
            f'<td>{_esc(old_text)}</td><td>{_esc(new_text)}</td></tr>'
        )
    return (
        '<div class="table-wrap"><table class="diff">'
        "<tr><th>Art</th><th>Position</th><th>Alte Version</th><th>Neue Version</th></tr>"
        + "".join(rows) + "</table></div>"
    )


def build_report(
    result: AnalysisResult,
    diff: DiffResult | None,
    new_doc_name: str,
    old_doc_name: str = "",
    pool_folder: str = "",
) -> str:
    """Baut den vollständigen HTML-Bericht als String."""
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    report_id = f"{new_doc_name}-{now}"
    uid_counter = 0

    def next_uid() -> str:
        nonlocal uid_counter
        uid_counter += 1
        return f"chk-{uid_counter}"

    sections = []

    # Zusammenfassung
    n_changes = len(diff.changes) if diff else 0
    affected_docs = sum(1 for r in result.pool_results if r.findings)
    sections.append(
        '<div class="summary">'
        f'<div class="tile"><b>{n_changes}</b>Änderungen erkannt</div>'
        f'<div class="tile"><b>{len(result.internal_findings)}</b>offene Stellen im Dokument</div>'
        f'<div class="tile"><b>{result.pool_findings_count}</b>Fundstellen im SOP-Pool</div>'
        f'<div class="tile"><b>{affected_docs} / {len(result.pool_results)}</b>betroffene Pool-Dokumente</div>'
        "</div>"
    )

    # Diff
    if diff is not None:
        sections.append("<h2>1. Erkannte Änderungen (alte vs. neue Version)</h2>")
        sections.append(_render_diff_table(diff))

    # Interne Konsistenz
    sections.append("<h2>2. Interne Konsistenz – Stellen in der neuen Version</h2>")
    if result.internal_findings:
        sections.append(
            "<p>An diesen Stellen kommt der alte Wortlaut (oder eine sehr ähnliche "
            "Passage) noch im Dokument vor. Jede Stelle prüfen und abhaken:</p>")
        for f in result.internal_findings:
            sections.append(_render_finding(f, next_uid()))
    else:
        sections.append('<div class="ok-box">Keine offenen Stellen – der alte Wortlaut '
                        "kommt in der neuen Version nicht mehr vor. ✓</div>")

    # Pool
    sections.append("<h2>3. Dokumentübergreifende Prüfung (SOP-Pool)</h2>")
    if pool_folder:
        sections.append(f'<p class="loc">Geprüfter Ordner: {_esc(pool_folder)} '
                        f"({len(result.pool_results)} Dokumente)</p>")
    if not result.pool_results:
        sections.append("<p>Kein SOP-Pool angegeben.</p>")
    else:
        any_findings = False
        for doc in result.pool_results:
            if doc.error:
                sections.append(f'<h3>{_esc(doc.path.name)}</h3>'
                                f'<p class="err">Fehler: {_esc(doc.error)}</p>')
                continue
            if not doc.findings:
                continue
            any_findings = True
            sections.append(f"<h3>{_esc(doc.path.name)} "
                            f'<span class="loc">({len(doc.findings)} Fundstellen · '
                            f"{_esc(str(doc.path))})</span></h3>")
            for f in doc.findings:
                sections.append(_render_finding(f, next_uid()))
        if not any_findings:
            sections.append('<div class="ok-box">Keine betroffenen Dokumente im Pool '
                            "gefunden. ✓</div>")

    subtitle = f"Neue Version: {new_doc_name}"
    if old_doc_name:
        subtitle += f" · Alte Version: {old_doc_name}"

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOP-Konsistenzbericht – {_esc(new_doc_name)}</title>
<style>{_CSS}</style>
</head>
<body data-report-id="{_esc(report_id)}">
<header>
  <h1>SOP-Konsistenzbericht</h1>
  <div class="meta">{_esc(subtitle)} · erstellt am {now}</div>
</header>
<div class="progress"><span class="label"></span><span class="bar"><i></i></span></div>
<main>
{"".join(sections)}
</main>
<script>{_JS}</script>
</body>
</html>
"""


def write_report(report_html: str, path: str | Path) -> Path:
    path = Path(path)
    path.write_text(report_html, encoding="utf-8")
    return path
