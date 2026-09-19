import type { ReactNode, ButtonHTMLAttributes } from 'react'
import { Link } from 'react-router-dom'

export function cn(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function Card({ children, className, hover = false }: { children: ReactNode; className?: string; hover?: boolean }) {
  return <div className={cn('glass rounded-3xl p-5 md:p-6', hover && 'card-hover', className)}>{children}</div>
}

export function CardLink({ to, children, className }: { to: string; children: ReactNode; className?: string }) {
  return (
    <Link to={to} className={cn('glass card-hover block rounded-3xl p-5 md:p-6 no-underline text-inherit', className)}>
      {children}
    </Link>
  )
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger' | 'outline'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({ variant = 'primary', size = 'md', className, children, ...rest }: ButtonProps) {
  const base = 'inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-all duration-200 select-none disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98] cursor-pointer'
  const sizes = { sm: 'px-3.5 py-2 text-sm', md: 'px-5 py-2.5 text-sm md:text-base', lg: 'px-7 py-3.5 text-base' }
  const variants = {
    primary: 'bg-gradient-to-r from-aqua-400 to-blue-500 text-white shadow-lg shadow-cyan-500/25 hover:shadow-cyan-400/40 hover:brightness-110',
    ghost: 'bg-transparent hover:bg-white/5 dark:hover:bg-white/5 text-inherit',
    outline: 'border border-strong bg-transparent hover:bg-white/5 text-inherit',
    danger: 'bg-gradient-to-r from-coral-400 to-coral-500 text-white shadow-lg shadow-rose-500/20',
  }
  return (
    <button className={cn(base, sizes[size], variants[variant], className)} {...rest}>
      {children}
    </button>
  )
}

export function Pill({ children, className, color = 'aqua' }: { children: ReactNode; className?: string; color?: 'aqua' | 'kelp' | 'coral' | 'sun' | 'violet' | 'neutral' }) {
  const colors = {
    aqua: 'bg-cyan-400/15 text-cyan-600 dark:text-cyan-300 border-cyan-400/30',
    kelp: 'bg-emerald-400/15 text-emerald-600 dark:text-emerald-300 border-emerald-400/30',
    coral: 'bg-rose-400/15 text-rose-600 dark:text-rose-300 border-rose-400/30',
    sun: 'bg-amber-400/15 text-amber-600 dark:text-amber-300 border-amber-400/30',
    violet: 'bg-violet-400/15 text-violet-600 dark:text-violet-300 border-violet-400/30',
    neutral: 'bg-slate-400/10 text-muted border-strong',
  }
  return <span className={cn('inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide', colors[color], className)}>{children}</span>
}

export function ProgressBar({ value, className, gradient = 'from-aqua-400 to-blue-500' }: { value: number; className?: string; gradient?: string }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)))
  return (
    <div className={cn('h-2 w-full overflow-hidden rounded-full bg-slate-500/15', className)}>
      <div className={cn('h-full rounded-full bg-gradient-to-r transition-all duration-700', gradient)} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function ProgressRing({ value, size = 64, stroke = 6, children, gradientId = 'ring' }: { value: number; size?: number; stroke?: number; children?: ReactNode; gradientId?: string }) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(1, value))
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="currentColor" strokeWidth={stroke} fill="none" className="text-slate-500/15" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={`url(#${gradientId})`} strokeWidth={stroke} fill="none" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{children}</div>
    </div>
  )
}

export function PageHeader({ eyebrow, title, subtitle, action }: { eyebrow?: string; title: string; subtitle?: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-col gap-3 md:mb-8 md:flex-row md:items-end md:justify-between animate-fade-up">
      <div>
        {eyebrow && <div className="mb-1 text-xs font-bold uppercase tracking-[0.2em] text-aqua-500">{eyebrow}</div>}
        <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
        {subtitle && <p className="mt-2 max-w-2xl text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function Stat({ label, value, sub, icon }: { label: string; value: ReactNode; sub?: string; icon?: ReactNode }) {
  return (
    <Card className="flex items-center gap-4">
      {icon && <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-aqua-400/20 to-indigo-500/20 text-aqua-400">{icon}</div>}
      <div className="min-w-0">
        <div className="text-xs font-semibold uppercase tracking-wider text-faint">{label}</div>
        <div className="font-display text-2xl font-bold leading-tight">{value}</div>
        {sub && <div className="text-xs text-muted">{sub}</div>}
      </div>
    </Card>
  )
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-faint">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-faint">{hint}</span>}
    </label>
  )
}

export const inputClass = 'w-full rounded-xl border border-strong bg-white/60 dark:bg-white/5 px-3.5 py-2.5 text-sm outline-none transition focus:border-aqua-400 focus:ring-2 focus:ring-aqua-400/30'

export function Empty({ icon, title, text, action }: { icon: ReactNode; title: string; text: string; action?: ReactNode }) {
  return (
    <Card className="flex flex-col items-center py-14 text-center">
      <div className="mb-4 text-5xl">{icon}</div>
      <h3 className="font-display text-xl font-bold">{title}</h3>
      <p className="mt-1 max-w-sm text-muted">{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </Card>
  )
}
