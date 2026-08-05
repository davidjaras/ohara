import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight } from 'lucide-react'
import { api, type Program, type ProgramRun } from '@/lib/api'
import { formatShortDate } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useLayoutContext } from '@/components/layout'
import { StartPlanDialog } from '@/components/start-plan-dialog'

/** The plan in progress: its dates, how much of it is done, a way in. */
function ActivePlanCard({ run }: { run: ProgramRun }) {
  const { t } = useTranslation()
  const done = run.adherence?.done ?? 0
  const planned = run.adherence?.planned ?? 0
  const progress = planned > 0 ? Math.min(100, (done / planned) * 100) : 0

  return (
    <Card>
      <Link
        to={`/training/${run.program.slug}`}
        className="block transition-colors hover:bg-accent/40"
      >
        <CardHeader className="flex items-center gap-3">
          <div className="grid min-w-0 flex-1 gap-1">
            <CardTitle className="truncate">{run.program.name}</CardTitle>
            <CardDescription>
              {t('training.planDates', {
                start: formatShortDate(run.started_on),
                end: formatShortDate(run.ends_on),
              })}
            </CardDescription>
          </div>
          <span className="shrink-0 rounded bg-primary/15 px-2 py-0.5 text-xs text-primary">
            {t('training.cardWeekOf', { week: run.plan_week, total: run.total_weeks })}
          </span>
          <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
        </CardHeader>
      </Link>
      <CardContent className="grid gap-2">
        <div className="h-2 overflow-hidden rounded-full bg-accent">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
        <p className="text-sm text-muted-foreground">
          {t('training.planProgress', { done, planned })}
        </p>
      </CardContent>
    </Card>
  )
}

/**
 * Entry screen of the training module: the plan in progress on top, then the
 * programs available to start. Starting one is a commitment to a date range,
 * not a label — that is what the dialog asks for.
 */
export function TrainingPage() {
  const { t } = useTranslation()
  const { refreshTraining } = useLayoutContext()
  const [programs, setPrograms] = useState<Program[] | null>(null)
  const [run, setRun] = useState<ProgramRun | null>(null)
  const [starting, setStarting] = useState<Program | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.training.programs().then(setPrograms, (e: Error) => setError(e.message))
    api.training.runs.active().then(setRun, () => setRun(null))
  }, [])

  useEffect(load, [load])

  if (error && !programs) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }

  return (
    <div className="mx-auto grid w-full max-w-lg gap-4">
      <div className="grid gap-1">
        <h1 className="text-lg font-semibold">{t('training.programsTitle')}</h1>
        <p className="text-sm text-muted-foreground">{t('training.programsDescription')}</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {run && (
        <div className="grid gap-2">
          <h2 className="text-sm font-medium text-muted-foreground">
            {t('training.planTitle')}
          </h2>
          <ActivePlanCard run={run} />
        </div>
      )}

      {programs === null ? (
        <p className="py-6 text-center text-sm text-muted-foreground">{t('training.loading')}</p>
      ) : programs.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t('training.programsEmpty')}
        </p>
      ) : (
        <div className="grid gap-3">
          {programs.map((program) => {
            const isActive = program.slug === run?.program.slug
            const subtitle = [
              program.coach ? t('training.coach', { coach: program.coach }) : '',
              program.variants.length > 1
                ? t('training.routineCount', { count: program.variants.length })
                : t('training.planWeeks', { count: program.variants[0]?.total_weeks ?? 0 }),
            ]
              .filter(Boolean)
              .join(' · ')

            return (
              <Card key={program.id}>
                <Link
                  to={`/training/${program.slug}`}
                  className="block transition-colors hover:bg-accent/40"
                >
                  <CardHeader className="flex items-center gap-3">
                    <div className="grid min-w-0 flex-1 gap-1">
                      <CardTitle>{program.name}</CardTitle>
                      {subtitle && <CardDescription>{subtitle}</CardDescription>}
                    </div>
                    {isActive && (
                      <span className="shrink-0 rounded bg-primary/15 px-2 py-0.5 text-xs text-primary">
                        {t('training.activeProgramTag')}
                      </span>
                    )}
                    <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
                  </CardHeader>
                </Link>
                {!isActive && (
                  <CardContent>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setStarting(program)}
                    >
                      {t('training.startPlan')}
                    </Button>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}

      <StartPlanDialog
        program={starting}
        currentRun={run}
        onClose={() => setStarting(null)}
        onStarted={(started) => {
          setStarting(null)
          setRun(started)
          // The nav and every consumer of the profile read the active run.
          refreshTraining()
        }}
      />
    </div>
  )
}
