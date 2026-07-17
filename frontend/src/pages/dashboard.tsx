import { useCallback, useEffect, useState } from 'react'
import { CalendarCheck, Clock, Flame } from 'lucide-react'
import { api, type Stats } from '@/lib/api'
import { formatMinutes } from '@/lib/format'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DailyChart, WeeklyChart } from '@/components/charts'
import { StatCard } from '@/components/stat-card'
import { TimerCard } from '@/components/timer-card'
import { WeekList } from '@/components/week-list'

const METRIC = 'estudio'

export function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(() => {
    api.stats(METRIC).then(setStats, (e: Error) => setError(e.message))
  }, [])

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
          label="Racha"
          value={stats?.streak_weeks ?? '–'}
          unit={stats?.streak_weeks === 1 ? 'semana' : 'semanas'}
          highlight={Boolean(stats && stats.streak_weeks > 0)}
        />
        <StatCard
          icon={CalendarCheck}
          label="Esta semana"
          value={stats?.week_minutes ?? '–'}
          unit={stats ? `/ ${stats.week_goal_minutes} min` : undefined}
          highlight={stats?.week_met}
        />
        <StatCard icon={Clock} label="Total" value={stats?.total_minutes ?? '–'} unit="min" />
      </div>

      <TimerCard metric={METRIC} onSessionSaved={loadStats} />

      {stats && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Esta semana</CardTitle>
              <CardDescription>
                {formatMinutes(stats.week_minutes)} de {formatMinutes(stats.week_goal_minutes)}
                {stats.week_met && ' · meta cumplida ✓'}
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
                <CardTitle>Minutos por día</CardTitle>
                <CardDescription>Últimos 14 días</CardDescription>
              </CardHeader>
              <CardContent>
                <DailyChart data={stats.daily} />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Minutos por semana</CardTitle>
                <CardDescription>
                  Últimas 12 semanas · la línea marca la meta vigente
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WeeklyChart data={stats.weekly} />
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Semanas cumplidas</CardTitle>
              <CardDescription>Meta semanal: {formatMinutes(stats.week_goal_minutes)}</CardDescription>
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
