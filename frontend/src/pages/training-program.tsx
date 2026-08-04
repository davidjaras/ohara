import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import { ArrowLeft, ChevronRight } from 'lucide-react'
import { api, type ProgramVariant } from '@/lib/api'
import { useProgramDetail } from '@/lib/use-program'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useLayoutContext } from '@/components/layout'

/** "4 días/semana · gimnasio" — the routine described by what it asks of you. */
function routineLabel(variant: ProgramVariant, t: TFunction) {
  const parts: string[] = []
  if (variant.days_per_week) {
    parts.push(t('training.routineDays', { count: variant.days_per_week }))
  }
  if (variant.environment === 'gym') parts.push(t('training.envGym'))
  if (variant.environment === 'home') parts.push(t('training.envHome'))
  return parts.length > 0 ? parts.join(' · ') : variant.slug
}

/** Second screen: pick the routine, then walk into a phase. */
export function TrainingProgramPage() {
  const { t } = useTranslation()
  const { slug } = useParams()
  const [searchParams] = useSearchParams()
  const mustPick = searchParams.get('pick') === '1'
  const { training, refreshTraining } = useLayoutContext()
  const { detail, error: loadError } = useProgramDetail(slug)
  const [viewedVariantId, setViewedVariantId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const activeVariantId = training?.active_variant?.id ?? null

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

  const activateRoutine = (variantId: number) => {
    setError(null)
    api.training.updateProfile({ active_variant: variantId }).then(
      () => refreshTraining(),
      (e: Error) => setError(e.message),
    )
  }

  if (loadError) {
    return <p className="py-10 text-center text-sm text-destructive">{loadError}</p>
  }
  if (!detail) {
    return <p className="py-10 text-center text-sm text-muted-foreground">{t('training.loading')}</p>
  }

  const hasRoutines = detail.variants.length > 1

  return (
    <div className="mx-auto grid w-full max-w-lg gap-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/training" aria-label={t('training.backToPrograms')}>
            <ArrowLeft className="size-5" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold">{detail.name}</h1>
          {detail.coach && (
            <p className="truncate text-sm text-muted-foreground">
              {t('training.coach', { coach: detail.coach })}
            </p>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {hasRoutines && (
        <Card className={cn(mustPick && 'ring-2 ring-primary')}>
          <CardHeader>
            <CardTitle>{t('training.routineTitle')}</CardTitle>
            <CardDescription>
              {mustPick ? t('training.pickRoutine') : t('training.routineDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            {detail.variants.map((variant) => (
              <button
                key={variant.id}
                type="button"
                onClick={() => setViewedVariantId(variant.id)}
                className={cn(
                  'flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                  variant.id === viewedVariant?.id
                    ? 'border-primary bg-accent'
                    : 'hover:bg-accent/50',
                )}
              >
                <span className="min-w-0 flex-1 truncate">{routineLabel(variant, t)}</span>
                {variant.id === activeVariantId && (
                  <span className="shrink-0 rounded bg-primary/15 px-1.5 py-0.5 text-xs text-primary">
                    {t('training.activeTag')}
                  </span>
                )}
              </button>
            ))}
            {viewedVariant && viewedVariant.id !== activeVariantId && (
              <div className="pt-1">
                <Button size="sm" onClick={() => activateRoutine(viewedVariant.id)}>
                  {t('training.useRoutine')}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {viewedVariant && viewedVariant.phases.length === 0 && (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t('training.phasesEmpty')}
        </p>
      )}

      {viewedVariant && viewedVariant.phases.length > 0 && (
        <div className="grid gap-2">
          {viewedVariant.phases.map((phase) => (
            <Card key={phase.id}>
              <Link
                to={`/training/${detail.slug}/phase/${phase.id}`}
                className="block transition-colors hover:bg-accent/40"
              >
                <CardHeader className="flex items-center gap-3">
                  <div className="grid min-w-0 flex-1 gap-1">
                    <CardTitle>
                      {t('training.phase', { number: phase.number })}
                      {phase.label && (
                        <span className="ml-2 font-normal text-muted-foreground">
                          {phase.label}
                        </span>
                      )}
                    </CardTitle>
                    <CardDescription>
                      {t('training.weeksCount', { count: phase.weeks.length })}
                    </CardDescription>
                  </div>
                  <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
                </CardHeader>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
