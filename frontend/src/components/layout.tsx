import { NavLink, Outlet } from 'react-router-dom'
import { History, LayoutDashboard, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV_ITEMS = [
  { to: '/', label: 'Panel', icon: LayoutDashboard },
  { to: '/historial', label: 'Historial', icon: History },
  { to: '/ajustes', label: 'Ajustes', icon: Settings },
]

function DesktopNav() {
  return (
    <nav className="hidden items-center gap-1 sm:flex">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
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
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

function MobileTabBar() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t bg-background/95 backdrop-blur sm:hidden">
      <div
        className="grid"
        style={{ gridTemplateColumns: `repeat(${NAV_ITEMS.length}, 1fr)` }}
      >
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
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
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

export function Layout() {
  return (
    <div className="min-h-svh">
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <NavLink to="/" className="flex items-center gap-2 text-lg font-semibold">
            <span className="size-2.5 rounded-full bg-primary" />
            ohara
          </NavLink>
          <DesktopNav />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 pb-24 sm:pb-10">
        <Outlet />
      </main>
      <MobileTabBar />
    </div>
  )
}
