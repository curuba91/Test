import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Check, X, RotateCcw, Shuffle } from 'lucide-react'
import { flashcards } from '../data/flashcards'
import { modules } from '../data/modules'
import { shuffle } from '../data/quizzes'
import { useProgress } from '../store/useProgress'
import { Button, PageHeader, cn, Pill, Card } from '../components/ui'

export function Flashcards() {
  const [params, setParams] = useSearchParams()
  const filter = params.get('modul') ?? 'all'
  const { flashcardsKnown, markFlashcard } = useProgress()
  const [onlyUnknown, setOnlyUnknown] = useState(false)
  const [seed, setSeed] = useState(0)
  const [i, setI] = useState(0)
  const [flipped, setFlipped] = useState(false)

  const deck = useMemo(() => {
    let d = flashcards.filter((f) => filter === 'all' || f.moduleId === filter)
    if (onlyUnknown) d = d.filter((f) => !flashcardsKnown.includes(f.id))
    return shuffle(d)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, onlyUnknown, seed])

  const card = deck[i]
  const known = flashcards.filter((f) => filter === 'all' || f.moduleId === filter).filter((f) => flashcardsKnown.includes(f.id)).length
  const total = flashcards.filter((f) => filter === 'all' || f.moduleId === filter).length

  const answer = (k: boolean) => {
    if (!card) return
    markFlashcard(card.id, k)
    setFlipped(false)
    setTimeout(() => setI((x) => x + 1), 120)
  }

  const reset = () => { setI(0); setFlipped(false); setSeed((s) => s + 1) }

  return (
    <div>
      <PageHeader eyebrow="Wiederholen" title="Karteikarten" subtitle="Karte antippen zum Umdrehen. Markiere, ob du es wusstest – unbekannte Karten kommen öfter." />
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <select className="rounded-xl border border-strong bg-transparent px-3 py-2 text-sm font-semibold" value={filter} onChange={(e) => { setParams(e.target.value === 'all' ? {} : { modul: e.target.value }); setI(0); setFlipped(false) }}>
          <option value="all">Alle Module</option>
          {modules.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
        </select>
        <button onClick={() => { setOnlyUnknown((o) => !o); setI(0) }} className={cn('rounded-xl border px-3 py-2 text-sm font-semibold cursor-pointer', onlyUnknown ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>Nur unbekannte</button>
        <Button variant="ghost" size="sm" onClick={reset}><Shuffle size={14} /> Mischen</Button>
        <Pill color="kelp" className="ml-auto">{known}/{total} gewusst</Pill>
      </div>

      {!card ? (
        <Card className="mx-auto max-w-xl py-14 text-center animate-pop">
          <div className="text-5xl">🎯</div>
          <h3 className="mt-3 font-display text-xl font-bold">Stapel durch!</h3>
          <p className="mt-1 text-muted">{onlyUnknown ? 'Keine unbekannten Karten mehr in dieser Auswahl.' : 'Du hast alle Karten in dieser Auswahl gesehen.'}</p>
          <Button className="mt-5" onClick={reset}><RotateCcw size={16} /> Nochmal</Button>
        </Card>
      ) : (
        <div className="mx-auto max-w-xl">
          <div className="mb-3 flex items-center justify-between text-xs font-semibold text-faint">
            <span>Karte {i + 1} / {deck.length}</span>
            <span>{modules.find((m) => m.id === card.moduleId)?.title}</span>
          </div>
          <div className="[perspective:1200px]" onClick={() => setFlipped((f) => !f)}>
            <div className={cn('relative h-72 w-full cursor-pointer transition-transform duration-500 [transform-style:preserve-3d]', flipped && '[transform:rotateY(180deg)]')}>
              <div className="glass absolute inset-0 flex flex-col items-center justify-center rounded-3xl p-8 text-center [backface-visibility:hidden]">
                <div className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-aqua-500">Frage</div>
                <div className="font-display text-2xl font-bold">{card.front}</div>
                <div className="mt-6 text-xs text-faint">Antippen zum Umdrehen</div>
              </div>
              <div className="absolute inset-0 flex flex-col items-center justify-center rounded-3xl border border-aqua-400/40 bg-gradient-to-br from-aqua-400/20 to-indigo-500/20 p-8 text-center backdrop-blur-xl [backface-visibility:hidden] [transform:rotateY(180deg)]">
                <div className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-aqua-500">Antwort</div>
                <div className="font-display text-xl font-bold md:text-2xl">{card.back}</div>
              </div>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3">
            <Button variant="outline" size="lg" onClick={() => answer(false)} className="border-rose-400/40 hover:bg-rose-400/10"><X size={18} className="text-rose-400" /> Nochmal üben</Button>
            <Button size="lg" onClick={() => answer(true)} className="from-emerald-400 to-teal-500 shadow-emerald-500/25"><Check size={18} /> Gewusst</Button>
          </div>
        </div>
      )}
    </div>
  )
}
