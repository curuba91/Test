import { useMemo, useState } from 'react'
import { Plus, Trash2, MapPin, Clock, ArrowDown, Thermometer, Eye, Users, Star, X, Download } from 'lucide-react'
import { useProgress, type DiveLogEntry } from '../store/useProgress'
import { Button, Card, Empty, Field, PageHeader, Stat, inputClass, cn } from '../components/ui'
import { sacBarPerMin, round } from '../lib/dive-math'

const blank = (): Omit<DiveLogEntry, 'id'> => ({
  date: new Date().toISOString().slice(0, 10),
  site: '',
  location: '',
  maxDepth: 18,
  duration: 45,
  waterTemp: 24,
  visibility: 15,
  buddy: '',
  startBar: 200,
  endBar: 60,
  notes: '',
  rating: 4,
})

export function DiveLog() {
  const { diveLog, addDive, removeDive } = useProgress()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(blank())
  const [confirm, setConfirm] = useState<string | null>(null)

  const stats = useMemo(() => {
    const total = diveLog.length
    const minutes = diveLog.reduce((a, d) => a + d.duration, 0)
    const max = diveLog.reduce((a, d) => Math.max(a, d.maxDepth), 0)
    const avgDepth = total ? diveLog.reduce((a, d) => a + d.maxDepth, 0) / total : 0
    return { total, minutes, max, avgDepth }
  }, [diveLog])

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) => setForm((f) => ({ ...f, [k]: v }))

  const submit = () => {
    if (!form.site.trim()) return
    addDive({ ...form, id: crypto.randomUUID() })
    setForm(blank())
    setOpen(false)
  }

  const exportCsv = () => {
    const header = ['Datum', 'Tauchplatz', 'Ort', 'Max Tiefe (m)', 'Dauer (min)', 'Wassertemp', 'Sicht (m)', 'Buddy', 'Start bar', 'Ende bar', 'Bewertung', 'Notizen']
    const rows = diveLog.map((d) => [d.date, d.site, d.location, d.maxDepth, d.duration, d.waterTemp ?? '', d.visibility ?? '', d.buddy ?? '', d.startBar ?? '', d.endBar ?? '', d.rating, (d.notes ?? '').replace(/\n/g, ' ')])
    const csv = [header, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'logbuch.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  return (
    <div>
      <PageHeader
        eyebrow="Logbuch"
        title="Deine Tauchgänge"
        subtitle="Jeder Eintrag bringt 40 XP. Deine Daten bleiben lokal auf diesem Gerät."
        action={
          <div className="flex gap-2">
            {diveLog.length > 0 && <Button variant="outline" onClick={exportCsv}><Download size={16} /> CSV</Button>}
            <Button onClick={() => setOpen(true)}><Plus size={18} /> Tauchgang</Button>
          </div>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Tauchgänge" value={stats.total} />
        <Stat label="Unter Wasser" value={`${Math.floor(stats.minutes / 60)} h ${stats.minutes % 60} min`} />
        <Stat label="Max. Tiefe" value={`${stats.max} m`} />
        <Stat label="Ø Tiefe" value={`${round(stats.avgDepth, 1)} m`} />
      </div>

      {diveLog.length === 0 ? (
        <Empty icon="📓" title="Noch kein Eintrag" text="Trage deinen ersten Tauchgang ein – Tiefe, Zeit, Luftverbrauch und Notizen." action={<Button onClick={() => setOpen(true)}><Plus size={18} /> Ersten Tauchgang loggen</Button>} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {diveLog.map((d, i) => {
            const sac = d.startBar && d.endBar && d.duration ? sacBarPerMin(d.startBar, d.endBar, d.duration, d.maxDepth * 0.6) : null
            return (
              <Card key={d.id} className="relative animate-fade-up" >
                <div className="flex items-start justify-between gap-3" style={{ animationDelay: `${i * 40}ms` }}>
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wider text-faint">#{diveLog.length - i} · {new Date(d.date).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })}</div>
                    <h3 className="font-display text-lg font-bold">{d.site}</h3>
                    {d.location && <div className="flex items-center gap-1 text-sm text-muted"><MapPin size={13} /> {d.location}</div>}
                  </div>
                  <div className="flex items-center gap-0.5 text-amber-400">{Array.from({ length: 5 }).map((_, k) => <Star key={k} size={14} fill={k < d.rating ? 'currentColor' : 'none'} />)}</div>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2 text-sm sm:grid-cols-4">
                  <div className="flex items-center gap-1.5"><ArrowDown size={14} className="text-aqua-400" /> {d.maxDepth} m</div>
                  <div className="flex items-center gap-1.5"><Clock size={14} className="text-aqua-400" /> {d.duration} min</div>
                  {d.waterTemp != null && <div className="flex items-center gap-1.5"><Thermometer size={14} className="text-aqua-400" /> {d.waterTemp} °C</div>}
                  {d.visibility != null && <div className="flex items-center gap-1.5"><Eye size={14} className="text-aqua-400" /> {d.visibility} m</div>}
                  {d.buddy && <div className="col-span-2 flex items-center gap-1.5 truncate"><Users size={14} className="text-aqua-400" /> {d.buddy}</div>}
                  {d.startBar != null && d.endBar != null && <div className="col-span-2 text-muted">{d.startBar} → {d.endBar} bar{sac ? ` · SAC ${round(sac, 2)} bar/min` : ''}</div>}
                </div>
                {d.notes && <p className="mt-3 rounded-xl bg-white/5 p-3 text-sm text-muted">{d.notes}</p>}
                <div className="mt-3 flex justify-end">
                  {confirm === d.id ? (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-muted">Wirklich löschen?</span>
                      <Button size="sm" variant="danger" onClick={() => { removeDive(d.id); setConfirm(null) }}>Ja</Button>
                      <Button size="sm" variant="ghost" onClick={() => setConfirm(null)}>Nein</Button>
                    </div>
                  ) : (
                    <button onClick={() => setConfirm(d.id)} className="flex items-center gap-1 text-xs text-faint hover:text-rose-400 cursor-pointer"><Trash2 size={14} /> Löschen</button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 backdrop-blur-sm sm:items-center sm:p-4" onClick={() => setOpen(false)}>
          <div className="glass-strong max-h-[92dvh] w-full max-w-2xl overflow-y-auto rounded-t-3xl p-5 animate-fade-up sm:rounded-3xl md:p-7" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="font-display text-2xl font-bold">Neuer Tauchgang</h2>
              <button onClick={() => setOpen(false)} className="rounded-xl p-2 hover:bg-white/5 cursor-pointer"><X size={20} /></button>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3">
              <Field label="Datum"><input type="date" className={inputClass} value={form.date} onChange={(e) => set('date', e.target.value)} /></Field>
              <div className="col-span-2 md:col-span-2"><Field label="Tauchplatz *"><input className={inputClass} placeholder="z. B. Blue Hole" value={form.site} onChange={(e) => set('site', e.target.value)} /></Field></div>
              <div className="col-span-2 md:col-span-3"><Field label="Ort / Land"><input className={inputClass} placeholder="Dahab, Ägypten" value={form.location} onChange={(e) => set('location', e.target.value)} /></Field></div>
              <Field label="Max. Tiefe (m)"><input type="number" className={inputClass} value={form.maxDepth} onChange={(e) => set('maxDepth', Number(e.target.value))} /></Field>
              <Field label="Dauer (min)"><input type="number" className={inputClass} value={form.duration} onChange={(e) => set('duration', Number(e.target.value))} /></Field>
              <Field label="Wasser (°C)"><input type="number" className={inputClass} value={form.waterTemp} onChange={(e) => set('waterTemp', Number(e.target.value))} /></Field>
              <Field label="Sicht (m)"><input type="number" className={inputClass} value={form.visibility} onChange={(e) => set('visibility', Number(e.target.value))} /></Field>
              <Field label="Start (bar)"><input type="number" className={inputClass} value={form.startBar} onChange={(e) => set('startBar', Number(e.target.value))} /></Field>
              <Field label="Ende (bar)"><input type="number" className={inputClass} value={form.endBar} onChange={(e) => set('endBar', Number(e.target.value))} /></Field>
              <div className="col-span-2 md:col-span-2"><Field label="Buddy"><input className={inputClass} value={form.buddy} onChange={(e) => set('buddy', e.target.value)} /></Field></div>
              <Field label="Bewertung">
                <div className="flex gap-1 pt-2 text-amber-400">
                  {Array.from({ length: 5 }).map((_, k) => <button key={k} onClick={() => set('rating', k + 1)} className="cursor-pointer"><Star size={22} fill={k < form.rating ? 'currentColor' : 'none'} /></button>)}
                </div>
              </Field>
              <div className="col-span-2 md:col-span-3"><Field label="Notizen"><textarea className={cn(inputClass, 'min-h-20')} placeholder="Was hast du gesehen? Was lief gut, was nicht?" value={form.notes} onChange={(e) => set('notes', e.target.value)} /></Field></div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setOpen(false)}>Abbrechen</Button>
              <Button onClick={submit} disabled={!form.site.trim()}>Speichern</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
