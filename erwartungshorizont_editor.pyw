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

Start: Doppelklick (Windows: .pyw ohne Konsolenfenster). Benötigt nur
Python 3.8+ mit Tkinter.
"""

import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_TITEL = "Erwartungshorizont-Editor (Klausur-Bewertung Englisch)"

AUFGABE_MUSTER = re.compile(
    r"^\s*(?:Aufgabe|Task)\s*(\d+[a-z]?)\s*[.):–-]?\s*(.*)$", re.IGNORECASE)
AUFGABE_NUMMER_MUSTER = re.compile(r"^\s*(\d+[a-z]?)\s*[.)]\s+(.{10,})$")
PUNKTE_MUSTER = re.compile(
    r"\(?\s*(\d+(?:[.,]\d+)?)\s*(?:P\b|BE\b|Punkte?\b|Pkt\.?)\s*\)?",
    re.IGNORECASE)
MINDESTENS_MUSTER = re.compile(
    r"(?:min\.?|mindestens)\s*(\d+)", re.IGNORECASE)
KLAMMER_WOERTER_MUSTER = re.compile(r"\[([^\]]+)\]")
SCHLUESSEL_MUSTER = re.compile(
    r"(?:Schlüsselwörter|Schluesselwoerter|Keywords?)\s*[:=]\s*(.+)$",
    re.IGNORECASE)
AUFZAEHLUNG_MUSTER = re.compile(r"^\s*[-•*o▪]\s+")


def parse_erwartungshorizont(text, titel=""):
    """Wandelt frei formatierten Text in die JSON-Struktur um."""
    aufgaben = []
    aktuelle = None
    for zeile in text.splitlines():
        if not zeile.strip():
            continue

        treffer = AUFGABE_MUSTER.match(zeile)
        if not treffer and not AUFZAEHLUNG_MUSTER.match(zeile):
            treffer = AUFGABE_NUMMER_MUSTER.match(zeile)
        if treffer:
            aktuelle = {
                "nummer": treffer.group(1),
                "titel": treffer.group(2).strip() or f"Aufgabe {treffer.group(1)}",
                "max_punkte": 0.0,
                "erwartungen": [],
            }
            aufgaben.append(aktuelle)
            continue

        if aktuelle is None:
            # Text vor der ersten Aufgabe: als Titel verwenden, falls leer
            if not titel:
                titel = zeile.strip()
            continue

        aktuelle["erwartungen"].append(_parse_erwartung(zeile))

    for aufgabe in aufgaben:
        summe = sum(e["punkte"] for e in aufgabe["erwartungen"])
        aufgabe["max_punkte"] = summe if summe > 0 else float(
            len(aufgabe["erwartungen"]) * 2)

    return {
        "titel": titel or "Klausur",
        "sprache": "en-GB",
        "gewichtung": {"inhalt": 0.4, "sprache": 0.6},
        "aufgaben": aufgaben,
    }


def _parse_erwartung(zeile):
    rest = AUFZAEHLUNG_MUSTER.sub("", zeile).strip()

    schluesselwoerter = []
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

    rest = re.sub(r"[(),;]\s*$", "", rest).strip()
    rest = re.sub(r"\(\s*\)", "", rest).strip()

    return {
        "beschreibung": rest,
        "punkte": punkte,
        "schluesselwoerter": schluesselwoerter,
        "mindestens": mindestens,
    }


class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITEL)
        self.geometry("1250x780")
        self.minsize(1000, 600)
        self.daten = {"titel": "Klausur", "sprache": "en-GB",
                      "gewichtung": {"inhalt": 0.4, "sprache": 0.6},
                      "aufgaben": []}
        self._baue_oberflaeche()

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

        # Links: Texteingabe
        links = ttk.LabelFrame(haupt, text="1. Erwartungshorizont als Text "
                                           "einfügen", padding=6)
        haupt.add(links, weight=1)
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
        ohne_woerter = sum(
            1 for a in daten["aufgaben"] for e in a["erwartungen"]
            if not e["schluesselwoerter"])
        hinweis = (f" – {ohne_woerter} Erwartung(en) noch OHNE "
                   f"Schlüsselwörter (bitte ergänzen!)" if ohne_woerter
                   else "")
        self.status.configure(
            text=f"{len(daten['aufgaben'])} Aufgabe(n) erkannt{hinweis}.")

    def _baum_neu(self):
        self.baum.delete(*self.baum.get_children())
        for a_index, aufgabe in enumerate(self.daten["aufgaben"]):
            knoten = self.baum.insert(
                "", tk.END, iid=f"a{a_index}", open=True,
                text=f"Aufgabe {aufgabe['nummer']}: {aufgabe['titel']} "
                     f"({aufgabe['max_punkte']:g} P)")
            for e_index, erwartung in enumerate(aufgabe["erwartungen"]):
                fehlt = "" if erwartung["schluesselwoerter"] else "  ⚠ ohne Schlüsselwörter"
                self.baum.insert(
                    knoten, tk.END, iid=f"a{a_index}e{e_index}",
                    text=f"{erwartung['beschreibung']} "
                         f"({erwartung['punkte']:g} P, min. "
                         f"{erwartung['mindestens']}){fehlt}")
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
                erwartung["schluesselwoerter"] = [
                    s.strip() for s in w["f3"].get().split(",") if s.strip()]
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
