import { useEffect, useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { signals } from '../data/signals'
import { Card, PageHeader, cn, inputClass } from '../components/ui'
import { useProgress } from '../store/useProgress'
import { achievements } from '../data/achievements'

const cats = ['Alle', 'Basis', 'Status', 'Notfall', 'Tiere', 'Zahlen'] as const

export function Signals() {
  const [cat, setCat] = useState<(typeof cats)[number]>('Alle')
  const [q, setQ] = useState('')
  const unlock = useProgress((s) => s.unlock)
  useEffect(() => { unlock('signals-visited', achievements.find((a) => a.id === 'signals-visited')?.xp ?? 0) }, [unlock])

  const list = useMemo(() => signals.filter((s) => (cat === 'Alle' || s.category === cat) && (q === '' || `${s.name} ${s.meaning}`.toLowerCase().includes(q.toLowerCase()))), [cat, q])

  return (
    <div>
      <PageHeader eyebrow="Kommunikation" title="Handzeichen" subtitle="Unter Wasser gibt es keine Worte. Diese Zeichen sind international – geh sie vor jedem Tauchgang mit deinem Buddy durch." />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
          <input className={cn(inputClass, 'pl-9')} placeholder="Suchen…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {cats.map((c) => <button key={c} onClick={() => setCat(c)} className={cn('shrink-0 rounded-xl border px-3 py-2 text-sm font-semibold cursor-pointer', cat === c ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong hover:bg-white/5')}>{c}</button>)}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {list.map((s, i) => (
          <Card key={s.id} hover className="animate-fade-up">
            <div className="flex items-start gap-4" style={{ animationDelay: `${i * 30}ms` }}>
              <div className={cn('flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-3xl', s.category === 'Notfall' ? 'bg-rose-400/15' : 'bg-aqua-400/15')}>{s.emoji}</div>
              <div className="min-w-0">
                <div className="text-[10px] font-bold uppercase tracking-widest text-faint">{s.category}</div>
                <h3 className="font-display font-bold leading-tight">{s.name}</h3>
                <p className="mt-1 text-sm text-muted">{s.meaning}</p>
              </div>
            </div>
            <div className="mt-3 rounded-xl bg-white/5 p-3 text-xs text-muted"><span className="font-bold text-inherit">So geht's: </span>{s.howTo}</div>
          </Card>
        ))}
      </div>
    </div>
  )
}
