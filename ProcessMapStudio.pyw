# -*- coding: utf-8 -*-
"""
ProcessMap Studio
=================
Einfaches Tool zum Erstellen von Process Maps mit Mermaid.js.

- Reine Python-Standardbibliothek (Tkinter) -> laeuft als .pyw ohne Installation.
- Mermaid-Code links eingeben (oder Copilot-Antwort einfuegen, der Code-Block
  wird automatisch herausgeloest).
- "Vorschau" erzeugt eine HTML-Datei und oeffnet sie im Standardbrowser.
- "PDF exportieren" erzeugt direkt eine PDF-Datei (Hoch-/Querformat, eine
  Seite oder mehrseitig). Dazu wird Edge oder Chrome unsichtbar im
  Headless-Modus aufgerufen; wird kein Browser gefunden, oeffnet sich als
  Fallback der Druckdialog des Standardbrowsers ("Als PDF speichern").
- "Visio exportieren" schreibt eine bearbeitbare .vsdx-Datei mit echten
  Visio-Formen und dynamisch verklebten Verbindern. Dafuer wird weder Visio
  noch eine Internetverbindung benoetigt - die Datei wird komplett aus der
  Standardbibliothek erzeugt (zipfile + XML nach dem OPC-Aufbau).
- "Master-Prompt kopieren" legt den standardisierten Copilot-Prompt in die
  Zwischenablage (Prompt + Quelltext/PDF-Inhalt in Copilot einfuegen,
  Antwort hier wieder einfuegen).

Offline-Betrieb: Liegt eine Datei "mermaid.min.js" im selben Ordner wie dieses
Skript, wird sie direkt in die HTML-Datei eingebettet. Andernfalls wird
Mermaid ueber das jsDelivr-CDN geladen (Browser braucht dann Internetzugang).
"""

import datetime
import html
import os
import re
import shutil
import subprocess
import tempfile
import webbrowser
import zipfile
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

APP_TITLE = "ProcessMap Studio"
SIDEBAR_WIDTH = 250          # Breite der Schrittleiste in Pixeln
MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"
LOCAL_MERMAID = Path(__file__).resolve().parent / "mermaid.min.js"

# ---------------------------------------------------------------------------
# Beispiel-Diagramm (zeigt die Notations-Konventionen des Master-Prompts)
# ---------------------------------------------------------------------------
EXAMPLE_DIAGRAM = '''flowchart TD
    %% Beispiel: Rechnungspruefung
    A0(["Start: Rechnung geht ein"]) --> A1["Rechnung im System erfassen"]
    A1 --> A2{"Bestellbezug vorhanden?"}
    A2 -->|Ja| A3["Automatischer 3-Wege-Abgleich"]
    A2 -->|Nein| A4["Manuelle Pruefung durch Fachabteilung"]
    A3 --> A5{"Abweichung festgestellt?"}
    A5 -->|Nein| A7["Rechnung zur Zahlung freigeben"]
    A5 -->|Ja| A6["Klaerung mit Lieferant"]
    A4 --> A6
    A6 --> A2
    A7 --> A8[/"Zahlungslauf-Datei"/]
    A8 --> A9(["Ende: Rechnung bezahlt"])
'''

# ---------------------------------------------------------------------------
# Master-Prompt fuer Copilot (Vorverarbeitung von Texten/PDF-Inhalten)
# ---------------------------------------------------------------------------
MASTER_PROMPT = '''Du bist ein erfahrener Prozessanalyst und Experte fuer Mermaid.js.

AUFGABE
Extrahiere aus dem unten stehenden INPUT (Text, PDF-Inhalt, Notizen,
Arbeitsanweisung o. ae.) den beschriebenen Geschaeftsprozess und gib ihn als
Mermaid-Flowchart aus.

AUSGABEFORMAT (zwingend einhalten)
- Gib AUSSCHLIESSLICH einen einzigen Mermaid-Codeblock aus
  (beginnend mit ```mermaid und endend mit ```). Kein Text davor oder danach.
- Erste Zeile im Block: flowchart TD
- Annahmen, die du treffen musstest, als Kommentarzeilen im Block notieren:
  %% ANNAHME: ...

NOTATIONS-KONVENTIONEN
1. Knoten-IDs fortlaufend: A0, A1, A2, ...
2. Alle Beschriftungen IMMER in doppelte Anfuehrungszeichen setzen,
   z. B. A1["Rechnung erfassen"] (wichtig wegen Umlauten/Sonderzeichen).
   Keine doppelten Anfuehrungszeichen INNERHALB von Beschriftungen verwenden.
3. Knotentypen:
   - Start/Ende:        A0(["Start: ..."])   bzw.   A9(["Ende: ..."])
   - Aktivitaet:        A1["Verb + Objekt, z. B. Antrag pruefen"]
   - Entscheidung:      A2{"Frage mit Ja/Nein?"}  mit Kanten -->|Ja| und -->|Nein|
   - Dokument/Daten:    A3[/"Dokumentname"/]
   - Subprozess:        A4[["Name des Teilprozesses"]]
4. Sind Rollen/Abteilungen erkennbar, gruppiere die Schritte je Rolle:
   subgraph "Rollenname"
       ...
   end
5. Beschriftungen kurz halten (max. ca. 60 Zeichen), Aktivitaeten im Stil
   "Verb + Objekt" formulieren.
6. Jede Entscheidung braucht mindestens zwei beschriftete Ausgaenge.
7. Genau EIN Startknoten; ein oder mehrere Endknoten.
8. Keine Styling-Anweisungen (kein classDef, style, click, linkStyle).
9. Ist der Prozess unklar oder lueckenhaft: plausibel ergaenzen und jede
   Ergaenzung mit %% ANNAHME: kennzeichnen.

=== INPUT (hier den zu analysierenden Text/PDF-Inhalt einfuegen) ===

'''

# ---------------------------------------------------------------------------
# HTML-Erzeugung
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; background: #f5f6f8; }}
  header {{ background: #1f3a5f; color: #fff; padding: 10px 20px; }}
  header h1 {{ font-size: 18px; margin: 0; }}
  header small {{ color: #c9d4e3; }}
  #wrap {{ padding: 20px; }}
  #diagram {{ background: #fff; border: 1px solid #d7dce3; border-radius: 6px;
             padding: 16px; overflow: auto; }}
  .mermaid svg {{ max-width: 100%; height: auto; }}
</style>
{mermaid_script}
</head>
<body>
<header><h1>{title}</h1><small>erstellt mit ProcessMap Studio &middot; {stamp}</small></header>
<div id="wrap"><div id="diagram">
<pre class="mermaid">
{code}
</pre>
</div></div>
<script>
  mermaid.initialize({{ startOnLoad: true, theme: "default", flowchart: {{ useMaxWidth: false }} }});
</script>
</body>
</html>
"""


def _mermaid_script_tag() -> str:
    if LOCAL_MERMAID.is_file():
        return "<script>%s</script>" % LOCAL_MERMAID.read_text(encoding="utf-8")
    return '<script src="%s"></script>' % MERMAID_CDN


def build_html(code: str, title: str) -> str:
    return HTML_TEMPLATE.format(
        title=html.escape(title) or "Process Map",
        stamp=datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        code=html.escape(code),
        mermaid_script=_mermaid_script_tag(),
    )


# Druckvorlage: @page steuert Papierformat/Ausrichtung, svg_css die Skalierung.
PRINT_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A4 {orientation}; margin: 10mm; }}
  html, body {{ margin: 0; padding: 0; background: #fff; }}
  pre.mermaid {{ margin: 0; }}
  .mermaid svg {{ {svg_css} }}
</style>
{mermaid_script}
</head>
<body>
<pre class="mermaid">
{code}
</pre>
<script>
  mermaid.initialize({{ startOnLoad: false, theme: "default",
                        flowchart: {{ useMaxWidth: false }} }});
  mermaid.run().then(function () {{ {after_render} }});
</script>
</body>
</html>
"""

# Nutzbare A4-Flaeche bei 10 mm Rand (Breite, Hoehe in mm)
PAGE_AREA = {"portrait": (190, 277), "landscape": (277, 190)}


def build_print_html(code: str, title: str, orientation: str,
                     fit_one_page: bool, auto_print: bool) -> str:
    width_mm, height_mm = PAGE_AREA[orientation]
    if fit_one_page:
        # Proportional verkleinern, bis das Diagramm auf eine Seite passt.
        svg_css = ("max-width: %dmm; max-height: %dmm; "
                   "width: auto; height: auto;" % (width_mm, height_mm - 5))
    else:
        # An Seitenbreite ausrichten; die Hoehe laeuft ueber mehrere Seiten.
        svg_css = "width: %dmm; height: auto;" % width_mm
    return PRINT_TEMPLATE.format(
        title=html.escape(title) or "Process Map",
        orientation=orientation,
        svg_css=svg_css,
        code=html.escape(code),
        mermaid_script=_mermaid_script_tag(),
        after_render="window.print();" if auto_print else "",
    )


def find_chromium_browser() -> str:
    """Sucht Edge oder Chrome fuer den Headless-PDF-Druck."""
    candidates = []
    for env in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            candidates.append(Path(base) / "Microsoft/Edge/Application/msedge.exe")
            candidates.append(Path(base) / "Google/Chrome/Application/chrome.exe")
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    for name in ("msedge", "chrome", "google-chrome", "chromium",
                 "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def headless_pdf(browser: str, html_path: Path, pdf_path: str) -> bool:
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        # Wartet auch auf asynchrones Mermaid-Rendering
        "--virtual-time-budget=10000",
        # neues und altes Flag fuer "ohne Kopf-/Fusszeile" (unbekannte
        # Schalter ignorieren Edge/Chrome stillschweigend)
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        "--print-to-pdf=%s" % pdf_path,
        html_path.as_uri(),
    ]
    kwargs = {"timeout": 90}
    if hasattr(subprocess, "CREATE_NO_WINDOW"):  # kein Konsolenfenster (Windows)
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        subprocess.run(cmd, check=True, capture_output=True, **kwargs)
    except (OSError, subprocess.SubprocessError):
        return False
    target = Path(pdf_path)
    return target.is_file() and target.stat().st_size > 0


def extract_mermaid(text: str) -> str:
    """Loest Mermaid-Code aus einer Copilot-/Chat-Antwort heraus.

    Erkennt ```mermaid ... ```-Bloecke; ohne Code-Block wird der Text
    unveraendert (nur getrimmt) zurueckgegeben.
    """
    match = re.search(r"```\s*mermaid\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(flowchart.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


# ===========================================================================
# VISIO-EXPORT, TEIL 1: Mermaid-Code -> Graphmodell
# ===========================================================================
# Formtypen (bestimmen Visio-Geometrie und Farbe)
K_TERMINATOR = "terminator"   # Start/Ende      A0(["..."])
K_PROCESS = "process"         # Aktivitaet      A1["..."]
K_DECISION = "decision"       # Entscheidung    A2{"..."}
K_DATA = "data"               # Dokument/Daten  A3[/"..."/]
K_SUBPROCESS = "subprocess"   # Teilprozess     A4[["..."]]

# Reihenfolge ist wichtig: laengere Klammern zuerst pruefen.
_NODE_BRACKETS = [
    ("([", "])", K_TERMINATOR),
    ("[[", "]]", K_SUBPROCESS),
    ("[/", "/]", K_DATA),
    ("[\\", "\\]", K_DATA),
    ("((", "))", K_TERMINATOR),
    ("{{", "}}", K_DECISION),
    ("{", "}", K_DECISION),
    ("(", ")", K_TERMINATOR),
    ("[", "]", K_PROCESS),
]

# Kantenoperator, optional mit Label davor (-- Text -->) oder danach (-->|Text|)
_EDGE_OP = re.compile(
    r"""(?:--\s*(?P<pre>[^-|>\n]+?)\s*)?"""
    r"""(?P<op>-{2,3}>|-\.->|={2,3}>|-{3}|-\.-)"""
    r"""(?:\s*\|\s*(?P<post>[^|]*?)\s*\|)?""",
    re.VERBOSE,
)

_NODE_ID = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*(.*)$", re.DOTALL)


class MNode:
    def __init__(self, nid, label, kind, group=None):
        self.nid = nid
        self.label = label
        self.kind = kind
        self.group = group


class MEdge:
    def __init__(self, src, dst, label=""):
        self.src = src
        self.dst = dst
        self.label = label


class MGraph:
    def __init__(self):
        self.nodes = {}        # nid -> MNode (Einfuegereihenfolge bleibt erhalten)
        self.edges = []
        self.groups = []       # Liste von (Name, [nid, ...])

    def touch(self, nid, label=None, kind=None, group=None):
        node = self.nodes.get(nid)
        if node is None:
            node = MNode(nid, label if label is not None else nid,
                         kind or K_PROCESS, group)
            self.nodes[nid] = node
        else:
            # Spaetere, vollstaendigere Definition gewinnt
            if label is not None:
                node.label = label
            if kind is not None:
                node.kind = kind
            if group is not None and node.group is None:
                node.group = group
        # Mitglied wird ein Knoten nur in der Gruppe, in der er zuerst
        # definiert wurde - spaetere Erwaehnungen in anderen Subgraphs
        # wuerden sonst zu ueberlappenden Rahmen fuehren.
        if group is not None and node.group == group:
            for name, members in self.groups:
                if name == group and nid not in members:
                    members.append(nid)
        return nid


def _clean_label(text):
    """Entfernt Anfuehrungszeichen und uebersetzt Mermaid-Escapes."""
    if text is None:
        return ""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = (text.replace("#quot;", '"').replace("&quot;", '"')
                .replace("#35;", "#").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">"))
    return text.strip()


def _parse_node_token(token):
    """'A1[\"Text\"]' -> ('A1', 'Text', K_PROCESS). Ohne Klammern: Label/Typ None."""
    token = token.strip().rstrip(";").strip()
    if not token:
        return None
    match = _NODE_ID.match(token)
    if not match:
        return None
    nid, rest = match.group(1), match.group(2).strip()
    if not rest:
        return nid, None, None
    for open_b, close_b, kind in _NODE_BRACKETS:
        if (rest.startswith(open_b) and rest.endswith(close_b)
                and len(rest) >= len(open_b) + len(close_b)):
            label = rest[len(open_b):len(rest) - len(close_b)]
            return nid, _clean_label(label), kind
    return nid, None, None


def _split_statement(line):
    """Zerlegt eine Zeile in Knoten-Token und Kantenlabels.

    Klammern und Anfuehrungszeichen werden mitgezaehlt, damit ein '-->' im
    Beschriftungstext nicht faelschlich als Kante erkannt wird.
    """
    tokens, labels, buf = [], [], []
    depth = 0
    in_quote = False
    i = 0
    while i < len(line):
        char = line[i]
        if in_quote:
            buf.append(char)
            if char == '"':
                in_quote = False
            i += 1
            continue
        if char == '"':
            in_quote = True
            buf.append(char)
            i += 1
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth = max(0, depth - 1)
        elif depth == 0 and char in "-=":
            match = _EDGE_OP.match(line, i)
            if match:
                tokens.append("".join(buf))
                buf = []
                labels.append(match.group("post") or match.group("pre") or "")
                i = match.end()
                continue
        buf.append(char)
        i += 1
    tokens.append("".join(buf))
    return tokens, labels


def _subgraph_name(rest):
    rest = rest.strip()
    match = re.search(r"[\[(]\s*(.*?)\s*[\])]\s*$", rest)
    if match:
        return _clean_label(match.group(1))
    return _clean_label(rest) or "Gruppe"


def parse_mermaid(code):
    """Parst ein Mermaid-Flowchart in ein MGraph-Modell."""
    graph = MGraph()
    group_stack = []
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%"):
            continue
        # Kommentar am Zeilenende abschneiden (nicht innerhalb von "...")
        if "%%" in line:
            depth = 0
            in_quote = False
            for pos, char in enumerate(line):
                if in_quote:
                    in_quote = char != '"'
                    continue
                if char == '"':
                    in_quote = True
                elif char in "([{":
                    depth += 1
                elif char in ")]}":
                    depth = max(0, depth - 1)
                elif char == "%" and depth == 0 and line[pos:pos + 2] == "%%":
                    line = line[:pos].strip()
                    break
        if not line:
            continue
        lower = line.lower()
        if lower.startswith(("flowchart", "graph")):
            continue
        if lower.startswith(("style ", "classdef", "class ", "click ",
                             "linkstyle", "direction ")):
            continue
        if lower.startswith("subgraph"):
            name = _subgraph_name(line[len("subgraph"):])
            graph.groups.append((name, []))
            group_stack.append(name)
            continue
        if lower == "end":
            if group_stack:
                group_stack.pop()
            continue

        group = group_stack[-1] if group_stack else None
        tokens, labels = _split_statement(line)
        parsed = [_parse_node_token(tok) for tok in tokens]
        ids = []
        for item in parsed:
            ids.append(graph.touch(item[0], item[1], item[2], group)
                       if item else None)
        for index, label in enumerate(labels):
            src, dst = ids[index], ids[index + 1]
            if src and dst:
                graph.edges.append(MEdge(src, dst, _clean_label(label)))
    # Leere Gruppen entfernen
    graph.groups = [(n, m) for n, m in graph.groups if m]
    return graph


# ===========================================================================
# VISIO-EXPORT, TEIL 2: Layout (Schichtenlayout nach Sugiyama, vereinfacht)
# ===========================================================================
MARGIN = 0.7           # Seitenrand in Zoll
H_GAP = 0.5            # horizontaler Abstand zwischen Formen
V_GAP = 0.62           # vertikaler Abstand zwischen Ebenen
GROUP_PAD = 0.28       # Innenabstand einer Subgraph-Umrandung
CHARS_PER_LINE = 22    # Umbruchbreite fuer die Groessenschaetzung
DUMMY_WIDTH = 0.26     # Spurbreite fuer durchlaufende Kanten
PARALLEL_GAP = 0.75    # Versatz zwischen mehreren Kanten derselben Formen
LANE_CLEARANCE = 0.22  # Abstand einer Leitungsspur zur naechsten Form
LANE_MIN = 0.30        # Mindestabstand zwischen zwei Leitungsspuren


def _node_size(kind, label):
    """Schaetzt eine passende Formgroesse (Breite, Hoehe) in Zoll."""
    lines = label.split("\n") if label else [""]
    longest = max((len(part) for part in lines), default=0)
    wrapped = sum(max(1, -(-len(part) // CHARS_PER_LINE)) for part in lines)
    width = 2.05
    if longest > CHARS_PER_LINE:
        width = min(3.3, 2.05 + 0.055 * (min(longest, 46) - CHARS_PER_LINE))
    height = 0.62 + 0.19 * (wrapped - 1)
    if kind == K_DECISION:
        width = max(width, 2.35)
        height = max(height + 0.38, 1.05)
    elif kind == K_TERMINATOR:
        width = max(width * 0.92, 1.5)
        height = max(height, 0.55)
    elif kind == K_DATA:
        width += 0.3
    return round(width, 4), round(height, 4)


def _rank_nodes(graph):
    """Weist jedem Knoten eine Ebene zu; Rueckwaertskanten brechen Zyklen auf."""
    ids = list(graph.nodes)
    succ = {nid: [] for nid in ids}
    indeg = {nid: 0 for nid in ids}
    for edge in graph.edges:
        succ[edge.src].append(edge.dst)
        indeg[edge.dst] += 1

    # Rueckwaertskanten per iterativer Tiefensuche finden (grau = auf dem Stack)
    color = {nid: 0 for nid in ids}
    back_edges = set()
    roots = [nid for nid in ids if indeg[nid] == 0] or ids[:1]
    for start in roots + ids:
        if color[start] != 0:
            continue
        stack = [(start, iter(succ[start]))]
        color[start] = 1
        while stack:
            node, children = stack[-1]
            advanced = False
            for child in children:
                if color[child] == 1:
                    back_edges.add((node, child))
                elif color[child] == 0:
                    color[child] = 1
                    stack.append((child, iter(succ[child])))
                    advanced = True
                    break
            if not advanced:
                color[node] = 2
                stack.pop()

    forward = [(e.src, e.dst) for e in graph.edges
               if (e.src, e.dst) not in back_edges]
    # Laengster Pfad = Ebene; iterative Relaxation (Graph ist zyklenfrei)
    rank = {nid: 0 for nid in ids}
    for _ in range(len(ids) + 1):
        changed = False
        for src, dst in forward:
            if rank[dst] < rank[src] + 1:
                rank[dst] = rank[src] + 1
                changed = True
        if not changed:
            break
    return rank


def _insert_dummies(graph, rank):
    """Zerlegt Kanten ueber mehrere Ebenen in Teilstuecke mit Hilfsknoten.

    Das ist der entscheidende Schritt des Sugiyama-Verfahrens: Eine Kante,
    die Ebenen ueberspringt, bekommt auf jeder Zwischenebene einen schmalen
    Platzhalter. Dieser nimmt an der Sortierung teil und haelt so eine eigene
    Spur frei - sonst wuerde die Kante quer durch die Formen laufen und alle
    Knoten fielen in eine einzige Spalte.
    """
    dummy_rank = {}
    layout_edges = []
    chains = []
    for index, edge in enumerate(graph.edges):
        start, end = rank[edge.src], rank[edge.dst]
        if edge.src == edge.dst or abs(end - start) <= 1:
            if edge.src != edge.dst:
                layout_edges.append((edge.src, edge.dst))
            chains.append([])
            continue
        step = 1 if end > start else -1
        chain = []
        for level in range(start + step, end, step):
            dummy = "\x00%d_%d" % (index, level)
            dummy_rank[dummy] = level
            chain.append(dummy)
        previous = edge.src
        for dummy in chain:
            layout_edges.append((previous, dummy))
            previous = dummy
        layout_edges.append((previous, edge.dst))
        chains.append(chain)
    return dummy_rank, layout_edges, chains


def _order_layers(node_ids, layout_edges, rank):
    """Sortiert die Knoten je Ebene, um Kantenkreuzungen zu reduzieren."""
    layers = {}
    for nid in node_ids:
        layers.setdefault(rank[nid], []).append(nid)

    pred = {nid: [] for nid in node_ids}
    succ = {nid: [] for nid in node_ids}
    for src, dst in layout_edges:
        succ[src].append(dst)
        pred[dst].append(src)

    levels = sorted(layers)
    position = {}
    for level in levels:
        for index, nid in enumerate(layers[level]):
            position[nid] = index

    def sweep(level, neighbours, other_level):
        weights = {}
        for nid in layers[level]:
            values = [position[other] for other in neighbours[nid]
                      if rank[other] == other_level]
            weights[nid] = (sum(values) / len(values)) if values else position[nid]
        layers[level].sort(key=lambda nid: (weights[nid], position[nid]))
        for index, nid in enumerate(layers[level]):
            position[nid] = index

    for _ in range(4):
        for level in levels[1:]:
            sweep(level, pred, level - 1)
        for level in reversed(levels[:-1]):
            sweep(level, succ, level + 1)
    return layers, levels


def _assign_coordinates(node_ids, layout_edges, layers, levels, sizes, chains=()):
    """Berechnet Mittelpunkte; Ursprung oben links, wird spaeter gespiegelt."""
    pred = {nid: [] for nid in node_ids}
    succ = {nid: [] for nid in node_ids}
    for src, dst in layout_edges:
        succ[src].append(dst)
        pred[dst].append(src)

    # Ebenen-Y (nach unten wachsend)
    layer_y = {}
    cursor = 0.0
    for level in levels:
        tallest = max(sizes[nid][1] for nid in layers[level])
        layer_y[level] = cursor + tallest / 2.0
        cursor += tallest + V_GAP

    # Start: dicht gepackt, je Ebene zentriert
    x_of = {}
    for level in levels:
        cursor = 0.0
        for nid in layers[level]:
            width = sizes[nid][0]
            x_of[nid] = cursor + width / 2.0
            cursor += width + H_GAP
        shift = cursor / 2.0
        for nid in layers[level]:
            x_of[nid] -= shift

    def compact(level):
        """Zieht Knoten zum Schwerpunkt ihrer Nachbarn und entzerrt Ueberlappungen."""
        order = layers[level]
        for index, nid in enumerate(order):
            width = sizes[nid][0]
            lower = (x_of[order[index - 1]] + sizes[order[index - 1]][0] / 2.0
                     + H_GAP + width / 2.0) if index else None
            if lower is not None and x_of[nid] < lower:
                x_of[nid] = lower
        for index in range(len(order) - 2, -1, -1):
            nid = order[index]
            right = order[index + 1]
            upper = (x_of[right] - sizes[right][0] / 2.0
                     - H_GAP - sizes[nid][0] / 2.0)
            if x_of[nid] > upper:
                x_of[nid] = upper

    for _ in range(6):
        for level in levels[1:]:
            for nid in layers[level]:
                values = [x_of[other] for other in pred[nid]
                          if other in x_of and other != nid]
                if values:
                    x_of[nid] = sum(values) / len(values)
            compact(level)
        for level in reversed(levels[:-1]):
            for nid in layers[level]:
                values = [x_of[other] for other in succ[nid]
                          if other in x_of and other != nid]
                if values:
                    x_of[nid] = sum(values) / len(values)
            compact(level)

    # Hilfsknoten einer Kante auf eine gemeinsame Spur ziehen. Ohne das
    # bekaeme jede Zwischenebene ihre eigene x-Position und eine lange
    # Linie wuerde auf ihrem Weg staendig seitlich pendeln.
    slot = {}
    for level in levels:
        for position, nid in enumerate(layers[level]):
            slot[nid] = (level, position)

    def feasible(nid, wish):
        """Naechstmoegliche Position zu 'wish', ohne die Nachbarn zu stoeren."""
        level, position = slot[nid]
        order = layers[level]
        low, high = float("-inf"), float("inf")
        if position > 0:
            left = order[position - 1]
            low = (x_of[left] + sizes[left][0] / 2.0
                   + H_GAP + sizes[nid][0] / 2.0)
        if position < len(order) - 1:
            right = order[position + 1]
            high = (x_of[right] - sizes[right][0] / 2.0
                    - H_GAP - sizes[nid][0] / 2.0)
        if low > high:
            return x_of[nid]
        return min(max(wish, low), high)

    long_chains = [chain for chain in chains if len(chain) > 1]
    for _ in range(4):
        for chain in long_chains:
            values = sorted(x_of[dummy] for dummy in chain)
            target = values[len(values) // 2]        # Median = stabile Spur
            for dummy in chain:
                x_of[dummy] = feasible(dummy, target)

    return {nid: (x_of[nid], layer_y[level])
            for level in levels for nid in layers[level]}


def _nearest_free(wish, intervals):
    """Naechstgelegener Wert zu 'wish', der in keinem gesperrten Bereich liegt."""
    merged = []
    for start, stop in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], stop)
        else:
            merged.append([start, stop])
    for start, stop in merged:
        if start < wish < stop:
            return start if (wish - start) <= (stop - wish) else stop
    return wish


def _free_bands(placements):
    """Waagerechte Streifen zwischen den Ebenen, in denen keine Form liegt."""
    spans = sorted((y - height / 2.0, y + height / 2.0)
                   for _, y, _, height in placements.values())
    merged = []
    for low, high in spans:
        if merged and low <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    return [(lower[1], upper[0]) for lower, upper in zip(merged, merged[1:])]


def _band_beyond(bands, edge_y, downward, fallback):
    """Mitte des freien Streifens direkt unterhalb bzw. oberhalb von edge_y."""
    if downward:
        candidates = [band for band in bands if band[1] <= edge_y + 1e-6]
        band = max(candidates, key=lambda b: b[1]) if candidates else None
    else:
        candidates = [band for band in bands if band[0] >= edge_y - 1e-6]
        band = min(candidates, key=lambda b: b[0]) if candidates else None
    if band is None:
        return edge_y - fallback if downward else edge_y + fallback
    return (band[0] + band[1]) / 2.0


def _channel_lane(wish, y_low, y_high, placements, exclude, used):
    """Sucht eine senkrechte Spur, die im Hoehenbereich keine Form beruehrt."""
    blocked = []
    for nid, (x, y, width, height) in placements.items():
        if nid in exclude:
            continue
        if y + height / 2.0 < y_low or y - height / 2.0 > y_high:
            continue                                   # kein Hoehenueberlapp
        blocked.append((x - width / 2.0 - LANE_CLEARANCE,
                        x + width / 2.0 + LANE_CLEARANCE))
    for lane, low, high in used:                       # schon belegte Spuren
        if high < y_low or low > y_high:
            continue
        blocked.append((lane - LANE_MIN, lane + LANE_MIN))
    return _nearest_free(wish, blocked)


def _parallel_offsets(graph):
    """Seitlicher Versatz fuer mehrfach vorhandene Kanten zwischen zwei Formen.

    Ohne das laegen z. B. der Ja- und der Nein-Zweig einer Entscheidung, die
    beide auf dieselbe Form zeigen, exakt uebereinander - samt Beschriftung.
    """
    buckets = {}
    for index, edge in enumerate(graph.edges):
        buckets.setdefault((edge.src, edge.dst), []).append(index)
    offsets = {}
    for indices in buckets.values():
        if len(indices) < 2:
            continue
        middle = (len(indices) - 1) / 2.0
        for position, index in enumerate(indices):
            offsets[index] = (position - middle) * PARALLEL_GAP
    return offsets


def layout_graph(graph):
    """Liefert (placements, routes, page_width, page_height) in Zoll.

    placements: nid -> (center_x, center_y, width, height) in Visio-Koordinaten
    (Ursprung unten links, Y waechst nach oben).
    routes:     Kantenindex -> Liste von Stuetzpunkten (x, y) zwischen den
                beiden Formen; leer bei direkten Nachbarn ohne Versatz.
    """
    sizes = {nid: _node_size(node.kind, node.label)
             for nid, node in graph.nodes.items()}
    rank = _rank_nodes(graph)

    # Hilfsknoten fuer Kanten ueber mehrere Ebenen einziehen
    dummy_rank, layout_edges, chains = _insert_dummies(graph, rank)
    combined_rank = dict(rank)
    combined_rank.update(dummy_rank)
    for dummy in dummy_rank:
        sizes[dummy] = (DUMMY_WIDTH, 0.0)
    node_ids = list(graph.nodes) + list(dummy_rank)

    layers, levels = _order_layers(node_ids, layout_edges, combined_rank)
    centers = _assign_coordinates(node_ids, layout_edges, layers, levels,
                                  sizes, chains)

    # Platz fuer Subgraph-Rahmen einplanen (nur echte Knoten begrenzen die Seite)
    pad = GROUP_PAD + 0.18 if graph.groups else 0.0
    real = list(graph.nodes)
    xs_min = min(centers[n][0] - sizes[n][0] / 2.0 for n in centers) - pad
    xs_max = max(centers[n][0] + sizes[n][0] / 2.0 for n in centers) + pad
    ys_min = min(centers[n][1] - sizes[n][1] / 2.0 for n in real) - pad
    ys_max = max(centers[n][1] + sizes[n][1] / 2.0 for n in real) + pad

    page_width = max(8.2677, (xs_max - xs_min) + 2 * MARGIN)
    page_height = max(11.6929, (ys_max - ys_min) + 2 * MARGIN)
    # Zeichnung horizontal zentrieren, oben ausrichten; Y spiegeln
    offset_x = (page_width - (xs_max - xs_min)) / 2.0 - xs_min
    offset_y = page_height - MARGIN + ys_min

    def to_page(point):
        return (round(point[0] + offset_x, 6), round(offset_y - point[1], 6))

    placements = {}
    for nid in real:
        x, y = to_page(centers[nid])
        width, height = sizes[nid]
        placements[nid] = (x, y, width, height)

    offsets = _parallel_offsets(graph)
    bands = _free_bands(placements)
    routes = {}
    used_lanes = []
    # Laengere Kanten zuerst: sie bekommen die aussen liegenden Spuren
    order = sorted(range(len(graph.edges)), key=lambda i: -len(chains[i]))
    for index in order:
        edge = graph.edges[index]
        if edge.src not in placements or edge.dst not in placements:
            routes[index] = []
            continue
        shift = offsets.get(index, 0.0)
        if not chains[index]:
            # Direkte Nachbarn: nur bei Mehrfachkanten seitlich versetzen
            if shift:
                sx, sy = placements[edge.src][0], placements[edge.src][1]
                tx, ty = placements[edge.dst][0], placements[edge.dst][1]
                routes[index] = [((sx + tx) / 2.0 + shift, (sy + ty) / 2.0)]
            else:
                routes[index] = []
            continue
        # Kante ueber mehrere Ebenen: eine gerade, freie Spur waehlen. Die
        # Hilfsknoten liefern nur noch den Wunschwert - ihre einzelnen
        # x-Positionen wuerden die Linie sonst staendig pendeln lassen.
        lane_x = [to_page(centers[dummy])[0] for dummy in chains[index]]
        lane_x.sort()
        wish = lane_x[len(lane_x) // 2] + shift
        sx, sy, sw, sh = placements[edge.src]
        tx, ty, tw, th = placements[edge.dst]
        downward = ty < sy
        # Die waagerechten Stuecke muessen in den freien Streifen zwischen den
        # Ebenen liegen - auf Hoehe der Formmitte wuerden sie Nachbarn schneiden.
        band_out = _band_beyond(bands, sy - sh / 2.0 if downward else sy + sh / 2.0,
                                downward, V_GAP / 2.0)
        band_in = _band_beyond(bands, ty + th / 2.0 if downward else ty - th / 2.0,
                               not downward, V_GAP / 2.0)
        y_low, y_high = sorted((band_out, band_in))
        lane = _channel_lane(wish, y_low, y_high, placements,
                             {edge.src, edge.dst}, used_lanes)
        used_lanes.append((lane, y_low, y_high))
        routes[index] = [(sx, band_out), (lane, band_out),
                         (lane, band_in), (tx, band_in)]

    # Seite verbreitern, falls eine Spur ueber den Rand hinausragt
    lanes = [lane for lane, _, _ in used_lanes]
    if lanes:
        left = min(lanes) - MARGIN / 2.0
        right = max(lanes) + MARGIN / 2.0
        if left < 0:
            placements = {n: (x - left, y, w, h)
                          for n, (x, y, w, h) in placements.items()}
            routes = {i: [(x - left, y) for x, y in pts]
                      for i, pts in routes.items()}
            page_width += -left
            right += -left
        page_width = max(page_width, right)

    return (placements, routes, round(page_width, 4), round(page_height, 4))


# ===========================================================================
# VISIO-EXPORT, TEIL 3: .vsdx schreiben (OPC-Paket, nur Standardbibliothek)
# ===========================================================================
VNS = ("xmlns='http://schemas.microsoft.com/office/visio/2012/main' "
       "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships' "
       "xml:space='preserve'")
XML_HEAD = "<?xml version='1.0' encoding='utf-8' ?>\n"
MASTER_CONNECTOR_ID = 2

# Farbschema je Formtyp: (Fuellung, Linie)
KIND_COLORS = {
    K_TERMINATOR: ("#D5E8D4", "#82B366"),
    K_PROCESS: ("#DAE8FC", "#6C8EBF"),
    K_DECISION: ("#FFF2CC", "#D6B656"),
    K_DATA: ("#E1D5E7", "#9673A6"),
    K_SUBPROCESS: ("#F5F5F5", "#8C8C8C"),
}
# Relative Geometrie (0..1 bezogen auf Breite/Hoehe) je Formtyp
KIND_GEOMETRY = {
    K_PROCESS: [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
    K_TERMINATOR: [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
    K_SUBPROCESS: [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
    K_DECISION: [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5), (0.5, 0)],
    K_DATA: [(0.18, 0), (1, 0), (0.82, 1), (0, 1), (0.18, 0)],
}


def _num(value):
    """Kompakte Zahlendarstellung ohne Exponentialschreibweise."""
    return ("%.10g" % float(value))


def _attr(value):
    return html.escape(str(value), quote=True)


def _cell(name, value, formula=None, unit=None):
    parts = ["<Cell N='%s' V='%s'" % (name, _attr(value))]
    if unit:
        parts.append(" U='%s'" % unit)
    if formula:
        parts.append(" F='%s'" % _attr(formula))
    parts.append("/>")
    return "".join(parts)


def _geometry_section(rows, index=0, no_fill=False):
    """Baut eine Geometry-Section. rows: ('RelLineTo', x, y) oder
    ('EllipticalArcTo', x, y, a, b, c, d)."""
    parts = ["<Section N='Geometry' IX='%d'>" % index,
             _cell("NoFill", 1 if no_fill else 0),
             _cell("NoLine", 0), _cell("NoShow", 0),
             _cell("NoSnap", 0), _cell("NoQuickDrag", 0)]
    for position, row in enumerate(rows, start=1):
        row_type = row[0]
        cells = _cell("X", _num(row[1])) + _cell("Y", _num(row[2]))
        if row_type == "EllipticalArcTo":
            for name, value in zip(("A", "B", "C", "D"), row[3:]):
                cells += _cell(name, _num(value))
        parts.append("<Row T='%s' IX='%d'>%s</Row>" % (row_type, position, cells))
    parts.append("</Section>")
    return "".join(parts)


def _rel_polygon(points):
    """Geschlossener Streckenzug in relativen Koordinaten (0..1)."""
    return [("RelMoveTo" if i == 0 else "RelLineTo", x, y)
            for i, (x, y) in enumerate(points)]


def _stadium_rows(width, height):
    """Start-/Endform: Rechteck mit halbrunden Seiten (absolute Zoll-Werte)."""
    radius = min(height / 2.0, width / 2.0)
    return [
        ("MoveTo", radius, 0),
        ("LineTo", width - radius, 0),
        ("EllipticalArcTo", width - radius, height, width, height / 2.0, 0, 1),
        ("LineTo", radius, height),
        ("EllipticalArcTo", radius, 0, 0, height / 2.0, 0, 1),
    ]


def _shape_geometry(kind, width, height):
    if kind == K_TERMINATOR:
        return _stadium_rows(width, height)
    return _rel_polygon(KIND_GEOMETRY.get(kind, KIND_GEOMETRY[K_PROCESS]))


def _connection_section(width, height):
    """Vier Klebepunkte (oben/rechts/unten/links) fuer eigene Verbinder."""
    points = [
        (width / 2.0, height, "Width*0.5", "Height*1", 0, 1),
        (width, height / 2.0, "Width*1", "Height*0.5", 1, 0),
        (width / 2.0, 0, "Width*0.5", "Height*0", 0, -1),
        (0, height / 2.0, "Width*0", "Height*0.5", -1, 0),
    ]
    rows = []
    for index, (x, y, fx, fy, dir_x, dir_y) in enumerate(points):
        rows.append("<Row IX='%d'>%s%s%s%s%s</Row>"
                    % (index,
                       _cell("X", _num(x), fx), _cell("Y", _num(y), fy),
                       _cell("DirX", dir_x), _cell("DirY", dir_y),
                       _cell("Type", 0)))
    return "<Section N='Connection'>" + "".join(rows) + "</Section>"


def _text_sections(font_pt, color="#000000", h_align=1, bold=False):
    # Font MUSS gesetzt werden: diese Row ersetzt die des Stylesheets komplett,
    # ohne Font-Angabe rendert Visio/LibreOffice Ersatzzeichen.
    return ("<Section N='Character'><Row IX='0'>"
            + _cell("Font", "Calibri")
            + _cell("Color", color)
            + _cell("Size", _num(font_pt / 72.0))
            + _cell("Style", 1 if bold else 0)
            + _cell("LangID", 1031)
            + "</Row></Section>"
            + "<Section N='Paragraph'><Row IX='0'>"
            + _cell("HorzAlign", h_align)
            + "</Row></Section>")


def _shape_xml(shape_id, node, x, y, width, height):
    """Eine Prozessform als Visio-Shape (2D, frei bearbeitbar)."""
    fill, line = KIND_COLORS.get(node.kind, KIND_COLORS[K_PROCESS])
    rows = _shape_geometry(node.kind, width, height)
    # Start/Ende hat bereits runde Kappen in der Geometrie
    rounding = 0.0 if node.kind in (K_TERMINATOR, K_DECISION) else 0.06

    parts = ["<Shape ID='%d' NameU='%s' Name='%s' Type='Shape' "
             "LineStyle='0' FillStyle='0' TextStyle='0'>"
             % (shape_id, _attr(node.nid), _attr(node.nid))]
    parts += [
        _cell("PinX", _num(x)), _cell("PinY", _num(y)),
        _cell("Width", _num(width)), _cell("Height", _num(height)),
        _cell("LocPinX", _num(width / 2.0), "Width*0.5"),
        _cell("LocPinY", _num(height / 2.0), "Height*0.5"),
        _cell("Angle", 0), _cell("FlipX", 0), _cell("FlipY", 0),
        _cell("ResizeMode", 0), _cell("ObjType", 1),
        _cell("LineColor", line), _cell("LineWeight", _num(1 / 72.0)),
        _cell("LinePattern", 1), _cell("Rounding", _num(rounding)),
        _cell("FillForegnd", fill), _cell("FillPattern", 1),
        _cell("VerticalAlign", 1),
        _cell("LeftMargin", 0.05), _cell("RightMargin", 0.05),
        _cell("TopMargin", 0.03), _cell("BottomMargin", 0.03),
    ]
    parts.append(_connection_section(width, height))
    parts.append(_geometry_section(rows))
    if node.kind == K_SUBPROCESS:
        # Zwei senkrechte Balken kennzeichnen den Teilprozess
        parts.append(_geometry_section(_rel_polygon([(0.08, 0), (0.08, 1)]),
                                       index=1, no_fill=True))
        parts.append(_geometry_section(_rel_polygon([(0.92, 0), (0.92, 1)]),
                                       index=2, no_fill=True))
    parts.append(_text_sections(9))
    parts.append("<Text>%s</Text>" % html.escape(node.label))
    parts.append("</Shape>")
    return "".join(parts)


def _group_shape_xml(shape_id, name, x, y, width, height):
    """Hintergrundrahmen fuer einen Subgraph (Rolle/Abteilung)."""
    parts = ["<Shape ID='%d' NameU='%s' Name='%s' Type='Shape' "
             "LineStyle='0' FillStyle='0' TextStyle='0'>"
             % (shape_id, _attr(name), _attr(name))]
    parts += [
        _cell("PinX", _num(x)), _cell("PinY", _num(y)),
        _cell("Width", _num(width)), _cell("Height", _num(height)),
        _cell("LocPinX", _num(width / 2.0), "Width*0.5"),
        _cell("LocPinY", _num(height / 2.0), "Height*0.5"),
        _cell("Angle", 0), _cell("FlipX", 0), _cell("FlipY", 0),
        _cell("ResizeMode", 0), _cell("ObjType", 1),
        _cell("LineColor", "#9AA5B1"), _cell("LinePattern", 2),
        _cell("LineWeight", _num(1 / 72.0)), _cell("Rounding", 0.08),
        _cell("FillForegnd", "#FAFBFC"), _cell("FillPattern", 1),
        _cell("VerticalAlign", 0),
        _cell("LeftMargin", 0.08), _cell("TopMargin", 0.04),
    ]
    parts.append(_geometry_section(_rel_polygon(KIND_GEOMETRY[K_PROCESS])))
    parts.append(_text_sections(9, color="#5A6672", h_align=0, bold=True))
    parts.append("<Text>%s</Text>" % html.escape(name))
    parts.append("</Shape>")
    return "".join(parts)


def _boundary_point(x, y, width, height, target_x, target_y):
    """Schnittpunkt der Verbindungslinie mit dem Formrand."""
    dx, dy = target_x - x, target_y - y
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return x, y
    scale_x = (width / 2.0) / abs(dx) if abs(dx) > 1e-9 else float("inf")
    scale_y = (height / 2.0) / abs(dy) if abs(dy) > 1e-9 else float("inf")
    scale = min(scale_x, scale_y)
    return x + dx * scale, y + dy * scale


def _orthogonal_path(points):
    """Macht aus Stuetzpunkten einen rechtwinkligen Streckenzug."""
    path = [points[0]]
    for previous, following in zip(points, points[1:]):
        if abs(following[0] - previous[0]) > 0.01:
            middle_y = (previous[1] + following[1]) / 2.0
            path.append((previous[0], middle_y))
            path.append((following[0], middle_y))
        path.append(following)
    # aufeinanderfolgende Doppelpunkte entfernen
    cleaned = [path[0]]
    for point in path[1:]:
        if (abs(point[0] - cleaned[-1][0]) > 0.005
                or abs(point[1] - cleaned[-1][1]) > 0.005):
            cleaned.append(point)
    return cleaned


def _path_midpoint(path):
    """Punkt auf halber Streckenlaenge - Ankerpunkt fuer die Beschriftung."""
    lengths = []
    total = 0.0
    for previous, following in zip(path, path[1:]):
        step = abs(following[0] - previous[0]) + abs(following[1] - previous[1])
        lengths.append(step)
        total += step
    if total <= 0:
        return path[0]
    walked = 0.0
    for (previous, following), step in zip(zip(path, path[1:]), lengths):
        if walked + step >= total / 2.0:
            share = (total / 2.0 - walked) / step if step else 0.0
            return (previous[0] + (following[0] - previous[0]) * share,
                    previous[1] + (following[1] - previous[1]) * share)
        walked += step
    return path[-1]


def _connector_xml(shape_id, from_id, to_id, path, label):
    """Dynamischer Verbinder entlang eines Streckenzugs, an beiden Formen verklebt."""
    begin_x, begin_y = path[0]
    end_x, end_y = path[-1]
    width = end_x - begin_x
    height = end_y - begin_y
    label_x, label_y = _path_midpoint(path)
    label_x -= begin_x
    label_y -= begin_y
    walk_begin = "_WALKGLUE(BegTrigger,EndTrigger,WalkPreference)"
    walk_end = "_WALKGLUE(EndTrigger,BegTrigger,WalkPreference)"

    parts = ["<Shape ID='%d' NameU='Dynamic connector' Name='Dynamic connector' "
             "Type='Shape' Master='%d'>" % (shape_id, MASTER_CONNECTOR_ID)]
    parts += [
        _cell("PinX", _num((begin_x + end_x) / 2.0), "Inh"),
        _cell("PinY", _num((begin_y + end_y) / 2.0), "Inh"),
        _cell("Width", _num(width), "GUARD(EndX-BeginX)"),
        _cell("Height", _num(height), "GUARD(EndY-BeginY)"),
        _cell("LocPinX", _num(width / 2.0), "Inh"),
        _cell("LocPinY", _num(height / 2.0), "Inh"),
        _cell("BeginX", _num(begin_x), walk_begin),
        _cell("BeginY", _num(begin_y), walk_begin),
        _cell("EndX", _num(end_x), walk_end),
        _cell("EndY", _num(end_y), walk_end),
        _cell("BegTrigger", 2, "_XFTRIGGER(Sheet.%d!EventXFMod)" % from_id),
        _cell("EndTrigger", 2, "_XFTRIGGER(Sheet.%d!EventXFMod)" % to_id),
        _cell("ShapeRouteStyle", 1),          # 1 = rechtwinklig (Flussdiagramm)
        _cell("ConFixedCode", 0),
        _cell("ConLineRouteExt", 0),
        _cell("LayerMember", 0),
        _cell("LineColor", "#4D5B6B"),
        _cell("LineWeight", _num(1 / 72.0)),
        _cell("EndArrow", 4),
        _cell("EndArrowSize", 2),
        # Beschriftung auf die Mitte der tatsaechlichen Strecke setzen (sonst
        # erbt sie die Position des Masters und landet neben der Zielform)
        _cell("TxtPinX", _num(label_x)),
        _cell("TxtPinY", _num(label_y)),
        _cell("TxtWidth", _num(0.6), "MAX(TEXTWIDTH(TheText),5*Char.Size)"),
        _cell("TxtHeight", _num(0.25), "TEXTHEIGHT(TheText,TxtWidth)"),
        _cell("TxtLocPinX", _num(0.3), "TxtWidth*0.5"),
        _cell("TxtLocPinY", _num(0.125), "TxtHeight*0.5"),
        _cell("TxtAngle", 0, "GUARD(0DA)"),
    ]
    parts.append("<Section N='Control'><Row N='TextPosition'>"
                 + _cell("X", _num(label_x))
                 + _cell("Y", _num(label_y))
                 + _cell("XDyn", _num(label_x), "Controls.TextPosition")
                 + _cell("YDyn", _num(label_y), "Controls.TextPosition.Y")
                 + _cell("XCon", 0) + _cell("YCon", 0) + _cell("CanGlue", 0)
                 + "</Row></Section>")
    # Geometrie ueberschreibt die des Masters: Streckenzug in Formkoordinaten
    rows = ["<Section N='Geometry' IX='0'>",
            "<Row T='MoveTo' IX='1'>%s%s</Row>" % (_cell("X", 0), _cell("Y", 0))]
    for position, (x, y) in enumerate(path[1:], start=2):
        rows.append("<Row T='LineTo' IX='%d'>%s%s</Row>"
                    % (position, _cell("X", _num(x - begin_x)),
                       _cell("Y", _num(y - begin_y))))
    # Der Master bringt drei Zeilen mit; ueberzaehlige entfernen
    for position in range(len(path) + 1, 4):
        rows.append("<Row T='LineTo' IX='%d' Del='1'/>" % position)
    rows.append("</Section>")
    parts.append("".join(rows))
    if label:
        parts.append(_text_sections(8, color="#333333"))
        parts.append("<Text>%s</Text>" % html.escape(label))
    parts.append("</Shape>")
    return "".join(parts)


def _document_xml():
    """document.xml mit genau einem Stylesheet; Formen setzen ihre Werte selbst."""
    style_cells = "".join([
        _cell("EnableLineProps", 1), _cell("EnableFillProps", 1),
        _cell("EnableTextProps", 1), _cell("HideForApply", 0),
        _cell("LineWeight", _num(1 / 72.0)), _cell("LineColor", "#000000"),
        _cell("LinePattern", 1), _cell("Rounding", 0),
        _cell("BeginArrow", 0), _cell("EndArrow", 0),
        _cell("BeginArrowSize", 2), _cell("EndArrowSize", 2),
        _cell("LineCap", 0), _cell("LineColorTrans", 0),
        _cell("FillForegnd", "#FFFFFF"), _cell("FillBkgnd", "#FFFFFF"),
        _cell("FillPattern", 1), _cell("ShdwPattern", 0),
        _cell("FillForegndTrans", 0), _cell("FillBkgndTrans", 0),
        _cell("ShapeShdwType", 0), _cell("ShapeShdwOffsetX", 0),
        _cell("ShapeShdwOffsetY", 0),
        _cell("LeftMargin", 0.05), _cell("RightMargin", 0.05),
        _cell("TopMargin", 0.03), _cell("BottomMargin", 0.03),
        _cell("VerticalAlign", 1),
        _cell("TextDirection", 0),
    ])
    character = ("<Section N='Character'><Row IX='0'>"
                 + _cell("Font", "Calibri") + _cell("Color", "#000000")
                 + _cell("Size", _num(9 / 72.0)) + _cell("Style", 0)
                 + _cell("Case", 0) + _cell("Pos", 0)
                 + _cell("FontScale", 1) + _cell("Locale", 0)
                 + "</Row></Section>")
    paragraph = ("<Section N='Paragraph'><Row IX='0'>"
                 + _cell("IndFirst", 0) + _cell("IndLeft", 0)
                 + _cell("IndRight", 0) + _cell("SpLine", -1.2)
                 + _cell("SpBefore", 0) + _cell("SpAfter", 0)
                 + _cell("HorzAlign", 1) + _cell("Bullet", 0)
                 + "</Row></Section>")
    return (XML_HEAD
            + "<VisioDocument %s>" % VNS
            + "<DocumentSettings TopPage='0' DefaultTextStyle='0' "
              "DefaultLineStyle='0' DefaultFillStyle='0' DefaultGuideStyle='0'>"
            + "<GlueSettings>9</GlueSettings>"
            + "<SnapSettings>65847</SnapSettings>"
            + "<SnapExtensions>34</SnapExtensions>"
            + "<SnapAngles/>"
            + "<DynamicGridEnabled>1</DynamicGridEnabled>"
            + "<ProtectStyles>0</ProtectStyles>"
            + "<ProtectShapes>0</ProtectShapes>"
            + "<ProtectMasters>0</ProtectMasters>"
            + "<ProtectBkgnds>0</ProtectBkgnds>"
            + "</DocumentSettings>"
            + "<FaceNames><FaceName NameU='Calibri' Panose='2 15 5 2 2 2 4 3 2 4'/>"
              "</FaceNames>"
            + "<StyleSheets>"
            + "<StyleSheet ID='0' NameU='No Style' IsCustomNameU='1' "
              "Name='No Style' IsCustomName='1'>"
            + style_cells + character + paragraph
            + "</StyleSheet>"
            + "</StyleSheets>"
            + "<DocumentSheet NameU='TheDoc' Name='TheDoc' "
              "LineStyle='0' FillStyle='0' TextStyle='0'>"
            + _cell("OutputFormat", 0) + _cell("LockPreview", 0)
            + _cell("AddMarkup", 0) + _cell("ViewMarkup", 0)
            + _cell("PreviewQuality", 0) + _cell("PreviewScope", 0)
            + _cell("DocLangID", 1031)
            + "</DocumentSheet>"
            + "</VisioDocument>")


def _masters_xml():
    """Der Standard-Master 'Dynamic connector' - Grundlage echter Visio-Verbinder."""
    return (XML_HEAD
            + "<Masters %s>" % VNS
            + "<Master ID='%d' NameU='Dynamic connector' IsCustomNameU='1' "
              "Name='Dynamic connector' IsCustomName='1' "
              "Prompt='Verbindet zwei Formen und folgt ihnen automatisch.' "
              "IconSize='1' AlignName='2' MatchByName='1' IconUpdate='0' "
              "BaseID='{F7290A45-E3AD-11D2-AE4F-006008C9F5A9}' "
              "UniqueID='{9E0B9A0E-1D2C-4B5E-9C3A-7A1B2C3D4E5F}' "
              "PatternFlags='0' Hidden='0' MasterType='0'>"
            % MASTER_CONNECTOR_ID
            + "<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>"
            + _cell("PageWidth", _num(3.937007874015748))
            + _cell("PageHeight", _num(3.937007874015748))
            + _cell("ShdwOffsetX", _num(0.1181102362204724))
            + _cell("ShdwOffsetY", _num(-0.1181102362204724))
            + _cell("PageScale", _num(1), unit="IN")
            + _cell("DrawingScale", _num(1), unit="IN")
            + _cell("DrawingSizeType", 4) + _cell("DrawingScaleType", 0)
            + _cell("InhibitSnap", 0) + _cell("UIVisibility", 0)
            + _cell("ShdwType", 0) + _cell("ShdwObliqueAngle", 0)
            + _cell("ShdwScaleFactor", 1) + _cell("DrawingResizeType", 0)
            + "</PageSheet>"
            + "<Rel r:id='rId1'/>"
            + "</Master>"
            + "</Masters>")


def _master1_xml():
    """Inhalt des Connector-Masters: 1D-Form mit dynamischer Verklebung."""
    guard = {
        "PinX": "GUARD((BeginX+EndX)/2)", "PinY": "GUARD((BeginY+EndY)/2)",
        "Width": "GUARD(EndX-BeginX)", "Height": "GUARD(EndY-BeginY)",
        "LocPinX": "GUARD(Width*0.5)", "LocPinY": "GUARD(Height*0.5)",
    }
    return (XML_HEAD
            + "<MasterContents %s>" % VNS
            + "<Shapes>"
            + "<Shape ID='5' OriginalID='0' Type='Shape' "
              "LineStyle='0' FillStyle='0' TextStyle='0'>"
            + _cell("PinX", _num(1.7716535433), guard["PinX"])
            + _cell("PinY", _num(1.7716535433), guard["PinY"])
            + _cell("Width", _num(1.1811023622), guard["Width"])
            + _cell("Height", _num(-1.1811023622), guard["Height"])
            + _cell("LocPinX", _num(0.5905511811), guard["LocPinX"])
            + _cell("LocPinY", _num(-0.5905511811), guard["LocPinY"])
            + _cell("Angle", 0, "GUARD(0DA)")
            + _cell("FlipX", 0, "GUARD(FALSE)")
            + _cell("FlipY", 0, "GUARD(FALSE)")
            + _cell("ResizeMode", 0)
            + _cell("BeginX", _num(1.1811023622))
            + _cell("BeginY", _num(2.3622047244))
            + _cell("EndX", _num(2.3622047244))
            + _cell("EndY", _num(1.1811023622))
            + _cell("TxtPinX", 0, "SETATREF(Controls.TextPosition)")
            + _cell("TxtPinY", _num(-1.1811023622),
                    "SETATREF(Controls.TextPosition.Y)")
            + _cell("TxtWidth", _num(0.5555555556),
                    "MAX(TEXTWIDTH(TheText),5*Char.Size)")
            + _cell("TxtHeight", _num(0.2444444444), "TEXTHEIGHT(TheText,TxtWidth)")
            + _cell("TxtLocPinX", _num(0.2777777778), "TxtWidth*0.5")
            + _cell("TxtLocPinY", _num(0.1222222222), "TxtHeight*0.5")
            + _cell("TxtAngle", 0)
            + _cell("LockHeight", 1) + _cell("LockCalcWH", 1)
            + _cell("NoAlignBox", 1) + _cell("DynFeedback", 2)
            + _cell("GlueType", 2) + _cell("ObjType", 2)
            + _cell("NoLiveDynamics", 1) + _cell("ShapeSplittable", 1)
            + _cell("LayerMember", 0)
            + _cell("LineColor", "#4D5B6B") + _cell("EndArrow", 4)
            + "<Section N='Control'><Row N='TextPosition'>"
            + _cell("X", 0, "Controls.TextPosition")
            + _cell("Y", _num(-1.1811023622), "Controls.TextPosition.Y")
            + _cell("XDyn", 0) + _cell("YDyn", _num(-1.1811023622))
            + _cell("XCon", 5,
                    'IF(OR(STRSAME(SHAPETEXT(TheText),""),HideText),5,0)')
            + _cell("YCon", 0) + _cell("CanGlue", 0)
            + _cell("Prompt", "Textposition verschieben")
            + "</Row></Section>"
            + "<Section N='Geometry' IX='0'>"
            + _cell("NoFill", 1) + _cell("NoLine", 0) + _cell("NoShow", 0)
            + _cell("NoSnap", 0) + _cell("NoQuickDrag", 0)
            + "<Row T='MoveTo' IX='1'>%s%s</Row>" % (_cell("X", 0), _cell("Y", 0))
            + "<Row T='LineTo' IX='2'>%s%s</Row>"
            % (_cell("X", 0), _cell("Y", _num(-1.1811023622)))
            + "<Row T='LineTo' IX='3'>%s%s</Row>"
            % (_cell("X", _num(1.1811023622)), _cell("Y", _num(-1.1811023622)))
            + "</Section>"
            + "</Shape></Shapes></MasterContents>")


def _pages_xml(page_width, page_height, title):
    return (XML_HEAD
            + "<Pages %s>" % VNS
            + "<Page ID='0' NameU='%s' Name='%s' ViewScale='1' "
              "ViewCenterX='%s' ViewCenterY='%s'>"
            % (_attr(title), _attr(title),
               _num(page_width / 2.0), _num(page_height / 2.0))
            + "<PageSheet LineStyle='0' FillStyle='0' TextStyle='0'>"
            + _cell("PageWidth", _num(page_width))
            + _cell("PageHeight", _num(page_height))
            + _cell("ShdwOffsetX", _num(0.1181102362))
            + _cell("ShdwOffsetY", _num(-0.1181102362))
            + _cell("PageScale", _num(1), unit="IN")
            + _cell("DrawingScale", _num(1), unit="IN")
            + _cell("DrawingSizeType", 0) + _cell("DrawingScaleType", 0)
            + _cell("InhibitSnap", 0) + _cell("UIVisibility", 0)
            + _cell("ShdwType", 0) + _cell("ShdwObliqueAngle", 0)
            + _cell("ShdwScaleFactor", 1) + _cell("DrawingResizeType", 1)
            + _cell("PageShapeSplit", 1)
            + "</PageSheet>"
            + "<Rel r:id='rId1'/>"
            + "</Page></Pages>")


def _page1_xml(graph, placements, routes):
    """Baut den Seiteninhalt: Rahmen, Formen, verklebte Verbinder."""
    shapes = []
    connects = []
    next_id = 1
    shape_ids = {}

    # 1. Subgraph-Rahmen zuerst (liegen hinten)
    for name, members in graph.groups:
        boxes = [placements[nid] for nid in members if nid in placements]
        if not boxes:
            continue
        left = min(x - w / 2.0 for x, y, w, h in boxes) - GROUP_PAD
        right = max(x + w / 2.0 for x, y, w, h in boxes) + GROUP_PAD
        bottom = min(y - h / 2.0 for x, y, w, h in boxes) - GROUP_PAD
        top = max(y + h / 2.0 for x, y, w, h in boxes) + GROUP_PAD + 0.16
        shapes.append(_group_shape_xml(next_id, name,
                                       (left + right) / 2.0, (bottom + top) / 2.0,
                                       right - left, top - bottom))
        next_id += 1

    # 2. Prozessformen
    for nid, node in graph.nodes.items():
        if nid not in placements:
            continue
        x, y, width, height = placements[nid]
        shape_ids[nid] = next_id
        shapes.append(_shape_xml(next_id, node, x, y, width, height))
        next_id += 1

    # 3. Verbinder (liegen vorn) inklusive Klebeverbindungen
    for index, edge in enumerate(graph.edges):
        if edge.src not in shape_ids or edge.dst not in shape_ids:
            continue
        sx, sy, sw, sh = placements[edge.src]
        tx, ty, tw, th = placements[edge.dst]
        waypoints = routes.get(index) or []
        # Austrittspunkt Richtung erster Stuetzpunkt, Eintritt vom letzten her -
        # dadurch verlassen parallele Kanten die Form an verschiedenen Stellen.
        first = waypoints[0] if waypoints else (tx, ty)
        last = waypoints[-1] if waypoints else (sx, sy)
        begin = _boundary_point(sx, sy, sw, sh, first[0], first[1])
        end = _boundary_point(tx, ty, tw, th, last[0], last[1])
        path = _orthogonal_path([begin] + waypoints + [end])
        from_id, to_id = shape_ids[edge.src], shape_ids[edge.dst]
        shapes.append(_connector_xml(next_id, from_id, to_id, path, edge.label))
        # FromPart 9 = Anfangspunkt, 12 = Endpunkt; ToPart 3 = ganze Form
        connects.append("<Connect FromSheet='%d' FromCell='BeginX' FromPart='9' "
                        "ToSheet='%d' ToCell='PinX' ToPart='3'/>"
                        % (next_id, from_id))
        connects.append("<Connect FromSheet='%d' FromCell='EndX' FromPart='12' "
                        "ToSheet='%d' ToCell='PinX' ToPart='3'/>"
                        % (next_id, to_id))
        next_id += 1

    return (XML_HEAD
            + "<PageContents %s>" % VNS
            + "<Shapes>" + "".join(shapes) + "</Shapes>"
            + ("<Connects>" + "".join(connects) + "</Connects>" if connects else "")
            + "</PageContents>")


def _windows_xml(page_width, page_height):
    return (XML_HEAD
            + "<Windows ClientWidth='1600' ClientHeight='900' %s>" % VNS
            + "<Window ID='0' WindowType='Drawing' WindowState='1073741824' "
              "WindowLeft='0' WindowTop='0' WindowWidth='1600' "
              "WindowHeight='900' ContainerType='Page' Page='0' "
              "ViewScale='1' ViewCenterX='%s' ViewCenterY='%s'>"
            % (_num(page_width / 2.0), _num(page_height / 2.0))
            + "<ShowRulers>1</ShowRulers><ShowGrid>1</ShowGrid>"
            + "<ShowPageBreaks>0</ShowPageBreaks><ShowGuides>1</ShowGuides>"
            + "<ShowConnectionPoints>1</ShowConnectionPoints>"
            + "<GlueSettings>9</GlueSettings>"
            + "<SnapSettings>65847</SnapSettings>"
            + "<SnapExtensions>34</SnapExtensions><SnapAngles/>"
            + "<DynamicGridEnabled>1</DynamicGridEnabled>"
            + "<TabSplitterPos>0.5</TabSplitterPos>"
            + "</Window></Windows>")


CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
    'package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/visio/document.xml" ContentType="application/'
    'vnd.ms-visio.drawing.main+xml"/>'
    '<Override PartName="/visio/masters/masters.xml" ContentType="application/'
    'vnd.ms-visio.masters+xml"/>'
    '<Override PartName="/visio/masters/master1.xml" ContentType="application/'
    'vnd.ms-visio.master+xml"/>'
    '<Override PartName="/visio/pages/pages.xml" ContentType="application/'
    'vnd.ms-visio.pages+xml"/>'
    '<Override PartName="/visio/pages/page1.xml" ContentType="application/'
    'vnd.ms-visio.page+xml"/>'
    '<Override PartName="/visio/windows.xml" ContentType="application/'
    'vnd.ms-visio.windows+xml"/>'
    '<Override PartName="/docProps/core.xml" ContentType="application/'
    'vnd.openxmlformats-package.core-properties+xml"/>'
    '</Types>'
)

ROOT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships">'
    '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/'
    'relationships/document" Target="visio/document.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/'
    '2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
    '</Relationships>'
)

DOCUMENT_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships">'
    '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/'
    'relationships/masters" Target="masters/masters.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.microsoft.com/visio/2010/'
    'relationships/pages" Target="pages/pages.xml"/>'
    '<Relationship Id="rId3" Type="http://schemas.microsoft.com/visio/2010/'
    'relationships/windows" Target="windows.xml"/>'
    '</Relationships>'
)


def _simple_rels(target, rel_type):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
            '2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/'
            '2010/relationships/%s" Target="%s"/>'
            '</Relationships>' % (rel_type, target))


def _core_xml(title):
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
            'metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<dc:title>%s</dc:title>'
            '<dc:creator>ProcessMap Studio</dc:creator>'
            '<cp:lastModifiedBy>ProcessMap Studio</cp:lastModifiedBy>'
            '<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
            '<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>'
            '</cp:coreProperties>' % (html.escape(title), stamp, stamp))


def write_vsdx(graph, path, title="Prozess"):
    """Schreibt den Graphen als bearbeitbare Visio-Datei (.vsdx)."""
    if not graph.nodes:
        raise ValueError("Der Mermaid-Code enthält keine erkennbaren Schritte.")
    placements, routes, page_width, page_height = layout_graph(graph)
    page_name = (title or "Prozess")[:40] or "Prozess"

    parts = {
        "[Content_Types].xml": CONTENT_TYPES_XML,
        "_rels/.rels": ROOT_RELS_XML,
        "docProps/core.xml": _core_xml(title or "Prozess"),
        "visio/document.xml": _document_xml(),
        "visio/_rels/document.xml.rels": DOCUMENT_RELS_XML,
        "visio/masters/masters.xml": _masters_xml(),
        "visio/masters/_rels/masters.xml.rels":
            _simple_rels("master1.xml", "master"),
        "visio/masters/master1.xml": _master1_xml(),
        "visio/pages/pages.xml": _pages_xml(page_width, page_height, page_name),
        "visio/pages/_rels/pages.xml.rels": _simple_rels("page1.xml", "page"),
        "visio/pages/page1.xml": _page1_xml(graph, placements, routes),
        "visio/pages/_rels/page1.xml.rels":
            _simple_rels("../masters/master1.xml", "master"),
        "visio/windows.xml": _windows_xml(page_width, page_height),
    }
    # [Content_Types].xml muss laut OPC der erste Eintrag im Archiv sein
    order = ["[Content_Types].xml"] + [k for k in parts if k != "[Content_Types].xml"]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in order:
            archive.writestr(name, parts[name].encode("utf-8"))
    return len(graph.nodes), len(graph.edges)


def mermaid_to_vsdx(code, path, title="Prozess"):
    return write_vsdx(parse_mermaid(code), path, title)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class PdfOptionsDialog(tk.Toplevel):
    """Fragt Ausrichtung und Skalierung fuer den PDF-Export ab."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("PDF-Export")
        self.resizable(False, False)
        self.transient(parent)
        self.result = None

        self.orientation = tk.StringVar(value="landscape")
        self.scaling = tk.StringVar(value="fit")

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        box1 = ttk.LabelFrame(frame, text="Ausrichtung", padding=8)
        box1.pack(fill="x")
        ttk.Radiobutton(box1, text="Querformat", value="landscape",
                        variable=self.orientation).pack(anchor="w")
        ttk.Radiobutton(box1, text="Hochformat", value="portrait",
                        variable=self.orientation).pack(anchor="w")

        box2 = ttk.LabelFrame(frame, text="Darstellung", padding=8)
        box2.pack(fill="x", pady=(10, 0))
        ttk.Radiobutton(
            box2, text="Auf eine Seite einpassen (verkleinert)",
            value="fit", variable=self.scaling,
        ).pack(anchor="w")
        ttk.Radiobutton(
            box2, text="Wie angezeigt (mehrseitig, an Seitenbreite)",
            value="flow", variable=self.scaling,
        ).pack(anchor="w")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(14, 0))
        ttk.Button(buttons, text="Abbrechen", command=self.destroy).pack(
            side="right"
        )
        ttk.Button(buttons, text="PDF erstellen", command=self._ok).pack(
            side="right", padx=(0, 6)
        )

        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        self.wait_visibility()
        # mittig ueber dem Hauptfenster platzieren
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def _ok(self):
        self.result = (self.orientation.get(), self.scaling.get() == "fit")
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1060x720")
        self.minsize(880, 560)
        self._build_ui()

    def _step_frame(self, parent, number, title, hint):
        """Ein nummerierter Prozessschritt in der linken Leiste."""
        frame = ttk.LabelFrame(parent, text="  %d.  %s  " % (number, title),
                               padding=(9, 5, 9, 8))
        frame.pack(fill="x")
        ttk.Label(frame, text=hint, font=self.hint_font, foreground="#5A6672",
                  wraplength=SIDEBAR_WIDTH - 40, justify="left").pack(
            anchor="w", pady=(0, 6))
        return frame

    def _arrow(self, parent):
        ttk.Label(parent, text="↓", foreground="#AAB3BD").pack(pady=(1, 1))

    def _build_ui(self):
        default_font = tkfont.nametofont("TkDefaultFont")
        self.hint_font = default_font.copy()
        self.hint_font.configure(size=max(7, int(default_font.cget("size")) - 1))

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True)

        # ------------------------------------------------ linke Schrittleiste
        sidebar = ttk.Frame(outer, padding=(12, 10, 6, 10), width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="So läuft es ab",
                  font=(default_font.cget("family"),
                        int(default_font.cget("size")) + 1, "bold")).pack(
            anchor="w", pady=(0, 8))

        step1 = self._step_frame(
            sidebar, 1, "Vorbereiten",
            "Prompt kopieren, in Copilot einfügen und den Text bzw. die PDF "
            "darunter anhängen.")
        ttk.Button(step1, text="Master-Prompt kopieren",
                   command=self.copy_prompt).pack(fill="x")
        self._arrow(sidebar)

        step2 = self._step_frame(
            sidebar, 2, "Übernehmen",
            "Antwort von Copilot kopieren und hier einsetzen. Der Codeblock "
            "wird automatisch herausgelöst.")
        ttk.Button(step2, text="Copilot-Antwort einfügen",
                   command=self.paste_copilot).pack(fill="x")
        ttk.Button(step2, text="Beispiel laden",
                   command=self.load_example).pack(fill="x", pady=(4, 0))
        self._arrow(sidebar)

        step3 = self._step_frame(
            sidebar, 3, "Prüfen",
            "Diagramm ansehen und im Editor rechts bei Bedarf korrigieren.")
        preview_button = ttk.Button(step3, text="Vorschau im Browser",
                                    command=self.preview)
        preview_button.pack(fill="x")
        self._arrow(sidebar)

        step4 = self._step_frame(
            sidebar, 4, "Ausgeben",
            "Ergebnis als Datei speichern.")
        visio_button = ttk.Button(step4, text="Visio (.vsdx) – bearbeitbar",
                                  command=self.export_visio)
        visio_button.pack(fill="x")
        pdf_button = ttk.Button(step4, text="PDF – zum Drucken",
                                command=self.export_pdf)
        pdf_button.pack(fill="x", pady=(4, 0))
        html_button = ttk.Button(step4, text="HTML – zum Teilen",
                                 command=self.save_html)
        html_button.pack(fill="x", pady=(4, 0))

        # Schritt 3 und 4 sind erst sinnvoll, wenn Code vorhanden ist.
        self._needs_code = [preview_button, visio_button, pdf_button, html_button]

        # ------------------------------------------------------ rechter Editor
        right = ttk.Frame(outer, padding=(6, 10, 12, 10))
        right.pack(side="left", fill="both", expand=True)

        title_row = ttk.Frame(right)
        title_row.pack(fill="x", pady=(0, 8))
        ttk.Label(title_row, text="Titel der Prozesskarte:").pack(side="left")
        self.title_var = tk.StringVar(value="Process Map")
        ttk.Entry(title_row, textvariable=self.title_var).pack(
            side="left", fill="x", expand=True, padx=(8, 0))

        ttk.Label(right, text="Prozess-Code (Mermaid) – jederzeit von Hand "
                              "änderbar",
                  font=self.hint_font, foreground="#5A6672").pack(
            anchor="w", pady=(0, 3))

        editor_frame = ttk.Frame(right)
        editor_frame.pack(fill="both", expand=True)
        self.text = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            background="#fdfdfd",
            relief="solid",
            borderwidth=1,
        )
        yscroll = ttk.Scrollbar(editor_frame, orient="vertical",
                                command=self.text.yview)
        xscroll = ttk.Scrollbar(editor_frame, orient="horizontal",
                                command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        # ---------------------------------------------------------- Statuszeile
        ttk.Separator(self, orient="horizontal").pack(fill="x")
        self.status_var = tk.StringVar()
        ttk.Label(self, textvariable=self.status_var, padding=(12, 6),
                  anchor="w").pack(fill="x")

        self._suppress_modified = False
        self.text.bind("<<Modified>>", self._on_modified)
        self.load_example()
        self.status_var.set("Bereit – mit Schritt 1 beginnen oder direkt "
                            "Mermaid-Code eintippen.")

    def _on_modified(self, _event=None):
        if self._suppress_modified:
            return
        self._suppress_modified = True
        self.text.edit_modified(False)
        self._suppress_modified = False
        self._update_actions()

    def _update_actions(self):
        """Schritt 3 und 4 nur freischalten, wenn es etwas auszugeben gibt."""
        state = "normal" if self.get_code() else "disabled"
        for button in self._needs_code:
            button.configure(state=state)

    # -- Aktionen -----------------------------------------------------------
    def get_code(self) -> str:
        return self.text.get("1.0", "end").strip()

    def set_code(self, code: str):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", code)
        self._update_actions()

    def load_example(self):
        self.set_code(EXAMPLE_DIAGRAM)
        self.status_var.set("Beispiel geladen – weiter mit Schritt 3 (Prüfen).")

    def copy_prompt(self):
        self.clipboard_clear()
        self.clipboard_append(MASTER_PROMPT)
        self.status_var.set(
            "Schritt 1 erledigt: Prompt liegt in der Zwischenablage. In Copilot "
            "einfügen, Text/PDF darunter anhängen – dann weiter mit Schritt 2."
        )

    def paste_copilot(self):
        try:
            raw = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(APP_TITLE, "Die Zwischenablage ist leer.")
            return
        code = extract_mermaid(raw)
        if not code:
            messagebox.showwarning(
                APP_TITLE, "In der Zwischenablage wurde kein Mermaid-Code gefunden."
            )
            return
        self.set_code(code)
        self.status_var.set(
            "Schritt 2 erledigt: Code übernommen. Bitte in Schritt 3 prüfen, "
            "ob der Prozess wirklich so stimmt."
        )

    def _validate(self, code: str) -> bool:
        if not code:
            messagebox.showwarning(APP_TITLE, "Bitte zuerst Mermaid-Code eingeben.")
            return False
        first = code.lstrip().splitlines()[0].strip().lower()
        known = ("flowchart", "graph", "sequencediagram", "statediagram",
                 "gantt", "journey", "classdiagram", "erdiagram", "%%")
        if not first.startswith(known):
            if not messagebox.askyesno(
                APP_TITLE,
                "Der Code beginnt nicht mit einem bekannten Mermaid-Diagrammtyp "
                "(z. B. „flowchart TD“).\nTrotzdem fortfahren?",
            ):
                return False
        return True

    def preview(self):
        code = self.get_code()
        if not self._validate(code):
            return
        html_doc = build_html(code, self.title_var.get().strip())
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", prefix="processmap_",
            delete=False, encoding="utf-8",
        )
        with tmp:
            tmp.write(html_doc)
        webbrowser.open(Path(tmp.name).as_uri())
        offline = " (Mermaid lokal eingebettet)" if LOCAL_MERMAID.is_file() else \
            " (Mermaid via CDN – Browser braucht Internet)"
        self.status_var.set("Vorschau im Browser geöffnet" + offline)

    def export_pdf(self):
        code = self.get_code()
        if not self._validate(code):
            return
        dialog = PdfOptionsDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        orientation, fit_one_page = dialog.result
        pdf_path = filedialog.asksaveasfilename(
            title="PDF exportieren",
            defaultextension=".pdf",
            filetypes=[("PDF-Datei", "*.pdf")],
            initialfile=re.sub(r"[^\w\- ]", "", self.title_var.get()).strip()
            or "process_map",
        )
        if not pdf_path:
            return
        title = self.title_var.get().strip()

        browser = find_chromium_browser()
        if browser:
            self.status_var.set("Erzeuge PDF…")
            self.update_idletasks()
            html_doc = build_print_html(
                code, title, orientation, fit_one_page, auto_print=False
            )
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", prefix="processmap_print_",
                delete=False, encoding="utf-8",
            )
            with tmp:
                tmp.write(html_doc)
            try:
                if headless_pdf(browser, Path(tmp.name), pdf_path):
                    self.status_var.set("PDF gespeichert: %s" % pdf_path)
                    return
            finally:
                try:
                    Path(tmp.name).unlink()
                except OSError:
                    pass

        # Fallback: Druckdialog des Standardbrowsers (dort "Als PDF speichern")
        html_doc = build_print_html(
            code, title, orientation, fit_one_page, auto_print=True
        )
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", prefix="processmap_print_",
            delete=False, encoding="utf-8",
        )
        with tmp:
            tmp.write(html_doc)
        webbrowser.open(Path(tmp.name).as_uri())
        messagebox.showinfo(
            APP_TITLE,
            "Der direkte PDF-Export war nicht möglich (kein Edge/Chrome "
            "gefunden).\n\nIm Browser öffnet sich nun der Druckdialog: Dort "
            "als Ziel „Als PDF speichern“ wählen. Format und Skalierung sind "
            "bereits voreingestellt.",
        )
        self.status_var.set(
            "Druckdialog im Browser geöffnet – dort „Als PDF speichern“ wählen."
        )

    def export_visio(self):
        code = self.get_code()
        if not self._validate(code):
            return
        title = self.title_var.get().strip() or "Prozess"
        path = filedialog.asksaveasfilename(
            title="Als Visio-Zeichnung exportieren",
            defaultextension=".vsdx",
            filetypes=[("Visio-Zeichnung", "*.vsdx")],
            initialfile=re.sub(r"[^\w\- ]", "", title).strip() or "process_map",
        )
        if not path:
            return
        try:
            nodes, edges = mermaid_to_vsdx(code, path, title)
        except Exception as error:  # defekter Mermaid-Code o. ae.
            messagebox.showerror(
                APP_TITLE,
                "Der Visio-Export ist fehlgeschlagen:\n\n%s\n\nPrüfe, ob der "
                "Mermaid-Code den Konventionen des Master-Prompts folgt." % error,
            )
            self.status_var.set("Visio-Export fehlgeschlagen.")
            return
        self.status_var.set(
            "Visio-Datei gespeichert (%d Formen, %d Verbinder): %s"
            % (nodes, edges, path)
        )

    def save_html(self):
        code = self.get_code()
        if not self._validate(code):
            return
        path = filedialog.asksaveasfilename(
            title="Process Map speichern",
            defaultextension=".html",
            filetypes=[("HTML-Datei", "*.html")],
            initialfile=re.sub(r"[^\w\- ]", "", self.title_var.get()).strip()
            or "process_map",
        )
        if not path:
            return
        Path(path).write_text(
            build_html(code, self.title_var.get().strip()), encoding="utf-8"
        )
        self.status_var.set("Gespeichert: %s" % path)


if __name__ == "__main__":
    App().mainloop()
