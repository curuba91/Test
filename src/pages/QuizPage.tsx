import { Link, Navigate, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { getModule } from '../data/modules'
import { questionsForModule, shuffle } from '../data/quizzes'
import { useProgress } from '../store/useProgress'
import { QuizRunner } from '../components/QuizRunner'
import { PageHeader } from '../components/ui'

export function QuizPage() {
  const { moduleId = '' } = useParams()
  const m = getModule(moduleId)
  const recordQuiz = useProgress((s) => s.recordQuiz)
  const [qs, setQs] = useState(() => shuffle(questionsForModule(moduleId)))
  if (!m) return <Navigate to="/kurse" replace />

  return (
    <div>
      <Link to={`/kurse/${m.id}`} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted no-underline hover:text-inherit"><ArrowLeft size={16} /> {m.title}</Link>
      <PageHeader eyebrow="Quiz" title={`${m.title} – Quiz`} subtitle="Jede Frage hat genau eine richtige Antwort. Nach jeder Antwort siehst du die Erklärung." />
      <QuizRunner
        key={qs[0]?.id}
        questions={qs}
        title={m.title}
        onFinish={(score, total) => recordQuiz({ moduleId: m.id, score, total, date: new Date().toISOString() })}
        onRestart={() => setQs(shuffle(questionsForModule(moduleId)))}
      />
    </div>
  )
}
