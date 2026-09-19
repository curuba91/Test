import { useState } from 'react'
import { CheckSquare, Square, RotateCcw } from 'lucide-react'
import { checklists } from '../data/checklists'
import { useProgress } from '../store/useProgress'
import { Button, Card, PageHeader, ProgressBar, cn } from '../components/ui'

export function Checklists() {
  const { checklistState, toggleChecklistItem, resetChecklist } = useProgress()
  const [active, setActive] = useState(checklists[0].id)
  const list = checklists.find((c) => c.id === active)!
  const state = checklistState[list.id] ?? []
  const done = state.filter(Boolean).length

  return (
    <div>
      <PageHeader eyebrow="Praxis" title="Checklisten" subtitle="Abhaken, was erledigt ist. Der Stand bleibt gespeichert, bis du die Liste zurücksetzt." />
      <div className="grid gap-4 md:grid-cols-[260px_1fr]">
        <div className="flex gap-2 overflow-x-auto md:flex-col">
          {checklists.map((c) => {
            const s = checklistState[c.id] ?? []
            const d = s.filter(Boolean).length
            return (
              <button key={c.id} onClick={() => setActive(c.id)} className={cn('glass shrink-0 rounded-2xl p-4 text-left cursor-pointer transition md:w-full', active === c.id ? 'border-aqua-400' : 'hover:border-strong')}>
                <div className="font-display font-bold">{c.title}</div>
                <div className="text-xs text-faint">{d}/{c.items.length}</div>
                <ProgressBar value={d / c.items.length} className="mt-2 h-1.5" />
              </button>
            )
          })}
        </div>
        <Card>
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-display text-2xl font-bold">{list.title}</h2>
              <p className="text-sm text-muted">{list.description}</p>
            </div>
            <Button size="sm" variant="ghost" onClick={() => resetChecklist(list.id)}><RotateCcw size={14} /> Reset</Button>
          </div>
          <ProgressBar value={done / list.items.length} className="my-4" gradient={done === list.items.length ? 'from-emerald-400 to-teal-500' : undefined} />
          {done === list.items.length && <div className="mb-4 rounded-2xl border border-emerald-400/40 bg-emerald-400/10 p-3 text-sm font-semibold text-emerald-500 animate-pop">✅ Alles erledigt – gute Tauchgänge!</div>}
          <div className="space-y-1.5">
            {list.items.map((it, i) => {
              const c = !!state[i]
              return (
                <button key={i} onClick={() => toggleChecklistItem(list.id, i, list.items.length)} className={cn('flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left text-sm transition cursor-pointer', c ? 'border-emerald-400/40 bg-emerald-400/10 text-muted line-through' : 'border-base hover:border-strong hover:bg-white/5')}>
                  {c ? <CheckSquare size={18} className="shrink-0 text-emerald-400" /> : <Square size={18} className="shrink-0 text-faint" />}
                  {it}
                </button>
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}
