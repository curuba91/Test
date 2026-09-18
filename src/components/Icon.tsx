import { Atom, HeartPulse, Wrench, Waves, Calculator, Compass, Fish, FlaskConical, Siren, BookOpen } from 'lucide-react'
import type { LucideProps } from 'lucide-react'

const map = { Atom, HeartPulse, Wrench, Waves, Calculator, Compass, Fish, FlaskConical, Siren, BookOpen }

export function ModuleIcon({ name, ...props }: { name: string } & LucideProps) {
  const C = map[name as keyof typeof map] ?? BookOpen
  return <C {...props} />
}
