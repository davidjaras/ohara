import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useOutletContext } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Dumbbell, Flame, History, LayoutDashboard, Scale, Settings } from 'lucide-react'
import { api, type Stats, type TrainingProfile } from '@/lib/api'
import { setAccent, storedAccent } from '@/lib/theme'
import { cn } from '@/lib/utils'
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

function DesktopNav({ trainingEnabled }: { trainingEnabled: boolean }) {
  const { t } = useTranslation()
  return (
    <nav className="hidden items-center gap-1 sm:flex">
      {navItems(trainingEnabled).map(({ to, key, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              isActive
                ? 'bg-accent text-foreground'
                : 'text-muted-foreground hover:text-foreground',
            )
          }
        >
          <Icon className="size-4" />
          {t(key)}
        </NavLink>
      ))}
    </nav>
  )
}

function MobileTabBar({ trainingEnabled }: { trainingEnabled: boolean }) {
  const { t } = useTranslation()
  const items = navItems(trainingEnabled)
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t bg-background/95 backdrop-blur sm:hidden">
      <div
        className="grid"
        style={{ gridTemplateColumns: `repeat(${items.length}, 1fr)` }}
      >
        {items.map(({ to, key, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors',
                isActive ? 'text-primary' : 'text-muted-foreground',
              )
            }
          >
            <Icon className="size-5" />
            {t(key)}
          </NavLink>
        ))}
      </div>
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
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold">
            <OharaLogo size={28} className="text-primary" />
            ohara
          </NavLink>
          <div className="flex items-center gap-2">
            <DesktopNav trainingEnabled={training !== null} />
            {streakWeeks !== null && (
              <span
                className="ml-2 flex items-center gap-1 text-sm text-muted-foreground"
                title={t('stats.streak')}
              >
                <Flame className={streakWeeks > 0 ? 'size-4 text-primary' : 'size-4'} />
                {streakWeeks}
              </span>
            )}
            <span className="hidden text-sm text-muted-foreground sm:inline">
              {username}
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 pb-24 sm:pb-10">
        <Outlet
          context={{ refreshStreak, training, refreshTraining } satisfies LayoutContext}
        />
      </main>
      <MobileTabBar trainingEnabled={training !== null} />
    </div>
  )
}
