import type { Checklist } from './types'

export const checklists: Checklist[] = [
  {
    id: 'packing',
    title: 'Packliste Tauchurlaub',
    description: 'Damit du am Ziel nichts vermisst.',
    items: ['Brevet / Zertifizierungskarte', 'Logbuch', 'Tauchtauglichkeitsbescheinigung', 'Tauchversicherung (DAN etc.)', 'Maske + Ersatzmaskenband', 'Schnorchel', 'Flossen + Füßlinge', 'Anzug passend zur Wassertemperatur', 'Jacket', 'Atemregler + Oktopus + Finimeter', 'Tauchcomputer (Batterie prüfen!)', 'Lampe + Ersatzakku', 'SMB / Boje + Spool', 'Kompass', 'Messer / Cutter', 'Ersatzteile: O‑Ringe, Maskenband, Flossenband', 'Riffsichere Sonnencreme', 'Ohrentropfen / Ohrspülung', 'Save‑a‑Dive‑Kit'],
  },
  {
    id: 'predive',
    title: 'Vor dem Tauchgang',
    description: 'Der Standard‑Check vor dem Sprung ins Wasser.',
    items: ['Ausgeschlafen, nüchtern, hydriert?', 'Erkältung / Ohrenprobleme? → Nicht tauchen', 'Flasche voll (≥ 200 bar) und Ventil ganz offen', 'Nitrox analysiert und am Computer eingestellt', 'Buddy‑Check BWRAF durchgeführt', 'Briefing: Tiefe, Zeit, Route, Umkehrdruck, Signale', 'Verlorener‑Buddy‑Prozedur abgesprochen', 'Computer gestartet, Uhrzeit passt', 'Maske entbeschlagen', 'Blei gesichert, Schnellabwurf erreichbar', 'Alles verstaut, nichts baumelt (Riffschutz)'],
  },
  {
    id: 'postdive',
    title: 'Nach dem Tauchgang',
    description: 'Ausrüstung pflegen, Körper beobachten.',
    items: ['Symptome? Schmerzen, Kribbeln, ungewöhnliche Müdigkeit → melden', 'Logbuch: Tiefe, Zeit, Luft, Blei, Bedingungen, Buddy', 'Trinken (mind. 0,5 l)', 'Ausrüstung mit Süßwasser gespült', 'Atemregler‑Kappe trocken aufgesetzt', 'Jacket innen gespült, halb aufgeblasen', 'Im Schatten getrocknet', 'Oberflächenpause ≥ 1 h vor dem nächsten Tauchgang', 'Flug‑/Höhenverbot beachtet (12–24 h)'],
  },
  {
    id: 'safety-kit',
    title: 'Sicherheitsausrüstung Boot / Basis',
    description: 'Frag beim Check‑in nach diesen Dingen.',
    items: ['Sauerstoff‑Notfallset vorhanden und voll', 'Erste‑Hilfe‑Kasten', 'Notrufnummern (Basis, Druckkammer, DAN) notiert', 'Funk / Handy an Bord', 'Rettungsleine / Strömungsleine', 'Taucherflagge gesetzt', 'Tauchleiter mit Aufstiegsleine', 'Divemaster kennt dein Profil und Tauchzeit'],
  },
]
