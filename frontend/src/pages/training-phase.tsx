import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, ChevronDown, ChevronRight } from 'lucide-react'
import type { TrainingPhase, TrainingWeek } from '@/lib/api'
import { useProgramDetail } from '@/lib/use-program'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

function WeekSection({
  week,
  slug,
  phaseId,
  defaultOpen,
}: {
  week: TrainingWeek
  slug: string
  phaseId: number
  defaultOpen: boolean
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(defaultOpen)

  return (
    <Card className="gap-0 py-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40"
      >
        <span className="text-sm font-medium">
          {t('training.week', { number: week.number })}
          {week.is_deload && (
            <span className="ml-2 rounded bg-accent px-1.5 py-0.5 text-xs font-normal text-muted-foreground">
              {t('training.deload')}
            </span>
          )}
        </span>
        <ChevronDown
          className={cn('size-4 shrink-0 text-muted-foreground transition-transform', open && 'rotate-180')}
        />
      </button>
      {open && (
        <div className="border-t">
          {week.days.length === 0 ? (
            <p className="px-4 py-3 text-sm text-muted-foreground">{t('training.daysEmpty')}</p>
          ) : (
            week.days.map((day) => (
              <Link
                key={day.id}
                to={`/training/day/${day.id}?week=${week.number}&program=${slug}&phase=${phaseId}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors not-last:border-b hover:bg-accent/40"
              >
                <div className="grid min-w-0 flex-1 gap-0.5">
                  <span className="truncate text-sm font-medium">
                    {day.name || t('training.day', { number: day.order })}
                  </span>
                  {day.day_of_week && (
                    <span className="truncate text-xs text-muted-foreground capitalize">
                      {day.day_of_week.toLowerCase()}
                    </span>
                  )}
                </div>
                <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
              </Link>
            ))
          )}
        </div>
      )}
    </Card>
  )
}

/** Third screen: the weeks of one phase, each opening into its days. */
export function TrainingPhasePage() {
  const { t } = useTranslation()
  const { slug, phaseId } = useParams()
  const { detail, error } = useProgramDetail(slug)

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
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }
  if (!detail) {
    return <p className="py-10 text-center text-sm text-muted-foreground">{t('training.loading')}</p>
  }
  if (!phase) {
    return <p className="py-10 text-center text-sm text-destructive">{t('training.phaseNotFound')}</p>
  }

  return (
    <div className="mx-auto grid w-full max-w-lg gap-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to={`/training/${detail.slug}`} aria-label={t('training.backToProgram')}>
            <ArrowLeft className="size-5" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold">
            {t('training.phase', { number: phase.number })}
            {phase.label && (
              <span className="ml-2 font-normal text-muted-foreground">{phase.label}</span>
            )}
          </h1>
          <p className="truncate text-sm text-muted-foreground">{detail.name}</p>
        </div>
      </div>

      <div className="grid gap-2">
        {phase.weeks.map((week, i) => (
          <WeekSection
            key={week.id}
            week={week}
            slug={detail.slug}
            phaseId={phase.id}
            defaultOpen={i === 0}
          />
        ))}
      </div>
    </div>
  )
}
