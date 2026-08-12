import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, ChevronRight, Dumbbell } from 'lucide-react'
import { api, type ProgramRun, type ScheduledDay, type Stats } from '@/lib/api'
import { METRIC_ESTUDIO } from '@/lib/constants'
import { formatMinutes, formatShortDate, todayISO } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { CumulativeWeekChart } from '@/components/charts'
import { EmptyState } from '@/components/empty-state'
import { IconTile } from '@/components/icon-tile'
import { ProgressBar } from '@/components/progress-bar'
import { Section } from '@/components/section'
import { useLayoutContext } from '@/components/layout'
import { SessionReviewBanner } from '@/components/session-review-banner'
import { TimerCard } from '@/components/timer-card'

/** The workouts of the current plan week, done ones marked. */
function WeekStrip({ days, activeDayId }: { days: ScheduledDay[]; activeDayId: number | null }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {days.map((entry) => (
        <span
          key={entry.day.id}
          className={cn(
            'flex items-center gap-1 rounded-md px-2 py-0.5 text-xs',
            entry.done
              ? 'bg-primary/15 text-primary'
              : entry.day.id === activeDayId
                ? 'glass-subtle font-medium text-foreground'
                : 'text-muted-foreground',
          )}
        >
          {entry.done && <Check className="size-3" />}
          {entry.day.name}
        </span>
      ))}
    </div>
  )
}

/**
 * The plan in progress: which week, what this week looks like, and one tap
 * into the workout to do now. With no plan it is the entry point to pick one.
 *
 * A slim row rather than a panel: the timer above it is the thing this screen
 * is for, and two panels stacked would make them argue.
 */
function TrainingRow() {
  const { t } = useTranslation()
  const [run, setRun] = useState<ProgramRun | null | undefined>(undefined)
  const [finishing, setFinishing] = useState(false)
  const [dismissedEnd, setDismissedEnd] = useState(false)

  useEffect(() => {
    api.training.runs.active().then(setRun, () => setRun(null))
  }, [])

  const finishPlan = () => {
    if (!run) return
    setFinishing(true)
    api.training.runs.update(run.id, { status: 'completed' }).then(
      () => setRun(null),
      () => setFinishing(false),
    )
  }

  if (run === undefined) return null

  if (!run) {
    return (
      <Link
        to="/training"
        className="-mx-2 flex items-center gap-3 rounded-2xl border-y border-hairline px-2 py-3 transition-colors hover:bg-glass"
      >
        <IconTile>
          <Dumbbell className="size-4" />
        </IconTile>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{t('training.cardTitle')}</p>
          <p className="truncate text-sm text-muted-foreground">{t('training.cardNone')}</p>
        </div>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
      </Link>
    )
  }

  const active = run.active_day ?? null
  const weekDays = (run.schedule ?? []).filter((e) => e.plan_week === run.plan_week)
  const isToday = active?.scheduled_on === todayISO()
  const pending = (run.adherence?.planned ?? 0) - (run.adherence?.done ?? 0)
  // Past the end date the plan is not closed behind your back: it asks.
  const isOver = run.ends_on < todayISO() && !dismissedEnd

  const dayHref = active
    ? `/training/day/${active.day.id}?program=${run.program.slug}`
    : `/training/${run.program.slug}`

  return (
    <div className="grid min-w-0 gap-3 border-y border-hairline py-3">
      <Link
        to={dayHref}
        className="-mx-2 flex items-center gap-3 rounded-2xl px-2 py-1 transition-colors hover:bg-glass"
      >
        <IconTile>
          <Dumbbell className="size-4" />
        </IconTile>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold">{run.program.name}</p>
          <p className="truncate text-sm text-muted-foreground">
            {t('training.cardWeekOf', { week: run.plan_week, total: run.total_weeks })}
            {active &&
              ` · ${t(isToday ? 'training.cardToday' : 'training.cardNext')}: ${active.day.name}`}
            {!active && ` · ${t('training.cardRestDay')}`}
          </p>
        </div>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
      </Link>
      {weekDays.length > 0 && (
        <WeekStrip days={weekDays} activeDayId={active?.day.id ?? null} />
      )}
      {isOver && (
        <div className="grid gap-2">
          <p className="text-sm text-muted-foreground">
            {pending > 0
              ? t('training.cardPlanOverPending', {
                  date: formatShortDate(run.ends_on),
                  count: pending,
                })
              : t('training.cardPlanOver', { date: formatShortDate(run.ends_on) })}
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={finishPlan} disabled={finishing}>
              {t('training.cardFinishPlan')}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setDismissedEnd(true)}>
              {t('training.cardKeepGoing')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Three blocks, in the order you need them: the timer you came to start, the
 * workout you owe today, and how the week is going. Everything historical —
 * the weekly bars, the list of met weeks — lives in History now; a dashboard
 * that needs scrolling to reach its own point is not a dashboard.
 */
export function DashboardPage() {
  const { t } = useTranslation()
  const { refreshStreak, training } = useLayoutContext()
  const [stats, setStats] = useState<Stats | null>(null)
  const [reviewKey, setReviewKey] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(() => {
    // One week of history is all this screen shows; the ranges live in History.
    api.stats(METRIC_ESTUDIO, 1).then(setStats, (e: Error) => setError(e.message))
  }, [])

  useEffect(loadStats, [loadStats])

  // A finished or auto-closed session changes the stats, the navbar streak
  // and possibly the pending-review banner — refresh the three together.
  const handleSessionSaved = useCallback(() => {
    loadStats()
    refreshStreak()
    setReviewKey((n) => n + 1)
  }, [loadStats, refreshStreak])

  if (error) {
    return <EmptyState tone="error">{error}</EmptyState>
  }

  const weekProgress = stats
    ? (stats.week_minutes / Math.max(1, stats.week_goal_minutes)) * 100
    : 0

  return (
    <div className="page-stack gap-6">
      <SessionReviewBanner
        metric={METRIC_ESTUDIO}
        refreshKey={reviewKey}
        onResolved={handleSessionSaved}
      />
      <TimerCard metric={METRIC_ESTUDIO} onSessionSaved={handleSessionSaved} />
      {training && <TrainingRow />}

      {stats && (
        <Section
          title={t('weekProgress.title')}
          action={
            <span className="text-sm tabular-nums">
              {/* The goal being met is the one fact worth an accent here. */}
              <span className={cn('font-semibold', stats.week_met && 'text-primary')}>
                {formatMinutes(stats.week_minutes)}
              </span>
              <span className="text-muted-foreground">
                {' '}
                / {formatMinutes(stats.week_goal_minutes)}
              </span>
            </span>
          }
        >
          <ProgressBar value={weekProgress} />
          <CumulativeWeekChart
            data={stats.week_cumulative}
            goal={stats.week_goal_minutes}
          />
        </Section>
      )}
    </div>
  )
}
