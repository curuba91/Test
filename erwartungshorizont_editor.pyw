#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Erwartungshorizont-Editor
=========================

Hilfstool zum Programm "Klausur-Bewertung Englisch": Die Lehrkraft kopiert
ihren Erwartungshorizont als einfachen Text in das linke Feld, das Tool
wandelt ihn in die JSON-Struktur um, die klausur_bewertung.pyw einliest.
Anschließend lässt sich alles bequem nachbearbeiten (Punkte,
Schlüsselwörter, Mindest-Treffer) und als .json speichern.

Erkanntes Textformat (tolerant):

    Aufgabe 1: Comprehension – Summarize the text
    - Nennt die zentrale These (4 P) [interconnected, global trade]
    - Benennt wirtschaftliche Aspekte (4 P, min. 2) [outsourcing, multinational]

    Aufgabe 2: Analysis ...
    ...

* "Aufgabe 1:", "Task 1)", "1." am Zeilenanfang beginnt eine neue Aufgabe.
* Zeilen mit "-", "•", "*" (oder normale Zeilen unter einer Aufgabe) werden
  Erwartungen.
* "(4 P)", "(4 BE)", "4 Punkte" → Punktzahl der Erwartung.
* "[wort1, wort2]" oder "Schlüsselwörter: wort1, wort2" → Schlüsselwörter.
* "min. 2" / "mindestens 2" → nötige Trefferzahl für volle Punkte.

Schlüsselwörter sind die ENGLISCHEN Begriffe/Synonyme, die im Schülertext
gesucht werden – je mehr Varianten, desto fairer der Abgleich.

Der Erwartungshorizont kann wahlweise als Text eingefügt ODER als PDF
geladen werden ("PDF laden…"). Beim PDF wird in dieser Reihenfolge
vorgegangen:

1. Tabellarischer Bewertungsbogen ("Teilaufgabe 1: Comprehension",
   Punktespalte "max.", "Total"-Zeile): Die Tabelle wird ausgewertet,
   mehrere Punktwerte einer Zelle werden ihren Stichpunkten zugeordnet,
   Gruppenüberschriften werden den Unterpunkten vorangestellt.
2. Sonstige PDFs (z. B. das Klausurblatt mit "1. Outline … (30 BE)"):
   Fließtext-Auswertung; Material-/Operatorenteile werden abgeschnitten.
3. Gescannte Bögen ohne Textebene: Handschrifterkennung aus
   klausur_bewertung.pyw (beide Dateien im selben Ordner, easyocr nötig).

Formuliert der Bogen die Erwartungen als ganze Sätze (der Normalfall),
werden daraus Schlüsselwörter VORGESCHLAGEN (im Baum mit ◆ markiert) -
diese sind zu prüfen. Kriterien zu Aufbau, Darstellung und Zitierweise
werden als "manuell zu bewerten" markiert (✎), weil sie sich inhaltlich
nicht automatisch prüfen lassen.

Start: Doppelklick (Windows: .pyw ohne Konsolenfenster). Benötigt nur
Python 3.8+ mit Tkinter; für PDF: pip install pymupdf.
"""

import importlib
import importlib.machinery
import importlib.util
import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITEL = "Erwartungshorizont-Editor (Klausur-Bewertung Englisch)"


# ----------------------------------------------------------------------------
# Automatische Installation fehlender Komponenten
# ----------------------------------------------------------------------------

class FehlendePakete(RuntimeError):
    """Signalisiert fehlende, per pip nachinstallierbare Komponenten."""

    def __init__(self, pip_namen, zweck):
        super().__init__(f"Für {zweck} fehlen folgende Komponenten: "
                         + ", ".join(pip_namen))
        self.pip_namen = list(pip_namen)
        self.zweck = zweck


class InstallationsDialog(tk.Toplevel):
    """Installiert Pakete mit dem pip des laufenden Python und zeigt den
    Fortschritt an. Ruft danach fertig(erfolg) im GUI-Thread auf."""

    def __init__(self, parent, pip_namen, zweck, fertig):
        super().__init__(parent)
        self.title("Komponenten werden installiert …")
        self.geometry("680x420")
        self.transient(parent)
        self.grab_set()
        self._fertig = fertig
        self._pakete = list(pip_namen)
        self._queue = queue.Queue()

        ttk.Label(self, padding=8, wraplength=650, justify=tk.LEFT,
                  text=f"Für {zweck} werden folgende kostenlose Komponenten "
                       f"installiert:\n{', '.join(pip_namen)}\n"
                       f"Dies geschieht nur einmal und kann – je nach Paket – "
                       f"einige Minuten dauern. Bitte Fenster geöffnet "
                       f"lassen.").pack(anchor=tk.W)
        rahmen = ttk.Frame(self, padding=(8, 0, 8, 0))
        rahmen.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(rahmen, wrap=tk.WORD, font=("Consolas", 9),
                           state=tk.DISABLED, height=14)
        rollbalken = ttk.Scrollbar(rahmen, command=self.log.yview)
        self.log.configure(yscrollcommand=rollbalken.set)
        rollbalken.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.pack(fill=tk.BOTH, expand=True)
        self.knopf = ttk.Button(self, text="Bitte warten …",
                                state=tk.DISABLED, command=self.destroy)
        self.knopf.pack(pady=8)
        self.protocol("WM_DELETE_WINDOW", self._schliessen_versuch)

        self._laeuft = True
        threading.Thread(target=self._installiere, args=(list(pip_namen),),
                         daemon=True).start()
        self.after(100, self._poll)

    def _schliessen_versuch(self):
        if not self._laeuft:
            self.destroy()

    def _installiere(self, pakete):
        for zusatz in ([], ["--user"]):
            befehl = [sys.executable, "-m", "pip", "install",
                      "--upgrade"] + zusatz + pakete
            self._queue.put(("zeile", "> " + " ".join(befehl)))
            try:
                flags = (subprocess.CREATE_NO_WINDOW
                         if os.name == "nt" else 0)
                prozess = subprocess.Popen(
                    befehl, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True,
                    encoding="utf-8", errors="replace",
                    creationflags=flags)
                for zeile in prozess.stdout:
                    self._queue.put(("zeile", zeile.rstrip()))
                if prozess.wait() == 0:
                    self._queue.put(("ende", True))
                    return
                self._queue.put(("zeile", "Installation fehlgeschlagen – "
                                          "versuche Alternative …"))
            except Exception as fehler:
                self._queue.put(("zeile", f"Fehler: {fehler}"))
        self._queue.put(("ende", False))

    def _poll(self):
        try:
            while True:
                art, daten = self._queue.get_nowait()
                if art == "zeile":
                    self.log.configure(state=tk.NORMAL)
                    self.log.insert(tk.END, daten + "\n")
                    self.log.see(tk.END)
                    self.log.configure(state=tk.DISABLED)
                else:
                    self._laeuft = False
                    importlib.invalidate_caches()
                    if daten:
                        self._fertig(True)
                        self.destroy()
                        return
                    self.title("Installation fehlgeschlagen")
                    self.log.configure(state=tk.NORMAL)
                    self.log.insert(
                        tk.END,
                        "\nDie automatische Installation hat nicht "
                        "geklappt.\nBitte manuell in einer "
                        "Eingabeaufforderung ausführen:\n"
                        "pip install " + " ".join(self._pakete) + "\n"
                        "und das Programm danach neu starten.\n")
                    self.log.configure(state=tk.DISABLED)
                    self.knopf.configure(state=tk.NORMAL, text="Schließen")
                    self._fertig(False)
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll)


def biete_installation_an(parent, fehler, wiederholen, status_setzen=None):
    """Fragt nach, installiert und wiederholt danach die Aktion.
    fehler braucht die Attribute pip_namen und zweck."""
    if messagebox.askyesno(
            "Komponente installieren?",
            f"Für {fehler.zweck} fehlen folgende kostenlose Komponenten:\n\n"
            f"    {'  '.join(fehler.pip_namen)}\n\n"
            f"Jetzt automatisch installieren?\n"
            f"(einmalig, benötigt Internet; danach wird der Vorgang "
            f"automatisch fortgesetzt)", parent=parent):
        InstallationsDialog(
            parent, fehler.pip_namen, fehler.zweck,
            lambda erfolg: erfolg and parent.after(100, wiederholen))
    elif status_setzen:
        status_setzen("Installation abgelehnt – Vorgang abgebrochen.")

AUFGABE_MUSTER = re.compile(
    r"^\s*(?:Teilaufgabe|Aufgabe|Task|Exercise)\s*(\d+[a-z]?)\s*[.:)–-]?\s*(.*)$",
    re.IGNORECASE)
AUFGABE_NUMMER_MUSTER = re.compile(r"^\s*(\d+[a-z]?)\s*[.)]\s+(.{10,})$")
PUNKTE_MUSTER = re.compile(
    r"\(?\s*(\d+(?:[.,]\d+)?)\s*(?:P\b|BE\b|Punkte?\b|Pkt\.?)\s*\)?",
    re.IGNORECASE)
# Zeile, die NUR eine Punktangabe enthaelt - z.B. "(30 BE)" unter der Aufgabe
NUR_PUNKTE_MUSTER = re.compile(
    r"^\s*\(?\s*(\d+(?:[.,]\d+)?)\s*(?:P|BE|Punkte?|Pkt\.?)?\s*\)?\s*$",
    re.IGNORECASE)
# "Total 30", "Total: 30", "Summe 30", "Gesamt 30"
TOTAL_MUSTER = re.compile(
    r"^\s*(?:Total|Summe|Gesamt|Zwischensumme)\s*:?\s*"
    r"(\d+(?:[.,]\d+)?)?\s*$", re.IGNORECASE)
MINDESTENS_MUSTER = re.compile(
    r"(?:min\.?|mindestens)\s*(\d+)", re.IGNORECASE)
KLAMMER_WOERTER_MUSTER = re.compile(r"\[([^\]]+)\]")
SCHLUESSEL_MUSTER = re.compile(
    r"(?:Schlüsselwörter|Schluesselwoerter|Keywords?)\s*[:=]\s*(.+)$",
    re.IGNORECASE)
# Aufzaehlungszeichen inkl. Word-Symbolzeichen (Wingdings) und "o"-Unterpunkte
BULLET_ZEICHEN = "•▪‣·◦●○*-–—"
AUFZAEHLUNG_MUSTER = re.compile(
    r"^\s*(?:[" + re.escape(BULLET_ZEICHEN) + r"]|o(?=\s))\s*")
# Zeilen aus Bewertungsbögen, die keine Erwartung sind
JUNK_MUSTER = re.compile(
    r"^\s*(?:max\.?|erreicht|Punkte|BE|Note|Bewertungsraster|Bewertungsbogen|"
    r"I{1,3}\.?\s*(?:INHALT|SPRACHE|DARSTELLUNG)|INHALT|"
    r"Summe\s+Inhalt|Notenpunkte.*|ENDNOTE|Seite\s*\d+|"
    r"Name\s*:?|Datum\s*:?|_{3,}|\d+\s*%)\s*$", re.IGNORECASE)
# Ab hier ist in einer Klausur-PDF nur noch Material/Anhang - nicht parsen
ABSCHNITT_ENDE_MUSTER = re.compile(
    r"^\s*(?:Operatoren\b|Material\s*:|Materialien\s*:|Anlage\b|Anhang\b|"
    r"Viel\s+Erfolg|Hilfsmittel\b|Annotations?\b|Quellen?\b)", re.IGNORECASE)


def parse_erwartungshorizont(text, titel="", auto_schluesselwoerter=True):
    """Wandelt frei formatierten Text in die JSON-Struktur um.

    Erkennt sowohl handgeschriebene Listen ("Aufgabe 1: …" + Spiegelstriche)
    als auch die aus PDF-Bewertungsbögen normalisierte Form
    ("Teilaufgabe 1: Comprehension", Erwartungen mit "(5 P)", "Total 30").
    Fehlen Schlüsselwörter, werden sie aus dem Beschreibungstext
    vorgeschlagen (auto_schluesselwoerter)."""
    aufgaben = []
    aktuelle = None
    letzte_erwartung = None
    titel_offen = False   # Aufgabentitel geht ueber mehrere Zeilen (Klausur-PDF)

    for roh in text.splitlines():
        zeile = roh.strip()
        if not zeile:
            titel_offen = False
            continue
        if ABSCHNITT_ENDE_MUSTER.match(zeile):
            break
        if JUNK_MUSTER.match(zeile):
            continue

        # "Total 30" -> Maximalpunktzahl der laufenden Aufgabe
        total = TOTAL_MUSTER.match(zeile)
        if total and aktuelle is not None:
            if total.group(1):
                aktuelle["max_punkte"] = float(total.group(1).replace(",", "."))
                aktuelle["_total_gesetzt"] = True
            continue

        # Zeile, die nur eine Punktzahl enthaelt: gehoert zur letzten Aufgabe
        # (Klausur-PDF: "1. Outline …" / "(30 BE)") oder zur letzten Erwartung
        nur_punkte = NUR_PUNKTE_MUSTER.match(zeile)
        if nur_punkte and (aktuelle is not None or letzte_erwartung is not None):
            wert = float(nur_punkte.group(1).replace(",", "."))
            if aktuelle is not None and not aktuelle["erwartungen"]:
                aktuelle["max_punkte"] = wert
                aktuelle["_total_gesetzt"] = True
            elif letzte_erwartung is not None:
                letzte_erwartung["punkte"] = wert
            continue

        ist_aufzaehlung = bool(AUFZAEHLUNG_MUSTER.match(roh))
        treffer = AUFGABE_MUSTER.match(zeile)
        if not treffer and not ist_aufzaehlung:
            treffer = AUFGABE_NUMMER_MUSTER.match(zeile)
        if treffer:
            aktuelle = {
                "nummer": treffer.group(1),
                "titel": (treffer.group(2).strip()
                          or f"Aufgabe {treffer.group(1)}"),
                "max_punkte": 0.0,
                "erwartungen": [],
            }
            # Punktangabe direkt im Aufgabentitel ("… (30 BE)")
            punkte_im_titel = PUNKTE_MUSTER.search(aktuelle["titel"])
            if punkte_im_titel:
                aktuelle["max_punkte"] = float(
                    punkte_im_titel.group(1).replace(",", "."))
                aktuelle["_total_gesetzt"] = True
                aktuelle["titel"] = PUNKTE_MUSTER.sub(
                    "", aktuelle["titel"], count=1).strip(" .,;()")
            aufgaben.append(aktuelle)
            letzte_erwartung = None
            titel_offen = True
            continue

        if aktuelle is None:
            if not titel:
                titel = zeile
            continue

        # Fortsetzung eines mehrzeiligen Aufgabentitels (Klausur-PDF):
        # solange noch keine Erwartung erfasst ist und die Zeile keine
        # Aufzaehlung ist.
        if titel_offen and not ist_aufzaehlung and not aktuelle["erwartungen"]:
            aktuelle["titel"] = (aktuelle["titel"] + " " + zeile).strip()
            punkte_im_titel = PUNKTE_MUSTER.search(aktuelle["titel"])
            if punkte_im_titel:
                aktuelle["max_punkte"] = float(
                    punkte_im_titel.group(1).replace(",", "."))
                aktuelle["_total_gesetzt"] = True
                aktuelle["titel"] = PUNKTE_MUSTER.sub(
                    "", aktuelle["titel"], count=1).strip(" .,;()")
            continue

        titel_offen = False
        erwartung = _parse_erwartung(zeile, auto_schluesselwoerter)
        if erwartung["beschreibung"]:
            aktuelle["erwartungen"].append(erwartung)
            letzte_erwartung = erwartung

    for aufgabe in aufgaben:
        summe = sum(e["punkte"] for e in aufgabe["erwartungen"])
        if not aufgabe.pop("_total_gesetzt", False):
            aufgabe["max_punkte"] = summe if summe > 0 else float(
                max(1, len(aufgabe["erwartungen"])) * 2)

    return {
        "titel": titel or "Klausur",
        "sprache": "en-GB",
        "gewichtung": {"inhalt": 0.4, "sprache": 0.6},
        "aufgaben": aufgaben,
    }


def _parse_erwartung(zeile, auto_schluesselwoerter=True):
    rest = AUFZAEHLUNG_MUSTER.sub("", zeile).strip()

    schluesselwoerter = []
    automatisch = False
    klammern = KLAMMER_WOERTER_MUSTER.search(rest)
    if klammern:
        schluesselwoerter = [w.strip() for w in klammern.group(1).split(",")
                             if w.strip()]
        rest = KLAMMER_WOERTER_MUSTER.sub("", rest).strip()
    else:
        benannt = SCHLUESSEL_MUSTER.search(rest)
        if benannt:
            schluesselwoerter = [w.strip() for w in
                                 benannt.group(1).split(",") if w.strip()]
            rest = SCHLUESSEL_MUSTER.sub("", rest).strip()

    punkte = 2.0
    punkte_treffer = PUNKTE_MUSTER.search(rest)
    if punkte_treffer:
        punkte = float(punkte_treffer.group(1).replace(",", "."))
        rest = PUNKTE_MUSTER.sub("", rest, count=1).strip()

    mindestens = 1
    mind_treffer = MINDESTENS_MUSTER.search(rest)
    if mind_treffer:
        mindestens = int(mind_treffer.group(1))
        rest = MINDESTENS_MUSTER.sub("", rest).strip()

    rest = re.sub(r"\s*[(),;]\s*$", "", rest).strip()
    rest = re.sub(r"\(\s*\)", "", rest).strip()

    if not schluesselwoerter and auto_schluesselwoerter:
        schluesselwoerter = schluesselwoerter_vorschlagen(rest)
        automatisch = bool(schluesselwoerter)
        if automatisch and not mind_treffer:
            mindestens = max(1, min(3, round(len(schluesselwoerter) / 3.0)))

    return {
        "beschreibung": rest,
        "punkte": punkte,
        "schluesselwoerter": schluesselwoerter,
        "mindestens": mindestens,
        "auto": automatisch,
        "manuell": ist_formales_kriterium(rest),
    }


# Kriterien zu Aufbau, Darstellung und Zitierweise lassen sich nicht über
# Inhaltsbegriffe prüfen - sie werden markiert und von der Lehrkraft vergeben.
FORMAL_MUSTER = re.compile(
    r"well[- ]structured|logically connected|coherent|structure of the text|"
    r"formal tone|register|own words|paraphras|omission of quotes|"
    r"quotations? are|cited|citation|introduction and conclusion|"
    r"Aufbau|gegliedert|strukturiert|kohärent|Zitat|zitiert|eigene[nrm]? Worte|"
    r"Darstellungsleistung|sprachliche Leistung|Umfang der Arbeit",
    re.IGNORECASE)


def ist_formales_kriterium(beschreibung):
    """True, wenn die Erwartung Aufbau/Darstellung statt Inhalt betrifft."""
    return bool(FORMAL_MUSTER.search(beschreibung or ""))


# ----------------------------------------------------------------------------
# Automatische Schluesselwort-Vorschlaege aus Fließtext-Erwartungen
# ----------------------------------------------------------------------------

STOPWOERTER = set("""
a an the and or but nor of in on at to for with by from as is are was were be
been being have has had do does did will would can could should may might must
shall this that these those it its they them their there here he she his her we
us our you your i me my not no so if then than when where which who whom whose
what how why all any some more most other others such own same also very too
just only even still well way ways make makes made get gets got take takes
taken use uses used using one two three first second third both each new like
into out up down over under about after before while during between through
e.g eg etc ie i.e para paras page pages line lines cf vgl
student students text texts author reader readers writer writing written
answer answers response responses task tasks exercise question questions
correctly correct mention mentions mentioned name names named identify
identifies identified following main given give gives given show shows shown
include includes including includes said says say seem seems seemed become
becomes becoming lead leads led lot lots
der die das dem den des und oder aber nicht ein eine einer eines einem einen
ist sind war waren wird werden wurde wurden hat haben hatte kann können soll
sollen muss müssen sich auch noch nur schon sehr mehr viel viele als wie von
mit für auf aus bei zum zur nach über unter durch gegen ohne dass wenn weil
nennt benennt beschreibt erläutert erklärt analysiert stellt dar zeigt geht
""".split())

# Quellenangaben und Verweise, die keine Inhaltsbegriffe sind
VERWEIS_MUSTER = re.compile(
    r"\((?:paras?\.|ll?\.|Z\.|vgl\.|cf\.|siehe|see)[^)]*\)|"
    r"\bparas?\.\s*[\d,\s–\-]+|\(Material\)|\(\s*\)", re.IGNORECASE)
ZITAT_MUSTER = re.compile(r"[“\"„]([^”\"“„]{4,60})[”\"“]")


def schluesselwoerter_vorschlagen(beschreibung, max_anzahl=8):
    """Schlägt Suchbegriffe aus einer Fließtext-Erwartung vor.

    Bewertungsbögen formulieren Erwartungen als ganze Sätze. Für den
    Abgleich mit dem Schülertext werden daraus die inhaltstragenden
    Begriffe gezogen: wörtliche Zitate, Eigennamen sowie aussagekräftige
    Wörter und Wortpaare. Die Vorschläge sind ein Startpunkt und von der
    Lehrkraft zu prüfen."""
    if not beschreibung or len(beschreibung) < 12:
        return []
    text = VERWEIS_MUSTER.sub(" ", beschreibung)

    kandidaten = []       # (gewicht, begriff)
    vergeben = set()

    def merken(begriff, gewicht):
        begriff = begriff.strip(" .,;:!?()[]\"'“”„-").lower()
        if (len(begriff) < 4 or begriff in vergeben
                or begriff in STOPWOERTER):
            return
        vergeben.add(begriff)
        kandidaten.append((gewicht, begriff))

    # 1. Wörtliche Zitate ("digital partner", "Personal AI Constitution")
    for zitat in ZITAT_MUSTER.findall(text):
        woerter = zitat.split()
        if 1 <= len(woerter) <= 5:
            merken(zitat, 100)
    text_ohne_zitate = ZITAT_MUSTER.sub(" ", text)

    # 2. Eigennamen (Parmy Olson, Bloomberg, Pandora's Box) - Großschreibung
    #    innerhalb des Satzes, nicht am Satzanfang
    for satz in re.split(r"(?<=[.!?;:])\s+|\n", text_ohne_zitate):
        woerter = satz.split()
        for pos, wort in enumerate(woerter):
            rein = wort.strip(" .,;:!?()[]\"'“”„")
            if pos > 0 and re.match(r"^[A-ZÄÖÜ][\wÄÖÜäöüß’'-]{2,}$", rein):
                folge = [rein]
                vorher = wort
                for weiter in woerter[pos + 1:pos + 3]:
                    # Satzzeichen am Vorgänger beendet den Eigennamen
                    if vorher.rstrip().endswith((",", ".", ";", ":", ")")):
                        break
                    nach = weiter.strip(" .,;:!?()[]\"'“”„")
                    if re.match(r"^[A-ZÄÖÜ][\wÄÖÜäöüß’'-]{2,}$", nach):
                        folge.append(nach)
                        vorher = weiter
                    else:
                        break
                merken(" ".join(folge), 90 + len(folge))

    # 3. Inhaltstragende Wortpaare und Einzelwörter
    for satz in re.split(r"[.;:!?]\s+|\n", text_ohne_zitate):
        woerter = re.findall(r"[A-Za-zÄÖÜäöüß][\wÄÖÜäöüß’'-]*", satz)
        klein = [w.lower() for w in woerter]
        inhalt = [(i, w) for i, w in enumerate(klein)
                  if w not in STOPWOERTER and len(w) >= 4]
        # Wortpaare aus direkt benachbarten Inhaltswörtern
        for (i1, w1), (i2, w2) in zip(inhalt, inhalt[1:]):
            if i2 == i1 + 1:
                merken(f"{w1} {w2}", 60 + min(len(w1) + len(w2), 24))
        for _i, wort in inhalt:
            merken(wort, 20 + min(len(wort), 14))

    kandidaten.sort(key=lambda p: (-p[0], p[1]))
    ausgewaehlt = []
    for _gewicht, begriff in kandidaten:
        # Begriffe überspringen, die schon in einem gewählten Wortpaar stecken
        if any(begriff in gewaehlt.split() or gewaehlt in begriff
               for gewaehlt in ausgewaehlt):
            continue
        ausgewaehlt.append(begriff)
        if len(ausgewaehlt) >= max_anzahl:
            break
    return ausgewaehlt


# ----------------------------------------------------------------------------
# Bewertungsbogen-PDF: tabellenbasiertes Einlesen
# ----------------------------------------------------------------------------

# Word-Symbolzeichen (Wingdings) fuer Aufzaehlungen aus PDF-Tabellen
SYMBOL_BULLETS = "\uf0b7\uf0a7\uf0d8\uf02c\uf00d"  # Wingdings/Symbol-Aufzählungszeichen aus Word-PDFs


def bogen_pdf_zu_text(pfad):
    """Wandelt einen tabellarischen Bewertungsbogen (PDF) in die
    normalisierte Textform um, die parse_erwartungshorizont versteht.

    Erkennt die typische Struktur hessischer Bewertungsraster:
    Kopfzeile "Teilaufgabe 1: Comprehension", Beschreibungsspalte,
    Punktespalte ("max.") und "Total"-Zeile. Mehrere Punktwerte in einer
    Zelle werden den Aufzählungspunkten der Zelle zugeordnet.

    Liefert (text, anzahl_aufgaben); anzahl_aufgaben = 0, wenn das PDF
    keine passende Tabelle enthält (dann Fließtext-Weg nutzen)."""
    import fitz  # PyMuPDF – Aufrufer hat Verfügbarkeit sichergestellt

    dokument = fitz.open(pfad)
    zeilen = []
    aufgaben_gefunden = 0
    aufgabe_offen = False
    try:
        # Ueberschrift des Bogens (steht ausserhalb der Tabellen)
        for kopfzeile in (dokument[0].get_text() or "").splitlines():
            kopfzeile = kopfzeile.strip()
            if len(kopfzeile) > 8 and not JUNK_MUSTER.match(kopfzeile):
                zeilen.append(kopfzeile)
                break
        for seite in dokument:
            for tabelle in seite.find_tables().tables:
                for reihe in tabelle.extract():
                    if not reihe:
                        continue
                    beschreibung = (reihe[0] or "").strip()
                    punkte_zelle = (reihe[1] or "").strip() if len(reihe) > 1 \
                        else ""
                    if not beschreibung and not punkte_zelle:
                        continue

                    kopf = AUFGABE_MUSTER.match(beschreibung)
                    if kopf:
                        zeilen.append("")
                        zeilen.append(f"Aufgabe {kopf.group(1)}: "
                                      f"{kopf.group(2).strip()}")
                        aufgaben_gefunden += 1
                        aufgabe_offen = True
                        continue
                    if not aufgabe_offen:
                        continue

                    if TOTAL_MUSTER.match(beschreibung):
                        werte = _punktwerte(punkte_zelle)
                        if werte:
                            zeilen.append(f"Total: {werte[0]:g}")
                        continue
                    if JUNK_MUSTER.match(beschreibung):
                        continue

                    werte = _punktwerte(punkte_zelle)
                    for teiltext, wert in _zelle_zerlegen(beschreibung, werte):
                        teiltext = _saubere_beschreibung(teiltext)
                        if len(teiltext) < 8:
                            continue
                        zeilen.append(f"- {teiltext} ({wert:g} P)"
                                      if wert else f"- {teiltext}")
    finally:
        dokument.close()
    return "\n".join(zeilen).strip(), aufgaben_gefunden


def _punktwerte(zelle):
    """Liest alle Punktzahlen einer Tabellenzelle ('5\\n5\\n5' -> [5,5,5])."""
    return [float(w.replace(",", "."))
            for w in re.findall(r"\d+(?:[.,]\d+)?", zelle or "")]


def _saubere_beschreibung(text):
    text = re.sub(r"[" + re.escape(SYMBOL_BULLETS) + r"]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .;:–-")


def _zelle_zerlegen(beschreibung, werte):
    """Ordnet die Punktwerte einer Zelle deren Aufzählungspunkten zu.

    Bewertungsbögen bündeln mehrere bepunktete Stichpunkte in einer Zelle.
    Auf welcher Ebene bepunktet wird (Hauptpunkte, Unterpunkte oder
    Absätze), unterscheidet sich je Zelle – daher wird die Gliederungsebene
    gewählt, deren Anzahl zu den Punktwerten passt."""
    text = beschreibung.replace("\r", "")
    ebenen = []
    for muster in (r"[" + re.escape(SYMBOL_BULLETS + "•▪‣") + r"]",
                   r"(?:^|\n)\s*o\s+",
                   r"\n\s*\n"):
        teile = [t.strip() for t in re.split(muster, text) if t.strip()]
        if len(teile) > 1:
            ebenen.append(teile)

    if not werte:
        return [(text, None)]
    if len(werte) == 1:
        return [(text, werte[0])]

    for teile in ebenen:
        if len(teile) == len(werte):
            return list(zip(teile, werte))
        # Ein Teil mehr als Punktwerte: die erste Zeile ist eine Überschrift
        # der Gruppe ("Negative impact", "Ways of manipulation …") und wird
        # nicht eigenständig bepunktet, sondern den Unterpunkten vorangestellt.
        if len(teile) == len(werte) + 1:
            kopf = _saubere_beschreibung(teile[0])
            return [((f"{kopf}: {rest}" if 0 < len(kopf) <= 80 else rest),
                     wert)
                    for rest, wert in zip(teile[1:], werte)]
    # Keine Ebene passt: gröbste Gliederung nehmen, Restpunkte anhängen
    teile = ebenen[0] if ebenen else [text]
    ergebnis = []
    for index, teiltext in enumerate(teile):
        if index < len(teile) - 1:
            ergebnis.append((teiltext, werte[index]
                             if index < len(werte) else None))
        else:
            rest = sum(werte[index:]) if index < len(werte) else None
            ergebnis.append((teiltext, rest))
    return ergebnis


def bogen_pdf_lesen(pfad, auto_schluesselwoerter=True):
    """Liest einen Bewertungsbogen (PDF) als Erwartungshorizont ein.
    Liefert (horizont_oder_None, normalisierter_text)."""
    text, anzahl = bogen_pdf_zu_text(pfad)
    if anzahl == 0:
        return None, ""
    horizont = parse_erwartungshorizont(
        text, titel="", auto_schluesselwoerter=auto_schluesselwoerter)
    if not horizont["aufgaben"]:
        return None, text
    return horizont, text


def _lade_klausur_loader(status_melden):
    """Importiert den KlausurLoader aus klausur_bewertung.pyw (gleicher
    Ordner), um dessen Handschrifterkennung fuer gescannte Boegen
    mitzunutzen."""
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "klausur_bewertung.pyw")
    if not os.path.exists(pfad):
        raise RuntimeError(
            "klausur_bewertung.pyw wurde nicht im selben Ordner gefunden – "
            "die Handschrifterkennung für gescannte PDFs steht daher nicht "
            "zur Verfügung.")
    lader = importlib.machinery.SourceFileLoader("klausur_bewertung", pfad)
    spec = importlib.util.spec_from_loader("klausur_bewertung", lader)
    modul = importlib.util.module_from_spec(spec)
    lader.exec_module(modul)
    return modul.KlausurLoader(status_melden)


class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITEL)
        self.geometry("1250x780")
        self.minsize(1000, 600)
        self.daten = {"titel": "Klausur", "sprache": "en-GB",
                      "gewichtung": {"inhalt": 0.4, "sprache": 0.6},
                      "aufgaben": []}
        self._queue = queue.Queue()
        self._baue_oberflaeche()
        self.after(100, self._verarbeite_queue)

    # ---------------- Aufbau ----------------

    def _baue_oberflaeche(self):
        kopf = ttk.Frame(self, padding=8)
        kopf.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(kopf, text="Titel der Klausur:").pack(side=tk.LEFT)
        self.titel_feld = ttk.Entry(kopf, width=50)
        self.titel_feld.insert(0, "Klausur")
        self.titel_feld.pack(side=tk.LEFT, padx=6)
        ttk.Label(kopf, text="Sprache:").pack(side=tk.LEFT, padx=(12, 4))
        self.sprach_wahl = ttk.Combobox(kopf, width=7, state="readonly",
                                        values=["en-GB", "en-US"])
        self.sprach_wahl.set("en-GB")
        self.sprach_wahl.pack(side=tk.LEFT)
        ttk.Button(kopf, text="JSON laden…",
                   command=self.lade_json).pack(side=tk.RIGHT, padx=4)
        ttk.Button(kopf, text="JSON speichern…",
                   command=self.speichere_json).pack(side=tk.RIGHT, padx=4)

        haupt = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        haupt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Links: Texteingabe oder PDF
        links = ttk.LabelFrame(haupt, text="1. Erwartungshorizont: Text "
                                           "einfügen oder PDF laden",
                               padding=6)
        haupt.add(links, weight=1)
        quellen = ttk.Frame(links)
        quellen.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))
        self.knopf_pdf = ttk.Button(quellen,
                                    text="PDF laden… (Bewertungsbogen)",
                                    command=self.lade_pdf)
        self.knopf_pdf.pack(side=tk.LEFT)
        ttk.Label(quellen, text="  oder Text unten einfügen/bearbeiten:"
                  ).pack(side=tk.LEFT)
        self.text_eingabe = tk.Text(links, wrap=tk.WORD,
                                    font=("Segoe UI", 10), undo=True)
        rb1 = ttk.Scrollbar(links, command=self.text_eingabe.yview)
        self.text_eingabe.configure(yscrollcommand=rb1.set)
        rb1.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_eingabe.pack(fill=tk.BOTH, expand=True)
        self.text_eingabe.insert("1.0", BEISPIELTEXT)
        ttk.Button(links, text="→ Text in Aufgaben umwandeln",
                   command=self.parse_text).pack(fill=tk.X, pady=(6, 0))

        # Mitte: Baum + Bearbeitung
        mitte = ttk.LabelFrame(haupt, text="2. Prüfen und bearbeiten",
                               padding=6)
        haupt.add(mitte, weight=1)
        self.baum = ttk.Treeview(mitte, show="tree", selectmode="browse")
        rb2 = ttk.Scrollbar(mitte, command=self.baum.yview)
        self.baum.configure(yscrollcommand=rb2.set)
        rb2.pack(side=tk.RIGHT, fill=tk.Y)
        self.baum.pack(fill=tk.BOTH, expand=True)
        self.baum.bind("<<TreeviewSelect>>", self._auswahl_geaendert)

        knoepfe = ttk.Frame(mitte)
        knoepfe.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(knoepfe, text="+ Aufgabe",
                   command=self.neue_aufgabe).pack(side=tk.LEFT, padx=2)
        ttk.Button(knoepfe, text="+ Erwartung",
                   command=self.neue_erwartung).pack(side=tk.LEFT, padx=2)
        ttk.Button(knoepfe, text="Löschen",
                   command=self.loesche_auswahl).pack(side=tk.LEFT, padx=2)
        ttk.Button(knoepfe, text="Schlüsselwörter vorschlagen",
                   command=self.schlage_woerter_vor).pack(side=tk.LEFT,
                                                          padx=(12, 2))

        felder = ttk.Frame(mitte)
        felder.pack(fill=tk.X, pady=(8, 0))
        self.feld_widgets = {}
        for zeilen_nr, (schluessel, beschriftung) in enumerate([
                ("f1", "Nummer / Beschreibung:"),
                ("f2", "Titel / Punkte:"),
                ("f3", "max. Punkte / Schlüsselwörter:"),
                ("f4", "– / mindestens Treffer:")]):
            ttk.Label(felder, text=beschriftung).grid(
                row=zeilen_nr, column=0, sticky=tk.W, pady=1)
            eingabe = ttk.Entry(felder, width=52)
            eingabe.grid(row=zeilen_nr, column=1, sticky=tk.EW, pady=1,
                         padx=(4, 0))
            self.feld_widgets[schluessel] = eingabe
        felder.columnconfigure(1, weight=1)
        ttk.Button(mitte, text="Änderungen übernehmen",
                   command=self.uebernehme_felder).pack(fill=tk.X,
                                                        pady=(6, 0))

        # Rechts: JSON-Vorschau
        rechts = ttk.LabelFrame(haupt, text="3. JSON-Vorschau", padding=6)
        haupt.add(rechts, weight=1)
        self.vorschau = tk.Text(rechts, wrap=tk.NONE,
                                font=("Consolas", 9))
        rb3 = ttk.Scrollbar(rechts, command=self.vorschau.yview)
        self.vorschau.configure(yscrollcommand=rb3.set)
        rb3.pack(side=tk.RIGHT, fill=tk.Y)
        self.vorschau.pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W,
                                padding=4,
                                text="Text links einfügen und umwandeln – "
                                     "oder direkt Aufgaben anlegen.")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # ---------------- PDF laden ----------------

    def lade_pdf(self):
        pfad = filedialog.askopenfilename(
            title="Erwartungshorizont / Bewertungsbogen als PDF wählen",
            filetypes=[("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")])
        if not pfad:
            return
        self._starte_pdf(pfad)

    def _starte_pdf(self, pfad):
        self.knopf_pdf.configure(state=tk.DISABLED)
        self.status.configure(text="PDF wird eingelesen …")
        threading.Thread(target=self._lese_pdf_im_hintergrund,
                         args=(pfad,), daemon=True).start()

    def _lese_pdf_im_hintergrund(self, pfad):
        try:
            try:
                import fitz  # PyMuPDF
            except ImportError:
                raise FehlendePakete(["pymupdf"],
                                     "das Einlesen von PDF-Dateien")
            # 1. Versuch: tabellarischer Bewertungsbogen (Punktespalte)
            self._queue.put(("status", "Prüfe PDF auf Bewertungsraster …"))
            horizont, roh = bogen_pdf_lesen(pfad)
            if horizont is not None:
                self._queue.put(("horizont", (horizont, roh)))
                return

            dokument = fitz.open(pfad)
            text = "\n".join(seite.get_text() for seite in dokument).strip()
            quelle = "PDF-Textebene"
            if len(re.findall(r"[A-Za-zÄÖÜäöüß]+", text)) < 20:
                # gescannter Bogen ohne Textebene -> Handschrifterkennung
                # aus klausur_bewertung.pyw mitnutzen
                self._queue.put(("status",
                                 "Keine Textebene – starte Texterkennung "
                                 "(erster Start: Modell-Download) …"))
                lader = _lade_klausur_loader(
                    lambda t: self._queue.put(("status", t)))
                text, protokoll = lader.lese(pfad)
                quelle = protokoll["quelle"]
            self._queue.put(("pdf", (text, quelle)))
        except Exception as fehler:
            self._queue.put(("fehler", (fehler, pfad)))

    def _verarbeite_queue(self):
        try:
            while True:
                art, daten = self._queue.get_nowait()
                if art == "status":
                    self.status.configure(text=daten)
                elif art == "horizont":
                    horizont, roh = daten
                    self.knopf_pdf.configure(state=tk.NORMAL)
                    self.text_eingabe.delete("1.0", tk.END)
                    self.text_eingabe.insert("1.0", roh)
                    self.daten = horizont
                    self.titel_feld.delete(0, tk.END)
                    self.titel_feld.insert(0, horizont["titel"])
                    self._baum_neu()
                    self._melde_ergebnis(horizont,
                                         "Bewertungsraster (Tabelle)")
                elif art == "pdf":
                    text, quelle = daten
                    self.knopf_pdf.configure(state=tk.NORMAL)
                    if not text.strip():
                        messagebox.showwarning(
                            "Nichts erkannt",
                            "Im PDF konnte kein Text erkannt werden.")
                        self.status.configure(text="PDF ohne erkennbaren "
                                                   "Text.")
                    else:
                        self.text_eingabe.delete("1.0", tk.END)
                        self.text_eingabe.insert("1.0", text)
                        self.status.configure(
                            text=f"PDF eingelesen ({quelle}). Bitte Text "
                                 f"prüfen/anpassen, dann „→ Text in "
                                 f"Aufgaben umwandeln“ klicken.")
                elif art == "fehler":
                    fehler, pfad = daten
                    self.knopf_pdf.configure(state=tk.NORMAL)
                    if getattr(fehler, "pip_namen", None):
                        biete_installation_an(
                            self, fehler,
                            lambda p=pfad: self._starte_pdf(p),
                            lambda text: self.status.configure(text=text))
                    else:
                        self.status.configure(text="PDF-Einlesen "
                                                   "fehlgeschlagen.")
                        messagebox.showerror("PDF-Einlesen fehlgeschlagen",
                                             str(fehler))
        except queue.Empty:
            pass
        self.after(100, self._verarbeite_queue)

    # ---------------- Parsen und Baum ----------------

    def parse_text(self):
        text = self.text_eingabe.get("1.0", tk.END)
        daten = parse_erwartungshorizont(text,
                                         self.titel_feld.get().strip())
        if not daten["aufgaben"]:
            messagebox.showwarning(
                "Nichts erkannt",
                "Es wurde keine Aufgabe erkannt. Aufgaben mit "
                "„Aufgabe 1: …“ oder „1. …“ beginnen, Erwartungen als "
                "Aufzählung („- …“) darunter.")
            return
        self.daten = daten
        self.titel_feld.delete(0, tk.END)
        self.titel_feld.insert(0, daten["titel"])
        self._baum_neu()
        self._melde_ergebnis(daten, "Text")

    def _melde_ergebnis(self, horizont, quelle):
        aufgaben = horizont["aufgaben"]
        gesamt = sum(a["max_punkte"] for a in aufgaben)
        erwartungen = sum(len(a["erwartungen"]) for a in aufgaben)
        auto = sum(1 for a in aufgaben for e in a["erwartungen"]
                   if e.get("auto"))
        manuell = sum(1 for a in aufgaben for e in a["erwartungen"]
                      if e.get("manuell"))
        text = (f"{quelle} erkannt: {len(aufgaben)} Aufgabe(n), "
                f"{erwartungen} Erwartungen, {gesamt:g} Punkte gesamt.")
        hinweise = []
        if auto:
            hinweise.append(
                f"Für {auto} Erwartungen wurden Schlüsselwörter automatisch "
                f"aus dem Text vorgeschlagen (im Baum mit ◆ markiert). Bitte "
                f"prüfen und ergänzen – sie bestimmen, was im Schülertext "
                f"gesucht wird.")
        if manuell:
            hinweise.append(
                f"{manuell} Erwartungen betreffen Aufbau/Darstellung/"
                f"Zitierweise (mit ✎ markiert). Diese kann das Programm "
                f"nicht automatisch prüfen; die Punkte vergeben Sie im "
                f"Bewertungsprogramm selbst.")
        self.status.configure(text=text)
        messagebox.showinfo("PDF eingelesen",
                            text + ("\n\n" + "\n\n".join(hinweise)
                                    if hinweise else ""))

    def _baum_neu(self):
        self.baum.delete(*self.baum.get_children())
        for a_index, aufgabe in enumerate(self.daten["aufgaben"]):
            knoten = self.baum.insert(
                "", tk.END, iid=f"a{a_index}", open=True,
                text=f"Aufgabe {aufgabe['nummer']}: {aufgabe['titel']} "
                     f"({aufgabe['max_punkte']:g} P)")
            for e_index, erwartung in enumerate(aufgabe["erwartungen"]):
                if not erwartung["schluesselwoerter"]:
                    markierung = "  ⚠ ohne Schlüsselwörter"
                elif erwartung.get("auto"):
                    markierung = "  ◆ Vorschlag – bitte prüfen"
                else:
                    markierung = ""
                if erwartung.get("manuell"):
                    markierung += "  ✎ manuell zu bewerten"
                self.baum.insert(
                    knoten, tk.END, iid=f"a{a_index}e{e_index}",
                    text=f"{erwartung['beschreibung']} "
                         f"({erwartung['punkte']:g} P, min. "
                         f"{erwartung['mindestens']}){markierung}")
        self._vorschau_neu()

    def _vorschau_neu(self):
        self.daten["titel"] = self.titel_feld.get().strip() or "Klausur"
        self.daten["sprache"] = self.sprach_wahl.get()
        self.vorschau.delete("1.0", tk.END)
        self.vorschau.insert("1.0", json.dumps(self.daten,
                                               ensure_ascii=False, indent=2))

    def _zerlege_iid(self, iid):
        treffer = re.match(r"a(\d+)(?:e(\d+))?$", iid or "")
        if not treffer:
            return None, None
        a_index = int(treffer.group(1))
        e_index = int(treffer.group(2)) if treffer.group(2) else None
        return a_index, e_index

    # ---------------- Bearbeiten ----------------

    def _auswahl_geaendert(self, _ereignis=None):
        auswahl = self.baum.selection()
        if not auswahl:
            return
        a_index, e_index = self._zerlege_iid(auswahl[0])
        if a_index is None:
            return
        for eingabe in self.feld_widgets.values():
            eingabe.delete(0, tk.END)
        if e_index is None:
            aufgabe = self.daten["aufgaben"][a_index]
            self.feld_widgets["f1"].insert(0, aufgabe["nummer"])
            self.feld_widgets["f2"].insert(0, aufgabe["titel"])
            self.feld_widgets["f3"].insert(0, f"{aufgabe['max_punkte']:g}")
        else:
            erwartung = self.daten["aufgaben"][a_index]["erwartungen"][e_index]
            self.feld_widgets["f1"].insert(0, erwartung["beschreibung"])
            self.feld_widgets["f2"].insert(0, f"{erwartung['punkte']:g}")
            self.feld_widgets["f3"].insert(
                0, ", ".join(erwartung["schluesselwoerter"]))
            self.feld_widgets["f4"].insert(0, str(erwartung["mindestens"]))

    def uebernehme_felder(self):
        auswahl = self.baum.selection()
        if not auswahl:
            messagebox.showinfo("Keine Auswahl",
                                "Bitte links eine Aufgabe oder Erwartung "
                                "auswählen.")
            return
        a_index, e_index = self._zerlege_iid(auswahl[0])
        if a_index is None:
            return
        w = self.feld_widgets
        try:
            if e_index is None:
                aufgabe = self.daten["aufgaben"][a_index]
                aufgabe["nummer"] = w["f1"].get().strip() or aufgabe["nummer"]
                aufgabe["titel"] = w["f2"].get().strip() or aufgabe["titel"]
                if w["f3"].get().strip():
                    aufgabe["max_punkte"] = float(
                        w["f3"].get().replace(",", "."))
            else:
                erwartung = self.daten["aufgaben"][a_index][
                    "erwartungen"][e_index]
                erwartung["beschreibung"] = (w["f1"].get().strip()
                                             or erwartung["beschreibung"])
                if w["f2"].get().strip():
                    erwartung["punkte"] = float(
                        w["f2"].get().replace(",", "."))
                neue_woerter = [s.strip() for s in w["f3"].get().split(",")
                                if s.strip()]
                if neue_woerter != erwartung["schluesselwoerter"]:
                    # von Hand geändert -> kein automatischer Vorschlag mehr
                    erwartung["auto"] = False
                erwartung["schluesselwoerter"] = neue_woerter
                if w["f4"].get().strip():
                    erwartung["mindestens"] = max(1, int(w["f4"].get()))
        except ValueError as fehler:
            messagebox.showerror("Ungültige Eingabe",
                                 f"Zahl konnte nicht gelesen werden:\n"
                                 f"{fehler}")
            return
        self._baum_neu()
        self.baum.selection_set(auswahl[0])
        self.status.configure(text="Änderung übernommen.")

    def schlage_woerter_vor(self):
        """Erzeugt Schlüsselwort-Vorschläge aus dem Beschreibungstext –
        für die ausgewählte Erwartung oder für alle noch leeren."""
        auswahl = self.baum.selection()
        a_index, e_index = self._zerlege_iid(auswahl[0] if auswahl else "")
        if a_index is not None and e_index is not None:
            ziele = [self.daten["aufgaben"][a_index]["erwartungen"][e_index]]
        else:
            ziele = [e for a in self.daten["aufgaben"]
                     for e in a["erwartungen"] if not e["schluesselwoerter"]]
            if not ziele:
                messagebox.showinfo(
                    "Nichts zu tun",
                    "Alle Erwartungen haben bereits Schlüsselwörter. Für eine "
                    "einzelne Erwartung diese links auswählen und erneut "
                    "klicken.")
                return
        ergaenzt = 0
        for erwartung in ziele:
            vorschlag = schluesselwoerter_vorschlagen(erwartung["beschreibung"])
            if vorschlag:
                erwartung["schluesselwoerter"] = vorschlag
                erwartung["auto"] = True
                erwartung["mindestens"] = max(
                    1, min(3, round(len(vorschlag) / 3.0)))
                ergaenzt += 1
        self._baum_neu()
        if auswahl:
            self.baum.selection_set(auswahl[0])
            self._auswahl_geaendert()
        self.status.configure(
            text=f"Schlüsselwörter für {ergaenzt} Erwartung(en) "
                 f"vorgeschlagen – bitte prüfen.")

    def neue_aufgabe(self):
        nummer = str(len(self.daten["aufgaben"]) + 1)
        self.daten["aufgaben"].append({
            "nummer": nummer, "titel": "Neue Aufgabe",
            "max_punkte": 10.0, "erwartungen": []})
        self._baum_neu()

    def neue_erwartung(self):
        auswahl = self.baum.selection()
        a_index, _ = self._zerlege_iid(auswahl[0] if auswahl else "")
        if a_index is None:
            if not self.daten["aufgaben"]:
                self.neue_aufgabe()
            a_index = len(self.daten["aufgaben"]) - 1
        self.daten["aufgaben"][a_index]["erwartungen"].append({
            "beschreibung": "Neue Erwartung", "punkte": 2.0,
            "schluesselwoerter": [], "mindestens": 1})
        self._baum_neu()

    def loesche_auswahl(self):
        auswahl = self.baum.selection()
        if not auswahl:
            return
        a_index, e_index = self._zerlege_iid(auswahl[0])
        if a_index is None:
            return
        if e_index is None:
            del self.daten["aufgaben"][a_index]
        else:
            del self.daten["aufgaben"][a_index]["erwartungen"][e_index]
        self._baum_neu()

    # ---------------- Laden / Speichern ----------------

    def lade_json(self):
        pfad = filedialog.askopenfilename(
            title="Erwartungshorizont (JSON) laden",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")])
        if not pfad:
            return
        try:
            with open(pfad, encoding="utf-8") as datei:
                daten = json.load(datei)
            if not isinstance(daten.get("aufgaben"), list):
                raise ValueError("Keine Liste 'aufgaben' enthalten.")
        except Exception as fehler:
            messagebox.showerror("Fehler", f"Datei konnte nicht gelesen "
                                           f"werden:\n{fehler}")
            return
        daten.setdefault("gewichtung", {"inhalt": 0.4, "sprache": 0.6})
        for aufgabe in daten["aufgaben"]:
            aufgabe.setdefault("erwartungen", [])
            aufgabe.setdefault("max_punkte", 0.0)
            for erwartung in aufgabe["erwartungen"]:
                erwartung.setdefault("schluesselwoerter", [])
                erwartung.setdefault("mindestens", 1)
                erwartung.setdefault("punkte", 2.0)
                erwartung.setdefault("auto", False)
                erwartung.setdefault("manuell", False)
        self.daten = daten
        self.titel_feld.delete(0, tk.END)
        self.titel_feld.insert(0, daten.get("titel", "Klausur"))
        if daten.get("sprache") in ("en-GB", "en-US"):
            self.sprach_wahl.set(daten["sprache"])
        self._baum_neu()
        self.status.configure(text=f"Geladen: {pfad}")

    def speichere_json(self):
        if not self.daten["aufgaben"]:
            messagebox.showwarning("Leer", "Es sind keine Aufgaben angelegt.")
            return
        ohne_woerter = [
            f"Aufgabe {a['nummer']}: {e['beschreibung'][:40]}"
            for a in self.daten["aufgaben"] for e in a["erwartungen"]
            if not e["schluesselwoerter"]]
        if ohne_woerter:
            if not messagebox.askyesno(
                    "Schlüsselwörter fehlen",
                    "Folgende Erwartungen haben noch keine Schlüsselwörter "
                    "und können daher nicht automatisch geprüft werden:\n\n"
                    + "\n".join(ohne_woerter[:10])
                    + ("\n…" if len(ohne_woerter) > 10 else "")
                    + "\n\nTrotzdem speichern?"):
                return
        self._vorschau_neu()
        pfad = filedialog.asksaveasfilename(
            title="Erwartungshorizont speichern",
            defaultextension=".json",
            initialfile="erwartungshorizont.json",
            filetypes=[("JSON-Datei", "*.json")])
        if not pfad:
            return
        with open(pfad, "w", encoding="utf-8") as datei:
            json.dump(self.daten, datei, ensure_ascii=False, indent=2)
        self.status.configure(text=f"Gespeichert: {pfad}")


BEISPIELTEXT = """Klausur Q1: Globalization

Aufgabe 1: Comprehension – Summarize the author's main points
- Nennt die zentrale These (4 P) [interconnected, global trade, interdependence]
- Benennt wirtschaftliche Aspekte (4 P, min. 2) [outsourcing, multinational, supply chain]
- Fasst die Risiken zusammen (4 P, min. 2) [inequality, job loss, exploitation]

Aufgabe 2: Analysis – Analyse the line of argument and use of language
- Beschreibt den Argumentationsaufbau (5 P, min. 2) [thesis, example, conclusion, structure]
- Analysiert sprachliche Mittel mit Beleg (6 P, min. 2) [metaphor, rhetorical question, repetition, imagery]
- Erläutert die Wirkung auf den Leser (5 P, min. 2) [effect, reader, persuade, intention]

Aufgabe 3: Comment – 'Globalization does more harm than good.' Discuss.
- Formuliert eine klare eigene Position (3 P) [in my opinion, I would argue, I believe]
- Nennt Pro-Argumente (4 P, min. 2) [prosperity, cultural exchange, innovation, opportunities]
- Nennt Contra-Argumente (4 P, min. 2) [inequality, pollution, exploitation, dependence]
- Schließt mit begründetem Fazit (1 P) [in conclusion, to sum up, all in all]
"""


if __name__ == "__main__":
    Editor().mainloop()
