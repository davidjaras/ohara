import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight } from 'lucide-react'
import { api, type Program, type ProgramRun } from '@/lib/api'
import { formatShortDate } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/empty-state'
import { Panel } from '@/components/panel'
import { Pill } from '@/components/pill'
import { ProgressBar } from '@/components/progress-bar'
import { Section } from '@/components/section'
import { useLayoutContext } from '@/components/layout'
import { StartPlanDialog } from '@/components/start-plan-dialog'

/**
 * The plan in progress: its dates, how much of it is done, a way in. The one
 * panel on this screen — everything else is a program you could start, and
 * this is the one you did.
 */
function ActivePlanPanel({ run }: { run: ProgramRun }) {
  const { t } = useTranslation()
  const done = run.adherence?.done ?? 0
  const planned = run.adherence?.planned ?? 0
  const progress = planned > 0 ? (done / planned) * 100 : 0

  return (
    <Panel className="p-4">
      <Link to={`/training/${run.program.slug}`} className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{run.program.name}</p>
          <p className="truncate text-sm text-muted-foreground">
            {t('training.planDates', {
              start: formatShortDate(run.started_on),
              end: formatShortDate(run.ends_on),
            })}
          </p>
        </div>
        <Pill tone="accent">
          {t('training.cardWeekOf', { week: run.plan_week, total: run.total_weeks })}
        </Pill>
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
      </Link>
      <div className="mt-3 grid gap-2">
        <ProgressBar value={progress} />
        <p className="text-sm text-muted-foreground">
          {t('training.planProgress', { done, planned })}
        </p>
      </div>
    </Panel>
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
    return <EmptyState tone="error">{error}</EmptyState>
  }

  return (
    <div className="page-stack gap-10 sm:gap-12">
      {error && <p className="text-sm text-destructive">{error}</p>}

      {run && (
        <Section title={t('training.planTitle')}>
          <ActivePlanPanel run={run} />
        </Section>
      )}

      <Section
        title={t('training.programsTitle')}
        description={t('training.programsDescription')}
      >
        {programs === null ? (
          <EmptyState>{t('training.loading')}</EmptyState>
        ) : programs.length === 0 ? (
          <EmptyState>{t('training.programsEmpty')}</EmptyState>
        ) : (
          <ul className="divide-y divide-hairline">
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
                <li key={program.id} className="flex items-center gap-3 py-3">
                  <Link to={`/training/${program.slug}`} className="flex min-w-0 flex-1 items-center gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{program.name}</p>
                      {subtitle && (
                        <p className="truncate text-sm text-muted-foreground">{subtitle}</p>
                      )}
                    </div>
                    {isActive && <Pill tone="accent">{t('training.activeProgramTag')}</Pill>}
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                  </Link>
                  {!isActive && (
                    <Button variant="outline" size="sm" onClick={() => setStarting(program)}>
                      {t('training.startPlan')}
                    </Button>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Section>

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
