import { Link, Navigate, useParams } from 'react-router-dom'
import { CheckCircle2, Circle, Clock, ArrowLeft, Zap, Layers } from 'lucide-react'
import { getModule } from '../data/modules'
import { useProgress } from '../store/useProgress'
import { Button, Card, PageHeader, Pill, ProgressRing } from '../components/ui'
import { ModuleIcon } from '../components/Icon'
import { questionsForModule } from '../data/quizzes'
import { flashcards } from '../data/flashcards'

export function ModulePage() {
  const { moduleId = '' } = useParams()
  const m = getModule(moduleId)
  const { completedLessons, quizResults } = useProgress()
  if (!m) return <Navigate to="/kurse" replace />
  const done = m.lessons.filter((l) => completedLessons.includes(l.id)).length
  const results = quizResults.filter((r) => r.moduleId === m.id)
  const best = results.reduce((a, r) => Math.max(a, r.score / r.total), 0)
  const nextLesson = m.lessons.find((l) => !completedLessons.includes(l.id)) ?? m.lessons[0]
  const cards = flashcards.filter((f) => f.moduleId === m.id).length

  return (
    <div>
      <Link to="/kurse" className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-muted no-underline hover:text-inherit"><ArrowLeft size={16} /> Alle Kurse</Link>
      <PageHeader eyebrow={m.level} title={m.title} subtitle={m.description} />

      <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
        <div className="space-y-3">
          {m.lessons.map((l, i) => {
            const isDone = completedLessons.includes(l.id)
            return (
              <Link key={l.id} to={`/kurse/${m.id}/${l.id}`} className="glass card-hover flex items-center gap-4 rounded-3xl p-4 no-underline text-inherit animate-fade-up md:p-5" style={{ animationDelay: `${i * 50}ms` }}>
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${isDone ? 'bg-emerald-400/15 text-emerald-400' : 'bg-slate-500/10 text-faint'}`}>
                  {isDone ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-semibold uppercase tracking-wider text-faint">Lektion {i + 1}</div>
                  <div className="font-display text-lg font-bold">{l.title}</div>
                  <div className="text-sm text-muted">{l.summary}</div>
                </div>
                <div className="hidden shrink-0 items-center gap-1 text-xs text-faint sm:flex"><Clock size={12} /> {l.minutes} min</div>
              </Link>
            )
          })}
        </div>

        <div className="space-y-4">
          <Card className="text-center">
            <div className={`mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${m.accent} text-white shadow-lg`}><ModuleIcon name={m.icon} size={26} /></div>
            <ProgressRing value={done / m.lessons.length} size={110} stroke={9} gradientId={`ring-${m.id}`}>
              <div className="font-display text-2xl font-bold">{Math.round((done / m.lessons.length) * 100)}%</div>
            </ProgressRing>
            <div className="mt-2 text-sm text-muted">{done} von {m.lessons.length} Lektionen</div>
            <Link to={`/kurse/${m.id}/${nextLesson.id}`} className="mt-4 block"><Button className="w-full">{done === 0 ? 'Modul starten' : done === m.lessons.length ? 'Wiederholen' : 'Weiterlernen'}</Button></Link>
          </Card>
          <Card>
            <div className="flex items-center gap-2 font-display font-bold"><Zap size={18} className="text-amber-400" /> Modul‑Quiz</div>
            <p className="mt-1 text-sm text-muted">{questionsForModule(m.id).length} Fragen · 70 % zum Bestehen</p>
            {best > 0 && <Pill color={best >= 0.7 ? 'kelp' : 'coral'} className="mt-2">Bestes Ergebnis: {Math.round(best * 100)} %</Pill>}
            <Link to={`/quiz/${m.id}`} className="mt-4 block"><Button variant="outline" className="w-full">Quiz starten</Button></Link>
          </Card>
          <Card>
            <div className="flex items-center gap-2 font-display font-bold"><Layers size={18} className="text-aqua-400" /> Karteikarten</div>
            <p className="mt-1 text-sm text-muted">{cards} Karten zu diesem Modul</p>
            <Link to={`/karteikarten?modul=${m.id}`} className="mt-4 block"><Button variant="ghost" className="w-full border border-base">Üben</Button></Link>
          </Card>
        </div>
      </div>
    </div>
  )
}
