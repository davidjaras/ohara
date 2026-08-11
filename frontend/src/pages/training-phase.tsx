import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, ChevronDown, ChevronRight } from 'lucide-react'
import type { ScheduledDay, TrainingPhase, TrainingWeek } from '@/lib/api'
import { formatShortDate } from '@/lib/format'
import { useProgramDetail } from '@/lib/use-program'
import { useActiveRun, useSchedule } from '@/lib/use-run'
import { cn } from '@/lib/utils'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { Pill } from '@/components/pill'

/** "3 – 9 ago", from the days actually scheduled in that week. */
function weekRange(entries: ScheduledDay[]): string | null {
  if (entries.length === 0) return null
  const dates = entries.map((e) => e.scheduled_on).sort()
  return `${formatShortDate(dates[0])} – ${formatShortDate(dates[dates.length - 1])}`
}

function WeekSection({
  week,
  slug,
  phaseId,
  schedule,
  defaultOpen,
}: {
  week: TrainingWeek
  slug: string
  phaseId: number
  schedule: Map<number, ScheduledDay>
  defaultOpen: boolean
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(defaultOpen)

  const entries = week.days
    .map((day) => schedule.get(day.id))
    .filter((entry): entry is ScheduledDay => entry !== undefined)
  const range = weekRange(entries)
  const done = entries.filter((entry) => entry.done).length

  return (
    <div className="border-b border-hairline">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="-mx-2 flex w-[calc(100%+1rem)] items-center justify-between gap-3 rounded-xl px-2 py-3 text-left transition-colors hover:bg-glass"
      >
        <span className="min-w-0 text-sm font-semibold">
          {t('training.week', { number: week.number })}
          {week.is_deload && <Pill className="ml-2">{t('training.deload')}</Pill>}
          {range && (
            <span className="ml-2 text-xs font-normal text-muted-foreground">{range}</span>
          )}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {entries.length > 0 && (
            <span
              className={cn(
                'text-xs',
                done === entries.length ? 'text-primary' : 'text-muted-foreground',
              )}
            >
              {t('training.weekAdherence', { done, planned: entries.length })}
            </span>
          )}
          <ChevronDown
            className={cn(
              'size-4 text-muted-foreground transition-transform',
              open && 'rotate-180',
            )}
          />
        </span>
      </button>
      {open && (
        <div className="border-t border-hairline">
          {week.days.length === 0 ? (
            <p className="py-3 text-sm text-muted-foreground">{t('training.daysEmpty')}</p>
          ) : (
            week.days.map((day) => {
              const entry = schedule.get(day.id)
              return (
                <Link
                  key={day.id}
                  to={`/training/day/${day.id}?program=${slug}&phase=${phaseId}`}
                  className="-mx-2 flex items-center gap-3 rounded-xl py-2.5 pr-2 pl-5 transition-colors not-last:border-b not-last:border-hairline hover:bg-glass"
                >
                  <div className="grid min-w-0 flex-1 gap-0.5">
                    <span className="truncate text-sm">
                      {day.name || t('training.day', { number: day.order })}
                    </span>
                    {/* The real date once the plan is running, the weekday
                        otherwise — a program not being run has no dates. */}
                    {entry ? (
                      <span className="truncate text-xs text-muted-foreground">
                        {formatShortDate(entry.scheduled_on)}
                      </span>
                    ) : (
                      day.day_of_week && (
                        <span className="truncate text-xs text-muted-foreground capitalize">
                          {day.day_of_week.toLowerCase()}
                        </span>
                      )
                    )}
                  </div>
                  {entry?.done && <Check className="size-4 shrink-0 text-primary" />}
                  <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
                </Link>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

/** Third screen: the weeks of one phase, each opening into its days. */
export function TrainingPhasePage() {
  const { t } = useTranslation()
  const { slug, phaseId } = useParams()
  const { detail, error } = useProgramDetail(slug)
  const { run } = useActiveRun()
  const schedule = useSchedule(run, slug)

  const phase: TrainingPhase | null = useMemo(() => {
    if (!detail) return null
    const id = Number(phaseId)
    for (const variant of detail.variants) {
      const found = variant.phases.find((p) => p.id === id)
      if (found) return found
    }
    return null
  }, [detail, phaseId])

  if (error) {
    return <EmptyState tone="error">{error}</EmptyState>
  }
  if (!detail) {
    return <EmptyState>{t('training.loading')}</EmptyState>
  }
  if (!phase) {
    return <EmptyState tone="error">{t('training.phaseNotFound')}</EmptyState>
  }

  // While the plan runs, the week you are on is the one worth opening.
  const currentWeekIndex = phase.weeks.findIndex((week) =>
    week.days.some((day) => schedule.get(day.id)?.plan_week === run?.plan_week),
  )

  return (
    <div className="grid gap-6">
      <PageHeader
        title={
          <>
            {t('training.phase', { number: phase.number })}
            {phase.label && (
              <span className="ml-2 font-normal text-muted-foreground">{phase.label}</span>
            )}
          </>
        }
        subtitle={detail.name}
        backTo={`/training/${detail.slug}`}
        backLabel={t('training.backToProgram')}
      />

      <div className="border-t border-hairline">
        {phase.weeks.map((week, i) => (
          <WeekSection
            key={week.id}
            week={week}
            slug={detail.slug}
            phaseId={phase.id}
            schedule={schedule}
            defaultOpen={i === Math.max(currentWeekIndex, 0)}
          />
        ))}
      </div>
    </div>
  )
}
