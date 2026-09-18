import type { QuizQuestion } from './types'

const q = (moduleId: string, n: number, question: string, options: string[], answer: number, explanation: string): QuizQuestion => ({
  id: `${moduleId}-q${n}`,
  moduleId,
  question,
  options,
  answer,
  explanation,
})

export const questions: QuizQuestion[] = [
  // Physik
  q('physik', 1, 'Welcher absolute Druck herrscht in 30 m Tiefe im Salzwasser?', ['3 bar', '4 bar', '30 bar', '1,3 bar'], 1, '1 bar Luftdruck + 3 bar Wasserdruck (1 bar pro 10 m) = 4 bar absolut.'),
  q('physik', 2, 'Ein Ballon hat an der Oberfläche 8 Liter Volumen. Wie groß ist er in 10 m Tiefe?', ['8 l', '6 l', '4 l', '2 l'], 2, 'In 10 m verdoppelt sich der Druck (2 bar), das Volumen halbiert sich: 4 Liter (Boyle‑Mariotte).'),
  q('physik', 3, 'In welchem Tiefenbereich ist die relative Druckänderung am größten?', ['30–40 m', '20–30 m', '10–20 m', '0–10 m'], 3, 'Von 0 auf 10 m verdoppelt sich der Druck (100 %). Von 30 auf 40 m steigt er nur um 25 %.'),
  q('physik', 4, 'Wie hoch ist der Sauerstoff‑Partialdruck von Luft in 40 m Tiefe?', ['0,21 bar', '0,84 bar', '1,05 bar', '1,4 bar'], 2, 'pO₂ = 0,21 × 5 bar = 1,05 bar.'),
  q('physik', 5, 'Welches Gasgesetz erklärt, warum sich Stickstoff unter Druck im Gewebe löst?', ['Boyle‑Mariotte', 'Dalton', 'Henry', 'Archimedes'], 2, 'Henry: Die Menge gelösten Gases ist proportional zum Partialdruck über der Flüssigkeit.'),
  q('physik', 6, 'Warum erscheinen Objekte unter Wasser größer?', ['Wasser vergrößert wie eine Lupe', 'Lichtbrechung an der Maske', 'Die Pupille weitet sich', 'Höherer Druck auf das Auge'], 1, 'Die Brechung an der Grenzfläche Wasser–Luft in der Maske lässt Objekte etwa 33 % größer und 25 % näher erscheinen.'),
  q('physik', 7, 'Welche Farbe verschwindet als erste mit zunehmender Tiefe?', ['Blau', 'Gelb', 'Grün', 'Rot'], 3, 'Rot hat die längste Wellenlänge und wird bereits ab ca. 5 m absorbiert.'),
  q('physik', 8, 'Was passiert mit dem Auftrieb eines Neoprenanzugs in der Tiefe?', ['Er steigt', 'Er bleibt gleich', 'Er sinkt', 'Er verdoppelt sich'], 2, 'Die Gasbläschen im Neopren werden komprimiert – der Anzug verliert Auftrieb. Deshalb muss man beim Abstieg Luft ins Jacket geben.'),
  q('physik', 9, 'Wie viel schneller breitet sich Schall unter Wasser aus als in Luft?', ['Gleich schnell', 'Etwa doppelt', 'Etwa viermal', 'Etwa zehnmal'], 2, 'Ca. 1500 m/s statt 340 m/s – deshalb kann man die Richtung nicht orten.'),

  // Physiologie
  q('physiologie', 1, 'Wann solltest du zum ersten Mal Druckausgleich machen?', ['In 3 m Tiefe', 'Wenn es leicht drückt', 'Schon an der Oberfläche', 'Wenn es schmerzt'], 2, 'Früh und oft – der erste Ausgleich noch an der Oberfläche, dann alle 0,5–1 m.'),
  q('physiologie', 2, 'Was tust du, wenn der Druckausgleich in 4 m nicht klappt?', ['Fester drücken', '1–2 m aufsteigen und erneut versuchen', 'Schnell weiter abtauchen', 'Maske abnehmen'], 1, 'Nie mit Gewalt. Etwas aufsteigen, entspannen, erneut versuchen. Klappt es nicht: Tauchgang abbrechen.'),
  q('physiologie', 3, 'Welche Verletzung droht beim Aufstieg mit angehaltenem Atem?', ['Mittelohr‑Barotrauma', 'Lungenüberdehnung', 'Stickstoffnarkose', 'Masken‑Squeeze'], 1, 'Die Luft in der Lunge dehnt sich aus – schon 1–2 m Aufstieg können Lungenbläschen zerreißen.'),
  q('physiologie', 4, 'Welches ist ein typisches Symptom von DCS Typ I?', ['Lähmung', 'Gelenkschmerzen', 'Krampfanfall', 'Bewusstlosigkeit'], 1, 'Typ I („Bends“): Gelenkschmerzen, Hautjucken, Müdigkeit. Typ II betrifft Nervensystem und Lunge.'),
  q('physiologie', 5, 'Was ist die wichtigste Erste‑Hilfe‑Maßnahme bei Verdacht auf DCS?', ['Zurück ins Wasser zum „Rekomprimieren“', 'Heiße Dusche', '100 % Sauerstoff', 'Schmerzmittel'], 2, 'Sauerstoff beschleunigt die Stickstoffabgabe. Nasses Rekomprimieren ist lebensgefährlich.'),
  q('physiologie', 6, 'Wie lange solltest du nach mehreren Tauchgängen mindestens mit dem Fliegen warten?', ['6 h', '12 h', '18 h', '48 h'], 2, '12 h nach einem, 18 h nach mehreren Tauchgängen, 24 h nach Deko‑Tauchgängen.'),
  q('physiologie', 7, 'Wie behebst du eine Stickstoffnarkose?', ['Sauerstoff atmen', 'Aufsteigen', 'Tiefer tauchen, um sich zu gewöhnen', 'Wasser trinken'], 1, 'Der Tiefenrausch verschwindet innerhalb weniger Meter Aufstieg ohne Nachwirkungen.'),
  q('physiologie', 8, 'Ab welchem Sauerstoff‑Partialdruck droht ZNS‑Toxizität?', ['0,21 bar', '0,5 bar', '1,4–1,6 bar', '3 bar'], 2, '1,4 bar ist die Planungsgrenze, 1,6 bar die absolute Obergrenze in Ruhe.'),
  q('physiologie', 9, 'Wofür steht das „T“ in VENTID‑C?', ['Temperatur', 'Twitching (Zucken)', 'Tinnitus', 'Tachykardie'], 1, 'Vision, Ears, Nausea, Twitching, Irritability, Dizziness, Convulsions.'),

  // Ausrüstung
  q('ausruestung', 1, 'Warum muss die Tauchmaske die Nase einschließen?', ['Für besseren Sitz', 'Um Druckausgleich in der Maske zu ermöglichen', 'Damit man riechen kann', 'Wegen des Schnorchels'], 1, 'Beim Abstieg wird die Luft in der Maske komprimiert – durch die Nase ausatmen verhindert den Masken‑Squeeze.'),
  q('ausruestung', 2, 'Auf welchen Druck reduziert die erste Stufe des Atemreglers?', ['Auf Umgebungsdruck', 'Auf ca. 9–10 bar über Umgebungsdruck', 'Auf 50 bar', 'Auf 1 bar'], 1, 'Die erste Stufe liefert Mitteldruck, die zweite Stufe reduziert auf Umgebungsdruck.'),
  q('ausruestung', 3, 'Wie viele Liter Luft enthält eine 12‑l‑Flasche bei 200 bar?', ['200 l', '1200 l', '2400 l', '12 000 l'], 2, '12 l × 200 bar = 2400 Liter.'),
  q('ausruestung', 4, 'Welche Angabe ist auf einem Tauchcomputer die wichtigste während des Tauchgangs?', ['Wassertemperatur', 'Verbleibende Nullzeit', 'Uhrzeit', 'Kompass'], 1, 'Die Nullzeit bestimmt, ob du noch direkt auftauchen darfst.'),
  q('ausruestung', 5, 'Was macht eine Aluflasche gegen Ende des Tauchgangs?', ['Wird schwerer', 'Wird positiv (Auftrieb)', 'Bleibt neutral', 'Wird kälter'], 1, 'Leere Aluflaschen sind ca. 1,5 kg positiv – das muss in der Bleiplanung berücksichtigt werden.'),
  q('ausruestung', 6, 'Wie oft sollte ein Atemregler zur Revision?', ['Nach jedem Tauchgang', 'Alle 1–2 Jahre oder 100 Tauchgänge', 'Nie, wenn er funktioniert', 'Alle 10 Jahre'], 1, 'Regelmäßige Revision hält Dichtungen und Ventile in Schuss.'),
  q('ausruestung', 7, 'Wo trägt man den Schnorchel?', ['Rechts', 'Links', 'Am Jacket', 'Egal'], 1, 'Links – rechts kommt der Atemregler.'),
  q('ausruestung', 8, 'Was ist beim Spülen des Atemreglers wichtig?', ['Luftdusche unter Wasser drücken', 'Staubkappe trocken aufsetzen', 'Mit Salzwasser spülen', 'In der Sonne trocknen'], 1, 'Ohne trockene Kappe dringt Wasser in die erste Stufe – Korrosion.'),

  // Skills
  q('skills', 1, 'Wofür steht das „W“ im BWRAF Buddy‑Check?', ['Water', 'Weights (Blei)', 'Wetsuit', 'Watch'], 1, 'BCD, Weights, Releases, Air, Final Check.'),
  q('skills', 2, 'Wie schnell darfst du maximal aufsteigen?', ['18 m/min', '9–10 m/min', '30 m/min', '3 m/min'], 1, 'Langsamer als die kleinsten Blasen; die meisten Computer warnen ab 10 m/min.'),
  q('skills', 3, 'Wie lange dauert der Sicherheitsstopp und in welcher Tiefe?', ['3 min bei 5 m', '5 min bei 3 m', '1 min bei 10 m', '10 min bei 5 m'], 0, 'Standard: 3 Minuten bei 5 Metern – bei jedem Tauchgang.'),
  q('skills', 4, 'Bei einem CESA (Kontrollierter Schwimmaufstieg) musst du …', ['die Luft anhalten', 'kontinuierlich ausatmen', 'den Regler herausnehmen', 'das Blei abwerfen'], 1, 'Beim Aufstieg dehnt sich die Luft aus – ständiges Ausatmen („Aaaah“) verhindert eine Lungenüberdehnung.'),
  q('skills', 5, 'Welche Methode ist die erste Wahl bei „Luft aus“ mit Buddy in Reichweite?', ['CESA', 'Bleiabwurf', 'Wechselatmung am Oktopus', 'Buddy‑Breathing mit einem Regler'], 2, 'Der Oktopus ist die Standardlösung – gemeinsamer, kontrollierter Aufstieg.'),
  q('skills', 6, 'Wie funktioniert Feintarierung?', ['Über den Inflator', 'Über die Atmung', 'Über die Flossen', 'Über Blei'], 1, 'Einatmen = leicht steigen, ausatmen = leicht sinken. Reaktion mit 2–3 s Verzögerung.'),
  q('skills', 7, 'Wie lange suchst du einen verlorenen Buddy, bevor du auftauchst?', ['5 min', '1 min', '10 min', 'Bis zur Reserve'], 1, 'Eine Minute suchen, dann langsam aufsteigen und an der Oberfläche treffen.'),
  q('skills', 8, 'Bei der Sweep‑Methode zum Wiederfinden des Reglers …', ['schwingt der rechte Arm von hinten nach vorne', 'greift man zur ersten Stufe', 'nimmt man den Oktopus', 'dreht man sich um'], 0, 'Rechte Schulter senken, Arm nach hinten unten, in einem Bogen nach vorne schwingen.'),

  // Planung
  q('planung', 1, 'Was ist die Nullzeit?', ['Zeit bis zum Luft‑Ende', 'Max. Zeit ohne Pflicht‑Dekostopp', 'Dauer des Sicherheitsstopps', 'Oberflächenpause'], 1, 'Nullzeit = No‑Decompression Limit.'),
  q('planung', 2, 'Welches Profil ist am sichersten?', ['Sägezahn', 'Tiefster Punkt zuerst, dann stufenweise flacher', 'Tiefster Punkt am Ende', 'Konstant auf max. Tiefe'], 1, 'Tiefster Punkt zuerst – dann kontinuierliche Stickstoffabgabe.'),
  q('planung', 3, 'Dein SAC: 200 → 120 bar in 40 min bei Ø 10 m. Wie viel bar/min an der Oberfläche?', ['2 bar/min', '1 bar/min', '0,5 bar/min', '4 bar/min'], 1, '80 bar ÷ 40 min = 2 bar/min in 2 bar Umgebungsdruck → 1 bar/min an der Oberfläche.'),
  q('planung', 4, 'Was besagt die Drittel‑Regel?', ['1/3 Tiefe, 1/3 Zeit, 1/3 Reserve', '1/3 Hin, 1/3 Zurück, 1/3 Reserve', 'Alle 1/3 des Tauchgangs Luft prüfen', 'Nur 1/3 der Flasche nutzen'], 1, 'Standard bei Tauchgängen ohne direkten Aufstiegsweg (Höhle, Wrack, Strömung).'),
  q('planung', 5, 'Mit wie viel bar sollst du mindestens an der Oberfläche ankommen?', ['0 bar', '20 bar', '50 bar', '100 bar'], 2, '50 bar sind die Standardreserve für Sporttaucher.'),
  q('planung', 6, 'Wie sollte der zweite Tauchgang des Tages sein?', ['Tiefer als der erste', 'Gleich tief', 'Flacher als der erste', 'Egal'], 2, 'Wiederholungstauchgänge immer flacher – der Reststickstoff zählt weiter.'),
  q('planung', 7, 'Wie viel Luft steckt in 150 bar einer 12‑l‑Flasche?', ['150 l', '1200 l', '1800 l', '3000 l'], 2, '150 × 12 = 1800 Liter.'),
  q('planung', 8, 'Wie lange reichen 1800 l bei 20 l/min RMV in 30 m?', ['90 min', '45 min', '22,5 min', '11 min'], 2, '20 l/min × 4 bar = 80 l/min → 1800 ÷ 80 = 22,5 min.'),

  // Navigation
  q('navigation', 1, 'Wie verlaufen Sandrippel im Verhältnis zum Ufer?', ['Senkrecht', 'Parallel', 'Diagonal', 'Kreisförmig'], 1, 'Parallel zum Ufer – senkrecht dazu geht es zum Strand.'),
  q('navigation', 2, 'Du startest mit dem Riff auf der linken Seite. Beim Rückweg ist es …', ['Links', 'Rechts', 'Vor dir', 'Hinter dir'], 1, 'Rückweg = Riff auf der anderen Seite.'),
  q('navigation', 3, 'In welche Richtung startest du bei Strömung?', ['Mit der Strömung', 'Gegen die Strömung', 'Quer', 'Egal'], 1, 'Gegen die Strömung hin, mit der Strömung entspannt zurück.'),
  q('navigation', 4, 'Dein Kurs beträgt 60°. Was ist der Umkehrkurs?', ['120°', '180°', '240°', '300°'], 2, '60° + 180° = 240°.'),
  q('navigation', 5, 'Um wie viel Grad drehst du bei jedem Eckpunkt eines Quadrats?', ['45°', '60°', '90°', '120°'], 2, 'Vier Ecken à 90° ergeben 360°.'),
  q('navigation', 6, 'Was lenkt die Kompassnadel ab?', ['Strömung', 'Metall in der Nähe', 'Tiefe', 'Kaltes Wasser'], 1, 'Flasche, Bleigurt, Lampe, Wrack – mind. 30 cm Abstand.'),
  q('navigation', 7, 'Wofür eignet sich das erweiterte Quadrat?', ['Riffwand entlang', 'Suchmuster vom Startpunkt', 'Strömungstauchgang', 'Nachttauchgang'], 1, '1‑1‑2‑2‑3‑3 Einheiten mit 90°‑Wendungen decken systematisch eine Fläche ab.'),

  // Meer
  q('meer', 1, 'Korallen sind …', ['Pflanzen', 'Steine', 'Tiere', 'Algen'], 2, 'Korallen sind Nesseltiere – Kolonien winziger Polypen.'),
  q('meer', 2, 'Was verursacht Korallenbleiche?', ['Zu viel Salz', 'Zu warmes Wasser', 'Taucherlampen', 'Zu viele Fische'], 1, 'Bei 1–2 °C über dem Sommermaximum stoßen Korallen ihre Symbiose‑Algen ab.'),
  q('meer', 3, 'Erste Hilfe bei einem Feuerfisch‑Stich?', ['Eis', 'Heißes Wasser (ca. 45 °C)', 'Essig', 'Süßwasser'], 1, 'Das Gift ist hitzelabil – 30–90 min in möglichst heißes Wasser.'),
  q('meer', 4, 'Wie entkommst du einem angreifenden Titan‑Drückerfisch?', ['Nach oben', 'Horizontal seitlich weg', 'Zum Boden', 'Stillhalten'], 1, 'Sein Revier ist ein Kegel nach oben – nach oben flüchten bringt dich tiefer hinein.'),
  q('meer', 5, 'Welchen Anteil aller Meeresarten beherbergen Korallenriffe?', ['1 %', '5 %', '25 %', '75 %'], 2, 'Rund ein Viertel – auf weniger als 1 % der Meeresbodenfläche.'),
  q('meer', 6, 'Welcher Inhaltsstoff in Sonnencreme schädigt Korallen?', ['Zinkoxid', 'Oxybenzon', 'Wasser', 'Aloe Vera'], 1, 'Oxybenzon und Octinoxat – „reef safe“ Cremes verzichten darauf.'),
  q('meer', 7, 'Welcher Rifftyp ist ein Ringriff um eine versunkene Vulkaninsel?', ['Saumriff', 'Barriereriff', 'Atoll', 'Fleckenriff'], 2, 'Atolle wie die Malediven entstehen, wenn die Insel absinkt und das Riff weiterwächst.'),

  // Nitrox
  q('nitrox', 1, 'Was ist der Hauptvorteil von Nitrox?', ['Weniger Luftverbrauch', 'Längere Nullzeit', 'Tiefer tauchen', 'Kein Tiefenrausch'], 1, 'Weniger Stickstoff → längere Nullzeit und kürzere Oberflächenpausen. Der Luftverbrauch bleibt gleich.'),
  q('nitrox', 2, 'MOD für EAN32 bei pO₂ 1,4 bar?', ['28 m', '33 m', '40 m', '45 m'], 1, '(1,4 ÷ 0,32 − 1) × 10 = 33,75 m.'),
  q('nitrox', 3, 'MOD für EAN36 bei pO₂ 1,4 bar?', ['22 m', '28 m', '33 m', '40 m'], 1, '(1,4 ÷ 0,36 − 1) × 10 = 28,9 m → 28 m.'),
  q('nitrox', 4, 'Was ist die EAD von EAN32 in 30 m (gerundet)?', ['18 m', '24 m', '30 m', '36 m'], 1, '(0,68 × 40) ÷ 0,79 − 10 ≈ 24,4 m.'),
  q('nitrox', 5, 'Wer muss das Nitrox‑Gemisch analysieren?', ['Nur die Basis', 'Der Taucher selbst', 'Der Buddy', 'Niemand, steht auf der Flasche'], 1, 'Immer selbst analysieren, eintragen und den Computer einstellen.'),
  q('nitrox', 6, 'Wie lange darfst du maximal bei pO₂ 1,6 bar bleiben (pro Tauchgang)?', ['45 min', '120 min', '150 min', '210 min'], 0, 'Bei 1,6 bar nur 45 min – deshalb nur als Notgrenze.'),
  q('nitrox', 7, 'Welches Gemisch ist für 25 m ideal (Best Mix bei 1,4 bar)?', ['EAN21', 'EAN32', 'EAN40', 'EAN50'], 2, '1,4 ÷ 3,5 bar = 0,40 → EAN40.'),
  q('nitrox', 8, 'Hilft Nitrox gegen den Tiefenrausch?', ['Ja, deutlich', 'Nein', 'Nur ab EAN36', 'Nur mit Helium'], 1, 'Nein – Sauerstoff gilt als etwa gleich narkotisch wie Stickstoff.'),

  // Notfall
  q('notfall', 1, 'Was ist der erste Schritt bei jedem Problem unter Wasser?', ['Sofort auftauchen', 'Stopp – Atmen – Denken – Handeln', 'Buddy anschreien', 'Blei abwerfen'], 1, 'Panik ist Handeln ohne Denken. Erst anhalten und atmen.'),
  q('notfall', 2, 'Wie näherst du dich einem panischen Taucher an der Oberfläche?', ['Frontal', 'Von hinten oder unten', 'Gar nicht', 'Mit dem Boot'], 1, 'Frontal würde er sich an dir festklammern und dich unter Wasser drücken.'),
  q('notfall', 3, 'Was ist bei der Rettung eines Bewusstlosen die erste Priorität?', ['Ausrüstung abnehmen', 'Eigensicherung', 'Beatmung', 'Notruf'], 1, 'Erst dein eigener Auftrieb – ein zweiter Verunglückter hilft niemandem.'),
  q('notfall', 4, 'Welche Sauerstoffkonzentration liefert ein Demand‑Ventil?', ['21 %', '50 %', 'Nahezu 100 %', '80 %'], 2, 'Demand‑Ventile liefern beim atmenden Patienten fast reinen Sauerstoff.'),
  q('notfall', 5, 'Wie lange gibst du Sauerstoff bei DCS‑Verdacht?', ['5 Minuten', 'Bis die Symptome verschwinden', 'Bis der Notarzt übernimmt', '1 Stunde'], 2, 'Auch wenn Symptome verschwinden – weiter geben bis zur Übergabe.'),
  q('notfall', 6, 'Welches Warnzeichen deutet auf Stress beim Buddy hin?', ['Ruhige, tiefe Atmung', 'Weit aufgerissene Augen, hektische Bewegungen', 'Regelmäßige OK‑Zeichen', 'Fotografieren'], 1, '„Big Eyes“, Paddeln, Fixierung – typische Stresszeichen.'),
  q('notfall', 7, 'Wie viele Beatmungen zu Herzdruckmassagen bei der HLW?', ['1:5', '2:15', '2:30', '5:30'], 2, '30 Kompressionen, 2 Beatmungen.'),
]

export function questionsForModule(moduleId: string) {
  return questions.filter((x) => x.moduleId === moduleId)
}

export function shuffle<T>(arr: T[]): T[] {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}
