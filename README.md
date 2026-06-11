# ProcessMap Studio

Einfaches `.pyw`-Tool zum Erstellen von Process Maps mit
[Mermaid.js](https://mermaid.js.org/) – gedacht für gesperrte
Arbeitsumgebungen, in denen nur Python-Bordmittel zur Verfügung stehen.

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

## Verwendung

1. `ProcessMapStudio.pyw` per Doppelklick starten.
2. Mermaid-Code in den Editor schreiben (ein Beispiel ist vorgeladen) und auf
   **„Vorschau im Browser“** klicken – die Map öffnet sich im Standardbrowser.
3. **„Als HTML speichern…“** erzeugt eine eigenständige HTML-Datei, die sich
   per E-Mail teilen oder im Browser drucken lässt (Drucken → als PDF speichern).

## Workflow mit Copilot (Vorverarbeitung ohne API)

1. Im Tool auf **„Master-Prompt kopieren“** klicken.
2. Prompt in Copilot einfügen und darunter den Quelltext anhängen
   (z. B. Text aus einer PDF kopieren, oder in M365 Copilot die PDF anhängen).
3. Copilot antwortet mit einem `mermaid`-Codeblock. Antwort komplett kopieren.
4. Im Tool auf **„Copilot-Antwort einfügen“** klicken – der Codeblock wird
   automatisch aus der Antwort herausgelöst.
5. **„Vorschau im Browser“** → fertig.

## Offline-Betrieb

Standardmäßig lädt die erzeugte HTML-Seite Mermaid vom jsDelivr-CDN.
Wer offline arbeiten muss: einmalig
<https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js>
herunterladen und als `mermaid.min.js` **neben** `ProcessMapStudio.pyw`
ablegen. Das Tool bettet die Datei dann direkt in jede erzeugte HTML-Seite
ein – Vorschau und gespeicherte Dateien funktionieren komplett ohne Internet.

## Ausbaustufe (Zielzustand)

Später kann die Copilot-Zwischenstufe durch eine lokale LLM-API ersetzt
werden: Der Master-Prompt bleibt identisch, statt Copy/Paste schickt das Tool
Prompt + extrahierten PDF-Text per `urllib.request` (Standardbibliothek) an
einen OpenAI-kompatiblen Endpunkt (z. B. Ollama/LM Studio) und übernimmt die
Antwort direkt in den Editor.
