import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { ChevronDown } from 'lucide-react'
import {
  api,
  type Program,
  type ProgramDetail,
  type ProgramVariant,
  type TrainingPhase,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useLayoutContext } from '@/components/layout'

function variantLabel(variant: ProgramVariant, t: TFunction) {
  const parts = [t('training.variantDays', { count: variant.days_per_week })]
  if (variant.environment === 'gym') parts.push(t('training.envGym'))
  if (variant.environment === 'home') parts.push(t('training.envHome'))
  return parts.join(' · ')
}

function PhaseSection({
  phase,
  defaultOpen,
}: {
  phase: TrainingPhase
  defaultOpen: boolean
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="rounded-lg border">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <span className="text-sm font-medium">
          {t('training.phase', { number: phase.number })}
          {phase.label && (
            <span className="ml-2 font-normal text-muted-foreground">{phase.label}</span>
          )}
        </span>
        <ChevronDown
          className={cn('size-4 text-muted-foreground transition-transform', open && 'rotate-180')}
        />
      </button>
      {open && (
        <div className="grid gap-3 border-t px-4 py-3">
          {phase.weeks.map((week) => (
            <div key={week.id} className="grid gap-2">
              <p className="text-sm text-muted-foreground">
                {t('training.week', { number: week.number })}
                {week.is_deload && (
                  <span className="ml-2 rounded bg-accent px-1.5 py-0.5 text-xs">
                    {t('training.deload')}
                  </span>
                )}
              </p>
              {week.days.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('training.daysEmpty')}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {week.days.map((day) => (
                    <Button key={day.id} variant="outline" size="sm" asChild>
                      <Link to={`/entrenamiento/dia/${day.id}?semana=${week.number}`}>
                        {day.name || t('training.day', { number: day.order })}
                      </Link>
                    </Button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function TrainingPage() {
  const { t } = useTranslation()
  const { training, refreshTraining } = useLayoutContext()
  const [programs, setPrograms] = useState<Program[]>([])
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [detail, setDetail] = useState<ProgramDetail | null>(null)
  const [viewedVariantId, setViewedVariantId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.training.programs().then(setPrograms, (e: Error) => setError(e.message))
  }, [])

  // Land on the active program; otherwise on the first accessible one.
  const slug = selectedSlug ?? training?.active_program ?? programs[0]?.slug ?? null

  useEffect(() => {
    if (!slug) return
    setDetail(null)
    api.training.program(slug).then(setDetail, (e: Error) => setError(e.message))
  }, [slug])

  const activeVariantId = training?.active_variant?.id ?? null

  // Default the viewed variant to the active one when it belongs to this
  // program; the user can browse other variants without activating them.
  const viewedVariant = useMemo(() => {
    if (!detail) return null
    return (
      detail.variants.find((v) => v.id === viewedVariantId) ??
      detail.variants.find((v) => v.id === activeVariantId) ??
      detail.variants[0] ??
      null
    )
  }, [detail, viewedVariantId, activeVariantId])

  const activateVariant = (variantId: number) => {
    api.training.updateProfile({ active_variant: variantId }).then(
      () => refreshTraining(),
      (e: Error) => setError(e.message),
    )
  }

  if (error) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }

  return (
    <div className="grid gap-4 sm:gap-5">
      <Card>
        <CardHeader>
          <CardTitle>{t('training.programsTitle')}</CardTitle>
          <CardDescription>{t('training.programsDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          {programs.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              {t('training.programsEmpty')}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {programs.map((program) => (
                <button
                  key={program.id}
                  type="button"
                  onClick={() => {
                    setSelectedSlug(program.slug)
                    setViewedVariantId(null)
                  }}
                  className={cn(
                    'rounded-lg border px-4 py-3 text-left transition-colors',
                    program.slug === slug
                      ? 'border-primary bg-accent'
                      : 'hover:bg-accent/50',
                  )}
                >
                  <span className="block text-sm font-medium">{program.name}</span>
                  {program.coach && (
                    <span className="block text-xs text-muted-foreground">
                      {t('training.coach', { coach: program.coach })}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {detail && detail.variants.length > 1 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('training.variantsTitle')}</CardTitle>
            <CardDescription>{t('training.variantsDescription')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {detail.variants.map((variant) => (
                <button
                  key={variant.id}
                  type="button"
                  onClick={() => setViewedVariantId(variant.id)}
                  className={cn(
                    'rounded-lg border px-4 py-2 text-left text-sm transition-colors',
                    variant.id === viewedVariant?.id
                      ? 'border-primary bg-accent'
                      : 'hover:bg-accent/50',
                  )}
                >
                  {variantLabel(variant, t)}
                  {variant.id === activeVariantId && (
                    <span className="ml-2 rounded bg-primary/15 px-1.5 py-0.5 text-xs text-primary">
                      {t('training.activeTag')}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {detail && viewedVariant && (
        <div className="grid gap-3">
          {viewedVariant.id !== activeVariantId && (
            <div>
              <Button size="sm" onClick={() => activateVariant(viewedVariant.id)}>
                {t('training.useVariant')}
              </Button>
            </div>
          )}
          {viewedVariant.phases.map((phase, i) => (
            <PhaseSection key={phase.id} phase={phase} defaultOpen={i === 0} />
          ))}
        </div>
      )}

      {slug && !detail && (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t('training.loading')}
        </p>
      )}
    </div>
  )
}
