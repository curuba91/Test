import type { CourseModule } from './types'

export const planung: CourseModule = {
  id: 'planung',
  title: 'Tauchgangsplanung',
  subtitle: 'Nullzeit, Tabellen & Gasmanagement',
  level: 'Advanced',
  icon: 'Calculator',
  accent: 'from-indigo-400 to-violet-500',
  description:
    'Plane Tauchgänge wie ein Profi: Nullzeitgrenzen, Wiederholungstauchgänge, Luftverbrauch und die Drittel‑Regel.',
  lessons: [
    {
      id: 'plan-nullzeit',
      title: 'Nullzeit verstehen',
      summary: 'Wie lange du in welcher Tiefe bleiben darfst.',
      minutes: 9,
      blocks: [
        { type: 'p', text: 'Die **Nullzeit** (No‑Decompression Limit, NDL) ist die maximale Zeit in einer Tiefe, nach der du ohne Pflicht‑Dekostopps direkt aufsteigen darfst. Je tiefer, desto kürzer.' },
        { type: 'table', headers: ['Tiefe', 'Nullzeit (ca.)'], rows: [['12 m', '147 min'], ['18 m', '56 min'], ['20 m', '45 min'], ['25 m', '29 min'], ['30 m', '20 min'], ['35 m', '14 min'], ['40 m', '9 min']] },
        { type: 'fact', text: 'Werte sind vereinfacht und orientieren sich an gängigen Sporttauchtabellen. Dein Tauchcomputer kann abweichen – er gilt.' },
        { type: 'h', text: 'Planung nach der Regel: Tiefster Punkt zuerst' },
        { type: 'p', text: 'Tauche das **tiefste Profil am Anfang** und steige dann stufenweise auf („Multilevel“). So gibst du Stickstoff kontinuierlich ab. Ein „Sägezahn‑Profil“ (mehrfach rauf und runter) erhöht das DCS‑Risiko deutlich.' },
        { type: 'tip', text: 'Plane immer mit einer **Reserve** zur Nullzeit (z. B. Nullzeit −5 min) und maximal geplanter Tiefe +2 m Puffer. „Plane deinen Tauchgang – tauche deinen Plan.“' },
      ],
    },
    {
      id: 'plan-wiederholung',
      title: 'Wiederholungstauchgänge & Oberflächenpause',
      summary: 'Der Reststickstoff aus dem ersten Tauchgang zählt weiter.',
      minutes: 8,
      blocks: [
        { type: 'p', text: 'Nach dem Auftauchen ist noch **Reststickstoff** in deinem Gewebe. Bei einem zweiten Tauchgang addiert sich dieser – deine Nullzeit ist kürzer. Tauchtabellen drücken das über **Wiederholungsgruppen** (Buchstaben A–Z) aus, Computer rechnen es live.' },
        { type: 'steps', items: ['Nach dem 1. Tauchgang: Wiederholungsgruppe ablesen (z. B. „J“).', 'Oberflächenpause: Mit jeder Stunde sinkt die Gruppe.', 'Vor dem 2. Tauchgang: Restzeit (Residual Nitrogen Time, RNT) für die geplante Tiefe ablesen.', 'Neue Nullzeit = Tabellen‑Nullzeit − RNT.'] },
        { type: 'fact', title: 'Faustregeln', text: 'Oberflächenpause mindestens **1 h** (besser 1,5–2 h). Zweiter Tauchgang immer **flacher** als der erste. Maximal 3–4 Tauchgänge pro Tag. Ein tauchfreier Tag pro Woche bei mehrtägigen Safaris.' },
        { type: 'warning', title: 'Höhe & Fliegen', text: 'Fahrten über Pässe (> 300 m) und Flüge zählen als Druckabfall. 12–24 h warten. Bergseetauchen braucht eigene Tabellen bzw. Höhenmodus am Computer.' },
      ],
    },
    {
      id: 'plan-gas',
      title: 'Gasmanagement: SAC & Drittel‑Regel',
      summary: 'Wie viel Luft brauchst du – und wann musst du umkehren?',
      minutes: 11,
      blocks: [
        { type: 'p', text: 'Dein **Atemminutenvolumen (AMV / RMV)** gibt an, wie viele Liter Luft du pro Minute an der Oberfläche atmest. Typisch: 15–25 l/min in Ruhe, bis 40+ l/min bei Anstrengung. Der **SAC** (Surface Air Consumption) ist dasselbe in bar/min für deine konkrete Flasche.' },
        { type: 'formula', label: 'SAC berechnen', formula: 'SAC = (Startdruck − Enddruck) ÷ Zeit ÷ P_abs(Ø‑Tiefe)', note: 'Beispiel: 200 → 100 bar in 40 min bei Ø 15 m (2,5 bar): 100 ÷ 40 ÷ 2,5 = 1 bar/min. Mit 12‑l‑Flasche: 12 l/min.' },
        { type: 'formula', label: 'Reichweite in Tiefe', formula: 'Minuten = (verfügbarer Druck × Flaschen‑l) ÷ (RMV × P_abs)', note: '150 bar × 12 l = 1800 l ÷ (20 l/min × 4 bar) = 22,5 min in 30 m.' },
        { type: 'h', text: 'Reserve‑Regeln' },
        { type: 'list', items: [
          '**50‑bar‑Regel:** Mit 50 bar an der Oberfläche ankommen – nie darunter. Bei 100 bar Umkehr signalisieren (bei symmetrischem Profil).',
          '**Drittel‑Regel:** 1/3 Hin, 1/3 Zurück, 1/3 Reserve. Standard bei Höhlen, Wracks, Strömung – überall, wo du nicht direkt auftauchen kannst.',
          '**Rock Bottom / Minimum Gas:** Reserve = Luft, die zwei Taucher brauchen, um von der max. Tiefe gemeinsam mit Stopps aufzutauchen. Bei 30 m für einen Buddy: ca. 60–70 bar in einer 12‑l‑Flasche.',
        ] },
        { type: 'tip', text: 'Tipp zum Luftsparen: Langsam, tief atmen. Ruhig bleiben. Perfekt tarieren. Hände stillhalten. Stromlinienförmig. Warm bleiben. – Nicht: Luft anhalten oder „Skip Breathing“ (CO₂‑Kopfschmerz!).' },
      ],
    },
    {
      id: 'plan-briefing',
      title: 'Tauchgangs‑Briefing & Verlorener Buddy',
      summary: 'Was vor dem Sprung ins Wasser geklärt sein muss.',
      minutes: 6,
      blocks: [
        { type: 'p', text: 'Ein gutes **Briefing** dauert 3 Minuten und verhindert 90 % aller Probleme. Es ist keine Formalität für Anfänger – Profis machen es *immer*.' },
        { type: 'list', items: [
          '**Ziel & Route:** Wohin, wie tief, wie lange, welche Richtung, Umkehrpunkt.',
          '**Max. Tiefe & Zeit:** Beides festlegen, am Computer prüfen.',
          '**Luft:** Umkehrdruck, Reserve, Zeichen für „halb“ und „Reserve“.',
          '**Signale:** Handzeichen gemeinsam durchgehen, Lampen‑Zeichen bei Nacht.',
          '**Verlorener Buddy:** 1 Minute suchen (drehen, nach Blasen schauen), dann langsam aufsteigen und an der Oberfläche treffen.',
          '**Notfall:** Wer hat Sauerstoff? Wo ist das nächste Telefon / die Druckkammer?',
          '**Umwelt:** Nichts anfassen, Strömungsrichtung, Bootsverkehr, Ein‑ und Ausstieg.',
        ] },
        { type: 'fact', title: 'Nach dem Tauchgang', text: 'Debriefing: Was war gut, was nicht? Logbuch ausfüllen (Tiefe, Zeit, Luft, Blei, Bedingungen). Das ist die beste Lernquelle, die du hast.' },
      ],
    },
  ],
}

export const nitrox: CourseModule = {
  id: 'nitrox',
  title: 'Nitrox (EANx)',
  subtitle: 'Mehr Sauerstoff, längere Nullzeit',
  level: 'Specialty',
  icon: 'FlaskConical',
  accent: 'from-lime-400 to-green-500',
  description:
    'Alles über angereicherte Luft: Vorteile, Grenzen, MOD, EAD, CNS‑Uhr und der richtige Umgang mit dem Analyser.',
  lessons: [
    {
      id: 'nitrox-basics',
      title: 'Was ist Nitrox?',
      summary: 'Warum weniger Stickstoff mehr Grundzeit bedeutet.',
      minutes: 7,
      blocks: [
        { type: 'p', text: '**Nitrox** (Enriched Air Nitrox, EANx) ist Luft mit erhöhtem Sauerstoffanteil – meist **32 %** (EAN32) oder **36 %** (EAN36). Weniger Stickstoff im Gemisch heißt: weniger Stickstoffaufnahme → **längere Nullzeiten** und **kürzere Oberflächenpausen**.' },
        { type: 'table', headers: ['Tiefe', 'Nullzeit Luft', 'Nullzeit EAN32', 'Nullzeit EAN36'], rows: [['18 m', '56 min', '95 min', '125 min'], ['24 m', '31 min', '50 min', '65 min'], ['30 m', '20 min', '30 min', '— (zu tief)']] },
        { type: 'h', text: 'Vorteile' },
        { type: 'list', items: ['Längere Grundzeit im Bereich 15–30 m', 'Weniger Stickstoff → geringeres DCS‑Risiko bei gleicher Tauchzeit (wenn mit Luft‑Tabellen getaucht)', 'Weniger Müdigkeit nach dem Tauchen (subjektiv berichtet)', 'Ideal für Wiederholungstauchgänge und Safaris'] },
        { type: 'h', text: 'Nachteile & Grenzen' },
        { type: 'list', items: ['**Maximale Einsatztiefe (MOD)** – Sauerstofftoxizität!', 'Spezielle Ausrüstung ab 40 % O₂ (Sauerstoffreinheit)', 'Analyse vor jedem Tauchgang zwingend', 'Kein Vorteil beim Luftverbrauch – die Flasche hält gleich lang', 'Kein Schutz vor Tiefenrausch (wird sogar diskutiert, dass O₂ ebenfalls narkotisch wirkt)'] },
      ],
    },
    {
      id: 'nitrox-mod',
      title: 'MOD & Best Mix berechnen',
      summary: 'Die eine Formel, die jeder Nitrox‑Taucher im Kopf haben muss.',
      minutes: 10,
      blocks: [
        { type: 'p', text: 'Die **MOD** (Maximum Operating Depth) ist die Tiefe, in der der Sauerstoff‑Partialdruck den Grenzwert erreicht. Standard‑Grenzwert: **1,4 bar** (Planung), **1,6 bar** nur als Notfall‑Obergrenze/Deko in Ruhe.' },
        { type: 'formula', label: 'MOD', formula: 'MOD = (pO₂max ÷ FO₂ − 1) × 10', note: 'EAN32 bei 1,4 bar: (1,4 ÷ 0,32 − 1) × 10 = 33,75 m → gerundet 33 m. EAN36: 28,9 m → 28 m.' },
        { type: 'formula', label: 'Best Mix', formula: 'FO₂ = pO₂max ÷ P_abs(Tiefe)', note: 'Geplante Tiefe 25 m (3,5 bar): 1,4 ÷ 3,5 = 0,40 → EAN40. Praktisch würde man EAN36 oder 32 nehmen.' },
        { type: 'table', headers: ['Gemisch', 'MOD @ 1,4 bar', 'MOD @ 1,6 bar'], rows: [['EAN28', '40 m', '47 m'], ['EAN32', '33 m', '40 m'], ['EAN36', '28 m', '34 m'], ['EAN40', '25 m', '30 m'], ['EAN50', '18 m', '22 m'], ['O₂ 100 %', '4 m', '6 m']] },
        { type: 'warning', text: 'Die MOD muss auf der Flasche stehen (Tape mit O₂‑%, MOD, Datum, Name). Vor jedem Tauchgang: selbst analysieren, selbst eintragen, Computer einstellen.' },
      ],
    },
    {
      id: 'nitrox-ead-cns',
      title: 'EAD, CNS‑Uhr & OTU',
      summary: 'So rechnest du Nitrox in Luft um und behältst die Sauerstoffbelastung im Blick.',
      minutes: 9,
      blocks: [
        { type: 'p', text: 'Die **Äquivalente Lufttiefe (EAD)** ist die Tiefe, in der Luft denselben Stickstoff‑Partialdruck hätte wie dein Nitrox in der echten Tiefe. Mit der EAD kannst du normale Lufttabellen nutzen.' },
        { type: 'formula', label: 'EAD', formula: 'EAD = ((1 − FO₂) × (Tiefe + 10)) ÷ 0,79 − 10', note: 'EAN32 in 30 m: (0,68 × 40) ÷ 0,79 − 10 = 24,4 m. Du tauchst physiologisch wie in 24 m mit Luft.' },
        { type: 'h', text: 'CNS‑Uhr (Sauerstoff‑Toxizitätsuhr)' },
        { type: 'p', text: 'Die Belastung des zentralen Nervensystems durch Sauerstoff wird in **Prozent pro Tauchgang und pro 24 h** getrackt. Bei 1,4 bar pO₂ sind 150 min erlaubt (= 100 %), bei 1,6 bar nur 45 min. Der Computer rechnet das mit. Ziel: unter 80 % bleiben.' },
        { type: 'table', headers: ['pO₂', 'Max. Zeit / Tauchgang', 'Max. Zeit / 24 h'], rows: [['1,2 bar', '210 min', '420 min'], ['1,3 bar', '180 min', '360 min'], ['1,4 bar', '150 min', '180 min'], ['1,5 bar', '120 min', '180 min'], ['1,6 bar', '45 min', '150 min']] },
        { type: 'fact', title: 'OTU', text: 'Oxygen Toxicity Units messen die Belastung der Lunge (pulmonale Toxizität) bei langen Expositionen – relevant für mehrtägige Tec‑Tauchgänge, nicht für Sporttaucher.' },
      ],
    },
  ],
}
