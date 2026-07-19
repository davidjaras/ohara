import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { History, LayoutDashboard, Scale, Settings } from 'lucide-react'
import { api } from '@/lib/api'
import { setAccent, storedAccent } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { OharaLogo } from '@/components/brand/OharaLogo'

const NAV_ITEMS = [
  { to: '/', key: 'nav.dashboard', icon: LayoutDashboard },
  { to: '/historial', key: 'nav.history', icon: History },
  { to: '/peso', key: 'nav.weight', icon: Scale },
  { to: '/ajustes', key: 'nav.settings', icon: Settings },
]

function DesktopNav() {
  const { t } = useTranslation()
  return (
    <nav className="hidden items-center gap-1 sm:flex">
      {NAV_ITEMS.map(({ to, key, icon: Icon }) => (
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

function MobileTabBar() {
  const { t } = useTranslation()
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t bg-background/95 backdrop-blur sm:hidden">
      <div
        className="grid"
        style={{ gridTemplateColumns: `repeat(${NAV_ITEMS.length}, 1fr)` }}
      >
        {NAV_ITEMS.map(({ to, key, icon: Icon }) => (
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
  const [username, setUsername] = useState('')

  useEffect(() => {
    api.me().then((me) => setUsername(me.username), () => {})
    // Reconcile the accent with the server value (localStorage was already
    // applied synchronously at startup, so this only corrects a stale cache).
    api.preferences.get().then((pref) => {
      if (pref.accent_color !== storedAccent()) setAccent(pref.accent_color)
    }, () => {})
  }, [])

  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold">
            <OharaLogo size={28} className="text-primary" />
            ohara
          </NavLink>
          <div className="flex items-center gap-2">
            <DesktopNav />
            <span className="ml-2 hidden text-sm text-muted-foreground sm:inline">
              {username}
            </span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 pb-24 sm:pb-10">
        <Outlet />
      </main>
      <MobileTabBar />
    </div>
  )
}
