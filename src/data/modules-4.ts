import type { CourseModule } from './types'

export const navigation: CourseModule = {
  id: 'navigation',
  title: 'Navigation',
  subtitle: 'Kompass & natürliche Orientierung',
  level: 'Advanced',
  icon: 'Compass',
  accent: 'from-sky-400 to-cyan-500',
  description:
    'Finde unter Wasser immer zurück: Kompassnavigation, natürliche Orientierung, Distanzmessung und Suchmuster.',
  lessons: [
    {
      id: 'nav-natuerlich',
      title: 'Natürliche Navigation',
      summary: 'Sonne, Sand, Strömung und Riff als Wegweiser.',
      minutes: 7,
      blocks: [
        { type: 'p', text: 'Bevor du den Kompass nutzt: Beobachte deine Umgebung. Die meisten Riffe lassen sich mit wenigen Merkmalen sicher navigieren.' },
        { type: 'list', items: [
          '**Riffwand:** Hinweg mit dem Riff links → Rückweg mit dem Riff rechts. Der Klassiker.',
          '**Sandrippel:** Verlaufen parallel zum Ufer – senkrecht dazu geht es zum Strand.',
          '**Lichteinfall & Sonnenstand:** Sonne im Rücken beim Hinweg = Sonne im Gesicht beim Rückweg.',
          '**Tiefe:** Bergauf = zum Ufer, bergab = ins offene Wasser. Gleiche Tiefe halten = am Hang entlang.',
          '**Strömung:** Immer **gegen** die Strömung starten, mit der Strömung zurück.',
          '**Markante Punkte:** Große Korallenblöcke, Ankerketten, Wracks, Bojen – beim Hinweg bewusst umdrehen und die Rückansicht einprägen.',
          '**Geräusche:** Bootsmotoren, Wellenschlag an Felsen.',
        ] },
        { type: 'tip', text: 'Alle 2–3 Minuten kurz „Wo bin ich, wo ist der Ausstieg?“ fragen. Wer erst am Ende darüber nachdenkt, hat schon verloren.' },
      ],
    },
    {
      id: 'nav-kompass',
      title: 'Kompassnavigation',
      summary: 'Kurs setzen, halten, umkehren – und Quadrate schwimmen.',
      minutes: 10,
      blocks: [
        { type: 'p', text: 'Ein Tauchkompass zeigt mit der **Nordnadel** nach magnetisch Nord. Über die drehbare **Lünette** (Bezel) markierst du deinen Kurs. Die **Peillinie** (Lubber Line) muss immer in deine Schwimmrichtung zeigen.' },
        { type: 'steps', items: [
          'Kompass waagerecht halten, Arme verschränkt oder beide Hände vor dem Körper – Peillinie in Körperachse.',
          'Zum Ziel drehen, Lünette so drehen, dass die Markierung über der Nordnadel liegt.',
          'Losschwimmen und die Nadel **zwischen den Markierungen** halten.',
          '**Umkehrkurs:** Die gegenüberliegende Markierung der Lünette (180°) über die Nadel bringen – oder 180° addieren/subtrahieren.',
        ] },
        { type: 'h', text: 'Muster' },
        { type: 'table', headers: ['Muster', 'Kurse', 'Nutzen'], rows: [['Hin und zurück', 'Kurs, +180°', 'Einfachster Fall'], ['Quadrat', '+90° pro Ecke, gleiche Distanz', 'Umrunden eines Gebiets'], ['Dreieck', '+120° pro Ecke', 'Mehr Fläche bei gleicher Zeit'], ['Erweitertes Quadrat', 'Jede zweite Seite länger', 'Suchmuster']] },
        { type: 'warning', text: 'Metall (Flasche, Bleigurt, Wrack, Lampe) lenkt die Nadel ab. Kompass mind. 30 cm von Metall entfernt halten.' },
      ],
    },
    {
      id: 'nav-distanz',
      title: 'Distanz messen & Suchmuster',
      summary: 'Flossenschläge, Zeit, Luftverbrauch – und wie man einen Anker wiederfindet.',
      minutes: 6,
      blocks: [
        { type: 'p', text: 'Um einen Kurs zu vervollständigen, brauchst du nicht nur die Richtung, sondern auch die **Distanz**. Drei Methoden:' },
        { type: 'list', items: ['**Flossenzyklen:** Ein Zyklus = beide Beine einmal. Kalibrieren: 30 m Leine im Pool abschwimmen und zählen (typisch 15–20 Zyklen).', '**Zeit:** Bei gleichmäßigem Tempo ca. 15–20 m/min. Ungenau bei Strömung.', '**Luftverbrauch:** Grob, aber praktisch bei langen Strecken.'] },
        { type: 'h', text: 'Suchmuster (z. B. verlorener Gegenstand)' },
        { type: 'list', items: ['**Kreissuche:** Buddy hält Leine am Fixpunkt, Sucher schwimmt Kreise mit wachsendem Radius.', '**U‑Muster:** Bahnen parallel abschwimmen, am Ende eine Bahnbreite versetzen. Gut bei guter Sicht.', '**Erweitertes Quadrat:** Vom Startpunkt 1‑1‑2‑2‑3‑3‑… Einheiten mit 90°‑Wendungen.'] },
      ],
    },
  ],
}

export const meer: CourseModule = {
  id: 'meer',
  title: 'Meeresbiologie & Umwelt',
  subtitle: 'Riffe, Tiere, Verantwortung',
  level: 'Beginner',
  icon: 'Fish',
  accent: 'from-fuchsia-400 to-purple-500',
  description:
    'Wie Riffe funktionieren, welche Tiere du respektieren musst und wie du als Taucher zum Meeresschutz beiträgst.',
  lessons: [
    {
      id: 'meer-riff',
      title: 'Das Korallenriff',
      summary: 'Ein Ökosystem, das von winzigen Tieren gebaut wird.',
      minutes: 8,
      blocks: [
        { type: 'p', text: '**Korallen sind Tiere** – Kolonien winziger Polypen, die ein Kalkskelett bauen. In ihrem Gewebe leben symbiotische Algen (**Zooxanthellen**), die durch Photosynthese bis zu 90 % der Energie liefern und den Korallen ihre Farbe geben.' },
        { type: 'p', text: 'Riffe bedecken weniger als **1 %** des Meeresbodens, beherbergen aber rund **25 % aller Meeresarten**. Sie schützen Küsten, ernähren Millionen Menschen und sind die Grundlage des Tauchtourismus.' },
        { type: 'h', text: 'Korallenbleiche' },
        { type: 'p', text: 'Bei Wassertemperaturen von nur 1–2 °C über dem Sommer‑Maximum stoßen die Korallen ihre Algen ab – sie werden weiß („bleichen“) und verhungern innerhalb von Wochen, wenn sich das Wasser nicht abkühlt. Seit 1998 gab es mehrere globale Bleichen; 2023/24 war die bisher stärkste.' },
        { type: 'table', headers: ['Rifftyp', 'Beschreibung'], rows: [['Saumriff', 'Direkt an der Küste (Rotes Meer)'], ['Barriereriff', 'Durch Lagune vom Land getrennt (Great Barrier Reef)'], ['Atoll', 'Ringriff um eine versunkene Vulkaninsel (Malediven)'], ['Fleckenriff', 'Isolierte Blöcke in Lagunen']] },
      ],
    },
    {
      id: 'meer-tiere',
      title: 'Gefährliche Meerestiere',
      summary: 'Respekt statt Angst: Was wirklich gefährlich ist und was du tust.',
      minutes: 9,
      blocks: [
        { type: 'p', text: 'Die meisten Verletzungen entstehen, weil Taucher Tiere **berühren, bedrängen oder auf sie treten** – nicht durch Angriffe. Regel Nr. 1: Nichts anfassen, gute Tarierung, Hände am Körper.' },
        { type: 'table', headers: ['Tier', 'Gefahr', 'Erste Hilfe'], rows: [
          ['Feuerfisch / Rotfeuerfisch', 'Giftstacheln, starker Schmerz', 'Heißes Wasser (45 °C) 30–90 min, Arzt'],
          ['Steinfisch', 'Extrem giftig, lebensbedrohlich', 'Heißes Wasser, sofort Notruf, Antiserum'],
          ['Feuerkoralle', 'Nesselgift, brennende Haut', 'Essig, nicht reiben, Kortisonsalbe'],
          ['Quallen', 'Nesseln, teils gefährlich (Würfelqualle)', 'Essig (bei Würfelquallen), Tentakel entfernen, kein Süßwasser'],
          ['Seeigel', 'Stacheln brechen ab', 'Heißes Wasser, Stacheln entfernen, Desinfektion'],
          ['Muräne', 'Beißt nur bei Bedrängung / Füttern', 'Wunde ausspülen, Arzt (Infektionsgefahr)'],
          ['Triggerfisch (Titan)', 'Verteidigt Nest im Kegel nach oben', 'Horizontal wegschwimmen, Flossen zum Fisch'],
          ['Haie', 'Extrem selten gefährlich', 'Ruhig bleiben, Blickkontakt, senkrecht bleiben'],
        ] },
        { type: 'warning', title: 'Kegel‑Regel beim Titan‑Drückerfisch', text: 'Sein Revier reicht als Kegel vom Nest nach oben – nicht nach oben flüchten! Seitlich horizontal wegtauchen.' },
      ],
    },
    {
      id: 'meer-verhalten',
      title: 'Verantwortungsvolles Tauchen',
      summary: 'Wie du das Riff schützt, das du liebst.',
      minutes: 6,
      blocks: [
        { type: 'list', items: [
          '**Nicht berühren, nicht sammeln.** Auch keine „leeren“ Muscheln – Einsiedlerkrebse brauchen sie.',
          '**Tarierung perfektionieren.** Ein Flossenschlag kann 100 Jahre Korallenwachstum zerstören.',
          '**Nicht füttern.** Verändert Verhalten und Gesundheit der Tiere.',
          '**Kein Riff‑Kontakt beim Fotografieren.** Kein Bild ist eine Koralle wert.',
          '**Riffsichere Sonnencreme** (ohne Oxybenzon, Octinoxat) oder UV‑Shirt.',
          '**Müll aufheben**, aber nur, wenn er nicht schon Lebensraum geworden ist (bewachsene Flaschen bleiben).',
          '**Basen wählen**, die Bojen statt Anker nutzen und Umweltstandards einhalten.',
          '**Citizen Science:** Sichtungen melden (z. B. Manta, Walhai), Riffchecks mitmachen.',
        ] },
        { type: 'fact', title: 'Take only pictures, leave only bubbles', text: 'Der einfachste Leitsatz – und immer noch der beste.' },
      ],
    },
  ],
}

export const notfall: CourseModule = {
  id: 'notfall',
  title: 'Notfälle & Rettung',
  subtitle: 'Wenn es ernst wird',
  level: 'Advanced',
  icon: 'Siren',
  accent: 'from-red-400 to-rose-600',
  description:
    'Stress erkennen, Panik verhindern, Taucher retten, Sauerstoff geben und den Notruf richtig absetzen.',
  lessons: [
    {
      id: 'not-stress',
      title: 'Stress & Panik erkennen',
      summary: 'Probleme beginnen im Kopf – lange bevor etwas passiert.',
      minutes: 7,
      blocks: [
        { type: 'p', text: 'Fast alle Tauchunfälle folgen einer **Kette kleiner Probleme**: Kälte + Strömung + schlechte Sicht + hoher Luftverbrauch + Buddy verloren → Panik. Unterbrichst du die Kette früh, passiert nichts.' },
        { type: 'h', text: 'Warnzeichen beim Buddy' },
        { type: 'list', items: ['Weit aufgerissene Augen, starrer Blick („Big Eyes“)', 'Schnelle, flache Atmung – viele kleine Blasen', 'Hektische Bewegungen, Paddeln mit den Händen', 'Kein Reagieren auf Zeichen', 'Fixierung auf ein Instrument', 'Plötzlicher Aufstieg, Regler herausnehmen, Maske abreißen'] },
        { type: 'h', text: 'Was du tust' },
        { type: 'steps', items: ['Blickkontakt herstellen, ruhig annähern.', 'Festhalten (Jacket/Arm), „OK?“‑Zeichen, „Langsam atmen“ zeigen (Hand flach heben/senken).', 'Problem lösen (Luft geben, Maske, Auftrieb).', 'Wenn nötig: kontrollierter gemeinsamer Aufstieg.'] },
        { type: 'tip', title: 'Stopp – Atmen – Denken – Handeln', text: 'Bei jedem Problem unter Wasser: Anhalten, drei tiefe Atemzüge, Situation bewerten, dann erst handeln. Panik ist immer ein Handeln ohne Denken.' },
      ],
    },
    {
      id: 'not-rettung',
      title: 'Rettung an der Oberfläche',
      summary: 'Bewusstlosen Taucher sichern, abschleppen, beatmen.',
      minutes: 10,
      blocks: [
        { type: 'steps', items: [
          '**Eigensicherung:** Jacket voll, Blei ggf. abwerfen. Ein zweiter Verunglückter hilft niemandem.',
          '**Ansprechen:** Panische Taucher an der Oberfläche von hinten oder unten anschwimmen, nie frontal.',
          '**Auftrieb herstellen:** Jacket des Betroffenen aufblasen, Blei abwerfen.',
          '**Atmung prüfen:** Kopf überstrecken, Maske und Regler entfernen, 10 s prüfen.',
          '**Beatmung im Wasser:** 2 Beatmungen, dann alle 5 s eine, während des Abschleppens – nur wenn der Weg kurz ist.',
          '**Abschleppen:** Zug am Flaschenventil, Griff unter der Achsel, Kopf über Wasser halten.',
          '**Aus dem Wasser:** Ausrüstung abnehmen, ab dann normale HLW (30:2), AED, Sauerstoff.',
        ] },
        { type: 'h', text: 'Bewusstloser Taucher unter Wasser' },
        { type: 'p', text: 'Regler im Mund halten (wenn drin), Kopf neutral, kontrollierter Aufstieg mit dessen Jacket steuern. Nicht nach dem Regler suchen, wenn er draußen ist – Zeit ist wichtiger. Unter Wasser ist keine Beatmung möglich.' },
        { type: 'warning', text: 'Ein Rescue‑Diver‑Kurs ist die beste Investition nach dem Advanced. Diese Lektion ersetzt keine praktische Ausbildung.' },
      ],
    },
    {
      id: 'not-sauerstoff',
      title: 'Sauerstoff & Notruf',
      summary: 'Der wichtigste Erste‑Hilfe‑Schritt bei jedem Tauchunfall.',
      minutes: 7,
      blocks: [
        { type: 'p', text: 'Bei Verdacht auf DCS oder Lungenüberdehnung ist **100 % Sauerstoff** die wichtigste Maßnahme. Er beschleunigt die Stickstoffabgabe, verkleinert Blasen und versorgt geschädigtes Gewebe. Jede Tauchbasis muss ein O₂‑Set haben – frag danach beim Check‑in.' },
        { type: 'list', items: ['**Demand‑Ventil** (atmender Patient) liefert nahezu 100 %.', '**Non‑Rebreather‑Maske** bei 15 l/min: ca. 90 %.', '**Beatmungsbeutel mit O₂** beim Nicht‑Atmenden.', 'Solange geben, bis der Notarzt übernimmt – auch wenn Symptome verschwinden.'] },
        { type: 'h', text: 'Notruf – die Struktur' },
        { type: 'steps', items: ['**Wo** ist der Unfall (Ort, Basis, Boot, GPS)?', '**Was** ist passiert (Tauchunfall, Profil, Symptome)?', '**Wie viele** Betroffene?', '**Welche** Verletzungen / Symptome?', '**Warten** auf Rückfragen.'] },
        { type: 'table', headers: ['Region', 'Nummer'], rows: [['Europa (allgemein)', '112'], ['DAN Europe Hotline', '+39 06 4211 5685'], ['DAN America', '+1 919 684 9111'], ['Ägypten (Sharm/Hurghada Kammern)', 'Über Basis – Nummer vorher notieren!']] },
        { type: 'fact', title: 'Tauchunfallversicherung', text: 'Druckkammerbehandlungen kosten 5.000–30.000 €. Eine Tauchversicherung (DAN, aqua med) kostet ~50–100 €/Jahr und beinhaltet eine 24‑h‑Hotline mit Tauchmedizinern.' },
      ],
    },
  ],
}
