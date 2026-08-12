import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight } from 'lucide-react'
import { formatShortDate } from '@/lib/format'
import { routineLabel } from '@/lib/routine'
import { useProgramDetail } from '@/lib/use-program'
import { useActiveRun, useSchedule } from '@/lib/use-run'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { Pill } from '@/components/pill'
import { Section } from '@/components/section'
import { useLayoutContext } from '@/components/layout'
import { StartPlanDialog } from '@/components/start-plan-dialog'

/** Second screen: pick the routine, then walk into a phase. */
export function TrainingProgramPage() {
  const { t } = useTranslation()
  const { slug } = useParams()
  const { refreshTraining } = useLayoutContext()
  const { detail, error: loadError } = useProgramDetail(slug)
  const { run, refresh: refreshRun } = useActiveRun()
  const schedule = useSchedule(run, slug)
  const [viewedVariantId, setViewedVariantId] = useState<number | null>(null)
  const [starting, setStarting] = useState(false)

  const activeVariantId = run?.variant.id ?? null

  // Default to the active routine when it belongs to this program; browsing
  // another one never changes what is active — that takes the button below.
  const viewedVariant = useMemo(() => {
    if (!detail) return null
    return (
      detail.variants.find((v) => v.id === viewedVariantId) ??
      detail.variants.find((v) => v.id === activeVariantId) ??
      detail.variants[0] ??
      null
    )
  }, [detail, viewedVariantId, activeVariantId])

  if (loadError) {
    return <EmptyState tone="error">{loadError}</EmptyState>
  }
  if (!detail) {
    return <EmptyState>{t('training.loading')}</EmptyState>
  }

  const hasRoutines = detail.variants.length > 1

  return (
    <div className="page-stack gap-10 sm:gap-12">
      <PageHeader
        title={detail.name}
        subtitle={detail.coach ? t('training.coach', { coach: detail.coach }) : undefined}
        backTo="/training"
        backLabel={t('training.backToPrograms')}
      />

      {hasRoutines && (
        <Section
          title={t('training.routineTitle')}
          description={t('training.routineDescription')}
        >
          <div className="grid gap-2">
            {detail.variants.map((variant) => (
              <button
                key={variant.id}
                type="button"
                onClick={() => setViewedVariantId(variant.id)}
                className={cn(
                  'flex items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors',
                  variant.id === viewedVariant?.id
                    ? 'border-primary/50 bg-primary/15'
                    : 'border-glass-border bg-glass hover:bg-glass-strong',
                )}
              >
                <span className="min-w-0 flex-1 truncate">{routineLabel(variant, t)}</span>
                {variant.id === activeVariantId && (
                  <Pill tone="accent">{t('training.activeTag')}</Pill>
                )}
              </button>
            ))}
            {viewedVariant && viewedVariant.id !== activeVariantId && (
              <div className="pt-1">
                {/* Using a routine now means starting a plan on a date, so it
                    opens the same dialog as the program list. */}
                <Button size="sm" onClick={() => setStarting(true)}>
                  {t('training.useRoutine')}
                </Button>
              </div>
            )}
          </div>
        </Section>
      )}

      {viewedVariant && viewedVariant.phases.length === 0 && (
        <EmptyState>{t('training.phasesEmpty')}</EmptyState>
      )}

      {viewedVariant && viewedVariant.phases.length > 0 && (
        <ul className="divide-y divide-hairline border-t border-hairline">
          {viewedVariant.phases.map((phase) => {
            const dates = phase.weeks
              .flatMap((week) => week.days)
              .map((day) => schedule.get(day.id)?.scheduled_on)
              .filter((date): date is string => date !== undefined)
              .sort()
            const range =
              dates.length > 0
                ? t('training.planDates', {
                    start: formatShortDate(dates[0]),
                    end: formatShortDate(dates[dates.length - 1]),
                  })
                : null

            return (
              <li key={phase.id}>
                <Link
                  to={`/training/${detail.slug}/phase/${phase.id}`}
                  className="-mx-2 flex items-center gap-3 rounded-xl px-2 py-3 transition-colors hover:bg-glass"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {t('training.phase', { number: phase.number })}
                      {phase.label && (
                        <span className="ml-2 font-normal text-muted-foreground">
                          {phase.label}
                        </span>
                      )}
                    </p>
                    <p className="truncate text-sm text-muted-foreground">
                      {[t('training.weeksCount', { count: phase.weeks.length }), range]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                  <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                </Link>
              </li>
            )
          })}
        </ul>
      )}

      <StartPlanDialog
        program={starting ? detail : null}
        initialVariantId={viewedVariant?.id ?? null}
        currentRun={run}
        onClose={() => setStarting(false)}
        onStarted={() => {
          setStarting(false)
          refreshTraining()
          // The run is what dates this very screen, so pull it again.
          refreshRun()
        }}
      />
    </div>
  )
}
