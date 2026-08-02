#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Klausur-Bewertung Englisch (Oberstufe) – nach dem hessischen Erlass zur
Bewertung und Beurteilung von schriftlichen Arbeiten in den modernen
Fremdsprachen (Erlass vom 7. August 2020, III.A.3 – 323.300.000-337)
=========================================================================

Bewertungsmodell des Erlasses:

* Sprachliche und inhaltliche Leistung werden getrennt bewertet.
* Gesamtnote = sprachliche Leistung : inhaltliche Leistung im Verhältnis
  60:40; NUR die Gesamtnote wird gerundet.
* Eine ungenügende sprachliche ODER inhaltliche Leistung schließt eine
  Gesamtnote von mehr als 3 Punkten aus (Sperrklausel).
* Die sprachliche Leistung wird anhand der Deskriptorentabelle ("Kriterien
  zur Bewertung der sprachlichen Leistung") aus zwei Bereichen im
  Verhältnis 50:50 gebildet, eine Dezimalstelle wird nicht gerundet:
    Bereich A "Sprachliche Richtigkeit":   Lexik, Grammatik/Syntax,
                                           Orthographie
    Bereich B "Ausdruck und Textgestaltung": Textaufbau/Textsortenspezifik,
                                           eigenständige Textgestaltung,
                                           Sprachregister, Wortschatz,
                                           Satzbau
  Innerhalb der Bereiche wird ganzheitlich bewertet (keine Teilnoten je
  Kriterium). Wiederholungsfehler werden nicht gewertet.

Das Programm ermittelt für jedes Kriterium einen automatischen Befund und
einen Banding-Vorschlag (sehr gut 15-13 ... ungenügend 0) anhand der
Original-Deskriptoren. Jeder Vorschlag kann von der Lehrkraft per Auswahl
übersteuert werden – besonders wichtig bei den Kriterien des Bereichs B,
die maschinell nur näherungsweise beurteilbar sind.

Start: Doppelklick auf die Datei (Windows: .pyw startet ohne Konsole).
Benötigt Python 3.8+ mit Tkinter. Optionale Pakete:
  pip install language_tool_python   -> Sprachpruefung lokal ohne Internet
  pip install python-docx            -> .docx einlesen
  pip install pymupdf easyocr        -> PDF laden + Handschrifterkennung
  pip install transformers torch     -> bessere Handschrifterkennung (TrOCR)

WICHTIG: Alle Bewertungen sind VORSCHLAEGE und ersetzen nicht die
pädagogische Beurteilung durch die Lehrkraft.
"""

import difflib
import json
import math
import queue
import re
import threading
import tkinter as tk
import urllib.parse
import urllib.request
from tkinter import filedialog, messagebox, ttk

APP_TITEL = "Klausur-Bewertung Englisch (Oberstufe, Erlass Hessen 2020)"

LT_PUBLIC_API = "https://api.languagetool.org/v2/check"
LT_CHUNK_LIMIT = 9000

# KMK-Zuordnung Prozent -> Notenpunkte (fuer die inhaltliche Leistung)
NOTENPUNKTE_TABELLE = [
    (95, 15), (90, 14), (85, 13), (80, 12), (75, 11), (70, 10),
    (65, 9), (60, 8), (55, 7), (50, 6), (45, 5), (40, 4),
    (33, 3), (27, 2), (20, 1),
]

# Notenbänder der Deskriptorentabelle:
# (Name, Punktspanne, Repräsentativwert bei manueller Wahl, Untergrenze)
BAENDER = [
    ("sehr gut", "15-13", 14.0, 12.5),
    ("gut", "12-10", 11.0, 9.5),
    ("befriedigend", "09-07", 8.0, 6.5),
    ("ausreichend", "06-04", 5.0, 3.5),
    ("mangelhaft", "03-01", 2.0, 0.5),
    ("ungenügend", "0", 0.0, -999.0),
]


def band_fuer_note(note):
    for name, spanne, _wert, untergrenze in BAENDER:
        if note >= untergrenze:
            return name, spanne
    return BAENDER[-1][0], BAENDER[-1][1]


def band_wert(band_name):
    for name, _spanne, wert, _ug in BAENDER:
        if name == band_name:
            return wert
    return 0.0


def trunc1(x):
    """Eine Dezimalstelle, NICHT gerundet (Vorgabe des Erlasses)."""
    return math.floor(x * 10.0) / 10.0


def kaufmaennisch_runden(x):
    return int(math.floor(x + 0.5))


def prozent_zu_notenpunkte(prozent):
    for schwelle, punkte in NOTENPUNKTE_TABELLE:
        if prozent >= schwelle:
            return punkte
    return 0


def woerter_zaehlen(text):
    return len(re.findall(r"[A-Za-zÄÖÜäöüß'’-]+", text))


# ----------------------------------------------------------------------------
# Deskriptorentabelle (Anlage des Erlasses, Originalwortlaut)
# ----------------------------------------------------------------------------

KRITERIEN_RICHTIGKEIT = ["lexik", "grammatik", "orthographie"]
KRITERIEN_AUSDRUCK = ["textaufbau", "eigenstaendigkeit", "register",
                      "wortschatz", "satzbau"]

KRITERIEN_NAMEN = {
    "lexik": "Lexik",
    "grammatik": "Grammatik / Syntax",
    "orthographie": "Orthographie",
    "textaufbau": "Textaufbau, ggf. Textsortenspezifik",
    "eigenstaendigkeit": "Eigenständige Textgestaltung",
    "register": "Sprachregister",
    "wortschatz": "Allgemeiner, thematischer, Funktions- und "
                  "Interpretationswortschatz",
    "satzbau": "Satzbau",
}

DESKRIPTOREN = {
    "lexik": {
        "sehr gut": "sehr hohes Maß an lexikalischer Korrektheit in allen "
            "Bereichen des Wortschatzes; vereinzelte Fehler resultieren "
            "daraus, dass sprachliche Risiken eingegangen werden; die "
            "Verständlichkeit wird nicht beeinträchtigt",
        "gut": "weitestgehend lexikalische Korrektheit in allen Bereichen "
            "des Wortschatzes; die Verständlichkeit wird durch einzelne "
            "Fehler nicht beeinträchtigt",
        "befriedigend": "im Wesentlichen lexikalisch korrekt; die "
            "Verständlichkeit wird durch Fehler nicht beeinträchtigt",
        "ausreichend": "wiederholt lexikalische Fehler, die vereinzelt zu "
            "Missverständnissen führen",
        "mangelhaft": "Häufung lexikalischer Fehler, die zu "
            "Missverständnissen führen",
        "ungenügend": "Häufung elementarer lexikalischer Fehler, die die "
            "Verständlichkeit stark beeinträchtigen",
    },
    "grammatik": {
        "sehr gut": "sehr hohes Maß an grammatischer/syntaktischer "
            "Korrektheit; vereinzelte Fehler betreffen nur komplexe "
            "Satzstrukturen oder weniger geläufige grammatische Strukturen "
            "und resultieren daraus, dass sprachliche Risiken eingegangen "
            "werden; die Verständlichkeit wird nicht beeinträchtigt",
        "gut": "weitestgehend grammatisch/syntaktisch korrekt; einzelne "
            "Fehler betreffen komplexe Satzstrukturen; die Verständlichkeit "
            "wird nicht beeinträchtigt",
        "befriedigend": "im Wesentlichen grammatisch/syntaktisch korrekt; "
            "die Verständlichkeit wird durch Fehler nicht beeinträchtigt",
        "ausreichend": "wiederholt grammatische/syntaktische Fehler, die "
            "vereinzelt zu Missverständnissen führen",
        "mangelhaft": "Häufung grammatischer/syntaktischer Fehler, die zu "
            "Missverständnissen führen",
        "ungenügend": "Häufung elementarer grammatischer/syntaktischer "
            "Fehler, die die Verständlichkeit stark beeinträchtigen",
    },
    "orthographie": {
        "sehr gut": "hohes Maß an orthographischer Korrektheit; vereinzelte "
            "Orthographiefehler haben den Charakter von "
            "Flüchtigkeitsfehlern; die Lesbarkeit wird nicht beeinträchtigt",
        "gut": "weitestgehend orthographisch korrekt; einzelne Fehler haben "
            "den Charakter von Flüchtigkeitsfehlern oder betreffen weniger "
            "geläufige Lexik; die Lesbarkeit wird nicht beeinträchtigt",
        "befriedigend": "im Wesentlichen orthographisch korrekt; die "
            "Lesbarkeit wird nicht beeinträchtigt",
        "ausreichend": "wiederholt orthographische Fehler, die die "
            "Lesbarkeit vereinzelt beeinträchtigen",
        "mangelhaft": "Häufung orthographischer Fehler, die die Lesbarkeit "
            "beeinträchtigen",
        "ungenügend": "Häufung elementarer orthographischer Fehler, die die "
            "Lesbarkeit stark beeinträchtigen",
    },
    "textaufbau": {
        "sehr gut": "durchgängig zielgerichteter, strukturierter und "
            "kohärenter Text; besonders überzeugende Umsetzung der in der "
            "Aufgabe geforderten spezifischen formalen Textsortenmerkmale",
        "gut": "weitestgehend zielgerichteter, strukturierter und "
            "kohärenter Text; weitestgehend überzeugende Umsetzung der in "
            "der Aufgabe geforderten spezifischen formalen "
            "Textsortenmerkmale",
        "befriedigend": "im Allgemeinen zielgerichteter, nicht durchgängig "
            "strukturierter und kohärenter Text; grundsätzlich gelungene "
            "Umsetzung der in der Aufgabe geforderten spezifischen formalen "
            "Textsortenmerkmale",
        "ausreichend": "ansatzweise strukturierter und kohärenter Text; in "
            "Ansätzen vorhandene Umsetzung der in der Aufgabe geforderten "
            "spezifischen formalen Textsortenmerkmale",
        "mangelhaft": "weitgehend unstrukturierter und inkohärenter Text; "
            "weitgehend fehlende Umsetzung der in der Aufgabe geforderten "
            "spezifischen formalen Textsortenmerkmale",
        "ungenügend": "unstrukturierter, inkohärenter Text; keine Umsetzung "
            "der in der Aufgabe geforderten spezifischen formalen "
            "Textsortenmerkmale",
    },
    "eigenstaendigkeit": {
        "sehr gut": "durchgängig eigenständige Darstellung; etwaige direkte "
            "oder indirekte Zitate sind kenntlich gemacht und gut in den "
            "Textfluss eingebettet",
        "gut": "weitestgehend eigenständige Darstellung; etwaige direkte "
            "oder indirekte Zitate sind kenntlich gemacht und angemessen in "
            "den Textfluss eingebettet",
        "befriedigend": "grundsätzlich eigenständige Darstellung; etwaige "
            "direkte oder indirekte Zitate sind im Wesentlichen kenntlich "
            "gemacht und grundsätzlich angemessen in den Textfluss "
            "eingebettet",
        "ausreichend": "noch eigenständige Anteile in der Darstellung; "
            "etwaige direkte oder indirekte Zitate sind ansatzweise "
            "kenntlich gemacht",
        "mangelhaft": "kaum eigenständige Darstellung; etwaige direkte oder "
            "indirekte Zitate sind kaum kenntlich gemacht",
        "ungenügend": "keine eigenständige Darstellung; etwaige Übernahmen "
            "aus den Materialien oder anderen Quellen sind nicht kenntlich "
            "gemacht und/oder der Aufgabe nicht angemessen",
    },
    "register": {
        "sehr gut": "Sprachregister der Aufgabe u. a. situativ durchgängig "
            "angemessen mit überzeugendem Adressatenbezug",
        "gut": "Sprachregister der Aufgabe u. a. situativ weitestgehend "
            "angemessen mit angemessenem Adressatenbezug",
        "befriedigend": "Sprachregister der Aufgabe u. a. situativ "
            "grundsätzlich angemessen mit Adressatenbezug",
        "ausreichend": "Sprachregister der Aufgabe u. a. ansatzweise "
            "situativ angemessen mit Adressatenbezug",
        "mangelhaft": "Sprachregister der Aufgabe u. a. weitgehend situativ "
            "nicht angemessen",
        "ungenügend": "Sprachregister der Aufgabe nicht angemessen",
    },
    "wortschatz": {
        "sehr gut": "präzise und durchgängig differenzierte und "
            "idiomatische Wortwahl",
        "gut": "präzise, weitestgehend differenzierte und idiomatische "
            "Wortwahl",
        "befriedigend": "grundsätzlich angemessene, verständliche Wortwahl",
        "ausreichend": "eingeschränkte, noch angemessene Wortwahl",
        "mangelhaft": "deutlich eingeschränkte Wortwahl",
        "ungenügend": "keine angemessene Wortwahl",
    },
    "satzbau": {
        "sehr gut": "durchgängig variabler und funktionaler Satzbau unter "
            "angemessener Verwendung komplexer, sprachtypischer Strukturen "
            "bei durchgängig überzeugendem Einsatz von textstrukturierenden "
            "Mitteln",
        "gut": "variabler und funktionaler Satzbau unter weitestgehend "
            "angemessener Verwendung komplexer, sprachtypischer Strukturen "
            "bei weitestgehend überzeugendem Einsatz von "
            "textstrukturierenden Mitteln",
        "befriedigend": "grundsätzlich variabler und funktionaler Satzbau "
            "unter Verwendung gängiger sprachlicher Strukturen bei "
            "grundsätzlich gelungenem Einsatz von textstrukturierenden "
            "Mitteln",
        "ausreichend": "wenig variabler, aber noch angemessener Satzbau "
            "unter Verwendung gängiger sprachlicher Strukturen bei "
            "ansatzweise gelungenem Einsatz von textstrukturierenden "
            "Mitteln",
        "mangelhaft": "sehr einfacher, teilweise sprachuntypischer Satzbau "
            "bei weitgehend unangemessenem oder fehlendem Einsatz von "
            "textstrukturierenden Mitteln",
        "ungenügend": "sprachuntypischer Satzbau bei durchgängig "
            "unangemessenem oder vollständig fehlendem Einsatz von "
            "textstrukturierenden Mitteln",
    },
}


# ----------------------------------------------------------------------------
# Grammatik- und Rechtschreibpruefung (LanguageTool)
# ----------------------------------------------------------------------------

# Zuordnung der LanguageTool-Kategorien zu den Kriterien der
# "Sprachlichen Richtigkeit"; Gewicht < 1 fuer Randbereiche
# (Primat der gesprochenen Sprache: Zeichensetzung/Typographie zaehlen halb).
KATEGORIE_ZU_KRITERIUM = {
    "TYPOS": ("orthographie", 1.0),
    "CASING": ("orthographie", 1.0),
    "TYPOGRAPHY": ("orthographie", 0.5),
    "PUNCTUATION": ("orthographie", 0.5),
    "GRAMMAR": ("grammatik", 1.0),
    "CONFUSED_WORDS": ("lexik", 1.0),
    "COLLOCATIONS": ("lexik", 1.0),
    "SEMANTICS": ("lexik", 1.0),
    "NONSTANDARD_PHRASES": ("lexik", 0.5),
    "MISC": ("lexik", 0.5),
    "BRITISH_ENGLISH": ("lexik", 0.5),
    "AMERICAN_ENGLISH_STYLE": ("lexik", 0.5),
}

KATEGORIE_ANZEIGE = {
    "TYPOS": "Orthographie", "CASING": "Groß-/Kleinschreibung",
    "TYPOGRAPHY": "Typographie", "PUNCTUATION": "Zeichensetzung",
    "GRAMMAR": "Grammatik/Syntax", "CONFUSED_WORDS": "Lexik (Verwechslung)",
    "COLLOCATIONS": "Lexik (Kollokation)", "SEMANTICS": "Lexik (Semantik)",
    "NONSTANDARD_PHRASES": "Lexik (Wendung)", "MISC": "Sonstiges",
    "REDUNDANCY": "Stil (Redundanz)", "STYLE": "Stil",
}


class SprachPruefung:
    """Prueft Text mit LanguageTool: lokal (falls installiert) oder ueber die
    kostenlose oeffentliche API. Markiert Wiederholungsfehler (werden laut
    Erlass nicht gewertet)."""

    def __init__(self, sprache="en-GB"):
        self.sprache = sprache

    def pruefe(self, text):
        try:
            roh = self._pruefe_lokal(text)
        except Exception:
            roh = self._pruefe_online(text)
        return self._markiere_wiederholungen(roh)

    def _pruefe_lokal(self, text):
        import language_tool_python  # optional
        tool = language_tool_python.LanguageTool(self.sprache)
        try:
            return [self._fehler_dict(text, m.offset, m.errorLength,
                                      m.category, m.ruleId, m.message,
                                      list(m.replacements)[:5])
                    for m in tool.check(text)]
        finally:
            tool.close()

    def _pruefe_online(self, text):
        fehler = []
        for basis, stueck in self._stuecke(text):
            daten = urllib.parse.urlencode({
                "text": stueck, "language": self.sprache,
            }).encode("utf-8")
            anfrage = urllib.request.Request(
                LT_PUBLIC_API, data=daten,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                ergebnis = json.loads(antwort.read().decode("utf-8"))
            for m in ergebnis.get("matches", []):
                regel = m.get("rule", {})
                fehler.append(self._fehler_dict(
                    text, basis + m["offset"], m["length"],
                    regel.get("category", {}).get("id", ""),
                    regel.get("id", ""), m.get("message", ""),
                    [r["value"] for r in m.get("replacements", [])][:5]))
        return fehler

    def _stuecke(self, text):
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

    def _fehler_dict(self, text, offset, laenge, kategorie, regel,
                     meldung, vorschlaege):
        start = max(0, offset - 30)
        ende = min(len(text), offset + laenge + 30)
        kriterium, gewicht = KATEGORIE_ZU_KRITERIUM.get(kategorie, (None, 0.0))
        return {
            "offset": offset,
            "laenge": laenge,
            "kategorie": KATEGORIE_ANZEIGE.get(kategorie,
                                               kategorie or "Sonstiges"),
            "kategorie_roh": kategorie,
            "regel": regel,
            "kriterium": kriterium,   # lexik/grammatik/orthographie oder None
            "gewicht": gewicht,
            "wiederholung": False,
            "meldung": meldung,
            "vorschlaege": vorschlaege,
            "text": text[offset:offset + laenge],
            "kontext": text[start:ende].replace("\n", " "),
        }

    @staticmethod
    def _markiere_wiederholungen(fehlerliste):
        """Erlass: Wiederholungsfehler werden nicht gewertet.
        Gleiche Regel + gleiche fehlerhafte Stelle zaehlt nur einmal."""
        gesehen = set()
        for f in sorted(fehlerliste, key=lambda x: x["offset"]):
            schluessel = (f["regel"], f["text"].strip().lower())
            if schluessel in gesehen:
                f["wiederholung"] = True
                f["gewicht"] = 0.0
            else:
                gesehen.add(schluessel)
        return sorted(fehlerliste, key=lambda x: x["offset"])


# ----------------------------------------------------------------------------
# Klausur-Loader: PDF/Bild mit Handschrifterkennung
# ----------------------------------------------------------------------------

OCR_UNSICHER_SCHWELLE = 0.45  # EasyOCR-Konfidenz, darunter gilt ein Wort
                              # als unsicher erkannt


class KlausurLoader:
    """Liest handschriftliche Klausuren als PDF oder Bild ein.

    Reihenfolge "so gut es geht":
    1. Eingebettete Textebene des PDFs (digital erstellte oder bereits
       per OCR erkannte PDFs) - beste Qualitaet, keine Erkennung noetig.
    2. Handschrifterkennung: EasyOCR findet und liest die Textzeilen
       (pip install easyocr). Falls zusaetzlich transformers + torch
       installiert sind, wird jede gefundene Zeile mit TrOCR
       (microsoft/trocr-base-handwritten, spezialisiert auf englische
       Handschrift) nachgelesen - deutlich bessere Ergebnisse bei
       Schreibschrift.

    Unsicher erkannte Woerter werden mit Seite und Konfidenz gemeldet,
    damit die Lehrkraft gezielt nachpruefen kann: Erkennungsfehler
    wuerden sonst als Sprachfehler in die Bewertung eingehen.
    """

    def __init__(self, status_melden=None):
        self.status_melden = status_melden or (lambda text: None)

    def lese(self, pfad):
        """Liefert (text, protokoll) mit protokoll =
        {quelle, seiten, unsicher: [(seite, wort, konfidenz)]}."""
        endung = pfad.lower().rsplit(".", 1)[-1]
        if endung == "pdf":
            return self._lese_pdf(pfad)
        from PIL import Image
        return self._ocr_bilder([Image.open(pfad).convert("RGB")])

    # ---------------- PDF ----------------

    def _lese_pdf(self, pfad):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError(
                "Zum Einlesen von PDF bitte einmalig installieren:\n"
                "pip install pymupdf")
        dokument = fitz.open(pfad)
        textebene = "\n\n".join(seite.get_text().strip()
                                for seite in dokument).strip()
        if woerter_zaehlen(textebene) >= 30:
            return textebene, {"quelle": "PDF-Textebene",
                               "seiten": len(dokument), "unsicher": []}
        self.status_melden("Keine Textebene im PDF – starte "
                           "Handschrifterkennung …")
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError(
                "Für die Handschrifterkennung bitte einmalig installieren:\n"
                "pip install pillow easyocr")
        bilder = []
        for seite in dokument:
            pix = seite.get_pixmap(dpi=300)
            bilder.append(Image.frombytes("RGB", (pix.width, pix.height),
                                          pix.samples))
        return self._ocr_bilder(bilder)

    # ---------------- OCR ----------------

    def _ocr_bilder(self, bilder):
        leser = self._lade_easyocr()
        trocr = self._lade_trocr()
        import numpy as np
        from PIL import ImageOps

        seiten_texte = []
        unsicher = []
        for nr, bild in enumerate(bilder, 1):
            self.status_melden(f"Erkenne Seite {nr}/{len(bilder)} …")
            grau = ImageOps.autocontrast(bild.convert("L"))
            ergebnisse = leser.readtext(np.array(grau), detail=1,
                                        paragraph=False)
            zeilen = self._zeilen_gruppieren(ergebnisse)
            zeilen_texte = []
            for zeile in zeilen:
                text_zeile = None
                if trocr:
                    text_zeile = self._trocr_zeile(trocr, bild, zeile)
                if not text_zeile:
                    text_zeile = " ".join(w["text"] for w in zeile)
                zeilen_texte.append(text_zeile)
                for w in zeile:
                    if w["conf"] < OCR_UNSICHER_SCHWELLE:
                        unsicher.append((nr, w["text"], round(w["conf"], 2)))
            seiten_texte.append("\n".join(zeilen_texte))

        quelle = ("Handschrifterkennung (TrOCR + EasyOCR)" if trocr
                  else "Handschrifterkennung (EasyOCR)")
        return ("\n\n".join(seiten_texte).strip(),
                {"quelle": quelle, "seiten": len(bilder),
                 "unsicher": unsicher})

    def _lade_easyocr(self):
        try:
            import easyocr
        except ImportError:
            raise RuntimeError(
                "Für die Handschrifterkennung bitte einmalig installieren:\n"
                "pip install easyocr\n"
                "(Beim ersten Start werden die Erkennungsmodelle "
                "heruntergeladen.)")
        self.status_melden("Lade Erkennungsmodell (erster Start: "
                           "Modell-Download) …")
        return easyocr.Reader(["en"], gpu=False, verbose=False)

    def _lade_trocr(self):
        """Optionales Handschrift-Spezialmodell; None, wenn transformers/
        torch nicht installiert sind."""
        try:
            from transformers import (TrOCRProcessor,
                                      VisionEncoderDecoderModel)
        except ImportError:
            return None
        try:
            self.status_melden("Lade TrOCR-Handschriftmodell (erster "
                               "Start: Modell-Download) …")
            name = "microsoft/trocr-base-handwritten"
            return {"prozessor": TrOCRProcessor.from_pretrained(name),
                    "modell": VisionEncoderDecoderModel.from_pretrained(name)}
        except Exception:
            return None

    @staticmethod
    def _trocr_zeile(trocr, bild, zeile):
        """Liest eine per EasyOCR gefundene Zeile mit TrOCR nach."""
        try:
            rand = 4
            x0 = max(0, int(min(w["x0"] for w in zeile)) - rand)
            y0 = max(0, int(min(w["y0"] for w in zeile)) - rand)
            x1 = min(bild.width, int(max(w["x1"] for w in zeile)) + rand)
            y1 = min(bild.height, int(max(w["y1"] for w in zeile)) + rand)
            if x1 - x0 < 8 or y1 - y0 < 8:
                return None
            ausschnitt = bild.crop((x0, y0, x1, y1))
            pixel = trocr["prozessor"](images=ausschnitt,
                                       return_tensors="pt").pixel_values
            ids = trocr["modell"].generate(pixel, max_new_tokens=96)
            text = trocr["prozessor"].batch_decode(
                ids, skip_special_tokens=True)[0].strip()
            return text or None
        except Exception:
            return None

    @staticmethod
    def _zeilen_gruppieren(ergebnisse):
        """Ordnet EasyOCR-Funde (Box, Text, Konfidenz) zu Textzeilen:
        Woerter mit aehnlicher vertikaler Lage bilden eine Zeile, innerhalb
        der Zeile wird von links nach rechts sortiert."""
        woerter = []
        for bbox, text, conf in ergebnisse:
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            if not text.strip():
                continue
            woerter.append({"text": text.strip(), "conf": float(conf),
                            "x0": min(xs), "x1": max(xs),
                            "y0": min(ys), "y1": max(ys),
                            "ym": (min(ys) + max(ys)) / 2.0})
        woerter.sort(key=lambda w: w["ym"])
        zeilen = []
        for w in woerter:
            ziel = None
            for zeile in zeilen:
                mitte = sum(z["ym"] for z in zeile) / len(zeile)
                hoehe = sum(z["y1"] - z["y0"] for z in zeile) / len(zeile)
                if abs(w["ym"] - mitte) <= 0.6 * max(hoehe,
                                                     w["y1"] - w["y0"]):
                    ziel = zeile
                    break
            if ziel is None:
                zeilen.append([w])
            else:
                ziel.append(w)
        for zeile in zeilen:
            zeile.sort(key=lambda z: z["x0"])
        zeilen.sort(key=lambda zeile: sum(z["ym"] for z in zeile) / len(zeile))
        return zeilen


# ----------------------------------------------------------------------------
# Bereich A: Sprachliche Richtigkeit (Lexik, Grammatik/Syntax, Orthographie)
# ----------------------------------------------------------------------------

# Ankerpunkte: (gewertete Fehler je 100 Woerter -> Notenpunkte), dazwischen
# wird linear interpoliert. Ueber den Erwartungshorizont anpassbar
# ("richtigkeit_anker": [[0,15],[0.5,13.5],...]).
RICHTIGKEIT_ANKER = [(0.0, 15.0), (0.5, 13.5), (1.5, 11.0), (3.0, 8.0),
                     (5.0, 5.0), (8.0, 2.0), (12.0, 0.0)]


def dichte_zu_note(dichte, anker=None):
    anker = anker or RICHTIGKEIT_ANKER
    if dichte <= anker[0][0]:
        return anker[0][1]
    for (d1, n1), (d2, n2) in zip(anker, anker[1:]):
        if dichte <= d2:
            anteil = (dichte - d1) / (d2 - d1)
            return n1 + anteil * (n2 - n1)
    return anker[-1][1]


def bewerte_richtigkeit(fehlerliste, wortzahl, anker=None):
    """Automatischer Befund + Notenvorschlag je Kriterium des Bereichs A."""
    ergebnis = {}
    for kriterium in KRITERIEN_RICHTIGKEIT:
        relevant = [f for f in fehlerliste if f["kriterium"] == kriterium]
        gewertet = [f for f in relevant if not f["wiederholung"]]
        wiederholungen = len(relevant) - len(gewertet)
        summe = sum(f["gewicht"] for f in gewertet)
        dichte = summe / wortzahl * 100.0 if wortzahl else 0.0
        note = dichte_zu_note(dichte, anker)
        band, spanne = band_fuer_note(note)
        befund = (f"{len(gewertet)} gewertete Auffälligkeiten "
                  f"(gewichtet {summe:g}; {dichte:.2f} je 100 Wörter)")
        if wiederholungen:
            befund += (f"; {wiederholungen} Wiederholungsfehler "
                       f"nicht gewertet")
        ergebnis[kriterium] = {
            "note": round(note, 1), "band": band, "spanne": spanne,
            "befund": befund, "automatisch": True,
        }
    return ergebnis


# ----------------------------------------------------------------------------
# Bereich B: Ausdruck und Textgestaltung (automatische Indikatoren)
# ----------------------------------------------------------------------------

KONNEKTOREN = [
    "however", "therefore", "moreover", "furthermore", "in addition",
    "firstly", "secondly", "thirdly", "finally", "in conclusion",
    "on the one hand", "on the other hand", "thus", "consequently",
    "nevertheless", "nonetheless", "in contrast", "by contrast",
    "for example", "for instance", "to sum up", "first of all",
    "as a result", "whereas", "although", "admittedly", "in summary",
    "to begin with", "above all", "in particular", "similarly",
]

SUBORDINATOREN = [
    "because", "although", "though", "which", "who", "whose", "whom",
    "if", "unless", "whereas", "while", "despite", "in spite of",
    "so that", "even though", "as if", "since", "until", "whenever",
    "provided that", "as long as",
]

UMGANGSSPRACHE = [
    "gonna", "wanna", "gotta", "kinda", "sorta", "stuff", "guys",
    "okay", "ok", "cool", "awesome", "totally", "super", "really really",
]

KONTRAKTIONEN = re.compile(
    r"\b\w+(?:n't|'re|'ve|'ll|'m|'d)\b", re.IGNORECASE)


def _saetze(text):
    saetze = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
              if s.strip()]
    return saetze or [text]


def _absaetze(text):
    absaetze = [a for a in re.split(r"\n\s*\n", text) if a.strip()]
    if len(absaetze) <= 1:
        absaetze = [a for a in text.split("\n") if a.strip()]
    return absaetze


def _zaehle_phrasen(text_klein, phrasen):
    return sum(len(re.findall(r"\b" + re.escape(p) + r"\b", text_klein))
               for p in phrasen)


def bewerte_ausdruck(text, fehlerliste, wortzahl):
    """Automatische Indikatoren + Notenvorschlaege fuer Bereich B.
    Diese Kriterien sind maschinell nur naeherungsweise beurteilbar -
    die Vorschlaege sind zum Uebersteuern durch die Lehrkraft gedacht."""
    text_klein = text.lower()
    saetze = _saetze(text)
    absaetze = _absaetze(text)
    tokens = re.findall(r"[a-z'’-]+", text_klein)
    ergebnis = {}

    # --- Textaufbau ---
    konnektoren = _zaehle_phrasen(text_klein, KONNEKTOREN)
    kd = konnektoren / wortzahl * 100.0 if wortzahl else 0.0
    note = 8.0
    note += 2.0 if len(absaetze) >= 3 else (0.0 if len(absaetze) == 2 else -2.0)
    if kd >= 1.5:
        note += 3.0
    elif kd >= 0.8:
        note += 2.0
    elif kd >= 0.4:
        note += 1.0
    else:
        note -= 2.0
    note = max(0.0, min(15.0, note))
    band, spanne = band_fuer_note(note)
    ergebnis["textaufbau"] = {
        "note": round(note, 1), "band": band, "spanne": spanne,
        "befund": (f"{len(absaetze)} Absätze, {konnektoren} "
                   f"textstrukturierende Mittel ({kd:.2f} je 100 Wörter). "
                   f"Textsortenmerkmale bitte manuell prüfen."),
        "automatisch": True,
    }

    # --- Eigenstaendige Textgestaltung (maschinell nicht pruefbar) ---
    zitate = text.count('"') // 2 + text.count("“")
    band, spanne = band_fuer_note(11.0)
    ergebnis["eigenstaendigkeit"] = {
        "note": 11.0, "band": band, "spanne": spanne,
        "befund": (f"Automatisch nicht beurteilbar (Abgleich mit Materialien "
                   f"erforderlich). Im Text erkennbar: "
                   f"{zitate} Zitat-Markierung(en). Bitte manuell einstufen; "
                   f"Voreinstellung: „gut“."),
        "automatisch": False,
    }

    # --- Sprachregister (Annahme: formeller Schreibauftrag) ---
    kontraktionen = len(KONTRAKTIONEN.findall(text))
    umgang = _zaehle_phrasen(text_klein, UMGANGSSPRACHE)
    ausrufe = text.count("!")
    marker = kontraktionen + umgang * 2 + ausrufe
    md = marker / wortzahl * 100.0 if wortzahl else 0.0
    if md == 0:
        note = 14.0
    elif md <= 0.5:
        note = 11.0
    elif md <= 1.5:
        note = 8.0
    elif md <= 3.0:
        note = 5.0
    elif md <= 5.0:
        note = 2.0
    else:
        note = 0.0
    band, spanne = band_fuer_note(note)
    ergebnis["register"] = {
        "note": round(note, 1), "band": band, "spanne": spanne,
        "befund": (f"Register-Marker (Annahme: formeller Text): "
                   f"{kontraktionen} Kontraktionen, {umgang} "
                   f"umgangssprachliche Ausdrücke, {ausrufe} Ausrufezeichen "
                   f"({md:.2f} je 100 Wörter). Bei informeller Textsorte "
                   f"(z. B. persönlicher Brief) bitte übersteuern."),
        "automatisch": True,
    }

    # --- Wortschatz (lexikalische Vielfalt: Guiraud-Index) ---
    typen = len(set(tokens))
    guiraud = typen / math.sqrt(len(tokens)) if tokens else 0.0
    stufen = [(8.5, 14.0), (7.5, 12.0), (6.5, 10.0), (5.5, 8.0),
              (4.5, 6.0), (3.5, 4.0)]
    note = 2.0
    for schwelle, n in stufen:
        if guiraud >= schwelle:
            note = n
            break
    band, spanne = band_fuer_note(note)
    ergebnis["wortschatz"] = {
        "note": round(note, 1), "band": band, "spanne": spanne,
        "befund": (f"Lexikalische Vielfalt: {typen} verschiedene Wörter bei "
                   f"{len(tokens)} Wörtern (Guiraud-Index {guiraud:.2f}). "
                   f"Idiomatik/Präzision bitte manuell würdigen."),
        "automatisch": True,
    }

    # --- Satzbau ---
    laengen = [len(re.findall(r"[A-Za-z'’-]+", s)) for s in saetze]
    mittel = sum(laengen) / len(laengen) if laengen else 0.0
    varianz = (sum((l - mittel) ** 2 for l in laengen) / len(laengen)
               if laengen else 0.0)
    streuung = math.sqrt(varianz)
    komplexe = sum(1 for s in saetze
                   if any(re.search(r"\b" + re.escape(sub) + r"\b", s.lower())
                          for sub in SUBORDINATOREN))
    komplex_anteil = komplexe / len(saetze) if saetze else 0.0
    note = 8.0
    if komplex_anteil >= 0.5:
        note += 3.0
    elif komplex_anteil >= 0.3:
        note += 2.0
    elif komplex_anteil >= 0.15:
        note += 1.0
    else:
        note -= 2.0
    if streuung >= 6.0:
        note += 2.0
    elif streuung >= 3.0:
        note += 1.0
    if 10.0 <= mittel <= 25.0:
        note += 1.0
    note = max(0.0, min(15.0, note))
    band, spanne = band_fuer_note(note)
    ergebnis["satzbau"] = {
        "note": round(note, 1), "band": band, "spanne": spanne,
        "befund": (f"{len(saetze)} Sätze, Ø {mittel:.1f} Wörter "
                   f"(Streuung {streuung:.1f}); {komplexe} Sätze "
                   f"({komplex_anteil:.0%}) mit Nebensatz-/"
                   f"Hypotaxe-Signalen."),
        "automatisch": True,
    }
    return ergebnis


# ----------------------------------------------------------------------------
# Sprachliche Leistung: Zusammenfuehrung nach Erlass
# ----------------------------------------------------------------------------

def sprachnote_bilden(noten):
    """noten: dict kriterium -> Notenwert (0-15).
    Bereich A und Bereich B werden jeweils ganzheitlich (Mittel der
    Kriterien) gebildet und im Verhaeltnis 50:50 zusammengefuehrt;
    eine Dezimalstelle wird nicht gerundet."""
    bereich_a = sum(noten[k] for k in KRITERIEN_RICHTIGKEIT) / len(
        KRITERIEN_RICHTIGKEIT)
    bereich_b = sum(noten[k] for k in KRITERIEN_AUSDRUCK) / len(
        KRITERIEN_AUSDRUCK)
    note = trunc1((bereich_a + bereich_b) / 2.0)
    return {
        "bereich_a": trunc1(bereich_a),
        "bereich_b": trunc1(bereich_b),
        "note": note,
        "band": band_fuer_note(note)[0],
    }


def gesamtnote_bilden(sprachnote, inhaltsnote):
    """Erlass: Gesamtnote = Sprache:Inhalt 60:40, nur hier wird gerundet.
    Sperrklausel: ungenuegende (0 Punkte) sprachliche oder inhaltliche
    Leistung -> hoechstens 3 Punkte."""
    roh = 0.6 * sprachnote + 0.4 * inhaltsnote
    gesamt = kaufmaennisch_runden(roh)
    gedeckelt = False
    if (sprachnote < 1.0 or inhaltsnote < 1.0) and gesamt > 3:
        gesamt = 3
        gedeckelt = True
    return {"roh": round(roh, 2), "punkte": gesamt, "gedeckelt": gedeckelt}


# ----------------------------------------------------------------------------
# Inhaltliche Pruefung gegen den Erwartungshorizont
# ----------------------------------------------------------------------------

def _tokens_inhalt(text):
    return re.findall(r"[a-zäöüß'’-]+", text.lower())


def _begriff_gefunden(begriff, text_klein, tokenliste):
    begriff = begriff.strip().lower()
    if not begriff:
        return False
    muster = r"\b" + r"\s+".join(re.escape(w) for w in begriff.split()) + r"\w*"
    if re.search(muster, text_klein):
        return True
    if " " not in begriff and len(begriff) >= 5:
        return bool(difflib.get_close_matches(begriff, tokenliste, n=1,
                                              cutoff=0.86))
    return False


def inhaltliche_bewertung(erwartungshorizont, schuelertext):
    text_klein = schuelertext.lower()
    tokenliste = _tokens_inhalt(schuelertext)

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

        if summe_teilpunkte > 0 and max_punkte > 0:
            erreicht = erreicht / summe_teilpunkte * max_punkte
        gesamt_max += max_punkte
        gesamt_erreicht += erreicht
        aufgaben_ergebnisse.append({
            "nummer": str(aufgabe.get("nummer", "?")),
            "titel": aufgabe.get("titel", ""),
            "max_punkte": max_punkte,
            "erreicht": round(erreicht, 1),
            "prozent": round(erreicht / max_punkte * 100, 1)
            if max_punkte else 0.0,
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
# Gutachten
# ----------------------------------------------------------------------------

def erstelle_gutachten(horizont, inhalt, kriterien, sprach, gesamt,
                       wortzahl, schueler_name=""):
    z = []
    z.append("GUTACHTEN" + (f" – {schueler_name}" if schueler_name else ""))
    z.append(f"Klausur: {horizont.get('titel', 'ohne Titel')}")
    z.append("Bewertungsgrundlage: Erlass HKM vom 07.08.2020 "
             "(Deskriptorentabelle, Sprache:Inhalt = 60:40)")
    z.append("")

    z.append("I. Sprachliche Leistung")
    z.append("-" * 60)
    z.append(f"Umfang: {wortzahl} Wörter.")
    z.append("")
    z.append("Bereich A – Sprachliche Richtigkeit "
             f"(ganzheitlich: {sprach['bereich_a']} Punkte):")
    for k in KRITERIEN_RICHTIGKEIT:
        e = kriterien[k]
        z.append(f"  {KRITERIEN_NAMEN[k]}: {e['band']} ({e['spanne']}) – "
                 f"{DESKRIPTOREN[k][e['band']]}")
    z.append("")
    z.append("Bereich B – Ausdruck und Textgestaltung "
             f"(ganzheitlich: {sprach['bereich_b']} Punkte):")
    for k in KRITERIEN_AUSDRUCK:
        e = kriterien[k]
        z.append(f"  {KRITERIEN_NAMEN[k]}: {e['band']} ({e['spanne']}) – "
                 f"{DESKRIPTOREN[k][e['band']]}")
    z.append("")
    z.append(f"Sprachliche Leistung (A:B = 50:50, Dezimalstelle nicht "
             f"gerundet): {sprach['note']} Punkte ({sprach['band']}).")
    z.append("")

    z.append("II. Inhaltliche Leistung")
    z.append("-" * 60)
    for a in inhalt["aufgaben"]:
        z.append(f"Aufgabe {a['nummer']} – {a['titel']}: "
                 f"{a['erreicht']}/{a['max_punkte']} Punkte ({a['prozent']} %).")
        voll = [d for d in a["details"]
                if d["punkte_erreicht"] >= d["punkte_max"] * 0.999]
        teils = [d for d in a["details"]
                 if 0 < d["punkte_erreicht"] < d["punkte_max"] * 0.999]
        fehlt = [d for d in a["details"] if d["punkte_erreicht"] == 0]
        if voll:
            z.append("  Erfüllt: " + "; ".join(d["beschreibung"] for d in voll))
        if teils:
            z.append("  Teilweise erfüllt: "
                     + "; ".join(d["beschreibung"] for d in teils))
        if fehlt:
            z.append("  Nicht nachgewiesen: "
                     + "; ".join(d["beschreibung"] for d in fehlt))
    z.append(f"Inhaltliche Leistung gesamt: {inhalt['erreicht']}/"
             f"{inhalt['max_punkte']} Punkte = {inhalt['prozent']} % → "
             f"{inhalt['notenpunkte']} Punkte.")
    z.append("")

    z.append("III. Gesamtnote")
    z.append("-" * 60)
    z.append(f"Sprachliche Leistung {sprach['note']} Punkte × 0,6 + "
             f"inhaltliche Leistung {inhalt['notenpunkte']} Punkte × 0,4 "
             f"= {gesamt['roh']} → gerundet: {gesamt['punkte']} Punkte.")
    if gesamt["gedeckelt"]:
        z.append("Sperrklausel angewendet: Eine ungenügende sprachliche oder "
                 "inhaltliche Leistung schließt eine Gesamtnote von mehr als "
                 "drei Punkten aus.")
    z.append("")
    z.append("Hinweis: Automatisch erstellter Vorschlag. Die Einstufungen im "
             "Bereich „Ausdruck und Textgestaltung“ sowie die inhaltliche "
             "Prüfung (Schlüsselwort-Abgleich) sind Näherungen und im "
             "Programm manuell übersteuerbar. Die endgültige Bewertung "
             "obliegt der Lehrkraft.")
    return "\n".join(z)


# ----------------------------------------------------------------------------
# Grafische Oberflaeche
# ----------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITEL)
        self.geometry("1200x800")
        self.minsize(950, 640)

        self.horizont = None
        self.analyse = None   # dict mit fehlerliste, kriterien, inhalt, ...
        self._queue = queue.Queue()
        self._kriterium_wahl = {}   # kriterium -> (Combobox, Label)

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

        self.text_schueler = self._neuer_texttab("Schülertext",
                                                 schreibbar=True)
        self.text_korrekturen = self._neuer_texttab("Korrekturen")
        self._baue_deskriptor_tab()
        self.text_inhalt = self._neuer_texttab("Inhaltliche Bewertung")
        self.text_gutachten = self._neuer_texttab("Gesamtgutachten")

        self.status = ttk.Label(self, relief=tk.SUNKEN, anchor=tk.W,
                                padding=4,
                                text="Bereit. Erwartungshorizont und "
                                     "Schülertext laden, dann Prüfung "
                                     "starten.")
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

    def _baue_deskriptor_tab(self):
        """Reiter 'Sprachliche Leistung': je Kriterium der Deskriptorentabelle
        automatischer Befund, Band-Auswahl (uebersteuerbar) und der
        Original-Deskriptor des gewaehlten Bandes."""
        aussen = ttk.Frame(self.mappe)
        self.mappe.add(aussen, text="Sprachliche Leistung")

        kopf = ttk.Frame(aussen, padding=(8, 6))
        kopf.pack(side=tk.TOP, fill=tk.X)
        self.sprachnote_label = ttk.Label(
            kopf, font=("Segoe UI", 11, "bold"),
            text="Noch keine Prüfung durchgeführt.")
        self.sprachnote_label.pack(side=tk.LEFT)
        ttk.Button(kopf, text="Note aus Auswahl neu berechnen",
                   command=self.neu_berechnen).pack(side=tk.RIGHT)

        leinwand = tk.Canvas(aussen, highlightthickness=0)
        rollbalken = ttk.Scrollbar(aussen, orient="vertical",
                                   command=leinwand.yview)
        self.deskriptor_rahmen = ttk.Frame(leinwand, padding=8)
        self.deskriptor_rahmen.bind(
            "<Configure>",
            lambda e: leinwand.configure(scrollregion=leinwand.bbox("all")))
        fenster = leinwand.create_window((0, 0),
                                         window=self.deskriptor_rahmen,
                                         anchor="nw")
        leinwand.bind("<Configure>",
                      lambda e: leinwand.itemconfigure(fenster, width=e.width))
        leinwand.configure(yscrollcommand=rollbalken.set)
        leinwand.bind_all(
            "<MouseWheel>",
            lambda e: leinwand.yview_scroll(int(-e.delta / 120), "units"))
        rollbalken.pack(side=tk.RIGHT, fill=tk.Y)
        leinwand.pack(fill=tk.BOTH, expand=True)

        band_werte = [f"{name} ({spanne})" for name, spanne, _w, _u in BAENDER]

        def bereich_ueberschrift(text):
            ttk.Label(self.deskriptor_rahmen, text=text,
                      font=("Segoe UI", 12, "bold")
                      ).pack(anchor=tk.W, pady=(10, 2))

        def kriterium_zeile(kriterium):
            box = ttk.LabelFrame(self.deskriptor_rahmen,
                                 text=KRITERIEN_NAMEN[kriterium], padding=6)
            box.pack(fill=tk.X, pady=3)
            befund = ttk.Label(box, text="–", wraplength=1000,
                               foreground="#444444")
            befund.pack(anchor=tk.W)
            zeile = ttk.Frame(box)
            zeile.pack(anchor=tk.W, fill=tk.X, pady=(4, 0))
            ttk.Label(zeile, text="Einstufung:").pack(side=tk.LEFT)
            wahl = ttk.Combobox(zeile, width=34, state="readonly",
                                values=band_werte)
            wahl.pack(side=tk.LEFT, padx=6)
            deskriptor = ttk.Label(box, text="", wraplength=1000,
                                   font=("Segoe UI", 9, "italic"))
            deskriptor.pack(anchor=tk.W, pady=(4, 0))

            def zeige_deskriptor(_ereignis=None):
                band = wahl.get().rsplit(" (", 1)[0]
                if band in DESKRIPTOREN[kriterium]:
                    deskriptor.configure(
                        text="Deskriptor: " + DESKRIPTOREN[kriterium][band])
            wahl.bind("<<ComboboxSelected>>", zeige_deskriptor)
            self._kriterium_wahl[kriterium] = (wahl, befund, deskriptor)

        bereich_ueberschrift("Bereich A – Sprachliche Richtigkeit "
                             "(automatisch aus der Fehleranalyse)")
        for k in KRITERIEN_RICHTIGKEIT:
            kriterium_zeile(k)
        bereich_ueberschrift("Bereich B – Ausdruck und Textgestaltung "
                             "(Vorschläge – bitte prüfen und ggf. "
                             "übersteuern)")
        for k in KRITERIEN_AUSDRUCK:
            kriterium_zeile(k)

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
        if horizont.get("sprache") in ("en-GB", "en-US"):
            self.sprach_wahl.set(horizont["sprache"])
        anzahl = len(horizont["aufgaben"])
        maxp = sum(float(a.get("max_punkte", 0)) for a in horizont["aufgaben"])
        self.info_horizont.configure(
            text=f"Erwartungshorizont: „{horizont.get('titel', pfad)}“ – "
                 f"{anzahl} Aufgabe(n), {maxp:g} inhaltliche Punkte "
                 f"(Optimum = 15 Notenpunkte). Verrechnung 60:40 nach "
                 f"Erlass.")
        self.status.configure(text="Erwartungshorizont geladen.")

    def lade_schuelertext(self):
        pfad = filedialog.askopenfilename(
            title="Schülertext wählen (Text, Word, PDF oder Foto)",
            filetypes=[("Alle unterstützten Formate",
                        "*.txt *.md *.docx *.pdf *.png *.jpg *.jpeg"),
                       ("Text/Word", "*.txt *.md *.docx"),
                       ("PDF (auch handschriftlich)", "*.pdf"),
                       ("Fotos/Scans", "*.png *.jpg *.jpeg"),
                       ("Alle Dateien", "*.*")])
        if not pfad:
            return
        endung = pfad.lower().rsplit(".", 1)[-1]
        if endung in ("pdf", "png", "jpg", "jpeg"):
            self.knopf_pruefen.configure(state=tk.DISABLED)
            self.status.configure(
                text="Dokument wird eingelesen … (Handschrifterkennung "
                     "kann beim ersten Start einige Minuten dauern: "
                     "Modell-Download)")
            threading.Thread(target=self._lade_dokument_im_hintergrund,
                             args=(pfad,), daemon=True).start()
            return
        try:
            if endung == "docx":
                inhalt = self._lese_docx(pfad)
            else:
                with open(pfad, encoding="utf-8", errors="replace") as datei:
                    inhalt = datei.read()
        except Exception as fehler:
            messagebox.showerror("Fehler beim Laden",
                                 f"Datei konnte nicht gelesen werden:\n"
                                 f"{fehler}")
            return
        self._setze_text(self.text_schueler, inhalt)
        self.mappe.select(0)
        self.status.configure(
            text=f"Schülertext geladen ({woerter_zaehlen(inhalt)} Wörter).")

    def _lade_dokument_im_hintergrund(self, pfad):
        try:
            loader = KlausurLoader(
                lambda text: self._queue.put(("status", text)))
            text, protokoll = loader.lese(pfad)
            self._queue.put(("dokument", (text, protokoll)))
        except Exception as fehler:
            self._queue.put(("ladefehler", str(fehler)))

    def _zeige_dokument(self, text, protokoll):
        self.knopf_pruefen.configure(state=tk.NORMAL)
        if not text.strip():
            messagebox.showwarning(
                "Nichts erkannt",
                "Im Dokument konnte kein Text erkannt werden. Tipps: mit "
                "300 dpi und gutem Kontrast scannen, Seiten gerade "
                "ausrichten, dunkle Tinte auf hellem Papier.")
            self.status.configure(text="Keine Texterkennung möglich.")
            return
        self._setze_text(self.text_schueler, text)
        self.mappe.select(0)
        unsicher = protokoll.get("unsicher", [])
        meldung = (f"Quelle: {protokoll['quelle']}, "
                   f"{protokoll['seiten']} Seite(n), "
                   f"{woerter_zaehlen(text)} Wörter erkannt.")
        if protokoll["quelle"] != "PDF-Textebene":
            beispiele = ", ".join(
                f"„{wort}“ (S. {seite})" for seite, wort, _k in unsicher[:12])
            if unsicher:
                meldung += (f"\n\n{len(unsicher)} Wörter wurden unsicher "
                            f"erkannt, z. B.: {beispiele}")
            meldung += ("\n\nWICHTIG: Bitte den erkannten Text im Reiter "
                        "„Schülertext“ mit der Klausur abgleichen und "
                        "korrigieren, BEVOR die Prüfung gestartet wird – "
                        "Erkennungsfehler würden sonst als Sprachfehler "
                        "der Schülerin/des Schülers gewertet.")
        messagebox.showinfo("Dokument eingelesen", meldung)
        self.status.configure(
            text=f"{meldung.splitlines()[0]} Bitte Text prüfen, dann "
                 f"Prüfung starten.")

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
                                   "Bitte zuerst den Erwartungshorizont "
                                   "(JSON) laden.")
            return
        text = self.text_schueler.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Kein Text",
                                   "Bitte zuerst einen Schülertext laden "
                                   "oder einfügen.")
            return
        self.knopf_pruefen.configure(state=tk.DISABLED)
        self.status.configure(text="Prüfung läuft … (LanguageTool, "
                                   "Deskriptoren-Analyse, Inhaltsabgleich)")
        threading.Thread(target=self._pruefe_im_hintergrund,
                         args=(text, self.sprach_wahl.get()),
                         daemon=True).start()

    def _pruefe_im_hintergrund(self, text, sprache):
        try:
            wortzahl = woerter_zaehlen(text)
            fehlerliste = SprachPruefung(sprache).pruefe(text)
            anker = self.horizont.get("richtigkeit_anker")
            anker = [tuple(a) for a in anker] if anker else None
            kriterien = {}
            kriterien.update(bewerte_richtigkeit(fehlerliste, wortzahl,
                                                 anker))
            kriterien.update(bewerte_ausdruck(text, fehlerliste, wortzahl))
            inhalt = inhaltliche_bewertung(self.horizont, text)
            self._queue.put(("fertig", {
                "text": text, "wortzahl": wortzahl,
                "fehlerliste": fehlerliste, "kriterien": kriterien,
                "inhalt": inhalt,
            }))
        except Exception as fehler:
            self._queue.put(("fehler", str(fehler)))

    def _verarbeite_queue(self):
        try:
            while True:
                art, daten = self._queue.get_nowait()
                if art == "fertig":
                    self._zeige_ergebnis(daten)
                elif art == "status":
                    self.status.configure(text=daten)
                elif art == "dokument":
                    self._zeige_dokument(*daten)
                elif art == "ladefehler":
                    self.knopf_pruefen.configure(state=tk.NORMAL)
                    self.status.configure(text="Einlesen fehlgeschlagen.")
                    messagebox.showerror("Einlesen fehlgeschlagen", daten)
                else:
                    self.knopf_pruefen.configure(state=tk.NORMAL)
                    self.status.configure(text="Prüfung fehlgeschlagen.")
                    messagebox.showerror(
                        "Prüfung fehlgeschlagen",
                        f"{daten}\n\nHinweise:\n"
                        f"– Für die Online-Prüfung wird eine "
                        f"Internetverbindung benötigt (kostenlose "
                        f"LanguageTool-API).\n"
                        f"– Alternativ einmalig installieren: "
                        f"pip install language_tool_python (benötigt Java).")
        except queue.Empty:
            pass
        self.after(100, self._verarbeite_queue)

    # ---------------- Ergebnis & Neuberechnung ----------------

    def _zeige_ergebnis(self, analyse):
        self.analyse = analyse
        for kriterium, ergebnis in analyse["kriterien"].items():
            wahl, befund, deskriptor = self._kriterium_wahl[kriterium]
            befund.configure(
                text=("Automatischer Befund: " if ergebnis["automatisch"]
                      else "Hinweis: ") + ergebnis["befund"]
                + f"  →  Vorschlag: {ergebnis['band']} "
                  f"({ergebnis['note']:g} P)")
            wahl.set(f"{ergebnis['band']} ({ergebnis['spanne']})")
            deskriptor.configure(
                text="Deskriptor: " + DESKRIPTOREN[kriterium][ergebnis["band"]])
        self._setze_text(self.text_korrekturen,
                         self._format_korrekturen(analyse["fehlerliste"]))
        self._setze_text(self.text_inhalt,
                         self._format_inhalt(analyse["inhalt"]))
        self.knopf_pruefen.configure(state=tk.NORMAL)
        self.neu_berechnen(erste_berechnung=True)
        self.mappe.select(2)

    def _gewaehlte_noten(self):
        """Liest die Band-Auswahl je Kriterium; solange die Auswahl dem
        automatischen Vorschlag entspricht, wird dessen Dezimalnote genutzt,
        sonst der Repraesentativwert des gewaehlten Bandes."""
        noten = {}
        baender = {}
        for kriterium, (wahl, _b, _d) in self._kriterium_wahl.items():
            band = wahl.get().rsplit(" (", 1)[0]
            vorschlag = self.analyse["kriterien"][kriterium]
            if band == vorschlag["band"]:
                noten[kriterium] = float(vorschlag["note"])
            else:
                noten[kriterium] = band_wert(band)
            baender[kriterium] = band
        return noten, baender

    def neu_berechnen(self, erste_berechnung=False):
        if not self.analyse:
            messagebox.showwarning("Keine Prüfung",
                                   "Bitte zuerst eine Prüfung durchführen.")
            return
        noten, baender = self._gewaehlte_noten()
        sprach = sprachnote_bilden(noten)
        inhalt = self.analyse["inhalt"]
        gesamt = gesamtnote_bilden(sprach["note"],
                                   float(inhalt["notenpunkte"]))

        kriterien_angezeigt = {}
        for kriterium, ergebnis in self.analyse["kriterien"].items():
            angezeigt = dict(ergebnis)
            angezeigt["band"] = baender[kriterium]
            for name, spanne, _w, _u in BAENDER:
                if name == baender[kriterium]:
                    angezeigt["spanne"] = spanne
            angezeigt["note"] = noten[kriterium]
            kriterien_angezeigt[kriterium] = angezeigt
        self._kriterien_angezeigt = kriterien_angezeigt
        self._sprach = sprach
        self._gesamt = gesamt

        gutachten = erstelle_gutachten(
            self.horizont, inhalt, kriterien_angezeigt, sprach, gesamt,
            self.analyse["wortzahl"], self.name_feld.get().strip())
        self._setze_text(self.text_gutachten, gutachten)

        deckel = " (Sperrklausel!)" if gesamt["gedeckelt"] else ""
        self.sprachnote_label.configure(
            text=f"Bereich A: {sprach['bereich_a']} P   |   "
                 f"Bereich B: {sprach['bereich_b']} P   |   "
                 f"Sprachliche Leistung: {sprach['note']} P   |   "
                 f"Inhalt: {inhalt['notenpunkte']} P   |   "
                 f"GESAMT: {gesamt['punkte']} Punkte{deckel}")
        self.status.configure(
            text=f"{'Prüfung abgeschlossen' if erste_berechnung else 'Neu berechnet'}: "
                 f"Sprache {sprach['note']} P, Inhalt "
                 f"{inhalt['notenpunkte']} P → Gesamt "
                 f"{gesamt['punkte']} Punkte (60:40{deckel}).")

    # ---------------- Darstellung ----------------

    def _format_korrekturen(self, fehlerliste):
        if not fehlerliste:
            return "Keine Auffälligkeiten gefunden – sehr gut!"
        gewertet = sum(1 for f in fehlerliste if not f["wiederholung"])
        zeilen = [f"{len(fehlerliste)} Korrekturhinweise, davon {gewertet} "
                  f"gewertet (Wiederholungsfehler werden laut Erlass nicht "
                  f"gewertet):", ""]
        for nr, f in enumerate(fehlerliste, 1):
            zusatz = "  [Wiederholungsfehler – nicht gewertet]" \
                if f["wiederholung"] else ""
            zeilen.append(f"{nr}. [{f['kategorie']}] „{f['text']}“{zusatz}")
            zeilen.append(f"   Kontext: …{f['kontext']}…")
            zeilen.append(f"   Hinweis: {f['meldung']}")
            if f["vorschlaege"]:
                zeilen.append("   Vorschlag: " + ", ".join(f["vorschlaege"]))
            zeilen.append("")
        return "\n".join(zeilen)

    def _format_inhalt(self, inhalt):
        zeilen = ["INHALTLICHE BEWERTUNG (Abgleich mit dem "
                  "Erwartungshorizont)", "=" * 60, ""]
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
                    zeilen.append("           gefunden: "
                                  + ", ".join(d["gefunden"]))
                if d["fehlend"] and d["punkte_erreicht"] < d["punkte_max"] * 0.999:
                    zeilen.append("           nicht gefunden: "
                                  + ", ".join(d["fehlend"]))
            zeilen.append("")
        zeilen.append(f"Gesamt: {inhalt['erreicht']} / {inhalt['max_punkte']} "
                      f"Punkte = {inhalt['prozent']} % → "
                      f"{inhalt['notenpunkte']} Notenpunkte")
        return "\n".join(zeilen)

    def _format_deskriptoren(self):
        zeilen = ["SPRACHLICHE LEISTUNG NACH DESKRIPTORENTABELLE",
                  "=" * 60, ""]
        for bereich, kriterien in (
                ("Bereich A – Sprachliche Richtigkeit",
                 KRITERIEN_RICHTIGKEIT),
                ("Bereich B – Ausdruck und Textgestaltung",
                 KRITERIEN_AUSDRUCK)):
            zeilen.append(bereich)
            zeilen.append("-" * 60)
            for k in kriterien:
                e = self._kriterien_angezeigt[k]
                zeilen.append(f"{KRITERIEN_NAMEN[k]}: {e['band']} "
                              f"({e['spanne']})")
                zeilen.append(f"  Befund: {e['befund']}")
                zeilen.append(f"  Deskriptor: {DESKRIPTOREN[k][e['band']]}")
                zeilen.append("")
        s = self._sprach
        zeilen.append(f"Bereich A (ganzheitlich): {s['bereich_a']} Punkte")
        zeilen.append(f"Bereich B (ganzheitlich): {s['bereich_b']} Punkte")
        zeilen.append(f"Sprachliche Leistung (50:50, nicht gerundet): "
                      f"{s['note']} Punkte ({s['band']})")
        return "\n".join(zeilen)

    # ---------------- Export ----------------

    def exportiere_bericht(self):
        if not self.analyse or not hasattr(self, "_sprach"):
            messagebox.showwarning("Kein Ergebnis",
                                   "Bitte zuerst eine Prüfung durchführen.")
            return
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
            self.text_gutachten.get("1.0", tk.END).strip(),
            self._format_deskriptoren(),
            self._format_inhalt(self.analyse["inhalt"]),
            self._format_korrekturen(self.analyse["fehlerliste"]),
        ])
        with open(pfad, "w", encoding="utf-8") as datei:
            datei.write(bericht)
        self.status.configure(text=f"Bericht gespeichert: {pfad}")


if __name__ == "__main__":
    App().mainloop()
