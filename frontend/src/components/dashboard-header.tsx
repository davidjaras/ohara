import { useTranslation } from 'react-i18next'
import { Flame } from 'lucide-react'
import { OharaLogo } from '@/components/brand/OharaLogo'
import { useLayoutContext } from '@/components/layout'

/**
 * Who you are and how many weeks you have met, above the timer.
 *
 * It belongs to the dashboard, not to the shell: repeated on every tab it was
 * a line of chrome that said the same thing five times. The other screens open
 * straight into their content — the nav already says where you are.
 */
export function DashboardHeader() {
  const { t } = useTranslation()
  const { username, streakWeeks } = useLayoutContext()

  return (
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
  )
}
