import type { Achievement } from './types'

export const achievements: Achievement[] = [
  { id: 'first-lesson', title: 'Erste Blasen', description: 'Erste Lektion abgeschlossen.', icon: '🫧', xp: 50 },
  { id: 'five-lessons', title: 'Lernfisch', description: '5 Lektionen abgeschlossen.', icon: '🐠', xp: 100 },
  { id: 'first-module', title: 'Modul‑Meister', description: 'Erstes Modul komplett durchgearbeitet.', icon: '📘', xp: 150 },
  { id: 'first-quiz', title: 'Quiz‑Neuling', description: 'Erstes Quiz bestanden (≥ 70 %).', icon: '✅', xp: 75 },
  { id: 'perfect-quiz', title: 'Fehlerfrei', description: 'Ein Quiz mit 100 % abgeschlossen.', icon: '💯', xp: 150 },
  { id: 'five-quizzes', title: 'Quiz‑Profi', description: '5 Quizze bestanden.', icon: '🧠', xp: 200 },
  { id: 'exam-passed', title: 'Zertifiziert', description: 'Abschlussprüfung bestanden.', icon: '🎓', xp: 500 },
  { id: 'all-modules', title: 'Enzyklopädie', description: 'Alle Lektionen aller Module abgeschlossen.', icon: '📚', xp: 400 },
  { id: 'first-dive', title: 'Logbuch eröffnet', description: 'Ersten Tauchgang eingetragen.', icon: '📓', xp: 50 },
  { id: 'ten-dives', title: 'Zehn unter Null', description: '10 Tauchgänge im Logbuch.', icon: '🔟', xp: 200 },
  { id: 'deep-dive', title: 'Tiefgänger', description: 'Tauchgang tiefer als 30 m geloggt.', icon: '🌊', xp: 100 },
  { id: 'streak-3', title: 'Dranbleiber', description: '3 Tage in Folge gelernt.', icon: '🔥', xp: 100 },
  { id: 'streak-7', title: 'Wochen‑Streak', description: '7 Tage in Folge gelernt.', icon: '⚡', xp: 250 },
  { id: 'flashcards-20', title: 'Karteikarten‑Held', description: '20 Karteikarten als „gewusst“ markiert.', icon: '🃏', xp: 100 },
  { id: 'signals-visited', title: 'Sprachtalent', description: 'Handzeichen‑Bibliothek angeschaut.', icon: '🤟', xp: 25 },
  { id: 'tools-used', title: 'Rechenkünstler', description: 'Tauchrechner genutzt.', icon: '🧮', xp: 25 },
]
