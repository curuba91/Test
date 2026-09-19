import { achievements } from '../data/achievements'
import { useProgress, levelFromXp } from '../store/useProgress'
import { Card, PageHeader, Pill, ProgressBar, cn } from '../components/ui'

export function Achievements() {
  const { unlockedAchievements, xp } = useProgress()
  const lvl = levelFromXp(xp)
  const levels = ['Schnorchler', 'Open Water Diver', 'Advanced Diver', 'Rescue Diver', 'Divemaster', 'Instructor', 'Tiefsee‑Legende']
  return (
    <div>
      <PageHeader eyebrow="Fortschritt" title="Erfolge & Level" subtitle={`${unlockedAchievements.length} von ${achievements.length} Abzeichen freigeschaltet.`} />
      <Card className="mb-6 relative overflow-hidden">
        <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full bg-amber-400/20 blur-3xl" />
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-amber-300 to-orange-500 font-display text-2xl font-bold text-white shadow-lg">{lvl.level}</div>
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-wider text-faint">Aktuelles Level</div>
            <div className="font-display text-2xl font-bold">{lvl.name}</div>
            <div className="text-sm text-muted">{xp} XP{lvl.nextXp ? ` · noch ${lvl.nextXp - xp} XP bis ${lvl.next}` : ' · Maximales Level erreicht'}</div>
          </div>
        </div>
        <ProgressBar value={lvl.progress} className="mt-4" gradient="from-amber-300 to-orange-500" />
        <div className="mt-4 flex flex-wrap gap-2">
          {levels.map((l, i) => <Pill key={l} color={i + 1 <= lvl.level ? 'sun' : 'neutral'}>{i + 1} · {l}</Pill>)}
        </div>
      </Card>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {achievements.map((a, i) => {
          const done = unlockedAchievements.includes(a.id)
          return (
            <Card key={a.id} className={cn('flex items-center gap-4 animate-fade-up', !done && 'opacity-60 grayscale')} >
              <div className={cn('flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-3xl', done ? 'bg-gradient-to-br from-amber-300/30 to-orange-500/30 shadow-lg shadow-amber-500/10' : 'bg-slate-500/10')} style={{ animationDelay: `${i * 30}ms` }}>{a.icon}</div>
              <div className="min-w-0 flex-1">
                <div className="font-display font-bold">{a.title}</div>
                <div className="text-sm text-muted">{a.description}</div>
              </div>
              <Pill color={done ? 'sun' : 'neutral'}>+{a.xp}</Pill>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
