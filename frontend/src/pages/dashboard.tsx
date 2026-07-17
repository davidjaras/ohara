import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CalendarCheck, Clock, Flame } from 'lucide-react'
import { api, type Stats } from '@/lib/api'
import { formatMinutes } from '@/lib/format'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { CumulativeWeekChart, WeeklyChart } from '@/components/charts'
import { RangeSelect } from '@/components/range-select'
import { StatCard } from '@/components/stat-card'
import { TimerCard } from '@/components/timer-card'
import { WeekList } from '@/components/week-list'

const METRIC = 'estudio'

// 12 weeks (a quarter) reads at a glance; 4 zooms into the current month and
// 26/52 give the half-year and full-year picture.
const WEEK_RANGES = [4, 12, 26, 52]

export function DashboardPage() {
  const { t } = useTranslation()
  const [stats, setStats] = useState<Stats | null>(null)
  const [weeks, setWeeks] = useState(12)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(() => {
    api.stats(METRIC, weeks).then(setStats, (e: Error) => setError(e.message))
  }, [weeks])

  useEffect(loadStats, [loadStats])

  if (error) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }

  const weekProgress = stats
    ? Math.min(100, (stats.week_minutes / Math.max(1, stats.week_goal_minutes)) * 100)
    : 0

  return (
    <div className="grid gap-4 sm:gap-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        <StatCard
          icon={Flame}
          label={t('stats.streak')}
          value={stats?.streak_weeks ?? '–'}
          unit={(stats?.streak_weeks === 1 ? t('stats.week') : t('stats.weeks')).toLowerCase()}
          highlight={Boolean(stats && stats.streak_weeks > 0)}
        />
        <StatCard
          icon={CalendarCheck}
          label={t('stats.thisWeek')}
          value={stats?.week_minutes ?? '–'}
          unit={stats ? `/ ${stats.week_goal_minutes} ${t('stats.min')}` : undefined}
          highlight={stats?.week_met}
        />
        <StatCard
          icon={Clock}
          label={t('stats.total')}
          value={stats?.total_minutes ?? '–'}
          unit={t('stats.min')}
        />
      </div>

      <TimerCard metric={METRIC} onSessionSaved={loadStats} />

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
