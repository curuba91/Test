import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen, Flame, Trophy, Zap, Calculator, Layers, BookA, Hand } from 'lucide-react'
import { useProgress, levelFromXp } from '../store/useProgress'
import { modules, allLessons } from '../data/modules'
import { achievements } from '../data/achievements'
import { Card, CardLink, Button, ProgressBar, ProgressRing, Pill, Stat } from '../components/ui'
import { ModuleIcon } from '../components/Icon'

export function Dashboard() {
  const { completedLessons, quizResults, xp, streak, unlockedAchievements, diveLog, name } = useProgress()
  const lvl = levelFromXp(xp)
  const totalLessons = allLessons.length
  const overall = completedLessons.length / totalLessons

  // Next lesson: first incomplete lesson in module order
  const next = allLessons.find((l) => !completedLessons.includes(l.id))
  const nextModule = next ? modules.find((m) => m.id === next.moduleId) : undefined

  const recentAchievements = achievements.filter((a) => unlockedAchievements.includes(a.id)).slice(-3)
  const hour = new Date().getHours()
  const greeting = hour < 11 ? 'Guten Morgen' : hour < 18 ? 'Hallo' : 'Guten Abend'

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-[2rem] border border-base bg-gradient-to-br from-ocean-800 via-ocean-900 to-ocean-950 p-6 text-white shadow-2xl shadow-cyan-900/30 md:p-10 animate-fade-up">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-aqua-400/25 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-72 w-72 rounded-full bg-indigo-500/25 blur-3xl" />
        <div className="relative grid gap-8 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <Pill color="aqua" className="mb-4">Level {lvl.level} · {lvl.name}</Pill>
            <h1 className="font-display text-3xl font-bold leading-tight md:text-5xl">
              {greeting}{name ? `, ${name}` : ''}.<br />
              <span className="gradient-text">Bereit für die Tiefe?</span>
            </h1>
            <p className="mt-3 max-w-xl text-white/70">
              {next
                ? `Als Nächstes: „${next.title}“ im Modul ${nextModule?.title}. Ca. ${next.minutes} Minuten.`
                : 'Du hast alle Lektionen abgeschlossen. Zeit für die Abschlussprüfung!'}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {next && nextModule ? (
                <Link to={`/kurse/${nextModule.id}/${next.id}`}><Button size="lg">Weiterlernen <ArrowRight size={18} /></Button></Link>
              ) : (
                <Link to="/pruefung"><Button size="lg">Zur Prüfung <ArrowRight size={18} /></Button></Link>
              )}
              <Link to="/kurse"><Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10">Alle Kurse</Button></Link>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <ProgressRing value={overall} size={150} stroke={12} gradientId="hero-ring">
              <div className="text-center">
                <div className="font-display text-3xl font-bold">{Math.round(overall * 100)}%</div>
                <div className="text-[11px] uppercase tracking-widest text-white/60">Gesamt</div>
              </div>
            </ProgressRing>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4">
        <Stat label="Lektionen" value={`${completedLessons.length}/${totalLessons}`} icon={<BookOpen size={22} />} />
        <Stat label="Quizze" value={quizResults.length} sub={quizResults.length ? `Ø ${Math.round((quizResults.reduce((a, r) => a + r.score / r.total, 0) / quizResults.length) * 100)} %` : 'Noch keins'} icon={<Zap size={22} />} />
        <Stat label="Streak" value={`${streak} Tage`} icon={<Flame size={22} />} />
        <Stat label="Tauchgänge" value={diveLog.length} sub="im Logbuch" icon={<BookA size={22} />} />
      </section>

      {/* Modules */}
      <section>
        <div className="mb-4 flex items-end justify-between">
          <h2 className="font-display text-xl font-bold md:text-2xl">Deine Module</h2>
          <Link to="/kurse" className="text-sm font-semibold text-aqua-500 no-underline hover:underline">Alle ansehen</Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 md:gap-4">
          {modules.slice(0, 6).map((m, i) => {
            const done = m.lessons.filter((l) => completedLessons.includes(l.id)).length
            return (
              <CardLink key={m.id} to={`/kurse/${m.id}`} className="animate-fade-up" >
                <div className="flex items-start justify-between" style={{ animationDelay: `${i * 60}ms` }}>
                  <div className={`flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${m.accent} text-white shadow-lg`}>
                    <ModuleIcon name={m.icon} size={22} />
                  </div>
                  <Pill color="neutral">{m.level}</Pill>
                </div>
                <div className="mt-4 font-display text-lg font-bold">{m.title}</div>
                <div className="text-sm text-muted">{m.subtitle}</div>
                <div className="mt-4 flex items-center gap-3">
                  <ProgressBar value={done / m.lessons.length} gradient={m.accent} />
                  <span className="shrink-0 text-xs font-semibold text-faint">{done}/{m.lessons.length}</span>
                </div>
              </CardLink>
            )
          })}
        </div>
      </section>

      {/* Quick tools + achievements */}
      <section className="grid gap-4 md:grid-cols-2">
        <Card>
          <h3 className="font-display text-lg font-bold">Schnellzugriff</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              { to: '/rechner', icon: Calculator, label: 'Rechner', sub: 'MOD, SAC, Nullzeit' },
              { to: '/karteikarten', icon: Layers, label: 'Karteikarten', sub: 'Schnell wiederholen' },
              { to: '/handzeichen', icon: Hand, label: 'Handzeichen', sub: '28 Signale' },
              { to: '/logbuch', icon: BookA, label: 'Logbuch', sub: 'Tauchgang eintragen' },
            ].map((t) => (
              <Link key={t.to} to={t.to} className="flex items-center gap-3 rounded-2xl border border-base p-3 no-underline text-inherit transition hover:border-strong hover:bg-white/5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-aqua-400/15 text-aqua-500"><t.icon size={18} /></div>
                <div className="min-w-0">
                  <div className="text-sm font-bold">{t.label}</div>
                  <div className="truncate text-xs text-faint">{t.sub}</div>
                </div>
              </Link>
            ))}
          </div>
        </Card>
        <Card>
          <div className="flex items-center justify-between">
            <h3 className="font-display text-lg font-bold">Erfolge</h3>
            <Link to="/erfolge" className="text-sm font-semibold text-aqua-500 no-underline hover:underline">{unlockedAchievements.length}/{achievements.length}</Link>
          </div>
          {recentAchievements.length === 0 ? (
            <div className="mt-4 flex items-center gap-3 rounded-2xl border border-dashed border-strong p-4 text-sm text-muted">
              <Trophy size={20} className="text-amber-400" /> Schließe deine erste Lektion ab, um ein Abzeichen zu verdienen.
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {recentAchievements.map((a) => (
                <div key={a.id} className="flex items-center gap-3 rounded-2xl border border-base p-3">
                  <div className="text-2xl">{a.icon}</div>
                  <div>
                    <div className="text-sm font-bold">{a.title}</div>
                    <div className="text-xs text-faint">{a.description}</div>
                  </div>
                  <Pill color="sun" className="ml-auto">+{a.xp} XP</Pill>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>
    </div>
  )
}
