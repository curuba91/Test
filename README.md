# DeepLearn – Lernplattform für Taucher

Eine moderne, komplett clientseitige Lern-App für Sporttaucher. Kein Backend, kein Login – alle Fortschritte liegen im Browser (localStorage) und lassen sich als Backup exportieren.

## Features

| Bereich | Inhalt |
|---|---|
| **9 Kursmodule, 34 Lektionen** | Tauchphysik, Physiologie, Ausrüstung, Tauchfertigkeiten, Tauchgangsplanung, Navigation, Meeresbiologie & Umwelt, Nitrox, Notfälle & Rettung |
| **Quizze** | 70+ Fragen mit Erklärungen, ein Quiz pro Modul (70 % zum Bestehen) |
| **Abschlussprüfung** | 30 Fragen, ausgewogen über alle Module, 75 % zum Bestehen |
| **Karteikarten** | 40 Flip-Cards mit „Gewusst / Nochmal üben“-Tracking, filterbar nach Modul |
| **Tauchrechner** | Nitrox (MOD, EAD, Best Mix, pO₂), Luftverbrauch (SAC/RMV, Reichweite), Druck & Volumen, Nullzeit-Check, Blei-Schätzung |
| **Logbuch** | Tauchgänge mit Tiefe, Zeit, Luft, Sicht, Buddy, Bewertung, Notizen; SAC-Berechnung; CSV-Export |
| **Handzeichen** | 28 internationale Signale in 5 Kategorien, durchsuchbar |
| **Glossar** | 37 Fachbegriffe |
| **Checklisten** | Packliste, Vor/Nach dem Tauchgang, Sicherheitsausrüstung – Stand wird gespeichert |
| **Gamification** | XP, 7 Level (Schnorchler → Tiefsee-Legende), 16 Achievements, Tages-Streak |
| **Design** | Dark „Tiefsee“ / Light „Lagune“ Theme, Glassmorphism, animierte Bubbles, responsive mit Bottom-Nav auf Mobile |

## Tech-Stack

- React 19 + TypeScript + Vite 8
- Tailwind CSS v4 (Theme-Tokens in `src/index.css`)
- React Router (HashRouter – läuft auf jedem statischen Host)
- Zustand mit `persist` für den Fortschritt
- Lucide Icons

## Entwicklung

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # Produktions-Build nach dist/
npm run preview  # Build lokal ansehen
npm run lint     # oxlint
```

## Deployment

`.github/workflows/deploy.yml` baut bei jedem Push auf `main` und veröffentlicht `dist/` auf GitHub Pages (in den Repo-Settings unter *Pages* die Quelle auf „GitHub Actions“ stellen). Durch `base: './'` und HashRouter funktioniert die App auch in Unterpfaden.

## Inhalte erweitern

- Lektionen: `src/data/modules-*.ts` – Inhalte als typisierte Blöcke (`p`, `h`, `list`, `steps`, `fact`, `warning`, `tip`, `formula`, `table`)
- Quizfragen: `src/data/quizzes.ts`
- Karteikarten: `src/data/flashcards.ts`
- Handzeichen / Glossar / Checklisten / Achievements: jeweils eigene Datei in `src/data/`

## Hinweis

DeepLearn ist eine Lernhilfe und ersetzt keine zertifizierte Tauchausbildung. Nullzeit-Tabelle und Rechner dienen ausschließlich Lernzwecken – für die reale Planung gelten Tauchcomputer und offizielle Tabellen.
