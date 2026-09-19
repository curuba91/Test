import { useState } from 'react'
import { Moon, Sun, Trash2, Download, Upload } from 'lucide-react'
import { useProgress } from '../store/useProgress'
import { Button, Card, Field, PageHeader, inputClass, cn } from '../components/ui'

export function Settings() {
  const s = useProgress()
  const [confirm, setConfirm] = useState(false)
  const [msg, setMsg] = useState('')

  const exportData = () => {
    const raw = localStorage.getItem('deeplearn-progress-v1') ?? '{}'
    const blob = new Blob([raw], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `deeplearn-backup-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const importData = (file: File) => {
    file.text().then((t) => {
      try {
        const parsed = JSON.parse(t)
        if (!parsed?.state) throw new Error('bad')
        localStorage.setItem('deeplearn-progress-v1', t)
        setMsg('Import erfolgreich – Seite wird neu geladen.')
        setTimeout(() => location.reload(), 800)
      } catch {
        setMsg('Datei ungültig.')
      }
    })
  }

  return (
    <div className="mx-auto max-w-2xl">
      <PageHeader eyebrow="Profil" title="Einstellungen" />
      <div className="space-y-4">
        <Card>
          <h3 className="font-display text-lg font-bold">Profil</h3>
          <div className="mt-3"><Field label="Dein Name" hint="Wird nur auf diesem Gerät gespeichert."><input className={inputClass} value={s.name} onChange={(e) => s.setName(e.target.value)} placeholder="z. B. Alex" /></Field></div>
        </Card>
        <Card>
          <h3 className="font-display text-lg font-bold">Darstellung</h3>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button onClick={() => s.setTheme('dark')} className={cn('flex items-center justify-center gap-2 rounded-2xl border py-3 font-semibold cursor-pointer', s.theme === 'dark' ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}><Moon size={16} /> Tiefsee (dunkel)</button>
            <button onClick={() => s.setTheme('light')} className={cn('flex items-center justify-center gap-2 rounded-2xl border py-3 font-semibold cursor-pointer', s.theme === 'light' ? 'border-aqua-400 bg-aqua-400/15' : 'border-strong')}><Sun size={16} /> Lagune (hell)</button>
          </div>
        </Card>
        <Card>
          <h3 className="font-display text-lg font-bold">Daten</h3>
          <p className="mt-1 text-sm text-muted">Alle Fortschritte, Quiz‑Ergebnisse und Logbucheinträge liegen ausschließlich im Browser dieses Geräts. Sichere sie regelmäßig.</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" onClick={exportData}><Download size={16} /> Backup exportieren</Button>
            <label className="inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-strong px-5 py-2.5 text-sm font-semibold hover:bg-white/5 md:text-base">
              <Upload size={16} /> Backup importieren
              <input type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files?.[0] && importData(e.target.files[0])} />
            </label>
          </div>
          {msg && <p className="mt-3 text-sm font-semibold text-aqua-500">{msg}</p>}
        </Card>
        <Card className="border-rose-400/30">
          <h3 className="font-display text-lg font-bold text-rose-400">Gefahrenzone</h3>
          <p className="mt-1 text-sm text-muted">Setzt Lektionen, Quizze, XP, Erfolge und das Logbuch zurück. Nicht rückgängig zu machen.</p>
          <div className="mt-4">
            {confirm ? (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold">Wirklich alles löschen?</span>
                <Button variant="danger" size="sm" onClick={() => { s.resetAll(); setConfirm(false) }}>Ja, löschen</Button>
                <Button variant="ghost" size="sm" onClick={() => setConfirm(false)}>Abbrechen</Button>
              </div>
            ) : (
              <Button variant="outline" onClick={() => setConfirm(true)} className="border-rose-400/40 text-rose-400 hover:bg-rose-400/10"><Trash2 size={16} /> Fortschritt zurücksetzen</Button>
            )}
          </div>
        </Card>
        <p className="pt-4 text-center text-xs text-faint">DeepLearn ist eine Lernhilfe und ersetzt keine zertifizierte Tauchausbildung. Alle Tabellen und Rechner dienen ausschließlich Lernzwecken.</p>
      </div>
    </div>
  )
}
