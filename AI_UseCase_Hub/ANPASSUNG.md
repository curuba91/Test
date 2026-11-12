# Standortdaten lokal einfügen (von Hand oder per KI)

Alles Standortspezifische steht in Dateien im Programmordner, nicht im Code:

| Datei | Inhalt | Stand |
|---|---|---|
| `standort.json` | Bezeichnungen, Wertelisten, Spaltenzuordnung, Stichtag, Score-Regel, Pfad-Vorgaben | vorhanden |
| `validation_rules.json` | Entscheidungslogik, Risikomatrix, Kontrollen und Texte des Vorabchecks | vorhanden, drei Teile sind PLATZHALTER |

## Ablauf

1. Sicherungskopie von `standort.json` anlegen.
2. Datei im freigegebenen internen GenAI-Tool anpassen lassen (Prompt unten) oder von Hand ändern.
3. Ergebnis zurück in den Programmordner speichern.
4. Prüfen, im Programmordner:

   ```bash
   python -B -m hub.config
   ```

   `FEHLER` muss beseitigt werden, `OFFEN` listet die noch nicht bestätigten Platzhalter.
   Dieselbe Liste zeigt der Hub unter Verwaltung → Einstellungen.

## Häufige Einzeländerungen

- **Stichtag der Richtlinie (Regel H09):** in `standort.json` bei `"deadline"` den Wert von `"date"` von `null`
  auf das Datum setzen, zum Beispiel `"date": "2027-06-30"`. Die Stelle ist in der Datei mit
  „HIER DEN STICHTAG EINTRAGEN“ markiert. Im Programmcode ist nichts zu ändern.
- **Spaltennamen der Quell-Excels:** unter `"columns"`. Die ID-Spalte füllt der Flow mit der
  Formular-Antwort-ID; aus `7` macht der Hub `UC-007` (`"id_prefix"`). Zeilen ohne ID werden nicht
  importiert und auf der Startseite gemeldet.
- **Ticket-Excel:** Die vorgeschlagenen Kopfzeilen sind `ID`, `Titel`, `Beschreibung`, `Betroffenes Tool`,
  `Melder:in`, `Gemeldet am`. Eine passende Datei mit Beispielzeilen erzeugt der Testmodus im lokalen
  Datenordner unter `test\Quelle2_Tickets.xlsx`.
- **Gewichteter Score:** je Kriterium unter `"score"` ein `"weight"` eintragen und `"mode"` auf
  `"gewichtet"` stellen.

## Was geändert werden darf

| Abschnitt | Erlaubt | Nicht erlaubt |
|---|---|---|
| `labels` | Platzhalter wie `<Sponsor>` durch echte Bezeichnungen ersetzen | Schlüssel umbenennen |
| `deadline` | `date` als `JJJJ-MM-TT` oder `null`; `lead_days` als ganze Zahl | anderes Datumsformat |
| `value_lists` mit `values` (`usecase_type`, `ticket_type`, `area`) | Werte frei ändern, ergänzen, entfernen | doppelte Werte |
| `value_lists` mit `entries` (Phase, Herkunft, Governance-Status, Ticket-Status, Schwere) | `label` (Anzeige) und `aliases` (Schreibweisen aus der Alt-Excel, die auf den Schlüssel abgebildet werden) | `key` ändern, Einträge hinzufügen, entfernen oder umsortieren |
| `score` | `weight` je Kriterium setzen und `mode` auf `gewichtet` stellen | `gewichtet` ohne vollständige Gewichte |
| `columns` | je Hub-Feld den exakten Spaltennamen der Quell-Excel oder `null` | dieselbe Spalte zwei Feldern zuordnen |
| `status` | nach Bestätigung von `PLATZHALTER` auf `FEST` setzen | – |

Die Schlüssel der Listen mit `entries` sind fest, weil die Geschäftsregeln daran hängen
(zum Beispiel: Sponsor und Gremium entfallen bei Herkunft `übernommen`). Kennt der Standort
einen **zusätzlichen** Zustand, ist das eine Regelentscheidung und keine Konfiguration:
bitte als Änderungswunsch melden, nicht in die Datei schreiben.

## Prompt zum Kopieren

```text
Du bearbeitest eine JSON-Konfigurationsdatei. Halte dich strikt an diese Regeln:
1. Gib die vollständige Datei als gültiges JSON zurück, ohne Kommentare und ohne Erklärtext.
2. Ändere keine Schlüsselnamen und keine Struktur. Ändere "config_version" nicht.
3. In "value_lists" gilt: Bei Listen mit "entries" darfst du nur "label" und "aliases"
   ändern. "key" bleibt unverändert, es kommen keine Einträge dazu oder weg, die
   Reihenfolge bleibt. Bei Listen mit "values" darfst du die Werte frei setzen.
4. Trage nur Werte ein, die in meinen Angaben unten stehen. Erfinde nichts. Was nicht
   angegeben ist, bleibt unverändert und behält "status": "PLATZHALTER".
5. Setze "status" nur bei den Listen und Zuordnungen auf "FEST", die ich unten
   vollständig angegeben habe.
6. Passt ein Wert aus meinen Angaben zu keinem vorhandenen "key", trage ihn nicht ein,
   sondern nenne ihn nach dem JSON in einer Liste "Nicht zuordenbar".

Meine Angaben:
- Bezeichnungen (labels): ...
- Stichtag der Richtlinie: ...
- Typen von Use Cases: ...
- Bereiche: ...
- Ticket-Typen: ...
- Bisherige Statuswerte und was sie bedeuten: ...
- Spaltennamen Quelle 1 (Use Cases), in Reihenfolge: ...
- Spaltennamen Quelle 2 (Tickets), in Reihenfolge: ...
- Gewichte der Score-Kriterien: ...

Die Datei:
<Inhalt von standort.json einfügen>
```

## Regelwerk des Vorabchecks (`validation_rules.json`)

Prüfen, im Programmordner:

```bash
python -B -m hub.validation
```

Beide Dateien lassen sich auch im Hub bearbeiten: Verwaltung → Einstellungen → „… bearbeiten“. Gespeichert wird
nur, was die Prüfung besteht.

| Abschnitt | Was einzutragen ist |
|---|---|
| `decision.rules` | Reihenfolge der Entscheidung. Jede Regel hat `result` (Schlüssel aus `results`) und optional `if` (Frage → erlaubte Antworten) und `if_unclear` (Fragen, von denen eine unbeantwortet oder „unklar“ ist). Die erste zutreffende Regel gilt, die letzte hat keine Bedingung. Der ausgelieferte Stand ist die ANNAHME aus Kapitel 10.4 des Konzepts. |
| `risk_matrix.values` | Neun Werte: `values[Entscheidungsfolge][Modelleinfluss]`, jeweils `hoch`, `mittel` oder `niedrig` laut Richtlinie. |
| `controls.by_capability` | Je KI-Fähigkeit die Liste der erforderlichen Kontrollen als Texte. |
| `status` in diesen drei Abschnitten | Nach Bestätigung von `PLATZHALTER` auf `FEST` setzen. Solange einer `PLATZHALTER` ist, zeigt der Hub „Regelwerk unvollständig“. |
| `rules_version` | Bei jeder inhaltlichen Änderung erhöhen; die Version wird mit jedem Durchlauf gespeichert. |

Prompt für die KI, zusätzlich zu den Regeln oben:

```text
Trage in diese JSON-Datei ausschließlich Werte ein, die wörtlich oder sinngemäß in den beigefügten
Richtliniendokumenten stehen, und nenne zu jedem eingetragenen Wert nach dem JSON den Abschnitt der
Richtlinie. Erfinde keine Werte der Risikomatrix und keine Kontrollen. Was die Richtlinie nicht hergibt,
bleibt "PLATZHALTER". Ändere keine Schlüssel in "questions" und "results". Gib die vollständige Datei
als gültiges JSON zurück.

Die Datei:
<Inhalt von validation_rules.json einfügen>
```
