import type { ContentBlock } from '../data/types'
import { AlertTriangle, Lightbulb, Sparkles } from 'lucide-react'
import { Fragment } from 'react'

/** Renders **bold** inline markup. */
export function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {parts.map((p, i) =>
        p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <Fragment key={i}>{p}</Fragment>,
      )}
    </>
  )
}

function Callout({ tone, title, text }: { tone: 'fact' | 'warning' | 'tip'; title?: string; text: string }) {
  const tones = {
    fact: { cls: 'border-cyan-400/40 bg-cyan-400/10', icon: <Sparkles size={18} className="text-cyan-400" />, def: 'Wusstest du?' },
    warning: { cls: 'border-rose-400/40 bg-rose-400/10', icon: <AlertTriangle size={18} className="text-rose-400" />, def: 'Achtung' },
    tip: { cls: 'border-emerald-400/40 bg-emerald-400/10', icon: <Lightbulb size={18} className="text-emerald-400" />, def: 'Profi‑Tipp' },
  }
  const t = tones[tone]
  return (
    <div className={`my-5 flex gap-3 rounded-2xl border p-4 ${t.cls}`}>
      <div className="mt-0.5 shrink-0">{t.icon}</div>
      <div>
        <div className="mb-1 text-sm font-bold">{title ?? t.def}</div>
        <div className="text-sm leading-relaxed text-muted"><Inline text={text} /></div>
      </div>
    </div>
  )
}

export function ContentRenderer({ blocks }: { blocks: ContentBlock[] }) {
  return (
    <div className="prose-dive">
      {blocks.map((b, i) => {
        switch (b.type) {
          case 'p':
            return <p key={i}><Inline text={b.text} /></p>
          case 'h':
            return <h3 key={i}>{b.text}</h3>
          case 'list':
            return (
              <ul key={i}>
                {b.items.map((it, j) => <li key={j}><Inline text={it} /></li>)}
              </ul>
            )
          case 'steps':
            return (
              <ol key={i} className="my-4 space-y-3">
                {b.items.map((it, j) => (
                  <li key={j} className="flex gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-aqua-400 to-indigo-500 text-xs font-bold text-white">{j + 1}</span>
                    <span className="pt-0.5 text-sm leading-relaxed text-muted"><Inline text={it} /></span>
                  </li>
                ))}
              </ol>
            )
          case 'fact':
            return <Callout key={i} tone="fact" title={b.title} text={b.text} />
          case 'warning':
            return <Callout key={i} tone="warning" title={b.title} text={b.text} />
          case 'tip':
            return <Callout key={i} tone="tip" title={b.title} text={b.text} />
          case 'formula':
            return (
              <div key={i} className="my-5 rounded-2xl border border-strong bg-gradient-to-br from-indigo-500/10 to-cyan-400/10 p-4">
                <div className="text-xs font-bold uppercase tracking-wider text-aqua-500">{b.label}</div>
                <div className="my-2 font-display text-lg font-bold md:text-xl">{b.formula}</div>
                {b.note && <div className="text-sm text-muted">{b.note}</div>}
              </div>
            )
          case 'table':
            return (
              <div key={i} className="my-5 overflow-x-auto rounded-2xl border border-base">
                <table className="w-full min-w-[420px] text-left text-sm">
                  <thead className="bg-white/5">
                    <tr>{b.headers.map((h, j) => <th key={j} className="px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-faint">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {b.rows.map((r, j) => (
                      <tr key={j} className="border-t border-base">
                        {r.map((c, k) => <td key={k} className={`px-4 py-2.5 ${k === 0 ? 'font-semibold' : 'text-muted'}`}>{c}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
        }
      })}
    </div>
  )
}
