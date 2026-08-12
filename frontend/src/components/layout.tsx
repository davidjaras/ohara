import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useOutletContext } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Dumbbell, Flame, History, LayoutDashboard, Scale, Settings } from 'lucide-react'
import { api, type Stats, type TrainingProfile } from '@/lib/api'
import { setAccent, storedAccent } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { AmbientBackdrop } from '@/components/ambient-backdrop'
import { OharaLogo } from '@/components/brand/OharaLogo'

const METRIC = 'estudio'

/** Handles the Layout shares with its routed pages through <Outlet>. */
export interface LayoutContext {
  /** Re-read the navbar streak after a session is saved or deleted. */
  refreshStreak: () => void
  /**
   * null while unknown or when the module is off (the profile endpoint answers
   * 404 for users without training) — nothing training-related renders then.
   */
  training: TrainingProfile | null
  /** Re-read the profile after the active variant changes. */
  refreshTraining: () => void
}

export function useLayoutContext() {
  return useOutletContext<LayoutContext>()
}

const BASE_NAV_ITEMS = [
  { to: '/', key: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/history', key: 'nav.history', icon: History },
  { to: '/weight', key: 'nav.weight', icon: Scale },
  { to: '/settings', key: 'nav.settings', icon: Settings },
]

// The training entry exists only while the module is enabled: the gate lives
// here, in the navigation render, not in the destination route.
function navItems(trainingEnabled: boolean) {
  if (!trainingEnabled) return BASE_NAV_ITEMS
  return [
    BASE_NAV_ITEMS[0],
    { to: '/training', key: 'nav.training', icon: Dumbbell },
    ...BASE_NAV_ITEMS.slice(1),
  ]
}

/**
 * The one navigation surface of the app: a floating glass pill, at the bottom
 * on a phone and centered at the top on a wider screen. Same component, same
 * items, same icon-over-label shape either way — a desktop only gets a
 * different position, never a different structure.
 *
 * It floats over the content rather than docking to an edge, which is why
 * pages reserve `--nav-offset` at the bottom instead of padding by eye.
 */
function NavPill({ trainingEnabled }: { trainingEnabled: boolean }) {
  const { t } = useTranslation()
  const items = navItems(trainingEnabled)
  return (
    <nav
      className={cn(
        'glass-overlay glass-lit fixed z-30 flex rounded-3xl px-1.5 py-1.5 shadow-xl',
        'inset-x-4 bottom-[max(1rem,env(safe-area-inset-bottom))]',
        'sm:inset-x-auto sm:bottom-auto sm:top-4 sm:left-1/2 sm:-translate-x-1/2',
      )}
    >
      {items.map(({ to, key, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            cn(
              'flex flex-1 flex-col items-center gap-1 rounded-2xl px-1 py-1.5 text-[11px] font-medium transition-colors sm:w-20 sm:flex-none',
              isActive ? 'bg-glass text-primary' : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          <Icon className="size-5" />
          {t(key)}
        </NavLink>
      ))}
    </nav>
  )
}

export function Layout() {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [streakWeeks, setStreakWeeks] = useState<number | null>(null)
  const [training, setTraining] = useState<TrainingProfile | null>(null)

  const refreshStreak = useCallback(() => {
    // weeks=1 keeps the payload minimal; the streak is computed independently
    // of the range (the backend walks every recorded week for it).
    api.stats(METRIC, 1).then((s: Stats) => setStreakWeeks(s.streak_weeks), () => {})
  }, [])

  const refreshTraining = useCallback(() => {
    // 404 = module off for this user; keep the UI exactly as it is without it.
    api.training.profile().then(setTraining, () => setTraining(null))
  }, [])

  useEffect(() => {
    api.me().then((me) => setUsername(me.username), () => {})
    refreshStreak()
    refreshTraining()
    // Reconcile the accent with the server value (localStorage was already
    // applied synchronously at startup, so this only corrects a stale cache).
    api.preferences.get().then((pref) => {
      if (pref.accent_color !== storedAccent()) setAccent(pref.accent_color)
    }, () => {})
  }, [refreshStreak, refreshTraining])

  return (
    <div className="min-h-svh">
      <AmbientBackdrop />
      {/* The column is centered and capped at a comfortable measure on every
          width: the same layout scaled, not a separate desktop one. The top
          padding on wider screens is what clears the floating nav. */}
      <main className="mx-auto w-full max-w-xl px-4 pt-5 pb-[var(--nav-offset)] sm:pt-24 sm:pb-12">
        <header className="mb-6 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            <OharaLogo size={28} className="shrink-0 text-primary" />
            <span className="truncate text-[15px] font-semibold">
              {username ? t('nav.greeting', { name: username }) : 'ohara'}
            </span>
          </div>
          {streakWeeks !== null && (
            <span
              className="glass-subtle flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold"
              title={t('stats.streak')}
            >
              <Flame className={streakWeeks > 0 ? 'size-4 text-primary' : 'size-4'} />
              {streakWeeks}
            </span>
          )}
        </header>
        <Outlet
          context={{ refreshStreak, training, refreshTraining } satisfies LayoutContext}
        />
      </main>
      <NavPill trainingEnabled={training !== null} />
    </div>
  )
}
