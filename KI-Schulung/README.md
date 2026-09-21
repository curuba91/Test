# KI-Schulungsreihe: 26 Konzepte für Einsteiger

**Setup dieser Reihe (bestätigt):**

| Punkt | Stand |
|---|---|
| Werkzeug 1 | Microsoft 365 Copilot, mit OpenAI- **und** Claude-Modellen zur Auswahl |
| Werkzeug 2 | Interne KI-Software, in der GPT-5.6 Thinking läuft (Reasoning-Modell) |
| Datenschutzregeln | Vorhanden, alle sind geschult |
| Format | **Nur remote** |
| Zielgruppe | Einsteiger, kein Coding |

Die drei Antworten haben den Plan an drei Stellen strukturell verändert. Was genau, steht in `Aenderungen.md`.

## Dokumente in diesem Ordner

| Datei | Inhalt |
|---|---|
| `README.md` | Diese Übersicht: Didaktik, Ablauf, Einbindungsmethoden |
| `26-Lernkonzepte.md` | Alle 26 Sessions im Detail (Zeigen / Mitmachen / Fragerunde / Material) |
| `Remote-Durchfuehrung.md` | Das Remote-Playbook. Pflichtlektüre, nicht Anhang. |
| `Aenderungen.md` | Was sich durch dein Setup geändert hat und warum |
| `Vorlage-Session.md` | Leere Vorlage für eine einzelne Session |
| `Prompt-Bibliothek.md` | Die Prompts aus allen Sessions zum Kopieren |
| `Teilnehmer-Fragen.md` | Was noch offen ist |
| `regiepult.html` | Quelldatei der Trainer-Oberfläche (als Artifact veröffentlicht) |

## Die Trainer-Oberfläche

Die Markdown-Dateien sind die Quelle, aber nicht das Arbeitswerkzeug. Dafür gibt es das **Regiepult**, eine Webseite mit drei Ansichten:

| Ansicht | Wofür |
|---|---|
| Übersicht | Vorbereitungsstand aller 26 Sessions, abgeleitet aus Häkchen. Zeigt, was als Nächstes fehlt. |
| Session | Ablauf mit Minutenangaben, Slide-Entwürfe zum Kopieren, Prompts mit Kopierknopf, Materialliste, Notizen, Parkplatz. |
| Live | Stoppuhr über die 7 Phasen. Leertaste startet, Pfeil rechts schaltet weiter. Rechts steht, was du in dieser Phase tust. |

Häkchen, Notizen und Parkplatz-Fragen werden gespeichert und überleben das Schließen der Seite.

**Was die Oberfläche nicht tut:** Sie baut keine Slides. Sie liefert deren Text, damit du ihn in die Firmenvorlage kopierst. Die Übungsdokumente und die Backup-Videos musst du selbst erstellen.

## Feste Session-Struktur (50 Minuten, remote)

| Phase | Dauer | Was passiert |
|---|---|---|
| Einstieg | 3 min | Eine Umfrage (Teams-Abstimmung oder Forms). Ergebnis bleibt sichtbar. |
| Zeigen | 10 min | Trainer macht es live vor. Ein einziges, realistisches Beispiel. Kein Slide-Vortrag. |
| Übergabe | 2 min | Prompt in den Chat, Breakout-Räume öffnen. |
| Mitmachen | 20 min | Alle machen dieselbe Aufgabe. In Breakout-Räumen zu zwei ("Pair-Prompting"). |
| Vergleichen | 6 min | Zwei vorher benannte Paare teilen den Bildschirm. |
| Fragerunde | 7 min | Namentlicher Aufruf, keine offene Frage in die Runde. Parkplatz für den Rest. |
| Abschluss | 2 min | Material im Kanal, Ausblick in einem Satz. |

45 Minuten wären richtig in Präsenz. Remote brauchst du 5 Minuten Puffer für Technik, Breakout-Wechsel und Copilot-Ladezeiten. Plan sie ein, sonst frisst es die Fragerunde.

## Rhythmus

Empfehlung: **wöchentlich, fester Slot** (z. B. Dienstag 11:00). 26 Sessions sind damit ein halbes Jahr. Zweiwöchentlich vergessen Einsteiger zu viel zwischen den Terminen, und remote ist die Bindung ohnehin schwächer.

Die Reihe ist in 5 Module gegliedert. Jedes Modul ist in sich abgeschlossen, damit Quereinsteiger andocken können.

| Modul | Sessions | Thema |
|---|---|---|
| A | 1–5 | Grundlagen: Wie funktioniert das, wie rede ich mit der KI |
| B | 6–12 | Alltag: Die 7 häufigsten Aufgaben im Büro |
| C | 13–17 | Qualität und Sicherheit: Fehler, Datenwege, Manipulation |
| D | 18–23 | Fortgeschrittene Techniken: Mehr aus dem Werkzeug holen |
| E | 24–26 | Anwenden: Eigene Workflows, Abschluss |

## Material pro Session

Pro Session brauchst du genau fünf Dinge. Mehr nicht.

1. **3–5 Slides** (Titel, Lernziel, der Prompt, die Übungsaufgabe, Fragerunde). Slides sind Gerüst, nicht Inhalt.
2. **Ein Backup-Video (2–4 min)** der Live-Demo, aufgenommen mit Clipchamp oder Teams-Aufnahme. Remote ist das **nicht optional**: Copilot hängt, VPN bricht, Lizenzen zicken. Das Video geht danach an alle, die gefehlt haben.
3. **Ein Übungsdokument** (lange E-Mail, Excel-Tabelle, Protokoll). Immer fiktiv.
4. **Ein gemeinsames Ergebnisdokument** (Word in Teams, alle dürfen schreiben). Eine Zeile pro Paar. Das ist remote der einzige verlässliche Mitmach-Zwang.
5. **Der Prompt als Chat-Nachricht.** Nicht nur auf der Slide. Bei geteiltem Bildschirm kann niemand von einer Slide abtippen.

## Einbindungsmethoden (remote angepasst)

| Methode | Wie remote | Wann |
|---|---|---|
| Pair-Prompting | Breakout-Raum zu zwei, einer teilt Bildschirm, nach 10 min tauschen | Jede Mitmach-Phase |
| Gemeinsames Ergebnisdokument | Eine Zeile pro Paar, live sichtbar | Jede Mitmach-Phase |
| Prompt-Battle | Zwei Breakout-Gruppen, dieselbe Aufgabe, Abstimmung per Teams-Poll | Session 7, 12, 26 |
| Fehler finden | Vorbereitete falsche Antworten im Ergebnisdokument, Urteil pro Zeile | Session 13, 17 |
| Bring Your Own Problem | Teilnehmer meldet die Aufgabe vorab im Kanal, wird live gelöst | Ab Session 6 ein Slot |
| Vorher/Nachher | Bildschirmfreigabe, Original und Ergebnis nebeneinander | Session 4, 7, 8 |
| Umfrage am Anfang | Teams-Abstimmung, läuft während die Leute reinkommen | Jede Session |
| Namentlicher Aufruf | Rotierende Liste, wer schon dran war. Nie "hat jemand eine Frage?" | Jede Fragerunde |
| Parkplatz | Kanal-Beitrag, den du live mitschreibst | Jede Session |
| Erfolgs-Sammlung | Teams-Kanal "KI-Erfolge": ein Satz pro gelöster Aufgabe | Laufend |

## Was du vermeiden solltest

- **Mitmach-Phase im Hauptraum.** Dann tippt niemand. Immer Breakouts, auch bei 6 Personen.
- **Slide-Vortrag über 10 Minuten.** Einsteiger lernen durch Tun.
- **Perfekte Demos.** Zeig auch, wenn die KI Unsinn produziert. Das ist der wichtigste Lernmoment, und bei einem denkenden Modell musst du dafür gezielt suchen.
- **Alle 26 Sessions vorab produzieren.** Bau die ersten 5, hol Feedback, dann den Rest.
- **Eine Funktion zeigen, die es bei euch nicht gibt.** Die interne KI-Software reicht vielleicht kein Datei-Upload, keine Bilder und keinen Sprachmodus durch. Prüfe das, bevor du Modul D planst.

## Erfolgsmessung

Am Ende von Modul A, C und E eine kurze Umfrage (3 Fragen):
1. "Ich habe diese Woche KI für eine echte Aufgabe genutzt." (Ja/Nein)
2. "Ich weiß, welches Werkzeug ich für welche Aufgabe nehme." (1–5)
3. "Was hat dir am meisten gebracht?" (Freitext)

Wenn Frage 1 nach Modul B unter 50 % liegt, ist der Inhalt zu weit vom Alltag der Gruppe weg. Dann Modul B wiederholen, nicht Modul C starten.
