import { useEffect, useState } from 'react'
import { FlaskConical, Wind, Gauge, Timer, Scale, Waves } from 'lucide-react'
import { Card, Field, PageHeader, inputClass, cn, Pill } from '../components/ui'
import { mod, ead, bestMix, sacBarPerMin, rmv, gasDuration, absolutePressure, volumeAtDepth, NDL_TABLE, ndlForDepth, estimateWeight, round } from '../lib/dive-math'
import { useProgress } from '../store/useProgress'
import { achievements } from '../data/achievements'

type Tab = 'nitrox' | 'gas' | 'druck' | 'nullzeit' | 'blei'

const tabs: { id: Tab; label: string; icon: typeof FlaskConical }[] = [
  { id: 'nitrox', label: 'Nitrox', icon: FlaskConical },
  { id: 'gas', label: 'Luftverbrauch', icon: Wind },
  { id: 'druck', label: 'Druck & Volumen', icon: Gauge },
  { id: 'nullzeit', label: 'Nullzeit', icon: Timer },
  { id: 'blei', label: 'Blei', icon: Scale },
]

function Result({ label, value, unit, tone = 'aqua' }: { label: string; value: string | number; unit?: string; tone?: 'aqua' | 'coral' | 'kelp' }) {
  const tones = { aqua: 'from-aqua-400/15 to-indigo-500/15', coral: 'from-rose-400/15 to-orange-400/15', kelp: 'from-emerald-400/15 to-teal-400/15' }
  return (
    <div className={cn('rounded-2xl bg-gradient-to-br p-4', tones[tone])}>
      <div className="text-xs font-semibold uppercase tracking-wider text-faint">{label}</div>
      <div className="font-display text-2xl font-bold">{value}<span className="ml-1 text-sm font-semibold text-muted">{unit}</span></div>
    </div>
  )
}

function Num({ value, onChange, min, max, step = 1 }: { value: number; onChange: (n: number) => void; min?: number; max?: number; step?: number }) {
  return <input type="number" className={inputClass} value={value} min={min} max={max} step={step} onChange={(e) => onChange(Number(e.target.value))} />
}

function Nitrox() {
  const [o2, setO2] = useState(32)
  const [ppo2, setPpo2] = useState(1.4)
  const [depth, setDepth] = useState(25)
  const f = o2 / 100
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h3 className="font-display text-lg font-bold">Eingaben</h3>
        <div className="mt-4 space-y-4">
          <Field label={`Sauerstoffanteil: ${o2} %`}>
            <input type="range" min={21} max={100} value={o2} onChange={(e) => setO2(Number(e.target.value))} className="w-full" />
          </Field>
          <Field label="pO₂‑Grenze (bar)">
            <div className="flex gap-2">
              {[1.2, 1.3, 1.4, 1.5, 1.6].map((v) => (
                <button key={v} onClick={() => setPpo2(v)} className={cn('flex-1 rounded-xl border py-2 text-sm font-semibold cursor-pointer transition', ppo2 === v ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong hover:bg-white/5')}>{v}</button>
              ))}
            </div>
          </Field>
          <Field label="Geplante Tiefe (m)"><Num value={depth} onChange={setDepth} min={0} max={60} /></Field>
        </div>
      </Card>
      <Card>
        <h3 className="font-display text-lg font-bold">Ergebnis</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Result label={`MOD @ ${ppo2} bar`} value={round(mod(f, ppo2), 1)} unit="m" tone={depth > mod(f, ppo2) ? 'coral' : 'aqua'} />
          <Result label="MOD @ 1,6 bar (Notgrenze)" value={round(mod(f, 1.6), 1)} unit="m" />
          <Result label={`EAD in ${depth} m`} value={round(Math.max(0, ead(f, depth)), 1)} unit="m" tone="kelp" />
          <Result label={`pO₂ in ${depth} m`} value={round(f * absolutePressure(depth, 1), 2)} unit="bar" tone={f * absolutePressure(depth, 1) > ppo2 ? 'coral' : 'aqua'} />
          <Result label={`Best Mix für ${depth} m`} value={`EAN${Math.floor(bestMix(depth, ppo2) * 100)}`} />
          <Result label={`pN₂ in ${depth} m`} value={round((1 - f) * absolutePressure(depth, 1), 2)} unit="bar" />
        </div>
        {depth > mod(f, ppo2) && <p className="mt-3 text-sm font-semibold text-rose-400">⚠ Tiefe überschreitet die MOD dieses Gemischs!</p>}
      </Card>
    </div>
  )
}

function Gas() {
  const [start, setStart] = useState(200)
  const [end, setEnd] = useState(110)
  const [minutes, setMinutes] = useState(45)
  const [avgDepth, setAvgDepth] = useState(15)
  const [cyl, setCyl] = useState(12)
  const [planDepth, setPlanDepth] = useState(25)
  const [reserve, setReserve] = useState(50)
  const sac = sacBarPerMin(start, end, minutes, avgDepth)
  const r = rmv(sac, cyl)
  const dur = gasDuration(r, cyl, start, reserve, planDepth)
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h3 className="font-display text-lg font-bold">Letzter Tauchgang</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Startdruck (bar)"><Num value={start} onChange={setStart} /></Field>
          <Field label="Enddruck (bar)"><Num value={end} onChange={setEnd} /></Field>
          <Field label="Dauer (min)"><Num value={minutes} onChange={setMinutes} min={1} /></Field>
          <Field label="Ø Tiefe (m)"><Num value={avgDepth} onChange={setAvgDepth} min={0} /></Field>
          <Field label="Flasche (l)">
            <select className={inputClass} value={cyl} onChange={(e) => setCyl(Number(e.target.value))}>
              {[7, 10, 11.1, 12, 15, 18].map((v) => <option key={v} value={v}>{v} l</option>)}
            </select>
          </Field>
        </div>
        <h3 className="mt-6 font-display text-lg font-bold">Nächster Tauchgang planen</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Field label="Geplante Tiefe (m)"><Num value={planDepth} onChange={setPlanDepth} min={0} /></Field>
          <Field label="Reserve (bar)"><Num value={reserve} onChange={setReserve} min={0} /></Field>
        </div>
      </Card>
      <Card>
        <h3 className="font-display text-lg font-bold">Ergebnis</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Result label="SAC" value={isFinite(sac) ? round(sac, 2) : '–'} unit="bar/min" />
          <Result label="RMV / AMV" value={isFinite(r) ? round(r, 1) : '–'} unit="l/min" tone="kelp" />
          <Result label={`Verbrauch in ${planDepth} m`} value={isFinite(r) ? round(r * absolutePressure(planDepth, 1), 1) : '–'} unit="l/min" />
          <Result label={`Reichweite in ${planDepth} m`} value={isFinite(dur) && dur > 0 ? Math.floor(dur) : '–'} unit="min" tone={dur < 20 ? 'coral' : 'aqua'} />
        </div>
        <p className="mt-4 text-xs text-faint">Bezugswert: {r > 25 ? 'Hoher Verbrauch – Tarierung und Ruhe verbessern.' : r > 15 ? 'Normaler Verbrauch für Sporttaucher.' : 'Sehr sparsam – Profi‑Niveau.'} Die Reichweite gilt für konstante Tiefe ohne Aufstieg und wird durch die Nullzeit begrenzt ({ndlForDepth(planDepth) ?? '–'} min).</p>
      </Card>
    </div>
  )
}

function Druck() {
  const [depth, setDepth] = useState(20)
  const [vol, setVol] = useState(6)
  const [fresh, setFresh] = useState(false)
  const p = fresh ? 1 + depth / 10.3 : absolutePressure(depth, 1)
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h3 className="font-display text-lg font-bold">Eingaben</h3>
        <div className="mt-4 space-y-4">
          <Field label={`Tiefe: ${depth} m`}><input type="range" min={0} max={60} value={depth} onChange={(e) => setDepth(Number(e.target.value))} className="w-full" /></Field>
          <Field label="Volumen an der Oberfläche (l)"><Num value={vol} onChange={setVol} min={0} /></Field>
          <div className="flex gap-2">
            <button onClick={() => setFresh(false)} className={cn('flex-1 rounded-xl border py-2 text-sm font-semibold cursor-pointer', !fresh ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>Salzwasser</button>
            <button onClick={() => setFresh(true)} className={cn('flex-1 rounded-xl border py-2 text-sm font-semibold cursor-pointer', fresh ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>Süßwasser</button>
          </div>
        </div>
      </Card>
      <Card>
        <h3 className="font-display text-lg font-bold">Ergebnis</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Result label="Absoluter Druck" value={round(p, 2)} unit="bar" />
          <Result label="Volumen in der Tiefe" value={round(vol / p, 2)} unit="l" tone="kelp" />
          <Result label="Luftdichte" value={`${round(p, 1)}×`} />
          <Result label="pO₂ (Luft)" value={round(0.21 * p, 2)} unit="bar" tone={0.21 * p > 1.4 ? 'coral' : 'aqua'} />
          <Result label="pN₂ (Luft)" value={round(0.79 * p, 2)} unit="bar" tone={0.79 * p > 3.2 ? 'coral' : 'aqua'} />
          <Result label="Luftverbrauch relativ" value={`${round(p, 1)}×`} />
        </div>
        <div className="mt-4">
          <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-faint">Ballon‑Visualisierung</div>
          <div className="flex h-24 items-end gap-3 rounded-2xl border border-base p-3">
            {[0, 10, 20, 30, 40].map((d) => {
              const v = volumeAtDepth(1, d)
              return (
                <div key={d} className="flex flex-1 flex-col items-center gap-1">
                  <div className="rounded-full bg-gradient-to-br from-aqua-300 to-blue-500 transition-all" style={{ width: `${18 + v * 40}px`, height: `${18 + v * 40}px`, opacity: d === depth ? 1 : 0.5 }} />
                  <span className="text-[10px] text-faint">{d} m</span>
                </div>
              )
            })}
          </div>
        </div>
      </Card>
    </div>
  )
}

function Nullzeit() {
  const [depth, setDepth] = useState(18)
  const [time, setTime] = useState(40)
  const ndl = ndlForDepth(depth)
  const pct = ndl ? time / ndl : 1
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h3 className="font-display text-lg font-bold">Tauchgang prüfen</h3>
        <div className="mt-4 space-y-4">
          <Field label={`Max. Tiefe: ${depth} m`}><input type="range" min={10} max={40} value={depth} onChange={(e) => setDepth(Number(e.target.value))} className="w-full" /></Field>
          <Field label="Geplante Grundzeit (min)"><Num value={time} onChange={setTime} min={1} /></Field>
        </div>
        <div className="mt-5">
          <div className="mb-1 flex justify-between text-xs font-semibold"><span className="text-faint">Nullzeit‑Auslastung</span><span className={pct > 1 ? 'text-rose-400' : pct > 0.8 ? 'text-amber-400' : 'text-emerald-400'}>{Math.round(pct * 100)} %</span></div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-500/15">
            <div className={cn('h-full rounded-full transition-all', pct > 1 ? 'bg-rose-500' : pct > 0.8 ? 'bg-amber-400' : 'bg-emerald-400')} style={{ width: `${Math.min(100, pct * 100)}%` }} />
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Result label={`Nullzeit bei ${depth} m`} value={ndl ?? '–'} unit="min" />
          <Result label="Sicherheitsstopp" value="3" unit="min @ 5 m" tone="kelp" />
        </div>
        {pct > 1 && <p className="mt-3 text-sm font-semibold text-rose-400">⚠ Nullzeit überschritten – Dekompressionspflicht. Plane kürzer oder flacher.</p>}
        {pct > 0.8 && pct <= 1 && <p className="mt-3 text-sm font-semibold text-amber-400">Knapp an der Grenze – plane mit Puffer.</p>}
      </Card>
      <Card>
        <h3 className="font-display text-lg font-bold">Nullzeit‑Tabelle (Luft)</h3>
        <div className="mt-3 overflow-hidden rounded-2xl border border-base">
          <table className="w-full text-sm">
            <thead className="bg-white/5"><tr><th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-faint">Tiefe</th><th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-faint">Nullzeit</th><th className="px-4 py-2 text-left text-xs uppercase tracking-wider text-faint">Druck</th></tr></thead>
            <tbody>
              {Object.entries(NDL_TABLE).map(([d, n]) => (
                <tr key={d} className={cn('border-t border-base', Number(d) === (Object.keys(NDL_TABLE).map(Number).find((x) => depth <= x) ?? 40) && 'bg-aqua-400/10 font-semibold')}>
                  <td className="px-4 py-2">{d} m</td><td className="px-4 py-2">{n} min</td><td className="px-4 py-2 text-muted">{1 + Number(d) / 10} bar</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-faint">Vereinfachte Lehrwerte für Erst‑Tauchgänge. Für echte Planung gilt ausschließlich dein Tauchcomputer bzw. eine offizielle Tabelle.</p>
      </Card>
    </div>
  )
}

function Blei() {
  const [kg, setKg] = useState(75)
  const [suit, setSuit] = useState<'none' | 'shorty' | '3mm' | '5mm' | '7mm' | 'dry'>('5mm')
  const [salt, setSalt] = useState(true)
  const [alu, setAlu] = useState(false)
  const w = estimateWeight(kg, suit, salt, alu)
  const suits: { id: typeof suit; label: string }[] = [{ id: 'none', label: 'Kein Anzug' }, { id: 'shorty', label: 'Shorty' }, { id: '3mm', label: '3 mm' }, { id: '5mm', label: '5 mm' }, { id: '7mm', label: '7 mm' }, { id: 'dry', label: 'Trocken' }]
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <h3 className="font-display text-lg font-bold">Eingaben</h3>
        <div className="mt-4 space-y-4">
          <Field label={`Körpergewicht: ${kg} kg`}><input type="range" min={40} max={140} value={kg} onChange={(e) => setKg(Number(e.target.value))} className="w-full" /></Field>
          <Field label="Anzug">
            <div className="grid grid-cols-3 gap-2">
              {suits.map((s) => <button key={s.id} onClick={() => setSuit(s.id)} className={cn('rounded-xl border py-2 text-sm font-semibold cursor-pointer', suit === s.id ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong hover:bg-white/5')}>{s.label}</button>)}
            </div>
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => setSalt(!salt)} className={cn('rounded-xl border py-2 text-sm font-semibold cursor-pointer', salt ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>{salt ? 'Salzwasser' : 'Süßwasser'}</button>
            <button onClick={() => setAlu(!alu)} className={cn('rounded-xl border py-2 text-sm font-semibold cursor-pointer', alu ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}>{alu ? 'Alu‑Flasche' : 'Stahl‑Flasche'}</button>
          </div>
        </div>
      </Card>
      <Card>
        <h3 className="font-display text-lg font-bold">Schätzung</h3>
        <div className="mt-4 grid grid-cols-2 gap-3">
          <Result label="Startwert Blei" value={w} unit="kg" />
          <Result label="Spanne" value={`${Math.max(0, w - 2)}–${w + 2}`} unit="kg" tone="kelp" />
        </div>
        <p className="mt-4 text-sm text-muted">Das ist nur ein Startwert. Der echte Test: Mit 50 bar, leerem Jacket und normaler Atmung auf Augenhöhe schweben, beim Ausatmen langsam sinken. Passe in 0,5‑kg‑Schritten an und notiere das Ergebnis im Logbuch.</p>
      </Card>
    </div>
  )
}

export function Tools() {
  const [tab, setTab] = useState<Tab>('nitrox')
  const unlock = useProgress((s) => s.unlock)
  useEffect(() => { unlock('tools-used', achievements.find((a) => a.id === 'tools-used')?.xp ?? 0) }, [unlock])
  return (
    <div>
      <PageHeader eyebrow="Werkzeuge" title="Tauchrechner" subtitle="Nitrox‑MOD, Luftverbrauch, Druck, Nullzeit und Blei – alle Formeln aus den Kursen zum Ausprobieren." action={<Pill color="sun"><Waves size={12} /> Nur zu Lernzwecken</Pill>} />
      <div className="mb-6 flex gap-2 overflow-x-auto pb-1">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={cn('flex shrink-0 items-center gap-2 rounded-2xl border px-4 py-2.5 text-sm font-semibold transition cursor-pointer', tab === t.id ? 'border-aqua-400 bg-gradient-to-r from-aqua-400/20 to-indigo-500/20' : 'border-base text-muted hover:border-strong')}>
            <t.icon size={16} /> {t.label}
          </button>
        ))}
      </div>
      <div className="animate-fade-up" key={tab}>
        {tab === 'nitrox' && <Nitrox />}
        {tab === 'gas' && <Gas />}
        {tab === 'druck' && <Druck />}
        {tab === 'nullzeit' && <Nullzeit />}
        {tab === 'blei' && <Blei />}
      </div>
    </div>
  )
}
