import { useState } from 'react'
import { GraduationCap, ShieldCheck } from 'lucide-react'
import { questions, shuffle } from '../data/quizzes'
import { useProgress } from '../store/useProgress'
import { QuizRunner } from '../components/QuizRunner'
import { Button, Card, PageHeader, Pill } from '../components/ui'
import { modules, allLessons } from '../data/modules'

const EXAM_SIZE = 30

/** Balanced sample: draw evenly across modules, then fill up randomly. */
function buildExam() {
  const perModule = Math.floor(EXAM_SIZE / modules.length)
  const picked: typeof questions = []
  for (const m of modules) picked.push(...shuffle(questions.filter((q) => q.moduleId === m.id)).slice(0, perModule))
  const rest = shuffle(questions.filter((q) => !picked.includes(q))).slice(0, EXAM_SIZE - picked.length)
  return shuffle([...picked, ...rest])
}

export function ExamPage() {
  const { examResults, recordExam, completedLessons } = useProgress()
  const [started, setStarted] = useState(false)
  const [qs, setQs] = useState(buildExam)
  const best = examResults.reduce((a, r) => Math.max(a, r.score / r.total), 0)
  const readiness = completedLessons.length / allLessons.length

  if (!started) {
    return (
      <div>
        <PageHeader eyebrow="Abschluss" title="Theorie‑Prüfung" subtitle="30 zufällige Fragen aus allen Modulen. Zum Bestehen brauchst du 75 %. Du kannst die Prüfung beliebig oft wiederholen." />
        <div className="grid gap-4 md:grid-cols-[1fr_320px]">
          <Card className="relative overflow-hidden">
            <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-indigo-500/20 blur-3xl" />
            <GraduationCap size={40} className="text-aqua-400" />
            <h2 className="mt-3 font-display text-2xl font-bold">Bereit?</h2>
            <ul className="mt-3 space-y-2 text-sm text-muted">
              <li>• {EXAM_SIZE} Fragen, gleichmäßig über alle {modules.length} Module verteilt</li>
              <li>• Direkte Rückmeldung mit Erklärung nach jeder Frage</li>
              <li>• Bestehensgrenze: 75 % (23 von 30)</li>
              <li>• Bestandene Prüfung schaltet das Abzeichen „Zertifiziert“ frei</li>
            </ul>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button size="lg" onClick={() => setStarted(true)}>Prüfung starten</Button>
              {readiness < 0.5 && <span className="text-xs text-faint">Tipp: Du hast erst {Math.round(readiness * 100)} % der Lektionen gelesen.</span>}
            </div>
          </Card>
          <div className="space-y-4">
            <Card>
              <div className="flex items-center gap-2 font-display font-bold"><ShieldCheck size={18} className="text-emerald-400" /> Deine Versuche</div>
              {examResults.length === 0 ? (
                <p className="mt-2 text-sm text-muted">Noch kein Versuch.</p>
              ) : (
                <div className="mt-3 space-y-2">
                  {[...examResults].reverse().slice(0, 5).map((r, i) => (
                    <div key={i} className="flex items-center justify-between rounded-xl border border-base px-3 py-2 text-sm">
                      <span className="text-muted">{new Date(r.date).toLocaleDateString('de-DE')}</span>
                      <Pill color={r.score / r.total >= 0.75 ? 'kelp' : 'coral'}>{Math.round((r.score / r.total) * 100)} %</Pill>
                    </div>
                  ))}
                </div>
              )}
              {best > 0 && <div className="mt-3 text-xs text-faint">Bestes Ergebnis: {Math.round(best * 100)} %</div>}
            </Card>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader eyebrow="Abschluss" title="Theorie‑Prüfung" />
      <QuizRunner
        key={qs[0]?.id}
        questions={qs}
        title="Theorie‑Prüfung"
        passThreshold={0.75}
        onFinish={(score, total) => recordExam({ moduleId: 'exam', score, total, date: new Date().toISOString() })}
        onRestart={() => setQs(buildExam())}
      />
    </div>
  )
}
