import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { LayoutDashboard, GraduationCap, Calculator, BookOpenCheck, Layers, Hand, BookA, Trophy, ClipboardCheck, BookMarked, Settings, Moon, Sun, Flame, Menu, X, Waves } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useProgress, levelFromXp } from '../store/useProgress'
import { cn } from './ui'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/kurse', label: 'Kurse', icon: GraduationCap },
  { to: '/pruefung', label: 'Prüfung', icon: BookOpenCheck },
  { to: '/karteikarten', label: 'Karteikarten', icon: Layers },
  { to: '/rechner', label: 'Rechner', icon: Calculator },
  { to: '/logbuch', label: 'Logbuch', icon: BookA },
  { to: '/handzeichen', label: 'Handzeichen', icon: Hand },
  { to: '/checklisten', label: 'Checklisten', icon: ClipboardCheck },
  { to: '/glossar', label: 'Glossar', icon: BookMarked },
  { to: '/erfolge', label: 'Erfolge', icon: Trophy },
  { to: '/einstellungen', label: 'Einstellungen', icon: Settings },
]

const mobileNav = nav.filter((n) => ['/', '/kurse', '/rechner', '/logbuch', '/erfolge'].includes(n.to))

function Bubbles() {
  const bubbles = Array.from({ length: 14 }, (_, i) => ({
    left: `${(i * 37) % 100}%`,
    size: 6 + ((i * 13) % 22),
    dur: `${12 + ((i * 7) % 12)}s`,
    delay: `${-((i * 3) % 12)}s`,
  }))
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--glow-a),transparent_55%),radial-gradient(ellipse_at_bottom_right,var(--glow-b),transparent_55%)]" />
      {bubbles.map((b, i) => (
        <span key={i} className="bubble" style={{ left: b.left, width: b.size, height: b.size, ['--dur' as string]: b.dur, ['--delay' as string]: b.delay }} />
      ))}
    </div>
  )
}

export function Layout() {
  const theme = useProgress((s) => s.theme)
  const setTheme = useProgress((s) => s.setTheme)
  const xp = useProgress((s) => s.xp)
  const streak = useProgress((s) => s.streak)
  const name = useProgress((s) => s.name)
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const lvl = levelFromXp(xp)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [location.pathname])

  const close = () => setOpen(false)

  const Sidebar = (
    <aside className="flex h-full flex-col gap-2 p-4">
      <NavLink to="/" onClick={close} className="mb-4 flex items-center gap-3 px-2 no-underline text-inherit">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-aqua-400 to-indigo-500 shadow-lg shadow-cyan-500/30">
          <Waves />
        </div>
        <div>
          <div className="font-display text-lg font-bold leading-none">DeepLearn</div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-faint">Dive Academy</div>
        </div>
      </NavLink>
      {nav.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          onClick={close}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-semibold no-underline transition-all',
              isActive ? 'bg-gradient-to-r from-aqua-400/20 to-indigo-500/20 text-inherit shadow-inner' : 'text-muted hover:bg-white/5 hover:text-inherit',
            )
          }
        >
          <n.icon size={18} />
          {n.label}
        </NavLink>
      ))}
      <div className="mt-auto glass rounded-2xl p-4">
        <div className="flex items-center justify-between">
          <div className="text-xs font-semibold uppercase tracking-wider text-faint">Level {lvl.level}</div>
          <div className="flex items-center gap-1 text-xs font-bold text-amber-400"><Flame size={14} /> {streak}</div>
        </div>
        <div className="mt-1 font-display font-bold">{lvl.name}</div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-500/15">
          <div className="h-full rounded-full bg-gradient-to-r from-aqua-400 to-indigo-500 transition-all duration-700" style={{ width: `${Math.round(lvl.progress * 100)}%` }} />
        </div>
        <div className="mt-1 text-[11px] text-faint">{xp} XP{lvl.nextXp ? ` · ${lvl.nextXp - xp} bis ${lvl.next}` : ' · Max‑Level'}</div>
      </div>
    </aside>
  )

  return (
    <div className="min-h-dvh">
      <Bubbles />
      {/* Desktop sidebar */}
      <div className="fixed inset-y-0 left-0 z-50 hidden w-64 border-r border-base glass-strong lg:block">{Sidebar}</div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 glass-strong animate-fade-up">{Sidebar}</div>
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-base glass-strong px-4 lg:ml-64">
        <div className="flex items-center gap-3">
          <button className="rounded-xl p-2 hover:bg-white/5 lg:hidden cursor-pointer" onClick={() => setOpen((o) => !o)} aria-label="Menü">
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="font-display font-bold lg:hidden">DeepLearn</div>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-1.5 rounded-full border border-base px-3 py-1 text-xs font-semibold text-amber-400 sm:flex"><Flame size={14} /> {streak} Tage</div>
          <div className="hidden rounded-full border border-base px-3 py-1 text-xs font-semibold text-muted sm:block">{xp} XP</div>
          <button className="rounded-xl p-2 hover:bg-white/5 cursor-pointer" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} aria-label="Theme wechseln">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-aqua-400 to-indigo-500 text-xs font-bold text-white">
            {(name || 'T').slice(0, 1).toUpperCase()}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-28 pt-6 md:px-8 md:pt-8 lg:pl-72 lg:pb-12 xl:pl-80">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav className="fixed inset-x-0 bottom-0 z-40 flex items-center justify-around border-t border-base glass-strong px-2 pb-[env(safe-area-inset-bottom)] lg:hidden">
        {mobileNav.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => cn('flex flex-col items-center gap-1 px-3 py-2.5 text-[10px] font-semibold no-underline', isActive ? 'text-aqua-400' : 'text-faint')}>
            <n.icon size={20} />
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
