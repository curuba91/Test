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
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITLE = "ProcessMap Studio"
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
        self.geometry("980x680")
        self.minsize(720, 480)
        self._build_ui()

    def _build_ui(self):
        toolbar = ttk.Frame(self, padding=(10, 8))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Titel:").pack(side="left")
        self.title_var = tk.StringVar(value="Process Map")
        ttk.Entry(toolbar, textvariable=self.title_var, width=32).pack(
            side="left", padx=(4, 16)
        )

        ttk.Button(toolbar, text="Vorschau im Browser", command=self.preview).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="PDF exportieren…", command=self.export_pdf).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Als HTML speichern…", command=self.save_html).pack(
            side="left", padx=2
        )
        ttk.Button(
            toolbar, text="Copilot-Antwort einfügen", command=self.paste_copilot
        ).pack(side="left", padx=2)
        ttk.Button(
            toolbar, text="Master-Prompt kopieren", command=self.copy_prompt
        ).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Beispiel laden", command=self.load_example).pack(
            side="left", padx=2
        )

        editor_frame = ttk.Frame(self, padding=(10, 0, 10, 0))
        editor_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            background="#fdfdfd",
        )
        yscroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.text.yview)
        xscroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(
            value="Bereit. Mermaid-Code eingeben oder Copilot-Antwort einfügen, "
            "dann „Vorschau im Browser“."
        )
        ttk.Label(self, textvariable=self.status_var, padding=(10, 6)).pack(fill="x")

        self.load_example()

    # -- Aktionen -----------------------------------------------------------
    def get_code(self) -> str:
        return self.text.get("1.0", "end").strip()

    def set_code(self, code: str):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", code)

    def load_example(self):
        self.set_code(EXAMPLE_DIAGRAM)
        self.status_var.set("Beispiel geladen.")

    def copy_prompt(self):
        self.clipboard_clear()
        self.clipboard_append(MASTER_PROMPT)
        self.status_var.set(
            "Master-Prompt in Zwischenablage. In Copilot einfügen, darunter den "
            "Quelltext/PDF-Inhalt anhängen, Antwort hier per "
            "„Copilot-Antwort einfügen“ übernehmen."
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
        self.status_var.set("Mermaid-Code aus Copilot-Antwort übernommen.")

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
