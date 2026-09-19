import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowRight, CheckCircle2, Clock } from 'lucide-react'
import { getModule } from '../data/modules'
import { useProgress } from '../store/useProgress'
import { Button, Pill } from '../components/ui'
import { ContentRenderer } from '../components/ContentRenderer'

export function LessonPage() {
  const { moduleId = '', lessonId = '' } = useParams()
  const navigate = useNavigate()
  const m = getModule(moduleId)
  const { completedLessons, completeLesson } = useProgress()
  if (!m) return <Navigate to="/kurse" replace />
  const idx = m.lessons.findIndex((l) => l.id === lessonId)
  if (idx < 0) return <Navigate to={`/kurse/${m.id}`} replace />
  const lesson = m.lessons[idx]
  const prev = m.lessons[idx - 1]
  const next = m.lessons[idx + 1]
  const done = completedLessons.includes(lesson.id)

  const finish = () => {
    completeLesson(lesson.id)
    if (next) navigate(`/kurse/${m.id}/${next.id}`)
    else navigate(`/quiz/${m.id}`)
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link to={`/kurse/${m.id}`} className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted no-underline hover:text-inherit"><ArrowLeft size={16} /> {m.title}</Link>

      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Pill color="aqua">Lektion {idx + 1} / {m.lessons.length}</Pill>
        <Pill color="neutral"><Clock size={12} /> {lesson.minutes} min</Pill>
        {done && <Pill color="kelp"><CheckCircle2 size={12} /> Abgeschlossen</Pill>}
      </div>
      <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl animate-fade-up">{lesson.title}</h1>
      <p className="mt-2 text-lg text-muted animate-fade-up">{lesson.summary}</p>

      <div className="mt-8 glass rounded-3xl p-5 md:p-8 animate-fade-up" style={{ animationDelay: '80ms' }}>
        <ContentRenderer blocks={lesson.blocks} />
      </div>

      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        {prev ? (
          <Link to={`/kurse/${m.id}/${prev.id}`}><Button variant="ghost"><ArrowLeft size={16} /> {prev.title}</Button></Link>
        ) : <span />}
        <Button size="lg" onClick={finish}>
          {done ? (next ? 'Weiter' : 'Zum Quiz') : next ? 'Abschließen & weiter' : 'Abschließen & Quiz starten'} <ArrowRight size={18} />
        </Button>
      </div>
    </div>
  )
}
