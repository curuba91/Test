#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Klausur-Bewertung Englisch (Oberstufe)
======================================

Ein kostenloses Hilfsprogramm fuer Lehrkraefte:

1. Liest einen Erwartungshorizont (JSON) ein - das Optimum entspricht 15 Notenpunkten.
2. Prueft den Schuelertext auf Grammatik, Rechtschreibung und Zeichensetzung
   (LanguageTool, kostenlos) und listet alle Korrekturen auf.
3. Erstellt eine sprachliche Bewertung (Fehlerdichte -> Prozent -> Notenpunkte).
4. Prueft den Text inhaltlich gegen die Erwartungen der einzelnen Aufgaben
   (Schluesselwort- und Aehnlichkeitsabgleich) und bewertet jede Aufgabe.
5. Erstellt ein Gesamtgutachten mit Notenvorschlag (0-15 Punkte) und
   exportiert den Bericht als Textdatei.

Start: Doppelklick auf die Datei (unter Windows oeffnet .pyw ohne Konsole).
Benoetigt nur Python 3.8+ mit Tkinter (Standardinstallation).
Optional: "pip install language_tool_python" fuer lokale Pruefung ohne Internet,
optional: "pip install python-docx" zum direkten Einlesen von .docx-Dateien.

WICHTIG: Alle Bewertungen sind VORSCHLAEGE und ersetzen nicht die
paedagogische Beurteilung durch die Lehrkraft.
"""

import difflib
import json
import queue
import re
import threading
import tkinter as tk
import urllib.parse
import urllib.request
from tkinter import filedialog, messagebox, ttk

APP_TITEL = "Klausur-Bewertung Englisch (Oberstufe)"

# KMK-uebliche Zuordnung Prozent -> Notenpunkte (Sek II)
NOTENPUNKTE_TABELLE = [
    (95, 15), (90, 14), (85, 13), (80, 12), (75, 11), (70, 10),
    (65, 9), (60, 8), (55, 7), (50, 6), (45, 5), (40, 4),
    (33, 3), (27, 2), (20, 1),
]

NOTEN_TEXT = {
    15: "sehr gut (+)", 14: "sehr gut", 13: "sehr gut (-)",
    12: "gut (+)", 11: "gut", 10: "gut (-)",
    9: "befriedigend (+)", 8: "befriedigend", 7: "befriedigend (-)",
    6: "ausreichend (+)", 5: "ausreichend", 4: "ausreichend (-)",
    3: "schwach ausreichend", 2: "mangelhaft", 1: "mangelhaft (-)",
    0: "ungenuegend",
}

LT_PUBLIC_API = "https://api.languagetool.org/v2/check"
LT_CHUNK_LIMIT = 9000  # Zeichen pro Anfrage an die oeffentliche API


def prozent_zu_notenpunkte(prozent):
    for schwelle, punkte in NOTENPUNKTE_TABELLE:
        if prozent >= schwelle:
            return punkte
    return 0


def woerter_zaehlen(text):
    return len(re.findall(r"[A-Za-zÄÖÜäöüß'’-]+", text))


# ----------------------------------------------------------------------------
# Grammatik- und Rechtschreibpruefung (LanguageTool)
# ----------------------------------------------------------------------------

class SprachPruefung:
    """Prueft Text mit LanguageTool: lokal (falls installiert) oder ueber die
    kostenlose oeffentliche API."""

    KATEGORIEN = {
        "TYPOS": "Rechtschreibung",
        "GRAMMAR": "Grammatik",
        "PUNCTUATION": "Zeichensetzung",
        "CASING": "Gross-/Kleinschreibung",
        "CONFUSED_WORDS": "Wortverwechslung",
        "REDUNDANCY": "Stil",
        "STYLE": "Stil",
        "COLLOCATIONS": "Kollokation",
    }

    def __init__(self, sprache="en-GB"):
        self.sprache = sprache

    def pruefe(self, text):
        """Liefert eine Liste von Fehler-Dicts:
        {offset, laenge, kategorie, meldung, vorschlaege, kontext}"""
        try:
            return self._pruefe_lokal(text)
        except Exception:
            return self._pruefe_online(text)

    def _pruefe_lokal(self, text):
        import language_tool_python  # optional
        tool = language_tool_python.LanguageTool(self.sprache)
        try:
            fehler = []
            for m in tool.check(text):
                fehler.append(self._fehler_dict(
                    text, m.offset, m.errorLength, m.category,
                    m.message, list(m.replacements)[:5]))
            return fehler
        finally:
            tool.close()

    def _pruefe_online(self, text):
        fehler = []
        for basis, stueck in self._stuecke(text):
            daten = urllib.parse.urlencode({
                "text": stueck,
                "language": self.sprache,
            }).encode("utf-8")
            anfrage = urllib.request.Request(
                LT_PUBLIC_API, data=daten,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                ergebnis = json.loads(antwort.read().decode("utf-8"))
            for m in ergebnis.get("matches", []):
                kat = m.get("rule", {}).get("category", {}).get("id", "")
                vorschlaege = [r["value"] for r in m.get("replacements", [])][:5]
                fehler.append(self._fehler_dict(
                    text, basis + m["offset"], m["length"], kat,
                    m.get("message", ""), vorschlaege))
        return fehler

    def _stuecke(self, text):
        """Zerlegt langen Text an Absatz-/Satzgrenzen in API-taugliche Stuecke.
        Liefert (offset_im_gesamttext, teiltext)."""
        if len(text) <= LT_CHUNK_LIMIT:
            yield 0, text
            return
        pos = 0
        while pos < len(text):
            ende = min(pos + LT_CHUNK_LIMIT, len(text))
            if ende < len(text):
                schnitt = text.rfind("\n", pos, ende)
                if schnitt <= pos:
                    schnitt = text.rfind(". ", pos, ende)
                    schnitt = schnitt + 2 if schnitt > pos else ende
                else:
                    schnitt += 1
                ende = schnitt
            yield pos, text[pos:ende]
            pos = ende

    def _fehler_dict(self, text, offset, laenge, kategorie, meldung, vorschlaege):
        start = max(0, offset - 30)
        ende = min(len(text), offset + laenge + 30)
        kontext = text[start:ende].replace("\n", " ")
        markiert = text[offset:offset + laenge]
        return {
            "offset": offset,
            "laenge": laenge,
            "kategorie": self.KATEGORIEN.get(kategorie, kategorie or "Sonstiges"),
            "kategorie_roh": kategorie,
            "meldung": meldung,
            "vorschlaege": vorschlaege,
            "text": markiert,
            "kontext": kontext,
        }


def sprachliche_bewertung(fehler, wortzahl, abzug_pro_fehler=10.0):
    """Fehlerdichte (gewichtete Fehler je 100 Woerter) -> Prozent."""
    relevanz = {"Rechtschreibung": 1.0, "Grammatik": 1.0,
                "Zeichensetzung": 0.5, "Gross-/Kleinschreibung": 0.5,
                "Wortverwechslung": 1.0, "Kollokation": 0.5, "Stil": 0.25}
    gewichtet = sum(relevanz.get(f["kategorie"], 0.5) for f in fehler)
    dichte = (gewichtet / wortzahl * 100.0) if wortzahl else 0.0
    prozent = max(0.0, min(100.0, 100.0 - dichte * abzug_pro_fehler))
    return {
        "fehler_gesamt": len(fehler),
        "fehler_gewichtet": round(gewichtet, 1),
        "wortzahl": wortzahl,
        "dichte_pro_100": round(dichte, 2),
        "prozent": round(prozent, 1),
        "notenpunkte": prozent_zu_notenpunkte(prozent),
    }


# ----------------------------------------------------------------------------
# Inhaltliche Pruefung gegen den Erwartungshorizont
# ----------------------------------------------------------------------------

def _tokens(text):
    return re.findall(r"[a-zäöüß'’-]+", text.lower())


def _begriff_gefunden(begriff, text_klein, tokenliste):
    """Sucht einen (auch mehrwortigen) Begriff; bei Einzelwoertern zusaetzlich
    unscharf (Tippfehler-tolerant) ueber difflib."""
    begriff = begriff.strip().lower()
    if not begriff:
        return False
    muster = r"\b" + r"\s+".join(re.escape(w) for w in begriff.split()) + r"\w*"
    if re.search(muster, text_klein):
        return True
    if " " not in begriff and len(begriff) >= 5:
        return bool(difflib.get_close_matches(begriff, tokenliste, n=1, cutoff=0.86))
    return False


def inhaltliche_bewertung(erwartungshorizont, schuelertext):
    """Vergleicht den Text mit jeder Aufgabe des Erwartungshorizonts.

    Jede Erwartung besitzt Schluesselwoerter; ab 'mindestens' Treffern gibt es
    die vollen Punkte, darunter anteilig."""
    text_klein = schuelertext.lower()
    tokenliste = _tokens(schuelertext)

    aufgaben_ergebnisse = []
    gesamt_max = 0.0
    gesamt_erreicht = 0.0

    for aufgabe in erwartungshorizont.get("aufgaben", []):
        max_punkte = float(aufgabe.get("max_punkte", 0))
        details = []
        erreicht = 0.0
        summe_teilpunkte = sum(float(e.get("punkte", 0))
                               for e in aufgabe.get("erwartungen", []))

        for erwartung in aufgabe.get("erwartungen", []):
            begriffe = erwartung.get("schluesselwoerter", [])
            mindestens = max(1, int(erwartung.get("mindestens", 1)))
            gefunden = [b for b in begriffe
                        if _begriff_gefunden(b, text_klein, tokenliste)]
            fehlend = [b for b in begriffe if b not in gefunden]
            anteil = min(1.0, len(gefunden) / mindestens) if begriffe else 0.0
            teilpunkte_roh = float(erwartung.get("punkte", 0))
            teilpunkte = anteil * teilpunkte_roh
            erreicht += teilpunkte
            details.append({
                "beschreibung": erwartung.get("beschreibung", ""),
                "punkte_max": teilpunkte_roh,
                "punkte_erreicht": round(teilpunkte, 1),
                "gefunden": gefunden,
                "fehlend": fehlend,
                "mindestens": mindestens,
            })

        # Teilpunkte auf die Maximalpunktzahl der Aufgabe normieren
        if summe_teilpunkte > 0 and max_punkte > 0:
            erreicht = erreicht / summe_teilpunkte * max_punkte
        gesamt_max += max_punkte
        gesamt_erreicht += erreicht
        aufgaben_ergebnisse.append({
            "nummer": str(aufgabe.get("nummer", "?")),
            "titel": aufgabe.get("titel", ""),
            "max_punkte": max_punkte,
            "erreicht": round(erreicht, 1),
            "prozent": round(erreicht / max_punkte * 100, 1) if max_punkte else 0.0,
            "details": details,
        })

    prozent = (gesamt_erreicht / gesamt_max * 100.0) if gesamt_max else 0.0
    return {
        "aufgaben": aufgaben_ergebnisse,
        "max_punkte": gesamt_max,
        "erreicht": round(gesamt_erreicht, 1),
        "prozent": round(prozent, 1),
        "notenpunkte": prozent_zu_notenpunkte(prozent),
    }


# ----------------------------------------------------------------------------
# Gutachten und Bericht
# ----------------------------------------------------------------------------

def gesamtnote(inhalt, sprache, gewichtung):
    w_inhalt = float(gewichtung.get("inhalt", 0.4))
    w_sprache = float(gewichtung.get("sprache", 0.6))
    summe = w_inhalt + w_sprache
    if summe <= 0:
        w_inhalt, w_sprache, summe = 0.4, 0.6, 1.0
    prozent = (inhalt["prozent"] * w_inhalt + sprache["prozent"] * w_sprache) / summe
    return {
        "prozent": round(prozent, 1),
        "notenpunkte": prozent_zu_notenpunkte(prozent),
        "gewichtung_inhalt": w_inhalt / summe,
        "gewichtung_sprache": w_sprache / summe,
    }


def erstelle_gutachten(horizont, inhalt, sprache, gesamt, schueler_name=""):
    z = []
    z.append("GUTACHTEN" + (f" – {schueler_name}" if schueler_name else ""))
    z.append(f"Klausur: {horizont.get('titel', 'ohne Titel')}")
    z.append("")

    z.append("Sprachliche Leistung")
    z.append("-" * 60)
    z.append(f"Umfang: {sprache['wortzahl']} Wörter. "
             f"LanguageTool meldet {sprache['fehler_gesamt']} Auffälligkeiten "
             f"(gewichtet {sprache['fehler_gewichtet']}), das entspricht "
             f"{sprache['dichte_pro_100']} gewichteten Fehlern je 100 Wörter.")
    d = sprache["dichte_pro_100"]
    if d <= 1:
        urteil = ("Der Text ist sprachlich weitgehend korrekt und flüssig; "
                  "Verstöße bleiben Einzelfälle und beeinträchtigen die "
                  "Verständlichkeit nicht.")
    elif d <= 2.5:
        urteil = ("Der Text ist überwiegend korrekt; wiederkehrende, aber "
                  "nicht sinnentstellende Verstöße sollten in der Überarbeitung "
                  "adressiert werden.")
    elif d <= 4.5:
        urteil = ("Die Fehlerdichte ist deutlich erhöht; Grammatik- und "
                  "Rechtschreibverstöße beeinträchtigen stellenweise den "
                  "Lesefluss.")
    else:
        urteil = ("Die hohe Fehlerdichte beeinträchtigt Verständlichkeit und "
                  "Darstellungsleistung erheblich.")
    z.append(urteil)
    z.append(f"Sprachliche Leistung: {sprache['prozent']} % → "
             f"{sprache['notenpunkte']} Punkte "
             f"({NOTEN_TEXT[sprache['notenpunkte']]}).")
    z.append("")

    z.append("Inhaltliche Leistung")
    z.append("-" * 60)
    for a in inhalt["aufgaben"]:
        z.append(f"Aufgabe {a['nummer']} – {a['titel']}: "
                 f"{a['erreicht']}/{a['max_punkte']} Punkte ({a['prozent']} %).")
        getroffen = [d_ for d_ in a["details"] if d_["punkte_erreicht"] >= d_["punkte_max"] * 0.999]
        teilweise = [d_ for d_ in a["details"]
                     if 0 < d_["punkte_erreicht"] < d_["punkte_max"] * 0.999]
        fehlend = [d_ for d_ in a["details"] if d_["punkte_erreicht"] == 0]
        if getroffen:
            z.append("  Erfüllt: " + "; ".join(d_["beschreibung"] for d_ in getroffen))
        if teilweise:
            z.append("  Teilweise erfüllt: " + "; ".join(d_["beschreibung"] for d_ in teilweise))
        if fehlend:
            z.append("  Nicht nachgewiesen: " + "; ".join(d_["beschreibung"] for d_ in fehlend))
    z.append(f"Inhaltliche Leistung gesamt: {inhalt['erreicht']}/{inhalt['max_punkte']} "
             f"Punkte = {inhalt['prozent']} % → {inhalt['notenpunkte']} Punkte "
             f"({NOTEN_TEXT[inhalt['notenpunkte']]}).")
    z.append("")

    z.append("Gesamtergebnis")
    z.append("-" * 60)
    z.append(f"Gewichtung: Inhalt {gesamt['gewichtung_inhalt']:.0%}, "
             f"sprachliche Leistung {gesamt['gewichtung_sprache']:.0%}.")
    z.append(f"Gesamt: {gesamt['prozent']} % → Notenvorschlag: "
             f"{gesamt['notenpunkte']} Punkte ({NOTEN_TEXT[gesamt['notenpunkte']]}).")
    z.append("")
    z.append("Hinweis: Automatisch erstellter Vorschlag. Die inhaltliche Prüfung "
             "beruht auf Schlüsselwort-Abgleich und kann Umschreibungen oder "
             "eigenständige Argumentationen nur begrenzt erkennen – bitte vor "
             "der Notenvergabe fachlich prüfen.")
    return "\n".join(z)


# ----------------------------------------------------------------------------
# Grafische Oberflaeche
# ----------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITEL)
        self.geometry("1100x750")
        self.minsize(900, 600)

        self.horizont = None
        self.horizont_pfad = None
        self.ergebnis = None  # (fehlerliste, sprache, inhalt, gesamt, gutachten)
        self._queue = queue.Queue()

        self._baue_oberflaeche()
        self.after(100, self._verarbeite_queue)

    # ---------------- Aufbau ----------------

    def _baue_oberflaeche(self):
        leiste = ttk.Frame(self, padding=8)
        leiste.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(leiste, text="1. Erwartungshorizont laden…",
                   command=self.lade_horizont).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(leiste, text="2. Schülertext laden…",
                   command=self.lade_schuelertext).pack(side=tk.LEFT, padx=6)
        self.knopf_pruefen = ttk.Button(leiste, text="3. Prüfung starten",
                                        command=self.starte_pruefung)
        self.knopf_pruefen.pack(side=tk.LEFT, padx=6)
        ttk.Button(leiste, text="Bericht exportieren…",
                   command=self.exportiere_bericht).pack(side=tk.LEFT, padx=6)

        ttk.Label(leiste, text="Sprache:").pack(side=tk.LEFT, padx=(18, 4))
        self.sprach_wahl = ttk.Combobox(leiste, width=7, state="readonly",
                                        values=["en-GB", "en-US"])
        self.sprach_wahl.set("en-GB")
        self.sprach_wahl.pack(side=tk.LEFT)

        ttk.Label(leiste, text="Name:").pack(side=tk.LEFT, padx=(18, 4))
        self.name_feld = ttk.Entry(leiste, width=20)
        self.name_feld.pack(side=tk.LEFT)

        self.info_horizont = ttk.Label(self, padding=(10, 0),
                                       text="Kein Erwartungshorizont geladen.")
        self.info_horizont.pack(side=tk.TOP, anchor=tk.W)

        self.mappe = ttk.Notebook(self)
        self.mappe.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.text_schueler = self._neuer_texttab("Schülertext", schreibbar=True)
        self.text_korrekturen = self._neuer_texttab("Korrekturen")
        self.text_sprache = self._neuer_texttab("Sprachliche Bewertung")
        self.text_inhalt = self._neuer_texttab("Inhaltliche Bewertung")
        self.text_gutachten = self._neuer_texttab("Gesamtgutachten")

        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W, padding=4,
                                text="Bereit. Erwartungshorizont und Schülertext "
                                     "laden, dann Prüfung starten.")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def _neuer_texttab(self, titel, schreibbar=False):
        rahmen = ttk.Frame(self.mappe)
        self.mappe.add(rahmen, text=titel)
        text = tk.Text(rahmen, wrap=tk.WORD, font=("Segoe UI", 11), undo=True)
        rollbalken = ttk.Scrollbar(rahmen, command=text.yview)
        text.configure(yscrollcommand=rollbalken.set)
        rollbalken.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(fill=tk.BOTH, expand=True)
        if not schreibbar:
            text.configure(state=tk.DISABLED)
        return text

    def _setze_text(self, widget, inhalt):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", inhalt)
        if widget is not self.text_schueler:
            widget.configure(state=tk.DISABLED)

    # ---------------- Aktionen ----------------

    def lade_horizont(self):
        pfad = filedialog.askopenfilename(
            title="Erwartungshorizont (JSON) wählen",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")])
        if not pfad:
            return
        try:
            with open(pfad, encoding="utf-8") as datei:
                horizont = json.load(datei)
            aufgaben = horizont.get("aufgaben")
            if not isinstance(aufgaben, list) or not aufgaben:
                raise ValueError("Die Datei enthält keine Liste 'aufgaben'.")
        except Exception as fehler:
            messagebox.showerror("Fehler beim Laden",
                                 f"Erwartungshorizont konnte nicht gelesen "
                                 f"werden:\n{fehler}")
            return
        self.horizont = horizont
        self.horizont_pfad = pfad
        if horizont.get("sprache") in ("en-GB", "en-US"):
            self.sprach_wahl.set(horizont["sprache"])
        anzahl = len(horizont["aufgaben"])
        maxp = sum(float(a.get("max_punkte", 0)) for a in horizont["aufgaben"])
        self.info_horizont.configure(
            text=f"Erwartungshorizont: „{horizont.get('titel', pfad)}“ – "
                 f"{anzahl} Aufgabe(n), {maxp:g} inhaltliche Punkte "
                 f"(Optimum = 15 Notenpunkte).")
        self.status.configure(text="Erwartungshorizont geladen.")

    def lade_schuelertext(self):
        pfad = filedialog.askopenfilename(
            title="Schülertext wählen",
            filetypes=[("Text/Word", "*.txt *.md *.docx"), ("Alle Dateien", "*.*")])
        if not pfad:
            return
        try:
            if pfad.lower().endswith(".docx"):
                inhalt = self._lese_docx(pfad)
            else:
                with open(pfad, encoding="utf-8", errors="replace") as datei:
                    inhalt = datei.read()
        except Exception as fehler:
            messagebox.showerror("Fehler beim Laden",
                                 f"Datei konnte nicht gelesen werden:\n{fehler}")
            return
        self._setze_text(self.text_schueler, inhalt)
        self.mappe.select(0)
        self.status.configure(
            text=f"Schülertext geladen ({woerter_zaehlen(inhalt)} Wörter). "
                 f"Der Text kann im Reiter „Schülertext“ bearbeitet werden.")

    def _lese_docx(self, pfad):
        try:
            import docx  # optional: python-docx
        except ImportError:
            raise RuntimeError(
                "Zum Einlesen von .docx bitte einmalig installieren:\n"
                "pip install python-docx\n"
                "Alternativ den Text als .txt speichern.")
        dokument = docx.Document(pfad)
        return "\n".join(absatz.text for absatz in dokument.paragraphs)

    def starte_pruefung(self):
        if not self.horizont:
            messagebox.showwarning("Erwartungshorizont fehlt",
                                   "Bitte zuerst den Erwartungshorizont (JSON) "
                                   "laden – er ist der Maßstab für 15 Punkte.")
            return
        text = self.text_schueler.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Kein Text",
                                   "Bitte zuerst einen Schülertext laden oder "
                                   "in den Reiter „Schülertext“ einfügen.")
            return
        self.knopf_pruefen.configure(state=tk.DISABLED)
        self.status.configure(text="Prüfung läuft … (Grammatik/Rechtschreibung "
                                   "über LanguageTool, danach Inhaltsabgleich)")
        threading.Thread(target=self._pruefe_im_hintergrund,
                         args=(text, self.sprach_wahl.get()),
                         daemon=True).start()

    def _pruefe_im_hintergrund(self, text, sprache):
        try:
            pruefer = SprachPruefung(sprache)
            fehlerliste = pruefer.pruefe(text)
            einstellungen = (self.horizont.get("sprachbewertung") or {})
            abzug = float(einstellungen.get("abzug_pro_fehler_pro_100_woerter", 10))
            sprach_erg = sprachliche_bewertung(fehlerliste, woerter_zaehlen(text), abzug)
            inhalt_erg = inhaltliche_bewertung(self.horizont, text)
            gesamt = gesamtnote(inhalt_erg, sprach_erg,
                                self.horizont.get("gewichtung") or {})
            gutachten = erstelle_gutachten(self.horizont, inhalt_erg, sprach_erg,
                                           gesamt, self.name_feld.get().strip())
            self._queue.put(("fertig", (fehlerliste, sprach_erg, inhalt_erg,
                                        gesamt, gutachten)))
        except Exception as fehler:
            self._queue.put(("fehler", str(fehler)))

    def _verarbeite_queue(self):
        try:
            while True:
                art, daten = self._queue.get_nowait()
                if art == "fertig":
                    self._zeige_ergebnis(*daten)
                else:
                    self.knopf_pruefen.configure(state=tk.NORMAL)
                    self.status.configure(text="Prüfung fehlgeschlagen.")
                    messagebox.showerror(
                        "Prüfung fehlgeschlagen",
                        f"{daten}\n\nHinweise:\n"
                        f"– Für die Online-Prüfung wird eine Internetverbindung "
                        f"benötigt (kostenlose LanguageTool-API).\n"
                        f"– Alternativ einmalig installieren: "
                        f"pip install language_tool_python (benötigt Java).")
        except queue.Empty:
            pass
        self.after(100, self._verarbeite_queue)

    # ---------------- Darstellung ----------------

    def _zeige_ergebnis(self, fehlerliste, sprach_erg, inhalt_erg, gesamt, gutachten):
        self.ergebnis = (fehlerliste, sprach_erg, inhalt_erg, gesamt, gutachten)

        self._setze_text(self.text_korrekturen, self._format_korrekturen(fehlerliste))
        self._setze_text(self.text_sprache, self._format_sprache(sprach_erg, fehlerliste))
        self._setze_text(self.text_inhalt, self._format_inhalt(inhalt_erg))
        self._setze_text(self.text_gutachten, gutachten)

        self.knopf_pruefen.configure(state=tk.NORMAL)
        self.mappe.select(4)
        self.status.configure(
            text=f"Fertig: Inhalt {inhalt_erg['notenpunkte']} P, Sprache "
                 f"{sprach_erg['notenpunkte']} P, Gesamtvorschlag "
                 f"{gesamt['notenpunkte']} Punkte.")

    def _format_korrekturen(self, fehlerliste):
        if not fehlerliste:
            return "Keine Auffälligkeiten gefunden – sehr gut!"
        zeilen = [f"{len(fehlerliste)} Korrekturhinweise "
                  f"(Reihenfolge wie im Text):", ""]
        for nr, f in enumerate(fehlerliste, 1):
            zeilen.append(f"{nr}. [{f['kategorie']}] „{f['text']}“")
            zeilen.append(f"   Kontext: …{f['kontext']}…")
            zeilen.append(f"   Hinweis: {f['meldung']}")
            if f["vorschlaege"]:
                zeilen.append("   Vorschlag: " + ", ".join(f["vorschlaege"]))
            zeilen.append("")
        return "\n".join(zeilen)

    def _format_sprache(self, s, fehlerliste):
        pro_kategorie = {}
        for f in fehlerliste:
            pro_kategorie[f["kategorie"]] = pro_kategorie.get(f["kategorie"], 0) + 1
        zeilen = [
            "SPRACHLICHE BEWERTUNG",
            "=" * 60,
            f"Wortzahl:                  {s['wortzahl']}",
            f"Auffälligkeiten gesamt:    {s['fehler_gesamt']}",
            f"Gewichtete Fehler:         {s['fehler_gewichtet']}",
            f"Fehlerdichte je 100 Wörter: {s['dichte_pro_100']}",
            "",
            "Nach Kategorie:",
        ]
        for kategorie, anzahl in sorted(pro_kategorie.items(),
                                        key=lambda p: -p[1]):
            zeilen.append(f"  {kategorie}: {anzahl}")
        zeilen += [
            "",
            f"Ergebnis: {s['prozent']} % → {s['notenpunkte']} Notenpunkte "
            f"({NOTEN_TEXT[s['notenpunkte']]})",
            "",
            "Berechnung: 100 % minus (gewichtete Fehler je 100 Wörter × Abzug).",
            "Der Abzug ist im Erwartungshorizont einstellbar "
            "(\"sprachbewertung\": {\"abzug_pro_fehler_pro_100_woerter\": 10}).",
        ]
        return "\n".join(zeilen)

    def _format_inhalt(self, inhalt):
        zeilen = ["INHALTLICHE BEWERTUNG (Abgleich mit dem Erwartungshorizont)",
                  "=" * 60, ""]
        for a in inhalt["aufgaben"]:
            zeilen.append(f"Aufgabe {a['nummer']}: {a['titel']}")
            zeilen.append(f"  Punkte: {a['erreicht']} / {a['max_punkte']} "
                          f"({a['prozent']} %)")
            for d in a["details"]:
                if d["punkte_erreicht"] >= d["punkte_max"] * 0.999:
                    symbol = "[voll]   "
                elif d["punkte_erreicht"] > 0:
                    symbol = "[teilw.] "
                else:
                    symbol = "[fehlt]  "
                zeilen.append(f"  {symbol}{d['beschreibung']} "
                              f"({d['punkte_erreicht']}/{d['punkte_max']} P)")
                if d["gefunden"]:
                    zeilen.append("           gefunden: " + ", ".join(d["gefunden"]))
                if d["fehlend"] and d["punkte_erreicht"] < d["punkte_max"] * 0.999:
                    zeilen.append("           nicht gefunden: " + ", ".join(d["fehlend"]))
            zeilen.append("")
        zeilen.append(f"Gesamt: {inhalt['erreicht']} / {inhalt['max_punkte']} Punkte "
                      f"= {inhalt['prozent']} % → {inhalt['notenpunkte']} "
                      f"Notenpunkte ({NOTEN_TEXT[inhalt['notenpunkte']]})")
        return "\n".join(zeilen)

    # ---------------- Export ----------------

    def exportiere_bericht(self):
        if not self.ergebnis:
            messagebox.showwarning("Kein Ergebnis",
                                   "Bitte zuerst eine Prüfung durchführen.")
            return
        fehlerliste, sprach_erg, inhalt_erg, gesamt, gutachten = self.ergebnis
        name = self.name_feld.get().strip() or "Bericht"
        pfad = filedialog.asksaveasfilename(
            title="Bericht speichern",
            defaultextension=".txt",
            initialfile=f"Klausurbewertung_{name}.txt".replace(" ", "_"),
            filetypes=[("Textdatei", "*.txt")])
        if not pfad:
            return
        trennung = "\n\n" + "=" * 70 + "\n\n"
        bericht = trennung.join([
            gutachten,
            self._format_inhalt(inhalt_erg),
            self._format_sprache(sprach_erg, fehlerliste),
            self._format_korrekturen(fehlerliste),
        ])
        with open(pfad, "w", encoding="utf-8") as datei:
            datei.write(bericht)
        self.status.configure(text=f"Bericht gespeichert: {pfad}")


if __name__ == "__main__":
    App().mainloop()
