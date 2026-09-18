import { useEffect } from 'react'
import { useProgress } from '../store/useProgress'
import { modules, allLessons } from '../data/modules'
import { achievements } from '../data/achievements'

const xpOf = (id: string) => achievements.find((a) => a.id === id)?.xp ?? 0

/** Evaluates achievement conditions whenever progress changes. */
export function useAchievementWatcher() {
  const s = useProgress()
  useEffect(() => {
    const unlock = (id: string) => s.unlock(id, xpOf(id))
    const lessons = s.completedLessons.length
    if (lessons >= 1) unlock('first-lesson')
    if (lessons >= 5) unlock('five-lessons')
    if (modules.some((m) => m.lessons.every((l) => s.completedLessons.includes(l.id)))) unlock('first-module')
    if (allLessons.every((l) => s.completedLessons.includes(l.id))) unlock('all-modules')
    const passed = s.quizResults.filter((r) => r.score / r.total >= 0.7)
    if (passed.length >= 1) unlock('first-quiz')
    if (passed.length >= 5) unlock('five-quizzes')
    if (s.quizResults.some((r) => r.score === r.total) || s.examResults.some((r) => r.score === r.total)) unlock('perfect-quiz')
    if (s.examResults.some((r) => r.score / r.total >= 0.75)) unlock('exam-passed')
    if (s.diveLog.length >= 1) unlock('first-dive')
    if (s.diveLog.length >= 10) unlock('ten-dives')
    if (s.diveLog.some((d) => d.maxDepth > 30)) unlock('deep-dive')
    if (s.streak >= 3) unlock('streak-3')
    if (s.streak >= 7) unlock('streak-7')
    if (s.flashcardsKnown.length >= 20) unlock('flashcards-20')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.completedLessons, s.quizResults, s.examResults, s.diveLog, s.streak, s.flashcardsKnown])
}
