import { useTranslation } from 'react-i18next'
import { CheckCircle2, Circle } from 'lucide-react'
import type { WeekSummary } from '@/lib/api'
import { formatMinutes, formatWeekRange } from '@/lib/format'
import { cn } from '@/lib/utils'

interface WeekListProps {
  weeks: WeekSummary[]
  currentWeekStart: string
}

/** Recent weeks with their green check, most recent first. */
export function WeekList({ weeks, currentWeekStart }: WeekListProps) {
  const { t } = useTranslation()
  const rows = [...weeks].reverse()
  return (
    <ul className="divide-y">
      {rows.map((week) => {
        const isCurrent = week.week_start === currentWeekStart
        return (
          <li key={week.week_start} className="flex items-center gap-3 py-2.5">
            {week.met ? (
              <CheckCircle2 className="size-5 shrink-0 text-primary" />
            ) : (
              <Circle className="size-5 shrink-0 text-muted-foreground/40" />
            )}
            <div className="min-w-0 flex-1">
              <p className={cn('text-sm font-medium', isCurrent && 'text-primary')}>
                {formatWeekRange(week.week_start)}
                {isCurrent && ` · ${t('weekList.current')}`}
              </p>
            </div>
            <p className="text-sm tabular-nums text-muted-foreground">
              {formatMinutes(week.minutes)}
              <span className="text-muted-foreground/60"> / {formatMinutes(week.goal_minutes)}</span>
            </p>
          </li>
        )
      })}
    </ul>
  )
}
