import { Clock, CheckCircle2 } from 'lucide-react'
import { modules } from '../data/modules'
import { useProgress } from '../store/useProgress'
import { CardLink, PageHeader, Pill, ProgressBar } from '../components/ui'
import { ModuleIcon } from '../components/Icon'
import { questionsForModule } from '../data/quizzes'

export function Courses() {
  const { completedLessons, quizResults } = useProgress()
  return (
    <div>
      <PageHeader eyebrow="Kurse" title="Alle Module" subtitle="Vom ersten Atemzug unter Wasser bis zur Nitrox‑Planung. Jedes Modul endet mit einem Quiz." />
      <div className="grid gap-4 md:grid-cols-2">
        {modules.map((m, i) => {
          const done = m.lessons.filter((l) => completedLessons.includes(l.id)).length
          const minutes = m.lessons.reduce((a, l) => a + l.minutes, 0)
          const best = quizResults.filter((r) => r.moduleId === m.id).reduce((a, r) => Math.max(a, r.score / r.total), 0)
          const complete = done === m.lessons.length
          return (
            <CardLink key={m.id} to={`/kurse/${m.id}`} className="animate-fade-up relative overflow-hidden">
              <div className={`absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${m.accent} opacity-20 blur-2xl`} style={{ animationDelay: `${i * 50}ms` }} />
              <div className="relative flex items-start gap-4">
                <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${m.accent} text-white shadow-lg`}>
                  <ModuleIcon name={m.icon} size={26} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-display text-xl font-bold">{m.title}</h2>
                    <Pill color={m.level === 'Beginner' ? 'kelp' : m.level === 'Advanced' ? 'violet' : 'sun'}>{m.level}</Pill>
                    {complete && <CheckCircle2 size={18} className="text-emerald-400" />}
                  </div>
                  <p className="mt-1 text-sm text-muted">{m.description}</p>
                  <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-faint">
                    <span>{m.lessons.length} Lektionen</span>
                    <span className="flex items-center gap-1"><Clock size={12} /> {minutes} min</span>
                    <span>{questionsForModule(m.id).length} Quizfragen</span>
                    {best > 0 && <span className="font-semibold text-aqua-500">Quiz‑Best: {Math.round(best * 100)} %</span>}
                  </div>
                  <div className="mt-3 flex items-center gap-3">
                    <ProgressBar value={done / m.lessons.length} gradient={m.accent} />
                    <span className="shrink-0 text-xs font-semibold">{done}/{m.lessons.length}</span>
                  </div>
                </div>
              </div>
            </CardLink>
          )
        })}
      </div>
    </div>
  )
}
