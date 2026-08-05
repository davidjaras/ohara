import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, ChevronRight, Dumbbell } from 'lucide-react'
import { api, type ProgramRun, type ScheduledDay, type Stats } from '@/lib/api'
import { METRIC_ESTUDIO } from '@/lib/constants'
import { formatMinutes, formatShortDate, todayISO } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CumulativeWeekChart, WeeklyChart } from '@/components/charts'
import { RangeSelect } from '@/components/range-select'
import { useLayoutContext } from '@/components/layout'
import { SessionReviewBanner } from '@/components/session-review-banner'
import { TimerCard } from '@/components/timer-card'
import { WeekList } from '@/components/week-list'

// 12 weeks (a quarter) reads at a glance; 4 zooms into the current month and
// 26/52 give the half-year and full-year picture.
const WEEK_RANGES = [4, 12, 26, 52]

/** The workouts of the current plan week, done ones marked. */
function WeekStrip({ days, activeDayId }: { days: ScheduledDay[]; activeDayId: number | null }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {days.map((entry) => (
        <span
          key={entry.day.id}
          className={cn(
            'flex items-center gap-1 rounded px-1.5 py-0.5 text-xs',
            entry.done
              ? 'bg-primary/15 text-primary'
              : entry.day.id === activeDayId
                ? 'bg-accent font-medium text-foreground'
                : 'bg-accent text-muted-foreground',
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
 * Renders only when the module is enabled — with it off the dashboard is
 * exactly the study dashboard.
 */
function TrainingCard() {
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
      <Card>
        <Link to="/training" className="block transition-colors hover:bg-accent/40">
          <CardHeader className="flex items-center gap-3">
            <div className="rounded-md bg-accent p-2">
              <Dumbbell className="size-5 text-primary" />
            </div>
            <div className="grid min-w-0 flex-1 gap-1">
              <CardTitle>{t('training.cardTitle')}</CardTitle>
              <CardDescription>{t('training.cardNone')}</CardDescription>
            </div>
            <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
          </CardHeader>
        </Link>
      </Card>
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
    <Card>
      <Link to={dayHref} className="block transition-colors hover:bg-accent/40">
        <CardHeader className="flex items-center gap-3">
          <div className="rounded-md bg-accent p-2">
            <Dumbbell className="size-5 text-primary" />
          </div>
          <div className="grid min-w-0 flex-1 gap-1">
            <CardTitle className="truncate">{run.program.name}</CardTitle>
            <CardDescription className="truncate">
              {t('training.cardWeekOf', {
                week: run.plan_week,
                total: run.total_weeks,
              })}
              {active &&
                ` · ${t(isToday ? 'training.cardToday' : 'training.cardNext')}: ${active.day.name}`}
              {!active && ` · ${t('training.cardRestDay')}`}
            </CardDescription>
          </div>
          <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
        </CardHeader>
      </Link>
      {(weekDays.length > 0 || isOver) && (
        <CardContent className="grid gap-3">
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
        </CardContent>
      )}
    </Card>
  )
}

export function DashboardPage() {
  const { t } = useTranslation()
  const { refreshStreak, training } = useLayoutContext()
  const [stats, setStats] = useState<Stats | null>(null)
  const [weeks, setWeeks] = useState(12)
  const [reviewKey, setReviewKey] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(() => {
    api.stats(METRIC_ESTUDIO, weeks).then(setStats, (e: Error) => setError(e.message))
  }, [weeks])

  useEffect(loadStats, [loadStats])

  // A finished or auto-closed session changes the stats, the navbar streak
  // and possibly the pending-review banner — refresh the three together.
  const handleSessionSaved = useCallback(() => {
    loadStats()
    refreshStreak()
    setReviewKey((n) => n + 1)
  }, [loadStats, refreshStreak])

  if (error) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }

  const weekProgress = stats
    ? Math.min(100, (stats.week_minutes / Math.max(1, stats.week_goal_minutes)) * 100)
    : 0

  return (
    <div className="grid gap-4 sm:gap-5">
      <SessionReviewBanner
        metric={METRIC_ESTUDIO}
        refreshKey={reviewKey}
        onResolved={handleSessionSaved}
      />
      <TimerCard metric={METRIC_ESTUDIO} onSessionSaved={handleSessionSaved} />
      {training && <TrainingCard />}

      {stats && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>{t('weekProgress.title')}</CardTitle>
              <CardDescription>
                {t('weekProgress.ofGoal', {
                  minutes: formatMinutes(stats.week_minutes),
                  goal: formatMinutes(stats.week_goal_minutes),
                })}
                {stats.week_met && ` · ${t('weekProgress.met')}`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-2 overflow-hidden rounded-full bg-accent">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${weekProgress}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-4 lg:grid-cols-2 sm:gap-5">
            <Card>
              <CardHeader>
                <CardTitle>{t('cumulativeChart.title')}</CardTitle>
                <CardDescription>{t('cumulativeChart.description')}</CardDescription>
              </CardHeader>
              <CardContent>
                <CumulativeWeekChart
                  data={stats.week_cumulative}
                  goal={stats.week_goal_minutes}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
                <div className="grid gap-1.5">
                  <CardTitle>{t('weeklyChart.title')}</CardTitle>
                  <CardDescription>{t('weeklyChart.description')}</CardDescription>
                </div>
                <RangeSelect
                  options={WEEK_RANGES.map((n) => ({
                    value: n,
                    label: t('ranges.weeks', { count: n }),
                  }))}
                  value={weeks}
                  onChange={setWeeks}
                />
              </CardHeader>
              <CardContent>
                <WeeklyChart data={stats.weekly} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t('weekList.title')}</CardTitle>
              <CardDescription>
                {t('weekList.goal', { goal: formatMinutes(stats.week_goal_minutes) })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <WeekList
                weeks={stats.weekly.slice(-8)}
                currentWeekStart={stats.weekly[stats.weekly.length - 1].week_start}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
