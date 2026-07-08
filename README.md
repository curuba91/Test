# SOP-Konsistenz-Checker

Ein Werkzeug für die Qualitätssicherung von SOPs (Standard Operating Procedures):
Bei einer Änderung an einer SOP prüft es automatisch,

1. **Interne Konsistenz** – ob der geänderte Inhalt an weiteren Stellen im
   selben Dokument vorkommt und dort ebenfalls noch angepasst werden muss, und
2. **Dokumentübergreifende Konsistenz** – ob weitere SOPs aus einem
   Dokumenten-Pool (Ordner/Netzlaufwerk/SharePoint-Sync) betroffen sind:
   alter Wortlaut, ähnliche Passagen oder Verweise auf die geänderte SOP.

Das Ergebnis ist ein **HTML-Prüfbericht mit Abhak-Checkliste**: Jede Fundstelle
wird mit Dokument, Absatznummer, hervorgehobenem Treffer und dem neuen Wortlaut
als Vorschlag angezeigt und kann einzeln als „geprüft/erledigt“ abgehakt werden
(der Abhak-Status bleibt im Browser gespeichert).

## Voraussetzungen

- **Nur Python** (ab Version 3.9, Standardinstallation von [python.org](https://www.python.org)
  oder aus dem Microsoft Store). **Keine Zusatzpakete nötig** – auch Word-Dateien
  (`.docx`) werden direkt gelesen.
- Läuft komplett **lokal** – kein Cloud-Dienst, keine Datenübertragung.
  Damit auch für vertrauliche QM-Dokumente unbedenklich.

Unterstützte Formate: `.docx`, `.txt`, `.md` (Text inkl. Tabelleninhalte;
`.doc`-Altformat bitte vorher in Word als `.docx` speichern).

## Start per Doppelklick (Windows)

`SOP_Checker.pyw` doppelklicken – die Oberfläche startet ohne Konsolenfenster:

1. **Neue Version** wählen (die geänderte SOP).
2. **Alte Version** wählen (der Stand vor der Änderung) – daraus ermittelt das
   Tool automatisch, *was* sich geändert hat.
3. **SOP-Pool** wählen: der Ordner mit allen übrigen SOPs (wird rekursiv
   durchsucht, Unterordner eingeschlossen).
4. Optional: **zusätzliche Suchbegriffe** und die **SOP-ID** (wird sonst
   automatisch aus Dateiname/Dokumentkopf erkannt, z. B. „SOP-042“).
5. **Prüfung starten** → Bericht öffnet sich im Browser.

> Hinweis: Die Datei muss im selben Ordner wie der Paketordner `sop_checker/`
> liegen (einfach das ganze Repository-Verzeichnis kopieren, z. B. auf ein
> Netzlaufwerk – dann können alle Kollegen dasselbe Tool starten).

## Kommandozeile / Automatisierung

```
python -m sop_checker --alt "SOP-042_v3.docx" --neu "SOP-042_v4.docx" ^
    --pool "P:\QM\SOPs" --bericht "Konsistenzbericht_SOP-042.html"
```

| Option | Bedeutung |
| --- | --- |
| `--neu` | neue (geänderte) Version – **Pflicht** |
| `--alt` | alte Version zum Vergleich |
| `--pool` | Ordner mit weiteren SOPs (rekursiv) |
| `--begriffe` | manuelle Suchbegriffe, getrennt mit `;` – optional mit neuem Wortlaut: `"Raumklasse C => Raumklasse B; Gerät XY-100"` |
| `--sop-id` | Kennung für die Verweis-Suche (sonst automatisch erkannt) |
| `--bericht` | Zieldatei des HTML-Berichts |
| `--schwellwert` | Ähnlichkeits-Schwelle 0..1 für „ähnliche Passagen“ (Standard 0.75) |

Ohne alte Version kann das Tool auch als reine **Begriffssuche** über den
ganzen Pool eingesetzt werden (nur `--neu`, `--pool` und `--begriffe` angeben).

## Wie die Prüfung funktioniert

1. Beide Versionen werden absatzweise verglichen (auch Tabellentexte).
2. Aus jeder Änderung wird der **konkrete alte Wortlaut** extrahiert. Sehr kurze
   Änderungen („C“ → „B“, „5“ → „10“) werden automatisch um unveränderte
   Kontextwörter erweitert („Raumklasse C“, „beträgt 5 Minuten“), damit sie
   eindeutig auffindbar sind.
3. Diese alten Wortlaute werden gesucht:
   - in der **neuen Version selbst** → Stellen, an denen die Änderung noch
     nicht nachgezogen wurde,
   - in **allen Pool-Dokumenten** → weitere anzupassende SOPs.
4. Zusätzlich werden gefunden:
   - **ähnliche Passagen** (Fuzzy-Vergleich, Schwellwert einstellbar) – fängt
     leicht abgewandelte Formulierungen desselben Inhalts ab,
   - **Verweise auf die geänderte SOP** (SOP-ID) in anderen Dokumenten – diese
     Dokumente sollten bei jeder Änderung gesichtet werden,
   - unverändert **verschobene Absätze** werden erkannt und lösen keinen
     Fehlalarm aus.

## Einsatz in einer Microsoft-Umgebung

- **SharePoint / OneDrive:** Die SOP-Bibliothek mit OneDrive lokal
  synchronisieren und den Sync-Ordner als Pool angeben – so wird immer der
  aktuelle Stand geprüft, ohne dass Dokumente kopiert werden müssen.
- **Alte Version beschaffen:** Bei aktivierter SharePoint-Versionierung die
  Vorgängerversion herunterladen („Versionsverlauf“ → gewünschte Version
  speichern) und als „Alte Version“ angeben. Alternativ vor jeder Überarbeitung
  eine Kopie `_v<alt>` ablegen.
- **Prüfbericht ablegen:** Der HTML-Bericht kann direkt neben der SOP in
  SharePoint abgelegt und als Nachweis der Konsistenzprüfung im
  Änderungsverfahren (Change Control) mitgeführt werden.
- Wer eine vollautomatische Lösung ohne lokale Python-Installation möchte, kann
  denselben Ablauf später in Power Automate / ein Office-Skript überführen –
  die Prüf­logik in `sop_checker/` ist bewusst von der Oberfläche getrennt.

## Grenzen / Hinweise

- Das Tool erkennt **Textkonsistenz**, keine fachliche Richtigkeit – die
  Bewertung jeder Fundstelle („anpassen“ oder „bewusst so belassen“) bleibt
  eine Fachentscheidung. Der Bericht macht diese Entscheidung dokumentierbar.
- Kopf-/Fußzeilen, Textfelder und eingebettete Objekte in Word werden nicht
  ausgewertet (nur der Haupttext inkl. Tabellen).
- „Absolute“ Konsistenz erreicht man organisatorisch am besten zusätzlich durch
  eindeutige Verweise (immer die SOP-ID nennen) statt Inhalte in mehreren
  Dokumenten zu duplizieren – das Tool zeigt über die Verweis-Suche genau diese
  Abhängigkeiten an.

## Beispiel ausprobieren

```
python -m sop_checker --alt beispiele/SOP-042_v3_alt.txt ^
    --neu beispiele/SOP-042_v4_neu.txt --pool beispiele/pool
```

Erwartetes Ergebnis: eine offene Stelle in der neuen Version (Abschnitt
„Dokumentation“ enthält noch „Raumklasse C“) und drei Fundstellen in
`SOP-100_Umgebungsmonitoring.txt` (alter Wortlaut ×2, Verweis auf SOP-042);
`SOP-200_Wareneingang.txt` ist korrekt nicht betroffen.

## Tests

```
python -m unittest discover -s tests
```
