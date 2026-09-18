export type ContentBlock =
  | { type: 'p'; text: string }
  | { type: 'h'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'fact'; title?: string; text: string }
  | { type: 'warning'; title?: string; text: string }
  | { type: 'tip'; title?: string; text: string }
  | { type: 'formula'; label: string; formula: string; note?: string }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'steps'; items: string[] }

export interface Lesson {
  id: string
  title: string
  summary: string
  minutes: number
  blocks: ContentBlock[]
}

export type ModuleLevel = 'Beginner' | 'Advanced' | 'Specialty'

export interface CourseModule {
  id: string
  title: string
  subtitle: string
  level: ModuleLevel
  icon: string
  accent: string
  description: string
  lessons: Lesson[]
}

export interface QuizQuestion {
  id: string
  moduleId: string
  question: string
  options: string[]
  answer: number
  explanation: string
}

export interface Flashcard {
  id: string
  moduleId: string
  front: string
  back: string
}

export interface HandSignal {
  id: string
  name: string
  meaning: string
  howTo: string
  category: 'Basis' | 'Status' | 'Notfall' | 'Tiere' | 'Zahlen'
  emoji: string
}

export interface GlossaryEntry {
  term: string
  definition: string
  tag: string
}

export interface Achievement {
  id: string
  title: string
  description: string
  icon: string
  xp: number
}

export interface Checklist {
  id: string
  title: string
  description: string
  items: string[]
}
