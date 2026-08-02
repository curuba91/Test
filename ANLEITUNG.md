# Klausur-Bewertung Englisch (Oberstufe)

Ein kostenloses Programm (`klausur_bewertung.pyw`) zur Unterstützung bei der
Korrektur englischer Oberstufenklausuren.

**Wichtig:** Das Programm liefert *Vorschläge*. Die endgültige Bewertung bleibt
immer eine pädagogische Entscheidung der Lehrkraft.

## Was das Programm macht

1. **Erwartungshorizont einlesen** (JSON-Datei): beschreibt pro Aufgabe die
   erwarteten Inhalte. Der Horizont ist das Optimum und entspricht 15 Notenpunkten.
2. **Grammatik & Rechtschreibung prüfen**: über LanguageTool (kostenlos) werden
   alle Auffälligkeiten mit Kontext, Erklärung und Korrekturvorschlag gelistet.
3. **Sprachliche Bewertung**: aus der Fehlerdichte (gewichtete Fehler je 100
   Wörter) wird ein Prozentwert und daraus ein Notenpunktwert (0–15) berechnet.
4. **Inhaltliche Prüfung**: der Schülertext wird pro Aufgabe gegen die
   Erwartungen abgeglichen (Schlüsselwörter, tippfehlertolerant). Pro Aufgabe
   gibt es eine Punktzahl; erfüllte, teilweise erfüllte und fehlende
   Erwartungen werden ausgewiesen.
5. **Gesamtgutachten**: gewichtete Gesamtnote (Standard: 60 % Sprache / 40 %
   Inhalt, im Horizont einstellbar) plus ausformuliertes Gutachten. Alles
   lässt sich als Textdatei exportieren.

## Voraussetzungen

- **Python 3.8+** mit Tkinter (bei der normalen Windows-Installation von
  [python.org](https://www.python.org) enthalten).
- **Internetverbindung** für die kostenlose LanguageTool-API
  (max. ca. 20 Anfragen/Minute – für den Korrektureinsatz völlig ausreichend;
  lange Texte werden automatisch aufgeteilt).
- *Optional, für Prüfung ohne Internet:* `pip install language_tool_python`
  (benötigt Java). Das Programm nutzt die lokale Variante automatisch, wenn
  sie installiert ist.
- *Optional:* `pip install python-docx`, um Schülertexte direkt aus
  Word-Dateien (.docx) zu laden. Ohne dieses Paket bitte als .txt speichern.

## Start und Bedienung

1. Doppelklick auf `klausur_bewertung.pyw` (Windows startet es ohne
   Konsolenfenster).
2. **„1. Erwartungshorizont laden…“** – JSON-Datei wählen
   (Beispiel: `erwartungshorizont_beispiel.json`).
3. **„2. Schülertext laden…“** – .txt/.md/.docx wählen, oder den Text direkt
   in den Reiter „Schülertext“ einfügen/tippen.
4. **„3. Prüfung starten“** – Ergebnis erscheint in den Reitern
   *Korrekturen*, *Sprachliche Bewertung*, *Inhaltliche Bewertung* und
   *Gesamtgutachten*.
5. **„Bericht exportieren…“** speichert alles als Textdatei
   (z. B. zum Ausdrucken oder Anhängen an die Klausur).

## Aufbau des Erwartungshorizonts (JSON)

```json
{
  "titel": "Klausur Q1.1 – Globalization",
  "sprache": "en-GB",
  "gewichtung": { "inhalt": 0.4, "sprache": 0.6 },
  "sprachbewertung": { "abzug_pro_fehler_pro_100_woerter": 10 },
  "aufgaben": [
    {
      "nummer": "1",
      "titel": "Comprehension: …",
      "max_punkte": 12,
      "erwartungen": [
        {
          "beschreibung": "Nennt die zentrale These …",
          "punkte": 4,
          "schluesselwoerter": ["interconnected", "global trade"],
          "mindestens": 1
        }
      ]
    }
  ]
}
```

- **aufgaben**: beliebig viele Aufgaben, jede mit `max_punkte`.
- **erwartungen**: inhaltliche Teilerwartungen. Ab `mindestens` gefundenen
  Schlüsselwörtern gibt es die vollen `punkte`, darunter anteilig.
  Tipp: Synonyme und Umschreibungen als weitere Schlüsselwörter eintragen –
  je mehr Varianten, desto fairer der Abgleich.
- **gewichtung**: Anteil Inhalt/Sprache an der Gesamtnote
  (NRW-üblich für Englisch: Sprache 60 %, Inhalt 40 %).
- **sprachbewertung**: Strenge der Sprachnote. `10` bedeutet: pro gewichtetem
  Fehler je 100 Wörter werden 10 Prozentpunkte abgezogen.

Die Umrechnung Prozent → Notenpunkte folgt dem üblichen KMK-Schlüssel
(15 P ab 95 %, 14 P ab 90 %, … 1 P ab 20 %).

## Grenzen und Empfehlung

- Die **Sprachprüfung** (LanguageTool) ist ausgereift und findet die meisten
  Grammatik-, Rechtschreib- und Zeichensetzungsfehler zuverlässig.
- Die **inhaltliche Prüfung** basiert auf Schlüsselwort-Abgleich. Sie erkennt
  Umschreibungen, eigenständige Argumentationen oder fehlerhafte Logik nur
  begrenzt. Sie eignet sich als schnelle Erstsichtung („Welche erwarteten
  Aspekte tauchen auf, welche fehlen?“), nicht als endgültiges Urteil.
- Wer eine **echte semantische Inhaltsbewertung** möchte, kann das Programm
  später um ein lokales, kostenloses Sprachmodell (z. B. über
  [Ollama](https://ollama.com)) erweitern – datenschutzfreundlich, da
  Schülertexte den Rechner nicht verlassen. Für den Einstieg ist die
  vorliegende transparente, regelbasierte Lösung jedoch bewusst
  nachvollziehbar: Jeder Punkt ist begründbar.

## Datenschutz-Hinweis

Bei der Online-Prüfung wird der Schülertext an die LanguageTool-API
(languagetool.org, Server in Deutschland) übertragen. Wer das vermeiden
möchte: `pip install language_tool_python` installieren – dann läuft die
Prüfung vollständig lokal. Namen vor der Prüfung zu entfernen ist in jedem
Fall gute Praxis.
