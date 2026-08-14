# ProcessMap Studio 0.1

Einfaches `.pyw`-Tool zum Erstellen von Process Maps mit
[Mermaid.js](https://mermaid.js.org/) – gedacht für gesperrte
Arbeitsumgebungen, in denen nur Python-Bordmittel zur Verfügung stehen.
Ergebnis wahlweise als **HTML**, **PDF** oder als **bearbeitbare
Visio-Zeichnung (.vsdx)**.

## Der Gesamtprozess

```
  Quelle              Vorverarbeitung           Zwischenformat        Ausgabe
┌──────────┐        ┌─────────────────┐       ┌──────────────┐    ┌──────────────┐
│ PDF      │        │ Copilot mit dem │       │ Mermaid-Code │    │ HTML (Ansicht)│
│ Word     │ ─────► │ Master-Prompt   │ ────► │ = die einzige│───►│ PDF (Bericht) │
│ Notizen  │        │ (später: lokale │       │   Wahrheit   │    │ VSDX (Visio)  │
│ Gespräch │        │  LLM-API)       │       │              │    │               │
└──────────┘        └─────────────────┘       └──────────────┘    └──────────────┘
                                                     ▲                    │
                                                     └────────────────────┘
                                              Korrektur im Editor, erneut ausgeben
```

Der **Mermaid-Code ist das führende Format**. Er ist versionierbar, in
Sekunden von Hand korrigierbar und erzeugt reproduzierbar alle drei
Ausgaben. Die Visio-Datei ist bewusst ein *Ergebnis*, keine Quelle: Wer
den Prozess ändert, ändert den Mermaid-Code und exportiert neu.

## Dateien

| Datei | Zweck |
|---|---|
| `ProcessMapStudio.pyw` | Das Tool (Doppelklick startet es ohne Konsolenfenster) |
| `MASTER_PROMPT.md` | Standardisierter Copilot-Prompt zur Vorverarbeitung von Texten/PDFs |

## Voraussetzungen

- Python 3.x mit Tkinter (Standard bei der Windows-Installation von python.org)
- Keine zusätzlichen Pakete, kein `pip install` nötig
- Für die Browser-Vorschau: Internetzugang **oder** eine lokale `mermaid.min.js`
  (siehe „Offline-Betrieb“)
- Der **Visio-Export braucht weder Visio noch Internet** – die Datei wird
  komplett aus der Python-Standardbibliothek erzeugt

## Die Oberfläche

Links führt eine Leiste **„So läuft es ab“** durch die vier Schritte, oben
nach unten mit Pfeilen verbunden; rechts steht der Editor:

```
┌──────────────────────┬──────────────────────────────────┐
│ 1. Vorbereiten       │  Titel: [ Rechnungsprüfung     ] │
│   [Master-Prompt…]   │                                  │
│         ↓            │  Prozess-Code (Mermaid)          │
│ 2. Übernehmen        │  ┌────────────────────────────┐  │
│   [Copilot-Antwort…] │  │ flowchart TD               │  │
│   [Beispiel laden]   │  │   A0(["Start"]) --> A1[…]  │  │
│         ↓            │  │   …                        │  │
│ 3. Prüfen            │  │                            │  │
│   [Vorschau…]        │  │                            │  │
│         ↓            │  │                            │  │
│ 4. Ausgeben          │  │                            │  │
│   [Visio (.vsdx)]    │  │                            │  │
│   [PDF]  [HTML]      │  └────────────────────────────┘  │
├──────────────────────┴──────────────────────────────────┤
│ Statuszeile: sagt, welcher Schritt als Nächstes dran ist│
└─────────────────────────────────────────────────────────┘
```

Schritt 3 und 4 sind **gesperrt, solange kein Code im Editor steht** – die
Reihenfolge ist damit nicht nur beschriftet, sondern durchgesetzt. Sobald
etwas im Editor steht, schalten sie sich frei. Die Statuszeile bestätigt
jeden Schritt und nennt den nächsten.

## Fließrichtung: senkrecht oder waagerecht

Über dem Editor schaltet ein Radiobutton zwischen **senkrecht (von oben
nach unten)** und **waagerecht (von links nach rechts)** um. Die Auswahl
schreibt die Richtung in die `flowchart`-Zeile des Codes – dieser bleibt
damit die einzige Wahrheit, und **Vorschau, PDF und Visio folgen
gemeinsam**. Wird Code mit `flowchart LR` eingefügt, stellt sich der
Radiobutton automatisch passend ein.

Faustregel: Senkrecht passt zu langen Abläufen mit vielen
aufeinanderfolgenden Schritten (druckt sich auf Hochformat gut).
Waagerecht lohnt sich bei wenigen Ebenen mit vielen parallelen Zweigen –
bei langen Ketten wird die Zeichnung sonst sehr breit.

Die Beschriftungen werden dabei **fest umgebrochen** – waagerecht enger
(18 Zeichen je Zeile) als senkrecht (26), weil die Feldbreite dort in
Flussrichtung zeigt und lange Felder die Zeichnung sonst endlos ziehen.
Der Umbruch steht in der Datei und nicht nur in der Breitenschätzung;
die Zeilenzahl stimmt dadurch unabhängig davon, wie breit die Schrift
auf dem jeweiligen Rechner tatsächlich baut.

## Verwendung

1. `ProcessMapStudio.pyw` per Doppelklick starten.
2. Mermaid-Code in den Editor schreiben (ein Beispiel ist vorgeladen) und auf
   **„Vorschau im Browser“** klicken – die Map öffnet sich im Standardbrowser.
3. **„PDF – zum Drucken“** erzeugt direkt eine PDF-Datei. Ein Dialog fragt ab:
   - **Ausrichtung:** Querformat oder Hochformat (A4)
   - **Darstellung:** auf eine Seite einpassen (verkleinert) oder wie
     angezeigt (mehrseitig, an der Seitenbreite ausgerichtet)

   Der Export ruft Edge oder Chrome unsichtbar im Headless-Modus auf —
   beides muss nicht als Standardbrowser eingestellt sein, Edge ist auf
   jedem Windows-Rechner vorhanden. Wird kein passender Browser gefunden,
   öffnet sich als Fallback der Druckdialog des Standardbrowsers mit
   voreingestelltem Format (dort „Als PDF speichern“ wählen).
4. **„Visio (.vsdx) – bearbeitbar“** erzeugt eine Visio-Datei (siehe unten).
5. **„HTML – zum Teilen“** erzeugt eine eigenständige HTML-Datei, die sich
   per E-Mail verschicken oder im Browser drucken lässt.

## Visio-Export (.vsdx)

Die Schaltfläche **„Visio (.vsdx) – bearbeitbar“** schreibt eine echte
Visio-Zeichnung. Was in Visio ankommt:

- **Native Visio-Formen**, keine Bilder – jede Form ist einzeln
  anklickbar, verschiebbar, umbenennbar, einfärbbar.
- **Formtypen** entsprechend den Konventionen des Master-Prompts:
  Start/Ende als Stadion, Aktivität als Rechteck, Entscheidung als Raute,
  Dokument als Parallelogramm, Teilprozess mit doppelten Seitenbalken.
- **Dynamisch verklebte Verbinder.** Die Pfeile hängen an den Formen
  (dynamische Verklebung an die ganze Form) und laufen automatisch neu,
  wenn eine Form verschoben wird. Genau das macht die Datei zu einem
  Arbeitsdokument statt zu einem Schaubild.
- **Vier Klebepunkte je Form** (oben/rechts/unten/links), damit eigene
  Verbinder sauber andocken.
- **Kantenbeschriftungen** („Ja“/„Nein“) sitzen auf dem Verbinder und
  lassen sich in Visio frei verschieben.
- **Subgraphs** aus dem Mermaid-Code werden als beschriftete
  Hintergrundrahmen (Rolle/Abteilung) gezeichnet.
- **Automatisches Layout** nach dem Sugiyama-Verfahren: Ebenen,
  Kreuzungsminimierung und – entscheidend – **Hilfsknoten für Kanten, die
  Ebenen überspringen**. Eine Kante, die z. B. von einer Prüfung weit nach
  unten auf einen gemeinsamen Fehlerpfad springt, bekommt auf jeder
  Zwischenebene einen schmalen Platzhalter. Der nimmt an der Sortierung
  teil und hält eine eigene Spur frei, sodass parallele Prozessstränge
  nebeneinander stehen und Linien **außen herum** statt quer durch die
  Formen laufen. Zyklen (Rücksprünge) brechen das Layout nicht.
- **Mehrfachkanten getrennt geführt:** Zeigen Ja- und Nein-Zweig einer
  Entscheidung auf dieselbe Form, verlassen sie die Raute an
  verschiedenen Stellen und behalten lesbare, getrennte Beschriftungen.
- **Lange Linien laufen gerade.** Eine Kante über mehrere Ebenen bekommt
  eine eigene senkrechte Spur, die vorab gegen alle Formen im
  betroffenen Höhenbereich freigeprüft wird. Die waagerechten Endstücke
  liegen in den freien Streifen *zwischen* den Ebenen. Dadurch hat jede
  lange Verbindung genau zwei Knicke statt eines Zickzackkurses.

Die Seitengröße wächst mit dem Diagramm, mindestens A4 hoch.

### Prüfstand

Der Export wurde geprüft gegen den Aufbau einer echten, von Visio
erzeugten Datei sowie mit einem eigenen Validator (OPC-Struktur,
XML-Wohlgeformtheit, Auflösung aller Beziehungen, Eindeutigkeit der
Form-IDs, Vollständigkeit der Klebeverbindungen). Zusätzlich wurde jede
erzeugte Datei mit **libvisio** (der Visio-Importfilter von
LibreOffice, eine unabhängige zweite Implementierung) eingelesen und
gerendert. Ein weiterer Test prüft geometrisch, dass **keine
Verbindungslinie durch eine fremde Form** verläuft.

> **Ehrliche Einschränkung:** Auf dem Rechner, auf dem dieses Tool
> entwickelt wurde, stand kein Microsoft Visio zur Verfügung. Struktur
> und Darstellung sind über zwei unabhängige Wege abgesichert, ein
> Praxistest in Visio selbst steht aber noch aus. Bitte die erste
> exportierte Datei einmal in Visio öffnen. Falls Visio eine Reparatur
> vorschlägt, bitte melden – die Ursache ist dann gezielt behebbar.

## Workflow mit Copilot (Vorverarbeitung ohne API)

1. Im Tool auf **„Master-Prompt kopieren“** klicken.
2. Prompt in Copilot einfügen und darunter den Quelltext anhängen
   (z. B. Text aus einer PDF kopieren, oder in M365 Copilot die PDF anhängen).
3. Copilot antwortet mit einem `mermaid`-Codeblock. Antwort komplett kopieren.
4. Im Tool auf **„Copilot-Antwort einfügen“** klicken – der Codeblock wird
   automatisch aus der Antwort herausgelöst.
5. Kurz prüfen und korrigieren, dann **„Vorschau“**, **„PDF“** oder
   **„Visio exportieren“**.

Schritt 5 ist der Grund für das Zwischenformat: Ein LLM erfindet
gelegentlich Schritte. Im Mermaid-Code sieht man das in Sekunden – in
einer fertigen Visio-Datei nicht mehr.

## Offline-Betrieb

Standardmäßig lädt die erzeugte HTML-Seite Mermaid vom jsDelivr-CDN.
Wer offline arbeiten muss: einmalig
<https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js>
herunterladen und als `mermaid.min.js` **neben** `ProcessMapStudio.pyw`
ablegen. Das Tool bettet die Datei dann direkt in jede erzeugte HTML-Seite
ein – Vorschau und gespeicherte Dateien funktionieren komplett ohne Internet.
Der Visio-Export ist von alledem nicht betroffen und läuft immer offline.

## Ausbaustufe (Zielzustand)

Später kann die Copilot-Zwischenstufe durch eine lokale LLM-API ersetzt
werden: Der Master-Prompt bleibt identisch, statt Copy/Paste schickt das Tool
Prompt + extrahierten PDF-Text per `urllib.request` (Standardbibliothek) an
einen OpenAI-kompatiblen Endpunkt (z. B. Ollama/LM Studio) und übernimmt die
Antwort direkt in den Editor. Am restlichen Prozess ändert sich nichts –
Zwischenformat und alle drei Ausgabewege bleiben wie sie sind.
