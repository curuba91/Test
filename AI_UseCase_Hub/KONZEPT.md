# AI Use Case Hub – Konzept v2 (Umsetzungsvorlage für Claude Code)

**Dokumenttyp:** Konzept und Umsetzungsauftrag (anonymisiert)
**Stand:** 12.11.2026
**Version:** 2.0 – ersetzt das Grundkonzept 1.0 vom 11.11.2026

> **Anonymisierung:** Organisation, Standort, Personen, Gremien, interne Tools und Dokumentnummern sind durch Platzhalter ersetzt (Kapitel 17). Im Code und in der Oberfläche dürfen keine echten Namen fest hinterlegt werden; alles Standortspezifische kommt aus der Konfiguration.

> **Kennzeichnungen in diesem Dokument**
> **FEST** = entschieden, nicht ohne Rückfrage ändern.
> **VORSCHLAG** = sinnvolle Vorgabe, darf nach Rückfrage angepasst werden.
> **ANNAHME** = nicht bestätigt; vor der Umsetzung des betroffenen Teils klären (Kapitel 16).

---

## 1. Auftrag in einem Absatz

Gebaut wird ein lokales Werkzeug für **eine pflegende Person**, das alle KI-Anwendungsfälle eines Standorts von der Meldung bis zum Betrieb verwaltet, inklusive Tickets zu produktiven Lösungen und Governance-Status. Der erste Entwurf war funktional vollständig, aber unübersichtlich. Version 2 behält die Datenlogik und baut Informationsarchitektur und Oberfläche neu: **vier Bereiche statt neun Ansichten, eine Detailseite pro Use Case, eine einzige Liste „Handlungsbedarf“ statt verteilter Ampeln.**

---

## 2. Entscheidungen (FEST)

| Nr. | Entscheidung | Begründung |
|---|---|---|
| E1 | Lokale Anwendung: Python-Server auf `127.0.0.1`, Oberfläche im Browser, SQLite als einziger Schreibort | Auf einem Standardrechner bestätigt lauffähig; volle Freiheit bei der Oberfläche; erfüllt alle Restriktionen |
| E2 | Genau eine pflegende Person. Eine Vertretung arbeitet nur, wenn die Hauptperson abwesend ist | Kein Mehrbenutzerbetrieb, keine Zusammenführung paralleler Änderungen |
| E3 | Die Datenbank liegt **lokal** (nicht im synchronisierten Ordner). Für die Vertretung gibt es einen expliziten **Übergabestand** im Team-Ordner (Kapitel 6) | Synchronisations-Clients können SQLite-Dateien während des Schreibens beschädigen |
| E4 | **Ordnerstruktur statt einer einzigen `.pyw`**: Startdatei, Python-Paket, getrennte Oberflächen-Dateien | Genauso leicht zu verteilen (Ordner kopieren), aber wartbar und testbar |
| E5 | **Kein Snapshot-HTML.** Stattdessen ein Reporting-Export (Excel mit festem Schema) und eine Druckansicht für Termine mit <Sponsor> und <AI-Gremium> | Sponsor und Gremium lesen nicht selbstständig; die Cloud-Ablage zeigt HTML-Dateien nicht als Seite an |
| E6 | Die Quell-Excels bleiben der Eingangskorb. Formulare und Flows bleiben unverändert | Bewährt; keine neue Plattform |
| E7 | Geschäftsregeln (Handlungsbedarf, Schrittleiste, Validierungs-Check) werden **nur im Server** berechnet, an genau einer Stelle | Oberfläche, Export und Druckansicht zeigen garantiert dasselbe |
| E8 | Kein eigenes Ticketsystem der Firma verfügbar; Tickets bleiben Teil des Hubs | – |

### Geprüfte und verworfene Alternativen

| Alternative | Grund der Ablehnung |
|---|---|
| Listen-basierte Kollaborationsplattform als Datenbank (X1) | Technisch möglich (Flows können Listeneinträge anlegen). Bei einer pflegenden Person kein Vorteil, der die Einschränkungen bei Übersicht, Detailseite und Validierungs-Check aufwiegt. **Neu bewerten, falls dauerhaft zwei oder mehr Personen pflegen.** |
| Natives Fenster (tkinter) statt Browser-Oberfläche | Nur nötig, wenn der lokale Server gesperrt wäre; ist er nicht |
| Reine HTML-Datei mit Schreibzugriff über die Browser-API | Per Unternehmensrichtlinie abschaltbar; Excel-Import ohne Bibliothek aufwendig |
| Nur Excel mit Power Query | Schreibt nicht zurück; Oberfläche bliebe Excel |
| Listen als Speicher plus eigene Oberfläche | Braucht Anmeldung/Hosting – der Engpass aus X7 |

---

## 3. Qualitätsziele und woran sie gemessen werden

| Ziel | Messbares Kriterium |
|---|---|
| Intuitiv | Jeder Eintrag im Handlungsbedarf führt mit **einem Klick** an die Stelle, an der er erledigt wird. Auf jedem Bildschirm gibt es höchstens **eine** hervorgehobene Hauptaktion. |
| Leicht in der Nutzung | Kein „Speichern“-Knopf für Einzelfelder: Änderungen werden beim Verlassen des Feldes gespeichert und sichtbar bestätigt. Keine verschachtelten Dialoge. |
| Zuverlässig | Kein Absturz bei fehlender, gesperrter oder halb synchronisierter Quelldatei. Jeder Schreibvorgang ist eine Transaktion. Start prüft die Datenbank-Integrität. |
| Präzise | Jede angezeigte Zahl ist per Klick auf die zugrunde liegenden Datensätze auflösbar. Jede Regel hat eine Kennung und einen Klartext, der erklärt, **warum** der Eintrag erscheint. |
| Optisch ansprechend | Ein einheitliches Gestaltungssystem (Kapitel 9.7); Statusfarben nie ohne Text oder Symbol. |
| Verständlich im Aufbau | Vier Bereiche in fester Reihenfolge; der Lebenszyklus ist auf der Detailseite als Schrittleiste sichtbar. |
| Schnell | Listen und Detailseite reagieren bei 500 Use Cases und 2.000 Tickets ohne spürbare Verzögerung (Ziel: unter 300 ms je Anfrage). |

---

## 4. Architektur

```
┌──────────────────────────┐     ┌──────────────────────────┐
│ Formular „Use Case       │     │ Formular „Problem mit    │
│ melden“                  │     │ AI-Tool melden“          │
└────────────┬─────────────┘     └────────────┬─────────────┘
             │ Flow: nur „Zeile anhängen“     │ Flow: nur „Zeile anhängen“
             ▼                                ▼
┌──────────────────────────┐     ┌──────────────────────────┐
│ Quelle 1: Use-Case-Excel │     │ Quelle 2: Ticket-Excel   │
│ (Cloud-Ablage, sync.)    │     │ (Cloud-Ablage, sync.)    │
└────────────┬─────────────┘     └────────────┬─────────────┘
             │        NUR LESEN, über Temp-Kopie
             └───────────────┬────────────────┘
                             ▼
        ┌─────────────────────────────────────────┐
        │ Hub-Server (Python, 127.0.0.1)          │
        │  Import · Regeln · API · Audit · Backup │
        └───────┬─────────────────────────┬───────┘
                │ LESEN + SCHREIBEN       │ erzeugt
                ▼                         ▼
   ┌─────────────────────────┐  ┌──────────────────────────────┐
   │ hub.db (SQLite, LOKAL)  │  │ Team-Ordner (synchronisiert) │
   │ einziger Schreibort     │  │  · Übergabestand (Kopie)     │
   └─────────────────────────┘  │  · Sperrdatei                │
                ▲               │  · Reporting-Excel           │
                │               └──────────────────────────────┘
   ┌─────────────────────────┐
   │ Oberfläche im Browser   │
   │ (HTML/CSS/JS, statisch) │
   └─────────────────────────┘
```

### 4.1 Ordnerstruktur des Programms (FEST)

```
AI_UseCase_Hub/
├─ AI_UseCase_Hub.pyw        Startdatei (Doppelklick)
├─ hub/
│  ├─ config.py              Konfiguration laden/speichern, Ersteinrichtung
│  ├─ db.py                  Verbindung, Schema, Migrationen
│  ├─ audit.py               Änderungsprotokoll
│  ├─ importer.py            Quellen lesen, Abgleich, Konflikte
│  ├─ rules.py               Schrittleiste + Handlungsbedarf (einzige Stelle)
│  ├─ validation.py          Vorabcheck + Prompt-Generator
│  ├─ handover.py            Sperre, Übergabestand, Backups
│  ├─ export.py              Reporting-Excel
│  ├─ server.py              HTTP-Server, API, Sicherheitsprüfungen
│  └─ testdata.py            Testmodus
├─ static/
│  ├─ index.html
│  ├─ app.css
│  └─ js/                    ES-Module, kein Build-Schritt
├─ validation_rules.json     Logik und Texte des Vorabchecks
├─ tests/                    unittest (Standardbibliothek)
└─ KONZEPT.md                dieses Dokument
```

Der Programmordner darf in einem synchronisierten Ordner liegen (er wird zur Laufzeit nur gelesen). Deshalb `sys.dont_write_bytecode = True` setzen, damit kein `__pycache__` entsteht.

### 4.2 Ablageorte der Daten (FEST)

| Was | Wo | Synchronisiert |
|---|---|---|
| Datenbank `hub.db`, Backups, Konfiguration, Fehlerprotokoll | `%LOCALAPPDATA%\AI_UseCase_Hub\` | nein |
| Test-Datenbank `hub_test.db` und Test-Quellen | `%LOCALAPPDATA%\AI_UseCase_Hub\test\` | nein |
| Übergabestand, Sperrdatei | `<Team-Ordner>\Hub_Uebergabe\` | ja |
| Reporting-Excel | `<Team-Ordner>\Hub_Reporting\` | ja |
| Quell-Excels | vom Formular-Owner vorgegeben | ja |

Die Konfiguration ist pro Benutzer lokal, weil sich die Pfade synchronisierter Ordner je Benutzer unterscheiden. Beim ersten Start fragt eine Einrichtungsseite die drei Pfade ab (Quelle 1, Quelle 2, Team-Ordner).

---

## 5. Datenmodell

Grundsätze (FEST): Alle Beziehungen laufen über feste IDs, nie über Titel oder Zeilenposition. Datumswerte werden als `JJJJ-MM-TT` gespeichert und als `TT.MM.JJJJ` angezeigt. Tabellen- und Feldnamen im Code sind englisch, alle Texte der Oberfläche deutsch.

### 5.1 `usecases`

| Feldgruppe | Felder | Hinweis |
|---|---|---|
| Schlüssel | `id` | `UC-xxx` aus der Formular-ID oder `M-xxx` für manuell angelegte |
| Quellfelder | `title`, `description`, `area`, `reporter`, `benefit` – jeweils zusätzlich `<feld>_src` | `<feld>` ist der wirksame Wert, `<feld>_src` der zuletzt importierte (Regeln S4/S5) |
| Nur intern | `reporter_email`, `submitted_at` | E-Mail wird nie exportiert oder gedruckt |
| Phase | `phase`, `merged_into` | `Eingang` · `In Bearbeitung` · `Abgeschlossen` · `Zusammengeführt` · `Discontinued` |
| Bewertung | `owner`, `type`, `origin`, `score` | `origin`: `lokal entwickelt` oder `übernommen` (steuert Sponsor/Gremium) |
| Einordnung | `reg_status`, `reg_result`, `reg_reference`, `reg_confirmed_at` | Status: `offen` · `Vorabcheck erfolgt` · `bestätigt`. `reg_reference` ist nur der Verweis ins kontrollierte Dokumentensystem (X16) |
| Sponsor | `sponsor_status`, `sponsor_date` | `offen` · `besprochen` · `nicht erforderlich` |
| Gremium | `board_status`, `board_date`, `board_note` | `offen` · `vorgelegt` · `freigegeben` · `Nachschärfen gefordert` · `nicht erforderlich` |
| Portal | `portal_status`, `portal_link` | `offen` · `veröffentlicht` |
| Kommunikation | `comm_status`, `comm_date` | `offen` · `kommuniziert` |
| Betrieb | `lc_owner`, `version`, `next_review`, `last_review` | Versionsformat siehe S9 |
| Hilfe | `needs_help`, `help_note` | – |
| Sonstiges | `notes`, `created_at`, `updated_at` | – |

Wertelisten sind VORSCHLAG; vorhandene Werte aus dem bisherigen Entwurf oder der Alt-Excel haben Vorrang (Kapitel 16, Punkt 3). Wertelisten liegen in der Konfiguration, nicht im Code.

### 5.2 Weitere Tabellen

| Tabelle | Felder | Schlüssel/Beziehung |
|---|---|---|
| `milestones` | `title`, `planned_date`, `done_date`, `sort_order` | → `usecases.id` |
| `releases` | `date`, `version`, `change`, `by`, `ticket_id` | → `usecases.id`; `ticket_id` eindeutig, damit S9 nie doppelt bucht |
| `links` | `label`, `url` | → `usecases.id` |
| `tickets` | Quellfelder `title`, `description`, `reporter`, `affected_tool_raw` (je mit `_src`); Pflegefelder `usecase_id`, `type`, `severity`, `status`, `assignee`, `fix_version`, `cause`, `solution`, `created_at`, `resolved_at`, `closed_at` | `T-xxx` aus Formular oder `TM-xxx` manuell |
| `validations` | `created_at`, `created_by`, `answers_json`, `result`, `risk`, `controls_json`, `prompt_text`, `prompt_lang`, `rules_version` | → `usecases.id`; mehrere Durchläufe je Use Case möglich, der neueste gilt |
| `audit` | `ts`, `user`, `machine`, `entity`, `entity_id`, `field`, `old`, `new`, `source` | `source`: `oberfläche` · `import` · `regel` · `übergabe` |
| `import_log` | `ts`, `source`, `rows`, `new`, `changed`, `conflicts`, `duplicates`, `message` | – |
| `conflicts` | `entity`, `entity_id`, `field`, `hub_value`, `old_src_value`, `new_src_value`, `status`, `resolved_at`, `resolution` | `status`: `offen` · `entschieden` |
| `meta` | `schema_version`, `revision`, `stand_id_published`, `revision_published` | genau eine Zeile; siehe Kapitel 6 |

Ticket-Werte: `type` = `Fehler` · `Verbesserung` · `Frage`; `severity` = `hoch` · `mittel` · `niedrig`; `status` = `Neu` → `In Analyse` → `In Umsetzung` → `Gelöst` → `Geschlossen`, Endzustand `Abgelehnt`.

### 5.3 Technische Vorgaben zur Datenbank (FEST)

- `PRAGMA journal_mode=DELETE`, `synchronous=FULL`, `foreign_keys=ON`. Kein WAL.
- Jeder schreibende API-Aufruf ist genau eine Transaktion und erhöht `meta.revision` um 1.
- Schemaänderungen laufen über nummerierte Migrationen in `db.py`; vor jeder Migration entsteht ein Backup.
- Beim Start `PRAGMA integrity_check`. Schlägt er fehl: nicht schreiben, das jüngste gültige Backup anbieten.

---

## 6. Betrieb, Sperre und Übergabe

### 6.1 Start und Ende

| Thema | Umsetzung |
|---|---|
| Start | Doppelklick auf `AI_UseCase_Hub.pyw`. Fehlt `openpyxl`, wird es einmalig im Benutzerkontext installiert (`python -m pip install --user`), mit sichtbarer Fortschrittsanzeige. |
| Zweitstart | Antwortet auf dem Port bereits ein Hub (Prüfung über `/api/ping` mit Kennung), wird nur der Browser geöffnet. |
| Port | Standard 8765; ist er belegt, die nächsten 9 Ports versuchen. |
| Ende | Schaltfläche „Hub beenden“ im Statusmenü. VORSCHLAG: zusätzlich automatisches Ende, wenn 10 Minuten lang kein Browser-Tab ein Lebenszeichen sendet. Beim Ende: Übergabestand veröffentlichen, Sperre freigeben. |
| Backup | Bei jedem Start eine Kopie der Datenbank mit Zeitstempel (über die SQLite-Backup-Funktion, nicht per Dateikopie); die letzten 30 bleiben. Zusätzlich vor jeder Übernahme eines fremden Stands und vor jeder Migration. |
| Fehlerprotokoll | `hub_fehler.log` im lokalen Datenordner; Fehler erscheinen außerdem in „Verwaltung → Protokoll“. |
| Testmodus | Arbeitet auf eigener Datenbank und eigenen Test-Quellen (Kapitel 4.2). Die echte Datenbank wird im Testmodus nie geöffnet. Ein deutliches Band „TESTMODUS“ steht über jeder Seite. |

### 6.2 Übergabestand für die Vertretung

Ziel: Die Vertretung kann am eigenen Rechner weiterarbeiten, ohne dass die Datenbank selbst synchronisiert wird.

**Veröffentlichen** (60 Sekunden nach der letzten Änderung und beim Beenden):

1. Neue `stand_id` (UUID) erzeugen und zusammen mit `revision_published = revision` in `meta` schreiben.
2. Konsistente Kopie über die SQLite-Backup-Funktion in eine temporäre Datei im Übergabe-Ordner schreiben.
3. `integrity_check` auf der Kopie; nur bei Erfolg per `os.replace` zu `stand.db` umbenennen.

**Prüfung beim Start** (gelesen wird eine Temp-Kopie von `stand.db`):

| Situation | Erkennung | Verhalten |
|---|---|---|
| Kein geteilter Stand | Datei fehlt | Normal starten |
| Niemand sonst hat gearbeitet | geteilte `stand_id` = lokale `stand_id_published` | Normal starten |
| Neuerer fremder Stand, lokal nichts Unveröffentlichtes | `stand_id` verschieden und `revision = revision_published` | Hinweis „Stand von <Benutzer> an <Rechner>, <Zeit>“ → nach Bestätigung übernehmen; lokale Datenbank vorher sichern |
| Auseinandergelaufen | `stand_id` verschieden und `revision > revision_published` | Deutliche Warnung. Auswahl: geteilten Stand übernehmen **oder** eigenen Stand behalten und veröffentlichen. Der andere Stand bleibt als Backup erhalten. **Keine automatische Zusammenführung.** |
| Geteilter Stand hat neueres Schema | `schema_version` höher als im Programm | Nur-Lese-Modus mit Hinweis, das Programm zu aktualisieren |

### 6.3 Sperre

Sperrdatei `aktiv.lock` im Übergabe-Ordner mit Benutzer, Rechner, Startzeit und letztem Lebenszeichen (alle 60 Sekunden). Sie verfällt 5 Minuten nach dem letzten Lebenszeichen. Bei gültiger fremder Sperre startet der Hub im **Nur-Lese-Modus** (Band über jeder Seite, alle Eingabefelder gesperrt). Die Sperre ist wegen der Synchronisationsverzögerung nur ein Hinweis; die eigentliche Absicherung ist die Erkennung „auseinandergelaufen“ aus 6.2.

### 6.4 Sicherheit (FEST)

- Server bindet ausschließlich an `127.0.0.1`.
- `Host`-Kopfzeile muss `127.0.0.1:<port>` oder `localhost:<port>` sein, sonst Ablehnung.
- Schreibende Anfragen brauchen ein Sitzungs-Token, das beim Start zufällig erzeugt und nur in die ausgelieferte Seite eingebettet wird; zusätzlich Prüfung der `Origin`-Kopfzeile.
- Keine externen Aufrufe, keine externen Bibliotheken, keine Telemetrie.
- Alle Ausgaben in der Oberfläche werden als Text eingesetzt, nie als HTML (Schutz vor eingeschleustem Markup aus Formularfeldern).

---

## 7. Synchronisationsregeln

| Nr. | Regel |
|---|---|
| S1 | Import beim Start; danach alle 20 Sekunden prüfen, ob sich das Änderungsdatum einer Quelldatei geändert hat (Intervall konfigurierbar). |
| S2 | Gelesen wird immer eine Temp-Kopie (`openpyxl`, `read_only=True`, `data_only=True`). Ist die Datei gesperrt oder unvollständig: bis zu 3 Versuche, dann Eintrag im Import-Protokoll und Statusanzeige „Quelle nicht lesbar“. Kein Absturz, kein Teilimport. |
| S3 | Neue IDs werden als neue Datensätze angelegt (Use Case: Phase `Eingang`; Ticket: Status `Neu`). Kommt dieselbe ID mehrfach vor (Flow-Wiederholung), gilt die erste Zeile; die Dublette wird im Import-Protokoll gezählt. |
| S4 | Quellfelder übernimmt der Hub aus der Quelle, solange der wirksame Wert dem zuletzt importierten entspricht (`<feld> = <feld>_src`). |
| S5 | Ändert sich ein Quellwert und wurde das Feld im Hub geändert (`<feld> ≠ <feld>_src`), entsteht ein Konflikt. Entscheidung per Klick: Quelle übernehmen oder Hub-Wert behalten. In beiden Fällen wird `<feld>_src` auf den neuen Quellwert gesetzt. Nie still überschreiben. |
| S6 | Pflegefelder gehören ausschließlich dem Hub. |
| S7 | Datensätze aus der Quelle werden nie gelöscht; stattdessen Endzustände (`Zusammengeführt`, `Discontinued`, `Abgelehnt`). Verschwindet eine ID aus der Quelle, bleibt der Datensatz erhalten und es entsteht ein Hinweis im Import-Protokoll. |
| S8 | Ein Ticket wird automatisch einem Use Case zugeordnet, wenn „Betroffenes Tool“ mit einer bekannten ID im Format `UC-xxx – Titel` beginnt. Sonst erscheint es unter „Neu eingegangen“ mit der Aktion „Zuordnen“. Die Auswahlliste für das Formular erzeugt der Hub (Verwaltung). |
| S9 | Wird ein Ticket **mit Fix-Version** erstmals auf `Gelöst` oder `Geschlossen` gesetzt, legt der Hub genau einen Eintrag in `releases` an (verknüpft über `ticket_id`). Die Version des Use Cases wird nur angehoben, wenn die Fix-Version höher ist. Vergleich numerisch nach dem Muster `Haupt.Neben[.Patch]`; ist eine Version nicht lesbar, wird nichts automatisch geändert und ein Hinweis angezeigt. Die Oberfläche bestätigt die automatische Buchung sichtbar, mit „Rückgängig“. |

Spaltenzuordnung: Die Spaltennamen der Quell-Excels stehen in der Konfiguration. Fehlt eine zugeordnete Spalte, bricht der Import mit klarer Meldung ab („Spalte ‚…‘ in Quelle 1 nicht gefunden“) und verweist auf die Einstellungen.

---

## 8. Regeln: Schrittleiste und Handlungsbedarf

Diese Regeln ersetzen die Ampellogik aus Version 1. Sie werden ausschließlich in `hub/rules.py` berechnet (E7).

### 8.1 Schrittleiste eines Use Cases

Die Oberfläche zeigt vier **Stufen**. Jede Stufe hat **Schritte** mit eindeutiger Erfüllungsbedingung.

| Stufe (Anzeige) | Phase in der Datenbank | Schritt | Erfüllt, wenn |
|---|---|---|---|
| 1 Eingang | `Eingang` | Gemeldet | Datensatz existiert |
| | | Bewertet | `score`, `owner`, `type` und `origin` gesetzt |
| 2 Umsetzung | `In Bearbeitung` | Geplant | mindestens ein Meilenstein mit Plandatum |
| | | Umgesetzt | Phase = `Abgeschlossen` |
| 3 Governance | `Abgeschlossen` | Betriebsbereit | `lc_owner`, `version`, `next_review` gesetzt |
| | | Eingeordnet | `reg_status = bestätigt` (Teilstand: `Vorabcheck erfolgt`) |
| | | Sponsor | `besprochen` – entfällt bei `origin = übernommen` |
| | | Gremium | `freigegeben` – entfällt bei `origin = übernommen` |
| | | Portal | `veröffentlicht` |
| | | Kommuniziert | `kommuniziert` |
| 4 Betrieb | `Abgeschlossen` | – | alle Governance-Schritte erfüllt oder entfallen |

Der **nächste Schritt** eines Use Cases ist der erste nicht erfüllte Schritt in dieser Reihenfolge. Die Reihenfolge ist eine Empfehlung: Schritte dürfen in anderer Reihenfolge erledigt werden, die Oberfläche blockiert nichts.

### 8.2 Handlungsbedarf

Zwei Stufen: **Blockierend** und **Offen**. Jede Regel liefert Kennung, Klartext mit Begründung und ein Sprungziel.

| Kennung | Stufe | Bedingung | Text (Muster) | Sprungziel |
|---|---|---|---|---|
| H01 | Blockierend | Meilenstein mit Plandatum in der Vergangenheit, nicht erledigt | „Meilenstein ‚…‘ seit N Tagen überfällig“ | Detail → Planung |
| H02 | Blockierend | Offenes Ticket mit Schwere `hoch` | „Ticket mit Schwere hoch seit N Tagen offen“ | Ticket |
| H03 | Blockierend | `next_review` in der Vergangenheit | „Review seit N Tagen überfällig“ | Detail → Betrieb |
| H04 | Blockierend | `board_status = Nachschärfen gefordert` | „Gremium fordert Nachschärfen“ | Detail → Governance |
| H05 | Blockierend | `needs_help` gesetzt | „Hilfe angefordert: …“ | Detail → Überblick |
| H06 | Blockierend | Abgeschlossen, kein `lc_owner` | „Kein Life-Cycle-Owner“ | Detail → Betrieb |
| H07 | Blockierend | Offener Import-Konflikt | „Quelle und Hub weichen ab: Feld …“ | Verwaltung → Konflikte |
| H08 | Blockierend | Quelle nicht lesbar oder Spalte fehlt | „Quelle … konnte nicht gelesen werden“ | Verwaltung → Quellen |
| H09 | Offen, ab Vorlaufzeit vor dem Stichtag Blockierend | Abgeschlossen, `reg_status ≠ bestätigt` | „Regulatorische Einordnung fehlt (Stichtag in N Tagen)“ | Detail → Governance |
| H10 | Offen | Nächster Schritt laut Schrittleiste (genau **ein** Eintrag je Use Case) | „Nächster Schritt: …“ | passender Abschnitt |
| H11 | Offen | Neues Ticket ohne Zuordnung zu einem Use Case | „Ticket zuordnen“ | Ticket |
| H12 | Offen | Abgeschlossen, keine Einträge in `releases` | „Keine Updatehistorie“ | Detail → Betrieb |

Regeln gegen Überladung (FEST):

- Auf der Startseite erscheint je Use Case höchstens **ein** Eintrag der Stufe „Offen“ (H10). Blockierende Einträge erscheinen immer alle.
- H10 entfällt, wenn derselbe Schritt bereits durch eine andere Regel gemeldet wird (z. B. H06 oder H09). Kein Sachverhalt erscheint doppelt.
- Die Detailseite zeigt alle offenen Punkte des Use Cases vollständig.
- H09 ist nötig, weil nach der Migration zunächst fast alle abgeschlossenen Lösungen ohne Einordnung sind. Stichtag und Vorlaufzeit stehen in der Konfiguration (VORSCHLAG Vorlauf: 60 Tage).
- Use Cases in Endzuständen erzeugen keinen Handlungsbedarf.

---

## 9. Oberfläche

### 9.1 Navigation (FEST)

Vier Bereiche in der Kopfzeile, immer sichtbar: **Start · Use Cases · Tickets · Verwaltung**. Rechts daneben: globale Suche (ID, Titel, Melder:in), Schaltfläche „Neu“ (Use Case oder Ticket manuell anlegen), Statusanzeige (Schreibmodus/Nur-Lesen, Zeitpunkt des letzten Imports, „Hub beenden“).

Zuordnung der neun Ansichten aus Version 1:

| Version 1 | Version 2 |
|---|---|
| Übersicht | Start |
| Eingang, In Bearbeitung, Life Cycle, Alle | Use Cases (eine Liste, Phase als Umschalter) |
| Tickets | Tickets |
| Validierungs-Check | Detailseite → Abschnitt Governance |
| Import & Protokoll, Einstellungen | Verwaltung |

### 9.2 Start

Zweck: in zehn Sekunden wissen, was heute zu tun ist.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ AI Use Case Hub    Start  Use Cases  Tickets  Verwaltung    [Suche]  [+ Neu] │
├───────────────────────────────────────────────────┬──────────────────────────┤
│ Handlungsbedarf (7)                               │ Bestand                  │
│                                                   │  Eingang            12   │
│ Blockierend (2)                                   │  Umsetzung           5   │
│  ! UC-014  Meilenstein „Pilot“ 9 Tage überfällig →│  Governance          8   │
│  ! T-031   Ticket Schwere hoch, 4 Tage offen     →│  Betrieb             6   │
│                                                   │                          │
│ Offen (5)                                         │ Stichtag <AI-Richtlinie> │
│  ○ UC-007  Nächster Schritt: Sponsor             →│  in 48 Tagen             │
│  ○ UC-019  Nächster Schritt: Bewerten            →│  6 von 14 eingeordnet    │
│  … alle anzeigen                                  │                          │
│                                                   │ Offene Tickets       9   │
│ Neu eingegangen (3)                               │                          │
│  UC-021  <Titel>                      [Bewerten]  │                          │
│  T-040   <Titel>                      [Zuordnen]  │                          │
└───────────────────────────────────────────────────┴──────────────────────────┘
```

- Links die Arbeitsliste, rechts die Zahlen. Jede Zahl ist ein Link auf die gefilterte Liste.
- Keine Diagramme auf der Startseite.
- Leerer Zustand: „Kein Handlungsbedarf. Letzter Import: <Zeit>.“

### 9.3 Use Cases – Liste

- Umschalter über der Liste: **Eingang · Umsetzung · Governance · Betrieb · Archiv · Alle** (mit Anzahl). „Archiv“ = `Zusammengeführt` und `Discontinued`.
- Tabelle statt Karten. Feste Spalten: Status-Symbol, ID, Titel, Owner, **Nächster Schritt**. Dazu je Umschalter:

| Umschalter | Zusätzliche Spalten | Standard-Sortierung |
|---|---|---|
| Eingang | Bereich, Melder:in, Eingangsdatum, Score | Blockierend zuerst, dann Score absteigend |
| Umsetzung | Nächster Meilenstein, fällig am | Fälligkeit aufsteigend |
| Governance | Fortschritt (z. B. „3 von 6“), Einordnung | Fortschritt aufsteigend |
| Betrieb | Version, Life-Cycle-Owner, nächstes Review, offene Tickets | nächstes Review aufsteigend |
| Archiv / Alle | Phase, zuletzt geändert | zuletzt geändert absteigend |

- Spalten sortierbar, Filter für Owner und Bereich, Textsuche. Filter und Sortierung bleiben beim Zurückkehren erhalten.
- Klick auf eine Zeile öffnet die Detailseite.

### 9.4 Use Case – Detailseite (Kern der Anwendung)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← Use Cases                                                                  │
│ UC-007  <Titel>                               Owner: <Name>   [Sponsor …]    │
│                                                                              │
│  (1) Eingang ─── (2) Umsetzung ─── (3) Governance ─── (4) Betrieb            │
│      erledigt        erledigt          aktiv: 3 von 6                        │
│                                                                              │
│  Offene Punkte: ○ Sponsor-Abstimmung  ○ Gremium  ○ Portal                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Überblick │ Planung │ Governance │ Betrieb │ Verlauf                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ (Inhalt des gewählten Abschnitts)                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Kopf:** ID, Titel, Owner, rechts genau eine Hauptaktion = der nächste Schritt (z. B. „Sponsor-Abstimmung eintragen“).
- **Schrittleiste:** vier Stufen; unter der aktiven Stufe die Schritte als Liste mit Haken.
- **Abschnitte** (der zur Stufe passende ist beim Öffnen vorausgewählt):

| Abschnitt | Inhalt |
|---|---|
| Überblick | Beschreibung, Nutzen, Bereich, Melder:in, Typ, Herkunft, Score, Links, Notizen, Hilfe-Kennzeichen. Im Hub geänderte Quellfelder sind markiert („weicht von Meldung ab“). Phasenwechsel inklusive „Zusammenführen mit …“ und „Discontinued“ (mit Rückfrage). |
| Planung | Meilensteine als einfache Liste: Titel, geplant, erledigt am. Überfällige hervorgehoben. Zeile hinzufügen direkt in der Liste. |
| Governance | Die sechs Governance-Schritte untereinander, je mit Status, Datum und Notiz. Der Schritt „Eingeordnet“ enthält den Validierungs-Vorabcheck (Kapitel 10) und den Verweis auf das kontrollierte Assessment. |
| Betrieb | Life-Cycle-Owner, Version, Reviews; Updatehistorie (`releases`); Tickets dieses Use Cases mit Status. |
| Verlauf | Audit-Einträge dieses Datensatzes, neueste zuerst. |

### 9.5 Tickets

- Board mit vier Spalten: **Neu · In Analyse · In Umsetzung · Gelöst**. `Geschlossen` und `Abgelehnt` sind über einen Umschalter „Erledigte anzeigen“ als Tabelle erreichbar.
- Karte: ID, Titel, Use Case, Schwere (Symbol und Text), Alter in Tagen, Zuständig.
- Statuswechsel per Ziehen **und** über ein Auswahlfeld auf der Karte (Tastaturbedienung).
- Klick öffnet das Ticket als Seitenleiste rechts: Beschreibung, Zuordnung, Typ, Schwere, Zuständig, Fix-Version, Ursache, Lösung, Verlauf.
- Filter: Use Case, Schwere, Zuständig.

### 9.6 Verwaltung

Unterseiten: **Quellen & Import** (Zustand je Quelle, letzte Läufe, „Jetzt importieren“) · **Konflikte** (Gegenüberstellung alt/neu/Hub, zwei Schaltflächen) · **Protokoll** (Audit gesamt, filterbar; Fehler) · **Export & Bericht** (Reporting-Excel, Druckansicht, Auswahlliste für das Ticket-Formular zum Kopieren) · **Übergabe & Backups** (aktueller Stand, Sperre, Backup wiederherstellen) · **Einstellungen** (Pfade, Spaltenzuordnung, Wertelisten, Stichtag, Testmodus).

### 9.7 Gestaltungssystem (VORSCHLAG, in sich FEST einzuhalten)

| Thema | Vorgabe |
|---|---|
| Schrift | System-Schrift (`"Segoe UI", system-ui, sans-serif`); Grundgröße 15 px; drei Größen (Text, Abschnittstitel, Seitentitel); Zahlen in Tabellen mit gleich breiten Ziffern |
| Raster | Abstände nur in Vielfachen von 4 px; Inhaltsbreite maximal 1.280 px; nutzbar ab 1.366 × 768 ohne horizontales Scrollen |
| Farben | Neutraler heller Hintergrund, weiße Flächen, **eine** Akzentfarbe für Hauptaktionen und Auswahl. Statusfarben: Rot (blockierend), Bernstein (offen), Grün (erledigt), Grau (entfällt). Alle Farben als CSS-Variablen an einer Stelle. Kontrast mindestens 4,5 : 1 |
| Status | Immer Symbol **und** Text, nie Farbe allein |
| Flächen | Dünne Rahmenlinien statt Schatten; keine Verläufe; Eckenradius einheitlich |
| Symbole | Eingebettete SVG, kein Icon-Font, keine Emojis |
| Eingaben | Speichern beim Verlassen des Feldes; kurze Bestätigung „Gespeichert“ am Feld; Fehler direkt am Feld mit Klartext. Datumsfelder mit dem Datumswähler des Browsers |
| Rückfragen | Nur bei Endzuständen und beim Übernehmen/Verwerfen eines Stands. Sonst „Rückgängig“ statt Rückfrage |
| Leere Zustände | Jede leere Liste erklärt in einem Satz, was hier erscheint und wie man den ersten Eintrag anlegt |
| Sprache | Deutsch, Sie-freie neutrale Form („Meilenstein hinzufügen“); Datumsformat `TT.MM.JJJJ` |
| Bedienung | Vollständig per Tastatur; sichtbarer Fokus; Adressen je Ansicht (z. B. `#/usecases/UC-007/governance`), damit „Zurück“ im Browser funktioniert |

### 9.8 Technik der Oberfläche (FEST)

Reines HTML, CSS und JavaScript als ES-Module, vom Hub aus `static/` ausgeliefert. Kein Framework, kein Build-Schritt, keine externen Dateien. Die Oberfläche enthält keine Geschäftsregeln; sie stellt dar, was die API liefert.

---

## 10. Validierungs-Vorabcheck

### 10.1 Zweck und Grenzen (FEST)

Einheitlich einschätzen, ob ein Use Case unter die <AI-Richtlinie> fällt und welcher Pfad gilt. **Der Check ersetzt keine Freigabe.** Die verbindliche Entscheidung trifft die zuständige Qualitäts- bzw. Validierungsfunktion; das freigegebene Assessment liegt im kontrollierten Dokumentensystem, der Hub speichert nur den Verweis (X16). Dieser Hinweis steht über dem Fragebogen, im Ergebnis, im Prompt und in der Druckansicht.

### 10.2 Fragen

1. Wird der KI-Output in einem regulierten Prozess verwendet?
2. Art der Lösung: freigegebenes Enterprise-GenAI-Tool, eigene Anwendung oder keine KI-Funktion
3. Ist die KI-Funktion in einen regulierten Prozess eingebettet oder automatisiert sie ihn?
4. Entscheidungsfolge bei falschem Output (hoch / mittel / niedrig)
5. Einfluss des Modells auf das Ergebnis (hoch / mittel / niedrig)
6. Genutzte KI-Fähigkeiten (Chat, Extraktion, Klassifikation, semantische Suche, Trendanalyse)
7. Werden nur Inhalte verarbeitet, die der Nutzer selbst auswählt?
8. Prüft und verantwortet eine geschulte Person jeden Output?
9. Gibt es eine unabhängige Zweitprüfung im bestehenden Prozess?
10. Wird die Freigabe durch den Prüfer dokumentiert?
11. Besteht ein direkter Bezug zu Produktion oder behördlichen Einreichungen?

Darstellung: ein Schritt je Bildschirmabschnitt, Fragen blenden sich aus, wenn sie nicht mehr relevant sind (z. B. nach „keine KI-Funktion“). Jede Frage erlaubt zusätzlich „unklar“.

### 10.3 Ergebnisse

| Ergebnis | Bedeutung |
|---|---|
| Außerhalb des Geltungsbereichs | Output wird nicht in regulierten Prozessen genutzt; Begründung dokumentieren |
| Keine KI-Funktion | Richtlinie nicht anwendbar; ggf. allgemeines Verfahren für computergestützte Systeme |
| Pfad A – Bedingungen erfüllt | Nutzung unter definierten Bedingungen ohne formales Assessment |
| Pfad A – Bedingungen nicht erfüllt | Nachschärfen oder in Pfad B wechseln |
| Pfad B – formales Risiko-Assessment | Assessment mit Vorlage, Akzeptanzkriterien, Test, Monitoring, Change Control |
| Pfad B + direkter Einfluss | zusätzlich erweiterter Standard für Modellbewertung |
| Klärung erforderlich | offene Fragen zuerst klären |

### 10.4 Entscheidungslogik (ANNAHME – vor Umsetzung bestätigen)

Die folgende Reihenfolge ist aus der Ergebnistabelle abgeleitet, **nicht** aus der <AI-Richtlinie>. Enthält der bisherige Entwurf bereits eine Logik, hat diese Vorrang.

1. Frage 2 = „keine KI-Funktion“ → **Keine KI-Funktion**
2. Frage 1 = „nein“ → **Außerhalb des Geltungsbereichs**
3. Eine entscheidungsrelevante Frage ist „unklar“ oder unbeantwortet → **Klärung erforderlich**
4. Frage 2 = „freigegebenes Enterprise-GenAI-Tool“ und Frage 3 = „nein“ → **Pfad A**; „Bedingungen erfüllt“, wenn die Fragen 7, 8 und 10 mit „ja“ beantwortet sind, sonst „Bedingungen nicht erfüllt“
5. Sonst → **Pfad B**; mit Zusatz „direkter Einfluss“, wenn Frage 11 = „ja“

Das Gesamtrisiko ergibt sich aus einer Matrix **Entscheidungsfolge × Modelleinfluss** (Fragen 4 und 5). Aus den gewählten KI-Fähigkeiten (Frage 6) leitet der Check die erforderlichen Kontrollen ab.

**Vorgabe an die Umsetzung:** Entscheidungsreihenfolge, Risikomatrix, Zuordnung Fähigkeit → Kontrollen und alle Ergebnistexte liegen in `validation_rules.json` mit einer Versionsnummer, die bei jedem Durchlauf mitgespeichert wird. Die Werte der Risikomatrix und die Kontrollen **dürfen nicht erfunden werden**. Solange sie nicht geliefert sind, enthält die Datei deutlich als `PLATZHALTER` markierte Werte, und die Oberfläche zeigt beim Ergebnis „Regelwerk unvollständig“.

### 10.5 Prompt-Generator

Aus Beschreibung und Antworten entsteht ein strukturierter Prompt auf Deutsch oder Englisch zum Kopieren. Er wird manuell im freigegebenen internen GenAI-Tool zusammen mit den Richtliniendokumenten ausgeführt (X15: kein API-Aufruf aus dem Hub). Der Prompt verlangt ausdrücklich: keine erfundenen Fakten, Kennzeichnung jeder Annahme, Abschnittsverweise, offene Fragen an die Qualitätsfunktion.

---

## 11. Export und Bericht

### 11.1 Reporting-Excel (Grundlage für eine spätere Power-BI-Auswertung)

- Datei `AI_UseCase_Hub_Reporting.xlsx` im Ordner `Hub_Reporting` des Team-Ordners.
- Wird 60 Sekunden nach der letzten Änderung und beim Beenden neu geschrieben: erst in eine temporäre Datei, dann per `os.replace`. Ist die Zieldatei geöffnet, wird der Versuch beim nächsten Zyklus wiederholt und der Zustand in der Verwaltung angezeigt.
- Jedes Blatt enthält genau eine formatierte Excel-Tabelle mit festem Namen:

| Blatt / Tabelle | Inhalt |
|---|---|
| `tbl_usecases` | eine Zeile je Use Case inkl. Anzeige-Stufe, nächstem Schritt, Governance-Fortschritt |
| `tbl_milestones` | Meilensteine |
| `tbl_releases` | Updatehistorie |
| `tbl_tickets` | Tickets |
| `tbl_handlungsbedarf` | aktueller Handlungsbedarf mit Regelkennung |
| `tbl_meta` | Exportzeitpunkt, Revision, Schema-Version |

- **Schema-Stabilität (FEST):** Spaltennamen und -reihenfolge ändern sich nie; neue Spalten kommen ans Ende. Keine E-Mail-Adressen, keine Notizfelder.
- Der Vollexport aller Tabellen (inklusive Audit) bleibt als manueller Export in der Verwaltung erhalten.

### 11.2 Druckansicht

- **Statusbericht:** eine Seite mit Bestand je Stufe, blockierenden Punkten und Governance-Fortschritt.
- **Steckbrief je Use Case:** eine Seite für die Vorlage beim <Sponsor> oder <AI-Gremium> (Beschreibung, Nutzen, Stufe, Einordnung, offene Punkte).
- Umsetzung über Druck-Stylesheet; Ausgabe als PDF über die Druckfunktion des Browsers. Keine PDF-Bibliothek.

### 11.3 Power BI (nicht Teil des Auftrags an Claude Code)

Spätere Ausbaustufe: Ein Bericht liest die Reporting-Excel aus der Cloud-Ablage. Voraussetzungen, die vorher zu klären sind: Lizenz zum Veröffentlichen, Arbeitsbereich, Leserkreis. Einschränkung: Die Excel ist nur so aktuell wie der letzte Lauf des Hubs.

---

## 12. API (Orientierung, Details legt die Umsetzung fest)

| Methode und Pfad | Zweck |
|---|---|
| `GET /api/ping` | Kennung des Hubs (Zweitstart-Erkennung) |
| `GET /api/state` | Modus, Benutzer, Zustand der Quellen, Zähler |
| `GET /api/actions` | Handlungsbedarf |
| `GET /api/usecases`, `GET /api/usecases/{id}` | Liste (mit Stufe, nächstem Schritt) und Detail (mit Schrittleiste, Meilensteinen, Releases, Tickets, Verlauf) |
| `POST /api/usecases`, `PATCH /api/usecases/{id}` | manuell anlegen; ein Feld ändern |
| `…/milestones`, `…/releases`, `…/links` | Unterlisten pflegen |
| `GET/POST/PATCH /api/tickets` | Tickets |
| `POST /api/usecases/{id}/validations` | Vorabcheck speichern, Ergebnis und Prompt zurückgeben |
| `GET /api/conflicts`, `POST /api/conflicts/{id}/resolve` | Konflikte |
| `POST /api/import/run`, `GET /api/import/log` | Import |
| `POST /api/export/reporting`, `POST /api/export/full` | Exporte |
| `GET/PUT /api/settings` | Einstellungen |
| `POST /api/shutdown` | Hub beenden |

Vorgaben: Feldänderungen senden den erwarteten alten Wert mit; weicht er in der Datenbank ab (zweiter Tab), antwortet der Server mit einem Konflikt statt zu überschreiben. Jede Änderung erzeugt einen Audit-Eintrag. Im Nur-Lese-Modus lehnt der Server jede schreibende Anfrage ab.

---

## 13. Restriktionen (FEST, bindend)

Neue Erweiterungen dürfen keine der folgenden Komponenten einführen.

| Nr. | Nicht verwenden | Grund |
|---|---|---|
| X1 | Listen-basierte Kollaborationsplattform als Datenbank | Für eine pflegende Person kein Mehrwert; siehe Kapitel 2 für die Bedingung zur Neubewertung |
| X2 | Low-Code-App-Baukasten (Canvas-Apps) | Hoher Entwicklungs- und Pflegeaufwand, langsame Iteration |
| X3 | Skript-Automatisierung innerhalb von Excel Online | Unzuverlässig (Timeouts, Abbrüche, fehlende Fehlerrückmeldung) |
| X4 | KI-gestützte App-Generatoren der Agenten-Plattform | Nicht verfügbar |
| X5 | Datenbank-Erweiterungen für Team-Chats | Abgekündigt |
| X6 | Archivierte Governance-Starterkits der Low-Code-Plattform | Nicht mehr gepflegt; erfasst nur Ressourcen der eigenen Plattform |
| X7 | Web-Frameworks mit eigenem Build/Hosting und Webparts für Intranet-Seiten | Hosting, Authentifizierung und Schreibzugriff sind der Engpass |
| X8 | Excel als Datenbank mit mehreren Schreibern | Merge-Konflikte, doppelte Zeilen, inkonsistente Daten |
| X9 | Schreiben in die Quell-Excels durch den Hub | Verlust von Formatierung; unbemerkte Doppelversionen |
| X10 | Verknüpfung über Titel oder Zeilenposition | Ursache der heutigen Verschiebungen |
| X11 | Zusätzliche Python-Pakete außer `openpyxl` | Installation ohne Administratorrechte; gilt auch für Test-Werkzeuge |
| X12 | Externe Bibliotheken per CDN | Abhängigkeit von Internet und Proxy; fremder Code |
| X13 | Skript-Interpreter des Betriebssystems in Desktop-Flows | Durch Datenverlust-Richtlinien gesperrt |
| X14 | Cloud-Hosting oder öffentlich erreichbarer Server | Kein Bedarf; zusätzliche Freigabeprozesse |
| X15 | Externe KI-APIs aus dem Hub heraus | Daten verlassen die freigegebene Umgebung |
| X16 | Ablage freigegebener regulatorischer Assessments im Hub | Der Hub ist kein kontrolliertes System; nur Verweise |

Die Reporting-Excel (Kapitel 11.1) verstößt nicht gegen X8/X9: Sie ist eine reine Ausgabedatei mit dem Hub als einzigem Schreiber und wird nie zurückgelesen.

---

## 14. Technische Rahmenbedingungen

- Windows-Dienstrechner ohne Administratorrechte; Python 3 (getestet mit 3.12)
- Nur Standardbibliothek plus `openpyxl`; Tests mit `unittest`
- Browser: aktueller Chromium-basierter Browser
- Formulare und Flows laufen in einer Umgebung der Automatisierungsplattform, die Formular-Konnektoren erlaubt. Flows hängen nur Zeilen an; in den Flow-Tabellen wird nicht sortiert und nicht gelöscht
- Keine Netzwerkzugriffe des Hubs außer `127.0.0.1` (Ausnahme: einmalige Installation von `openpyxl`)

### Nicht-Ziele der Version 2

Mehrbenutzerbetrieb · Benachrichtigungen per Mail oder Chat · mobile Nutzung · automatisches Zusammenführen auseinandergelaufener Stände · Ablage von Assessments · Power-BI-Bericht.

---

## 15. Umsetzungsplan für Claude Code

Arbeitsweise (FEST):

1. Dieses Dokument vollständig lesen. Bei Widerspruch zwischen Kapiteln gilt Kapitel 2.
2. Phase für Phase arbeiten. Nach jeder Phase anhalten, das Ergebnis zeigen und auf Rückmeldung warten.
3. Punkte aus Kapitel 16 nicht stillschweigend entscheiden: nachfragen, sobald die betroffene Phase beginnt.
4. Keine zusätzlichen Abhängigkeiten, keine externen Dateien, kein regulatorischer Inhalt aus eigener Annahme.
5. Liegt der bisherige Entwurf im Arbeitsverzeichnis: Import-, Sperr- und Backup-Logik als Referenz lesen. Die Oberfläche wird **nicht** übernommen, sondern neu gebaut.
6. Für `importer.py`, `rules.py`, `validation.py` und `handover.py` zuerst Tests schreiben.

| Phase | Inhalt | Abnahme |
|---|---|---|
| 0 Gerüst | Ordnerstruktur, Start, Port-Suche, Zweitstart, Einrichtungsseite, Auslieferung von `static/`, leere Oberfläche mit vier Bereichen, Sicherheitsprüfungen | Doppelklick öffnet den Browser; zweiter Doppelklick erzeugt keinen zweiten Server; fremde `Host`-Kopfzeile wird abgelehnt |
| 1 Datenkern | Schema, Migrationen, Audit, Backup, Integritätsprüfung, Testmodus mit Beispieldaten, Import mit S1–S7 und Konflikten | Tests grün für: neue ID, Dublette, geändertes Quellfeld ohne/mit Hub-Änderung, fehlende Spalte, gesperrte Datei |
| 2 Use Cases | Regeln aus Kapitel 8, Liste, Detailseite mit Schrittleiste und allen Abschnitten außer Vorabcheck, Startseite | Jeder Eintrag der Startseite führt mit einem Klick zum Ziel; Regeln durch Tests je Kennung belegt |
| 3 Tickets | Board, Seitenleiste, S8, S9 mit „Rückgängig“ | S9 bucht genau einmal, auch bei `Gelöst` → `Geschlossen` |
| 4 Vorabcheck | Fragebogen, `validation_rules.json`, Ergebnis, Prompt-Generator | Jedes der sieben Ergebnisse durch einen Test erreichbar; Platzhalter-Regelwerk wird sichtbar gekennzeichnet |
| 5 Übergabe und Ausgabe | Sperre, Übergabestand mit allen fünf Situationen aus 6.2, Reporting-Excel, Druckansicht, Verwaltung vollständig | Tests für alle fünf Situationen; Reporting-Excel öffnet fehlerfrei und hat stabile Spalten |
| 6 Migration | Einmaliger Import der bisherigen Pflegeinformationen (Status, Score, Planung, Life Cycle) über IDs | Abgleichsbericht: übernommene, nicht zuordenbare und widersprüchliche Zeilen; nichts wird ohne Bestätigung geschrieben |

---

## 16. Offene Punkte und Annahmen

| Nr. | Punkt | Betrifft Phase | Benötigt | Stand 12.11.2026 |
|---|---|---|---|---|
| 1 | Entscheidungslogik, Risikomatrix und Kontrollen des Vorabchecks | 4 | Logik aus dem bisherigen Entwurf oder Vorgabe aus der <AI-Richtlinie> | Wird lokal per KI in `validation_rules.json` eingefügt (kein Upload möglich). Die Datei entsteht in Phase 4 mit festem Schema, Prüfbefehl und Anleitung in `ANPASSUNG.md`; bis dahin PLATZHALTER. |
| 2 | Spaltennamen der echten Quell-Excels (inklusive ID-Spalte) | 1 | Kopfzeilen beider Dateien | Quelle 1 geliefert: Titel Use Case · Link zu Ordner · Erwarteter Nutzen (Input Melder) · Interner Titel Use Case · AI Summary · Verantwortliche Person · Score Abweichungsvermeidung /RFT · Score CAPA-Beschleunigung · Score Arbeitszeit-Reduktion · Score Kosten-Reduktion · Score Potenzielle Anzahl Nutzer · Life Cycle erforderlich nach Implementierung? · Gewichteter Gesamtscore · Status Use Case. ID-Spalte fehlt und müsste ergänzt werden. **Offen:** wer die ID vergibt; Kopfzeilen von Quelle 2; fehlende Felder Beschreibung, Bereich, Melder:in, Datum. **Nachtrag:** Die ID schreibt der Flow als Formular-Antwort-ID in eine neue Spalte `ID`; der Hub macht daraus `UC-007` bzw. `T-007`. Weitere Spalten gibt es in Quelle 1 nicht (Beschreibung, Bereich, Melder:in, Datum bleiben leer, bis Formular/Flow erweitert werden). Der Flow schreibt in dieselbe Tabelle, in der auch die Pflegespalten stehen. Kopfzeilen Quelle 2 (Vorschlag des Hubs): ID · Titel · Beschreibung · Betroffenes Tool · Melder:in · Gemeldet am. |
| 3 | Wertelisten: Typ, Herkunft, Governance-Status, Ticket-Typ | 1–3 | bestehende Werte aus Entwurf oder Alt-Excel | Wird lokal per KI in `standort.json` eingefügt (siehe `ANPASSUNG.md`). Listen mit Regelbezug haben feste Schlüssel; anpassbar sind Anzeige und Alias-Werte. |
| 4 | Score: manuell eingegeben oder aus Kriterien berechnet? | 2 | Regel oder Bestätigung „manuell“ | Zunächst manuell. Kriterien und Gewichte sind in `standort.json` (`score`) vorbereitet; Umschalten auf `gewichtet` ohne Codeänderung. |
| 5 | Stichtag der <AI-Richtlinie> und Vorlaufzeit für H09 | 2 | Datum; Vorschlag 60 Tage | Vorlauf 60 Tage bestätigt. **Offen:** das Datum des Stichtags (`deadline.date`). **Nachtrag:** Zunächst ohne Frist. Eintragen in `standort.json` unter `deadline.date` (Stelle ist dort und in `hub/rules.py` markiert). |
| 6 | Versionsformat der Lösungen (`Haupt.Neben[.Patch]`?) | 3 | Bestätigung | Bestätigt: `Haupt.Neben[.Patch]`. |
| 7 | Aufbau der bisherigen Pflege-Tabellen für die Migration | 6 | anonymisierte Beispieldatei | Keine separate Datei vorhanden. Die Pflegespalten stehen in Quelle 1 selbst (siehe Punkt 2) und sind in `standort.json` unter `migration` hinterlegt; eine passende Beispieldatei wird in Phase 6 erzeugt. |
| 8 | Pfad des Team-Ordners; ist der Ordner für die Vertretung synchronisiert? | 5 | Bestätigung | Das gesamte Konstrukt liegt auf einem Teams-SharePoint. Pfade werden relativ zum Programmordner gespeichert. Die Datenbank bleibt lokal (E3). |
| 9 | Automatisches Beenden nach 10 Minuten ohne offenen Tab | 0 | Zustimmung oder Ablehnung | Zustimmung. Zusätzlich gewünscht: Schutz gegen versehentlichen Zugriff einer zweiten Person (Umsetzung mit der Sperre in Phase 5). |
| 10 | Liegt der bisherige Entwurf als Referenz vor? | 0 | Datei im Arbeitsverzeichnis | Nein. Neubau ausschließlich auf Basis dieses Konzepts. |
| 11 | Wechsel von „Eingang“ in die Umsetzung: Kapitel 8.1 nennt dafür keinen Schritt | 2 | Bestätigung | **ANNAHME aus Phase 2:** Ist ein Use Case bewertet und noch in Phase `Eingang`, heißt die Hauptaktion „Umsetzung starten“ (setzt Phase `In Bearbeitung`, mit „Rückgängig“). Es gibt keinen automatischen Phasenwechsel. |
| 12 | Governance-Fortschritt bei entfallenen Schritten | 2 | Bestätigung | **ANNAHME aus Phase 2:** Gezählt werden nur anwendbare Schritte, bei Herkunft `übernommen` also „x von 4“ statt „x von 6“. |
| 13 | Startseite: Auswahl des einen Eintrags „Offen“ je Use Case; Neueingänge | 2 | Bestätigung | **ANNAHME aus Phase 2:** Vorrang H10, dann H09, dann H12. Was unter „Neu eingegangen“ steht, erscheint nicht zusätzlich als „Nächster Schritt: Bewerten“ oder „Ticket zuordnen“. |
| 14 | Eingangsdatum und Melder:in ohne Spalte in Quelle 1 | 2 | Entscheidung zum Flow | Nicht zwingend. Ohne Spalte gilt der Tag des ersten Imports als Eingangsdatum; Melder:in bleibt leer oder wird im Hub nachgetragen. Schreibt der Flow die Angaben später, genügt die Zuordnung in `standort.json`. |
| 15 | Vorabcheck: welche Fragen „entscheidungsrelevant“ sind und wann „unklar“ zu „Klärung erforderlich“ führt | 4 | Bestätigung | **ANNAHME aus Phase 4:** Fragen 1 bis 3 immer; 7, 8 und 10 nur auf dem Weg zu Pfad A; 11 nur auf dem Weg zu Pfad B. Frage 9 entscheidet nicht. Steht so in `validation_rules.json` und ist dort änderbar. |
| 16 | S9: Buchung nach „Rückgängig“ | 3 | Bestätigung | **ANNAHME aus Phase 3:** Eine zurückgenommene Buchung wird bei einem späteren Statuswechsel nicht erneut ausgelöst. |
| 17 | Schutz vor versehentlichem Zugriff einer zweiten Person | 5 | Bestätigung | Umgesetzt als Liste berechtigter Benutzer (`Hub_Uebergabe/berechtigte.json`) plus Sperrdatei; alle anderen und jede zweite gleichzeitige Sitzung sehen den Hub nur lesend. |
| 18 | Migration: Umgang mit vorhandenen Werten | 6 | Bestätigung | **ANNAHME aus Phase 6:** Leere Felder im Hub werden gefüllt, vorhandene nie überschrieben (Widerspruch im Bericht). „AI Summary“ wird zur Beschreibung, „Interner Titel“ und „Life Cycle erforderlich“ kommen in die Notizen. |

---

## 17. Platzhalter

| Platzhalter | Bedeutung |
|---|---|
| `<Organisation>` | Unternehmen |
| `<Standort>` | Werk bzw. Standort, für den der Hub betrieben wird |
| `<Sponsor>` | Standortverantwortliche Person für KI-Themen |
| `<AI-Gremium>` | Entscheidungsgremium für KI-Lösungen |
| `<Lösungsportal>` | Interne Übersichtsseite der freigegebenen Prompts, Tools und Agents |
| `<AI-Richtlinie>` | Interne Arbeitsanweisung zur Nutzung von KI in regulierten Umgebungen, inkl. Assessment-Vorlage und Standard zur Modellbewertung |
| `<interne Kommunikationsplattform>` | Unternehmensinternes soziales Netzwerk bzw. Newsfeed |
| `<Team-Ordner>` | Synchronisierter Ordner der Cloud-Ablage für Übergabestand und Reporting |
| internes GenAI-Tool | Vom Unternehmen freigegebener Chat-Assistent |
