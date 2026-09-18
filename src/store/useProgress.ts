import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface QuizResult {
  moduleId: string
  score: number
  total: number
  date: string
}

export interface DiveLogEntry {
  id: string
  date: string
  site: string
  location: string
  maxDepth: number
  duration: number
  waterTemp?: number
  visibility?: number
  buddy?: string
  startBar?: number
  endBar?: number
  notes?: string
  rating: number
}

interface ProgressState {
  completedLessons: string[]
  quizResults: QuizResult[]
  examResults: QuizResult[]
  unlockedAchievements: string[]
  xp: number
  streak: number
  lastActive: string | null
  diveLog: DiveLogEntry[]
  flashcardsKnown: string[]
  checklistState: Record<string, boolean[]>
  theme: 'dark' | 'light'
  name: string

  completeLesson: (id: string) => void
  recordQuiz: (r: QuizResult) => void
  recordExam: (r: QuizResult) => void
  unlock: (id: string, xp: number) => void
  touchStreak: () => void
  addDive: (d: DiveLogEntry) => void
  removeDive: (id: string) => void
  markFlashcard: (id: string, known: boolean) => void
  toggleChecklistItem: (checklistId: string, index: number, length: number) => void
  resetChecklist: (checklistId: string) => void
  setTheme: (t: 'dark' | 'light') => void
  setName: (n: string) => void
  resetAll: () => void
}

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

function daysBetween(a: string, b: string) {
  const ms = new Date(b).getTime() - new Date(a).getTime()
  return Math.round(ms / 86400000)
}

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      completedLessons: [],
      quizResults: [],
      examResults: [],
      unlockedAchievements: [],
      xp: 0,
      streak: 0,
      lastActive: null,
      diveLog: [],
      flashcardsKnown: [],
      checklistState: {},
      theme: 'dark',
      name: '',

      completeLesson: (id) => {
        if (get().completedLessons.includes(id)) return
        set((s) => ({ completedLessons: [...s.completedLessons, id], xp: s.xp + 25 }))
        get().touchStreak()
      },
      recordQuiz: (r) => {
        set((s) => ({ quizResults: [...s.quizResults, r], xp: s.xp + r.score * 10 }))
        get().touchStreak()
      },
      recordExam: (r) => {
        set((s) => ({ examResults: [...s.examResults, r], xp: s.xp + r.score * 15 }))
        get().touchStreak()
      },
      unlock: (id, xp) => {
        if (get().unlockedAchievements.includes(id)) return
        set((s) => ({ unlockedAchievements: [...s.unlockedAchievements, id], xp: s.xp + xp }))
      },
      touchStreak: () => {
        const today = todayISO()
        const last = get().lastActive
        if (last === today) return
        if (last && daysBetween(last, today) === 1) {
          set((s) => ({ streak: s.streak + 1, lastActive: today }))
        } else {
          set({ streak: 1, lastActive: today })
        }
      },
      addDive: (d) => {
        set((s) => ({ diveLog: [d, ...s.diveLog], xp: s.xp + 40 }))
        get().touchStreak()
      },
      removeDive: (id) => set((s) => ({ diveLog: s.diveLog.filter((d) => d.id !== id) })),
      markFlashcard: (id, known) =>
        set((s) => ({
          flashcardsKnown: known
            ? Array.from(new Set([...s.flashcardsKnown, id]))
            : s.flashcardsKnown.filter((x) => x !== id),
        })),
      toggleChecklistItem: (checklistId, index, length) =>
        set((s) => {
          const current = s.checklistState[checklistId] ?? Array(length).fill(false)
          const next = [...current]
          next[index] = !next[index]
          return { checklistState: { ...s.checklistState, [checklistId]: next } }
        }),
      resetChecklist: (checklistId) =>
        set((s) => {
          const copy = { ...s.checklistState }
          delete copy[checklistId]
          return { checklistState: copy }
        }),
      setTheme: (theme) => set({ theme }),
      setName: (name) => set({ name }),
      resetAll: () =>
        set({
          completedLessons: [],
          quizResults: [],
          examResults: [],
          unlockedAchievements: [],
          xp: 0,
          streak: 0,
          lastActive: null,
          diveLog: [],
          flashcardsKnown: [],
          checklistState: {},
        }),
    }),
    { name: 'deeplearn-progress-v1' },
  ),
)

export function levelFromXp(xp: number) {
  const levels = [
    { name: 'Schnorchler', min: 0 },
    { name: 'Open Water Diver', min: 300 },
    { name: 'Advanced Diver', min: 800 },
    { name: 'Rescue Diver', min: 1600 },
    { name: 'Divemaster', min: 2800 },
    { name: 'Instructor', min: 4500 },
    { name: 'Tiefsee-Legende', min: 7000 },
  ]
  let idx = 0
  for (let i = 0; i < levels.length; i++) if (xp >= levels[i].min) idx = i
  const current = levels[idx]
  const next = levels[idx + 1]
  const progress = next ? (xp - current.min) / (next.min - current.min) : 1
  return { level: idx + 1, name: current.name, next: next?.name ?? null, nextXp: next?.min ?? null, progress }
}
