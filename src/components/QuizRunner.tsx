import { useMemo, useState } from 'react'
import { CheckCircle2, XCircle, ArrowRight, RotateCcw } from 'lucide-react'
import type { QuizQuestion } from '../data/types'
import { Button, Card, ProgressBar, ProgressRing, cn } from './ui'
import { shuffle } from '../data/quizzes'

export function QuizRunner({ questions, title, passThreshold = 0.7, onFinish, onRestart }: {
  questions: QuizQuestion[]
  title: string
  passThreshold?: number
  onFinish: (score: number, total: number) => void
  onRestart?: () => void
}) {
  const prepared = useMemo(
    () =>
      questions.map((q) => {
        const order = shuffle(q.options.map((_, i) => i))
        return { ...q, options: order.map((i) => q.options[i]), answer: order.indexOf(q.answer) }
      }),
    [questions],
  )
  const [i, setI] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [answers, setAnswers] = useState<boolean[]>([])
  const [finished, setFinished] = useState(false)

  const q = prepared[i]
  const score = answers.filter(Boolean).length

  const choose = (idx: number) => {
    if (selected !== null) return
    setSelected(idx)
    setAnswers((a) => [...a, idx === q.answer])
  }

  const nextQ = () => {
    if (i + 1 >= prepared.length) {
      setFinished(true)
      onFinish(score, prepared.length)
    } else {
      setI(i + 1)
      setSelected(null)
    }
  }

  const restart = () => {
    setI(0)
    setSelected(null)
    setAnswers([])
    setFinished(false)
    onRestart?.()
  }

  if (finished) {
    const pct = score / prepared.length
    const passed = pct >= passThreshold
    return (
      <Card className="mx-auto max-w-xl text-center animate-pop">
        <div className="text-5xl">{passed ? (pct === 1 ? '🏆' : '🎉') : '🫧'}</div>
        <h2 className="mt-3 font-display text-2xl font-bold">{passed ? (pct === 1 ? 'Perfekt!' : 'Bestanden!') : 'Noch nicht ganz'}</h2>
        <p className="mt-1 text-muted">{title}</p>
        <div className="my-6 flex justify-center">
          <ProgressRing value={pct} size={140} stroke={12} gradientId="quiz-ring">
            <div>
              <div className="font-display text-3xl font-bold">{Math.round(pct * 100)}%</div>
              <div className="text-xs text-faint">{score}/{prepared.length}</div>
            </div>
          </ProgressRing>
        </div>
        <p className="text-sm text-muted">
          {passed ? `Du hast die Grenze von ${Math.round(passThreshold * 100)} % geschafft. Weiter so!` : `Du brauchst ${Math.round(passThreshold * 100)} %. Wiederhole die Lektionen und versuche es erneut.`}
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button variant="outline" onClick={restart}><RotateCcw size={16} /> Nochmal</Button>
        </div>
      </Card>
    )
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between text-sm">
        <span className="font-semibold text-muted">Frage {i + 1} von {prepared.length}</span>
        <span className="font-semibold text-aqua-500">{score} richtig</span>
      </div>
      <ProgressBar value={(i + (selected !== null ? 1 : 0)) / prepared.length} className="mb-6" />

      <Card key={q.id} className="animate-fade-up">
        <h2 className="font-display text-xl font-bold leading-snug md:text-2xl">{q.question}</h2>
        <div className="mt-5 space-y-2.5">
          {q.options.map((opt, idx) => {
            const isCorrect = idx === q.answer
            const isSel = idx === selected
            const revealed = selected !== null
            return (
              <button
                key={idx}
                onClick={() => choose(idx)}
                disabled={revealed}
                className={cn(
                  'flex w-full items-center gap-3 rounded-2xl border px-4 py-3.5 text-left text-sm font-medium transition-all md:text-base cursor-pointer disabled:cursor-default',
                  !revealed && 'border-strong hover:border-aqua-400 hover:bg-aqua-400/10',
                  revealed && isCorrect && 'border-emerald-400 bg-emerald-400/15',
                  revealed && isSel && !isCorrect && 'border-rose-400 bg-rose-400/15',
                  revealed && !isSel && !isCorrect && 'border-base opacity-50',
                )}
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-strong text-xs font-bold">{String.fromCharCode(65 + idx)}</span>
                <span className="flex-1">{opt}</span>
                {revealed && isCorrect && <CheckCircle2 size={20} className="text-emerald-400" />}
                {revealed && isSel && !isCorrect && <XCircle size={20} className="text-rose-400" />}
              </button>
            )
          })}
        </div>
        {selected !== null && (
          <div className={cn('mt-5 rounded-2xl border p-4 text-sm animate-fade-up', selected === q.answer ? 'border-emerald-400/40 bg-emerald-400/10' : 'border-rose-400/40 bg-rose-400/10')}>
            <div className="mb-1 font-bold">{selected === q.answer ? 'Richtig!' : 'Leider falsch.'}</div>
            <div className="text-muted">{q.explanation}</div>
          </div>
        )}
        <div className="mt-5 flex justify-end">
          <Button onClick={nextQ} disabled={selected === null}>{i + 1 >= prepared.length ? 'Auswerten' : 'Nächste Frage'} <ArrowRight size={16} /></Button>
        </div>
      </Card>
    </div>
  )
}
