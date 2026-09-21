# Was sich durch dein Setup geändert hat

Drei Antworten, drei strukturelle Änderungen. Die kosmetischen Umbenennungen sind hier nicht aufgeführt.

## 1. Nur remote → eigenes Playbook, 50 statt 45 Minuten

**Warum:** Die Mitmach-Phase ist der Kern der Reihe, und remote ist sie das Erste, was zusammenbricht. Kamera aus, nicht angesprochen, nicht mitgemacht.

**Was daraus folgt:**
- `Remote-Durchfuehrung.md` ist neu und Pflichtlektüre, nicht Anhang.
- Sessions sind 50 Minuten mit 5 Minuten Technikpuffer.
- Pair-Prompting läuft in **vorab konfigurierten** Breakout-Räumen, nicht live zugewiesen.
- Jede Mitmach-Phase braucht ein **gemeinsames Ergebnisdokument mit einer Zeile pro Paar**. Ohne Abgabe arbeitet remote die Hälfte nicht.
- In der Fragerunde nie "hat jemand eine Frage?". Namentlich, rotierend, mit Liste.
- Ab 10 Teilnehmern brauchst du einen zweiten Trainer für den Chat.
- Das Backup-Video pro Session ist nicht mehr optional.

## 2. GPT-5.6 Thinking als Standardmodell → Session 1 und 19 umgebaut

**Die unbequeme Konsequenz:** Ein Reasoning-Modell macht zwei der klassischen Einsteiger-Lerninhalte kaputt.

**Session 1 (Grundlagen):** Der Standard-Aha-Moment "Wie viele Buchstaben hat Erdbeere" funktioniert bei denkenden Modellen oft nicht mehr, weil das Modell nachrechnet. Wenn du ihn trotzdem zeigst und er klappt, hast du das Gegenteil bewiesen. Ersetzt durch: **die Denkspur aufklappen und mitlesen.** Das ist der stärkere Moment, weil die Leute zum ersten Mal sehen, dass da kein Wissen abgerufen, sondern gearbeitet wird. Der Bruch kommt danach über eine Wissensfrage, die das Modell nicht wissen kann.

**Session 19 (früher "Schritt für Schritt"):** "Denke Schritt für Schritt" ist bei GPT-5.6 Thinking überflüssig und kann die interne Struktur sogar überschreiben. Die Session heißt jetzt **"Denkende Modelle: Wann Thinking hilft und wann es bremst"** und vermittelt drei neue Fähigkeiten:
1. Die Denkspur als Prüfwerkzeug lesen und einen einzelnen falschen Schritt gezielt korrigieren.
2. Erkennen, wann Denken Verschwendung ist (Umformulieren, Übersetzen, Zusammenfassen) und ein schnelles Modell reicht.
3. Aufgaben zerlegen, damit **du** an jeder Naht prüfen kannst, nicht damit das Modell denkt.

**Session 3 (Nachbessern):** Von 5 auf 3 Runden reduziert und dafür das Bündeln mehrerer Korrekturen in einen Prompt eingeführt. Wartezeit bei denkenden Modellen frisst sonst die Übungszeit.

**Session 13 (Halluzinationen):** Deutlich schwerer geworden. Ein Reasoning-Modell halluziniert seltener und damit gefährlicher, weil die Leute aufhören zu prüfen. Die Demo braucht jetzt Fälle, an denen das Modell tatsächlich scheitert: DOIs, Fakten nach dem Wissensstichtag, zusammengesetzte lokale Informationen. **Teste jede Demo am Vortag. Wenn sie funktioniert, hast du das falsche Beispiel.**

## 3. Datenschutzregeln vorhanden und geschult → Session 14 komplett neu

**Warum:** Eine Datenschutz-Grundschulung zu wiederholen, wenn alle sie hatten, verbrennt eine Session und dein Standing.

**Was stattdessen drinsteht:** Session 14 heißt jetzt **"Welches Modell, welcher Datenweg?"** und behandelt das, was in deinem Setup wirklich unklar ist:
- Die Werkzeuglandschaft als Bild: Copilot im Tenant, interne KI-Software, und alles Übrige als rote Spalte.
- **Der Modellwechsel in Copilot.** Deine Teilnehmer treffen zwischen OpenAI- und Claude-Modellen eine Wahl, von der sie nicht wissen, dass sie sie treffen. Dieselbe Aufgabe mit beiden laufen lassen und vergleichen.
- Die Grenzfälle der bestehenden Richtlinie, nicht ihre Grundlagen. Die Kartensortierung bleibt, aber die Auflösung lautet jetzt "was sagt unsere Richtlinie dazu", nicht "hier ist die Regel".
- Copilot macht falsch gesetzte SharePoint-Freigaben sichtbar. Das überrascht regelmäßig und gehört auf eine Slide.

## 4. Interne KI-Software statt ChatGPT-Oberfläche → offenes Risiko in Modul D

**Das musst du noch prüfen.** Custom Instructions, Projekte, Datei-Upload, Bildgenerierung und Sprachmodus sind Funktionen der **ChatGPT-Oberfläche**, nicht des Modells. Eine interne Software, die GPT-5.6 Thinking über die Schnittstelle einbindet, reicht davon oft nichts durch.

Betroffen sind Sessions 20, 21, 22, 23. Jede trägt jetzt einen Prüfhinweis und eine Copilot-Rückfalloption. Für Session 20 steht ein Ersatz ohne gespeicherte Anweisungen drin (Textbaustein in OneNote). Wenn Bilder und Sprache komplett wegfallen, sind zwei Slots frei. Mein Vorschlag dafür steht am Ende von `26-Lernkonzepte.md`: eine zweite Workflow-Session und eine offene Sprechstunde. Die Sprechstunde wird bei Einsteigern oft die beliebteste Session der Reihe.
