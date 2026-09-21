# Prompt-Bibliothek zur Schulungsreihe

Alle Prompts zum Kopieren. Platzhalter in [eckigen Klammern] ersetzen. Reihenfolge folgt den Sessions.

**Remote:** Jeden Prompt als Chat-Nachricht posten, nicht nur auf die Slide. Bei geteiltem Bildschirm kann niemand von einer Slide abtippen, während er selbst tippt.

**Bei GPT-5.6 Thinking weggelassen:** "Denke Schritt für Schritt" steht hier nicht mehr als eigener Prompt. Das Modell macht es selbst. Stattdessen stehen unten die Prompts für denkende Modelle.

## Grundlagen

**Der Vier-Bausteine-Prompt (Session 2)**
```
Du bist [Rolle, z. B. Assistenz der Geschäftsführung].
Aufgabe: [Was genau soll entstehen?]
Kontext: [Für wen, warum, was ist wichtig, was ist tabu?]
Format: [Länge, Ton, Sprache, Struktur, z. B. "maximal 5 Sätze, per Sie, freundlich"]
```

**Nachbessern (Session 3)**
```
Kürzer.
Förmlicher.
Streich den zweiten Absatz.
Gib mir 3 Varianten der Betreffzeile.
Formuliere den letzten Satz so, dass er nach einer Handlung fragt.
```

## Alltag

**Zusammenfassen nach Zielgruppe (Session 6)**
```
Fasse den folgenden Text für [Zielgruppe] zusammen.
Nur [Entscheidungen und Risiken / offene Punkte / nächste Schritte].
Maximal [5] Bullets. Wenn etwas fehlt, das du erwarten würdest, sag es am Ende.

[Text]
```

**Ton anpassen (Session 7)**
```
Formuliere die folgende Nachricht für drei Empfänger um:
1. [Betriebsrat]
2. [neue Kollegen]
3. [Vorstand]
Inhalt bleibt identisch. Jede Version maximal 4 Sätze.

[Nachricht]
```

**Korrekturlesen mit Änderungsliste (Session 8)**
```
Korrigiere Rechtschreibung, Grammatik und Zeichensetzung.
Ändere nicht den Inhalt und nicht den Stil.
Liste am Ende jede Änderung auf: Original → Korrektur.

[Text]
```

**Excel-Copilot (Session 10)**
```
Welche [Region] hat den höchsten [Umsatz] im [Q2]?
Füge eine Spalte "Marge" hinzu: Umsatz minus Kosten.
Erkläre mir die Formel in [E2] in einfachen Worten.
Markiere alle Zeilen, in denen [Marge] negativ ist.
```

**Brainstorming in vier Schritten (Session 12)**
```
Gib mir 20 Ideen für [Thema]. Bedingung: [z. B. unter 30 € pro Person].
```
```
Gruppiere die Ideen in [Kategorien].
```
```
Bewerte jede Idee nach Aufwand (1–5) und Wirkung (1–5).
```
```
Welche 3 würdest du streichen und warum?
```

## Qualität und Sicherheit

**Selbstprüfung erzwingen (Session 13)**
```
Welche Aussagen in deiner Antwort sind Fakten, die ich prüfen sollte?
Markiere alles, wo du dir nicht sicher bist.
```

**Quellen einfordern (Session 16)**
```
Beantworte die Frage und gib zu jeder Aussage die Quelle als Link an.
Wenn du keine Quelle hast, schreib "keine Quelle" statt eine zu erfinden.

[Frage]
```

**Bias-Check (Session 15)**
```
Prüfe den folgenden Text auf geschlechtsspezifische, altersbezogene oder kulturelle Verzerrungen.
Nenne jede Stelle und schlage eine neutrale Alternative vor.

[Text]
```

## Fortgeschritten

**Beispiele geben (Session 18)**
```
Hier sind drei Beispiele für [Stil / Format]:
1. [Beispiel]
2. [Beispiel]
3. [Beispiel]
Erstelle ein viertes im exakt gleichen Stil für: [neuer Fall]
```

**Denkende Modelle (Session 19)**

Einen einzelnen falschen Schritt aus der Denkspur korrigieren, statt "das ist falsch" zu sagen:
```
In Schritt [2] hast du [19 % Umsatzsteuer] angenommen. Richtig ist [7 %].
Rechne von dort neu, alles Übrige bleibt.
```
Rückfragen erzwingen, funktioniert bei denkenden Modellen besonders gut:
```
Bevor du antwortest, stell mir 3 Rückfragen, die deine Antwort verbessern würden.
```
Zerlegen, damit du an jeder Naht prüfen kannst:
```
Zerlege diese Aufgabe in Teilaufgaben. Bearbeite dann nur die erste und warte auf mein OK.
```
Nachbessern bündeln, weil jede Runde Wartezeit kostet (Session 3):
```
Kürzer, förmlicher, und streich den letzten Absatz.
```

**Modelle vergleichen (Session 14)**

Dieselbe Aufgabe an ein OpenAI- und ein Claude-Modell in Copilot, dann vergleichen:
```
[Deine echte Arbeitsaufgabe, wörtlich identisch in beiden Durchläufen.]
```
Danach notieren: Welches Ergebnis passte besser und woran genau lag es?

**Persönliche Anweisungen (Session 20, Vorlage)**
```
Ich arbeite als [Rolle] in [Bereich, Firmengröße].
Antworte auf Deutsch, per Sie, knapp.
Wenn du dir nicht sicher bist, sag es.
Keine Einleitungssätze, keine Zusammenfassung am Ende.
```

**Dateien befragen (Session 21)**
```
Wo im Dokument steht [Thema]? Zitiere die Stelle und nenne die Seite.
```
```
Erstelle aus Kapitel [3] eine Checkliste mit Ankreuzfeldern.
```
```
Welche Auffälligkeiten siehst du in diesen Daten? Nenne konkrete Zeilen.
```

**Bilder (Session 22)**
```
Erstelle ein [Icon / Titelbild] für [Zweck].
Stil: [flach, minimalistisch], Farben: [blau, weiß], ohne Text, ohne Personen.
```

**Diktat aufräumen (Session 23)**
```
Das folgende ist ein freies Diktat. Mach daraus 3 klare Bullets. Streich Füllwörter und Wiederholungen.

[Diktat]
```

## Vorlage für eigene Prompt-Karten (Session 24)

```
Name:            [Kurzer Name, z. B. "Kundenabsage freundlich"]
Wann nutzen:     [Situation]
Werkzeug:        [ChatGPT / Copilot Word / Copilot Outlook]
Prompt:          [Der Text]
Beispielergebnis: [Ein gutes Ergebnis, gekürzt]
Prüfen:          [Was muss ich immer kontrollieren?]
Zuletzt getestet: [Datum]
```
