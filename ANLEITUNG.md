# Klausur-Bewertung Englisch (Oberstufe) – nach dem hessischen Erlass

Zwei kostenlose Programme zur Unterstützung bei der Korrektur englischer
Oberstufenklausuren:

| Datei | Zweck |
|---|---|
| `klausur_bewertung.pyw` | Klausur prüfen und bewerten (Sprache + Inhalt) |
| `erwartungshorizont_editor.pyw` | Erwartungshorizont als Text einfügen → JSON erzeugen |

**Bewertungsgrundlage:** Erlass des Hessischen Kultusministeriums zur
Bewertung und Beurteilung von schriftlichen Arbeiten in den modernen
Fremdsprachen vom 7. August 2020 (III.A.3 – 323.300.000-337) samt Anlage
„Deskriptorentabelle – Kriterien zur Bewertung der sprachlichen Leistung“.

**Wichtig:** Beide Programme liefern *Vorschläge*. Die endgültige Bewertung
bleibt immer die pädagogische Entscheidung der Lehrkraft.

## Das Bewertungsmodell (wie im Erlass)

1. **Sprachliche und inhaltliche Leistung werden getrennt bewertet.**
2. **Sprachliche Leistung** nach der Deskriptorentabelle aus zwei Bereichen
   im Verhältnis **50:50** (eine Dezimalstelle, *nicht* gerundet):
   - **Bereich A – Sprachliche Richtigkeit:** Lexik, Grammatik/Syntax,
     Orthographie
   - **Bereich B – Ausdruck und Textgestaltung:** Textaufbau/ggf.
     Textsortenspezifik, eigenständige Textgestaltung, Sprachregister,
     allgemeiner/thematischer/Funktions- und Interpretationswortschatz,
     Satzbau
   - Innerhalb der Bereiche wird **ganzheitlich** bewertet (keine Teilnoten
     je Kriterium). **Wiederholungsfehler werden nicht gewertet** – das
     Programm erkennt sie (gleiche Regel, gleiche Fehlstelle) und schließt
     sie automatisch aus.
3. **Gesamtnote = Sprache : Inhalt im Verhältnis 60:40**, gerundet wird
   *nur* hier.
4. **Sperrklausel:** Eine ungenügende sprachliche oder inhaltliche Leistung
   schließt eine Gesamtnote von mehr als 3 Punkten aus – wird automatisch
   angewendet und im Gutachten ausgewiesen.

## Was `klausur_bewertung.pyw` automatisch prüft

**Bereich A (verlässlich automatisierbar):** LanguageTool findet
Grammatik-, Lexik- und Orthographiefehler; jeder Fund wird dem passenden
Kriterium zugeordnet (Zeichensetzung/Typographie zählen halb – Primat der
gesprochenen Sprache). Aus der Dichte der *gewerteten* Fehler je 100 Wörter
wird je Kriterium ein Banding-Vorschlag (sehr gut 15-13 … ungenügend 0)
mit dem Original-Deskriptor der Tabelle ermittelt.

**Bereich B (Näherung – bitte prüfen):** Das Programm liefert messbare
Indikatoren und daraus abgeleitete Vorschläge:
- *Textaufbau:* Absatzstruktur, Dichte textstrukturierender Mittel
  (however, moreover, in conclusion …)
- *Eigenständige Textgestaltung:* maschinell nicht beurteilbar
  (Materialabgleich nötig) – Voreinstellung „gut“, bitte manuell einstufen
- *Sprachregister:* Kontraktionen, Umgangssprache, Ausrufezeichen
  (Annahme: formeller Schreibauftrag – bei informeller Textsorte übersteuern)
- *Wortschatz:* lexikalische Vielfalt (Guiraud-Index)
- *Satzbau:* Satzlängen-Variation, Anteil hypotaktischer Sätze

**Jedes der 8 Kriterien kann im Reiter „Sprachliche Leistung“ per Auswahl
übersteuert werden** – danach „Note aus Auswahl neu berechnen“ klicken.
Der gewählte Band-Deskriptor (Originalwortlaut der Tabelle) erscheint im
Gutachten.

**Inhalt:** Abgleich mit dem Erwartungshorizont über zwei Signale –
(1) **Schlüsselwörter** je Erwartung (tippfehlertolerant) und
(2) **Textabdeckung**: Anteil der inhaltstragenden Wörter einer
Fließtext-Erwartung, die im Schülertext vorkommen. Gewertet wird das
jeweils stärkere Signal; der Bericht weist beide aus. Daraus Punkte je
Aufgabe, Prozent → Notenpunkte nach KMK-Schlüssel (15 P ab 95 %, … 1 P ab
20 %). Kriterien zu Aufbau/Darstellung (✎) bleiben automatisch bei 0 und
sind manuell zu ergänzen.

## Bedienung

### Schritt 1: Erwartungshorizont erstellen (`erwartungshorizont_editor.pyw`)

1. Eigenen Erwartungshorizont/Bewertungsbogen einbringen – wahlweise:
   - **„PDF laden…“** (empfohlen): erkennt **tabellarische Bewertungsraster**
     automatisch – „Teilaufgabe 1: Comprehension“, Punktespalte „max.“,
     „Total“-Zeile, Stichpunkte mit mehreren Punktwerten je Zelle,
     seitenübergreifende Tabellen. Auch das reine **Klausurblatt**
     („1. Outline … (30 BE)“) funktioniert und liefert das Aufgabengerüst;
     Material- und Operatorenteile werden abgeschnitten. Gescannte Bögen
     ohne Textebene laufen über die Handschrifterkennung des
     Hauptprogramms (beide .pyw-Dateien im selben Ordner, easyocr).
   - **Text einfügen**: den Horizont einfach in das linke Feld kopieren.

   Erkanntes Format (tolerant):

   ```
   Aufgabe 1: Comprehension – Summarize the text
   - Nennt die zentrale These (4 P) [interconnected, global trade]
   - Benennt wirtschaftliche Aspekte (4 P, min. 2) [outsourcing, multinational]
   ```

   - `Aufgabe 1:` / `Task 1)` / `1.` beginnt eine neue Aufgabe
   - `(4 P)`, `(4 BE)`, `4 Punkte` → Punktzahl
   - `[wort1, wort2]` oder `Schlüsselwörter: …` → Suchbegriffe
   - `min. 2` / `mindestens 2` → nötige Treffer für volle Punkte
2. Beim Text-Weg „→ Text in Aufgaben umwandeln“ klicken; danach in der
   Mitte prüfen und bearbeiten. Markierungen im Baum:
   - ⚠ **ohne Schlüsselwörter** – wird nicht automatisch geprüft, bitte
     ergänzen (Knopf „Schlüsselwörter vorschlagen“ hilft).
   - ◆ **Vorschlag – bitte prüfen**: Formuliert der Bogen die Erwartung als
     ganzen Satz, zieht das Tool die inhaltstragenden Begriffe automatisch
     heraus (Zitate, Eigennamen, aussagekräftige Wortpaare). Das ist ein
     Startpunkt, kein fertiges Ergebnis – ergänzen Sie Synonyme, die
     Ihre Schülerinnen und Schüler realistisch verwenden.
   - ✎ **manuell zu bewerten**: Kriterien zu Aufbau, Darstellung und
     Zitierweise („well-structured“, „own words“, „paraphrasing“). Sie
     lassen sich inhaltlich nicht automatisch prüfen; diese Punkte
     vergeben Sie später im Bewertungsprogramm selbst.
3. **Schlüsselwörter sind die englischen Begriffe/Synonyme, die im
   Schülertext gesucht werden** – je mehr Varianten, desto fairer.
4. „JSON speichern…“.

### Schritt 2: Klausur bewerten (`klausur_bewertung.pyw`)

1. Erwartungshorizont (JSON) laden.
2. Schülertext laden (.txt/.md/.docx/.pdf/.png/.jpg) oder einfügen.
   **Handschriftliche Klausuren als PDF/Foto:** siehe nächster Abschnitt.
3. „Prüfung starten“ → Reiter *Korrekturen*, *Sprachliche Leistung*
   (Deskriptoren mit Übersteuerung), *Inhaltliche Bewertung*,
   *Gesamtgutachten*.
4. Ggf. Einstufungen übersteuern → „Note aus Auswahl neu berechnen“.
   Im Reiter *Inhaltliche Bewertung* stehen oben die **erreichten Punkte je
   Aufgabe** als Eingabefelder: Der automatische Wert ist ein Vorschlag und
   kann überschrieben werden – nötig für die mit ✎ markierten Kriterien
   (Aufbau, Darstellung, Zitierweise), die automatisch 0 Punkte bekommen.
   Das Feld zeigt an, wie viele Punkte dort noch offen sind.
   Danach „Inhaltspunkte übernehmen & Note neu berechnen“.
5. „Bericht exportieren…“ (Textdatei mit Gutachten, Deskriptoren-Bewertung,
   Inhaltsbewertung und vollständiger Korrekturliste).

## Handschriftliche Klausuren einlesen (PDF/Foto)

Das Programm lädt gescannte Klausuren direkt als PDF (oder Foto) und
erkennt den Text automatisch – „so gut es geht“, in drei Stufen:

1. **PDF-Textebene:** Enthält das PDF bereits Text (digital erstellt oder
   vom Scanner mit OCR versehen), wird dieser direkt übernommen – keine
   Erkennung nötig.
2. **EasyOCR** (`pip install pymupdf easyocr`): findet die Textzeilen auf
   der Seite und liest sie. Beim ersten Start werden die Modelle einmalig
   heruntergeladen; die Erkennung läuft danach vollständig lokal
   (datenschutzfreundlich – die Klausur verlässt den Rechner nicht).
3. **TrOCR** (optional, `pip install transformers torch`): Microsofts frei
   verfügbares Spezialmodell für englische *Handschrift*
   (trocr-base-handwritten) liest jede gefundene Zeile nach – deutlich
   bessere Ergebnisse bei Schreibschrift. Wird automatisch genutzt, wenn
   installiert.

Nach dem Einlesen zeigt das Programm, wie viele Wörter **unsicher erkannt**
wurden (mit Beispielen und Seitenangabe).

> **Unbedingt beachten:** Den erkannten Text im Reiter „Schülertext“ mit
> der Original-Klausur abgleichen und korrigieren, **bevor** die Prüfung
> gestartet wird. Jeder Erkennungsfehler würde sonst als Sprachfehler der
> Schülerin/des Schülers in die Bewertung eingehen. Der Zeitgewinn liegt
> im Abtippen-Ersparen – das Gegenlesen bleibt nötig.

**Scan-Tipps für gute Erkennung:** 300 dpi, Seiten gerade auflegen, guter
Kontrast (dunkle Tinte, helles Papier), keine Schatten/Knicke, eine
Klausur pro PDF. Auch Handy-Scans (z. B. mit einer Scanner-App) als PDF
funktionieren. Grenze der Technik: Sehr unleserliche oder stark verbundene
Schreibschrift bleibt auch für die besten freien Modelle schwierig – die
unsicheren Wörter zeigen, wo nachgesehen werden muss.

## Voraussetzungen

- **Python 3.8+** mit Tkinter (in der Windows-Installation von
  [python.org](https://www.python.org) enthalten). Start per Doppelklick.
- **Zusatzkomponenten installieren sich automatisch:** Wird eine Funktion
  genutzt, deren Komponente fehlt (z. B. PDF laden → `pymupdf`,
  Handschrifterkennung → `easyocr`, Word-Datei → `python-docx`), fragt das
  Programm nach und installiert sie **auf Klick selbst** – mit
  Fortschrittsfenster; danach wird der Vorgang automatisch fortgesetzt.
  Nötig ist dafür nur eine Internetverbindung. (Wer lieber selbst
  installiert: die pip-Befehle stehen im jeweiligen Dialog.)
- **Sprachprüfung:** Internetverbindung für die kostenlose
  LanguageTool-API, *oder* einmalig `pip install language_tool_python`
  (benötigt zusätzlich Java) für die vollständig lokale Prüfung – wird
  automatisch bevorzugt. (Diese Komponente wird wegen der
  Java-Voraussetzung nicht automatisch installiert.)
- *Optional (beste Handschrifterkennung):* `pip install transformers torch`
  für TrOCR – groß (mehrere GB), daher ebenfalls bewusst nicht
  automatisch; EasyOCR funktioniert auch ohne.

## JSON-Format des Erwartungshorizonts

```json
{
  "titel": "Klausur Q1.1 – Globalization",
  "sprache": "en-GB",
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

Optional kann `"richtigkeit_anker": [[0, 15], [0.5, 13.5], [1.5, 11],
[3, 8], [5, 5], [8, 2], [12, 0]]` ergänzt werden, um die Zuordnung
„gewertete Fehler je 100 Wörter → Notenpunkte“ im Bereich A strenger oder
milder einzustellen (Standardwerte wie gezeigt, dazwischen wird linear
interpoliert).

## Grenzen

- Bereich A (Richtigkeit) ist gut automatisierbar; LanguageTool findet
  allerdings nicht jeden Fehler und beurteilt keine „sprachlichen Risiken“
  im Sinne des sehr-gut-Deskriptors.
- Bereich B ist eine Näherung über messbare Indikatoren – die Deskriptoren
  verlangen dort ein fachliches Urteil (deshalb die Übersteuerung).
- Die inhaltliche Prüfung erkennt Umschreibungen und eigenständige
  Argumentation nur begrenzt (Schlüsselwort- und Wortabdeckungs-Abgleich).
  In einem Test mit dem Bewertungsbogen „In a relationship with AI“
  erreichte eine inhaltlich vollständige Antwort 90 von 100 Punkten
  (die fehlenden 10 sind die ✎-Kriterien), eine oberflächliche Antwort
  6 Punkte, ein themenfremder Text 0 Punkte. Die Rangfolge stimmt also –
  die exakte Punktzahl bleibt zu prüfen.
- Wer später echte semantische Bewertung möchte, kann kostenlos ein lokales
  Sprachmodell (z. B. über [Ollama](https://ollama.com)) anbinden –
  datenschutzfreundlich, da Schülertexte den Rechner nicht verlassen.

## Datenschutz

Bei der Online-Prüfung wird der Schülertext an die LanguageTool-API
(languagetool.org, Server in Deutschland) übertragen. Zur Vermeidung:
`pip install language_tool_python` – dann läuft alles lokal. Namen vor der
Prüfung zu entfernen ist in jedem Fall gute Praxis.
