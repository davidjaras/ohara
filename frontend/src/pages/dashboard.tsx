import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight, Dumbbell } from 'lucide-react'
import { api, type Program, type Stats, type TrainingProfile } from '@/lib/api'
import { METRIC_ESTUDIO } from '@/lib/constants'
import { formatMinutes } from '@/lib/format'
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

/** Entry point to the active training program. Renders only when the module
 *  is enabled — with it off the dashboard is exactly the study dashboard. */
function TrainingCard({ training }: { training: TrainingProfile }) {
  const { t } = useTranslation()
  const [programs, setPrograms] = useState<Program[]>([])

  useEffect(() => {
    api.training.programs().then(setPrograms, () => {})
  }, [])

  const activeProgram = programs.find((p) => p.slug === training.active_program)

  return (
    <Card>
      <Link to="/entrenamiento" className="block transition-colors hover:bg-accent/40">
        <CardHeader className="flex items-center gap-3">
          <div className="rounded-md bg-accent p-2">
            <Dumbbell className="size-5 text-primary" />
          </div>
          <div className="grid min-w-0 flex-1 gap-1">
            <CardTitle>{t('training.cardTitle')}</CardTitle>
            <CardDescription className="truncate">
              {activeProgram
                ? t('training.cardActive', { name: activeProgram.name })
                : t('training.cardNone')}
            </CardDescription>
          </div>
          <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
        </CardHeader>
      </Link>
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
      {training && <TrainingCard training={training} />}

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
