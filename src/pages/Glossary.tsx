import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { glossary } from '../data/glossary'
import { PageHeader, Pill, cn, inputClass } from '../components/ui'

export function Glossary() {
  const [q, setQ] = useState('')
  const [tag, setTag] = useState('Alle')
  const tags = ['Alle', ...Array.from(new Set(glossary.map((g) => g.tag)))]
  const list = useMemo(() => glossary.filter((g) => (tag === 'Alle' || g.tag === tag) && (q === '' || `${g.term} ${g.definition}`.toLowerCase().includes(q.toLowerCase()))).sort((a, b) => a.term.localeCompare(b.term, 'de')), [q, tag])
  return (
    <div>
      <PageHeader eyebrow="Nachschlagen" title="Glossar" subtitle={`${glossary.length} Begriffe aus Physik, Medizin, Ausrüstung und Praxis.`} />
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
          <input className={cn(inputClass, 'pl-9')} placeholder="Begriff suchen…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {tags.map((t) => <button key={t} onClick={() => setTag(t)} className={cn('shrink-0 rounded-xl border px-3 py-2 text-sm font-semibold cursor-pointer', tag === t ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>{t}</button>)}
        </div>
      </div>
      <div className="glass divide-y divide-[var(--border)] rounded-3xl">
        {list.map((g) => (
          <div key={g.term} className="flex flex-col gap-1 p-4 sm:flex-row sm:items-start sm:gap-6 md:p-5">
            <div className="w-full shrink-0 font-display font-bold sm:w-44">{g.term}</div>
            <div className="flex-1 text-sm text-muted">{g.definition}</div>
            <Pill color="neutral" className="self-start">{g.tag}</Pill>
          </div>
        ))}
        {list.length === 0 && <div className="p-8 text-center text-muted">Kein Treffer.</div>}
      </div>
    </div>
  )
}
