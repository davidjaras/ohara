import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type Program, type ProgramRun } from '@/lib/api'
import { formatShortDate, parseISODate, todayISO } from '@/lib/format'
import { routineLabel } from '@/lib/routine'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

/** The ISO Monday of that date — the only day a plan can start on. */
function mondayOf(iso: string): string {
  const date = parseISODate(iso)
  date.setDate(date.getDate() - ((date.getDay() + 6) % 7))
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${mm}-${dd}`
}

function addDays(iso: string, days: number): string {
  const date = parseISODate(iso)
  date.setDate(date.getDate() + days)
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${mm}-${dd}`
}

/** Next Monday — the default, so week 1 is a full week. */
function nextMonday(): string {
  return addDays(mondayOf(todayISO()), 7)
}

/**
 * Starting a plan: pick the routine (when there is a choice) and the Monday it
 * begins. The end date follows from the program's length, so the commitment is
 * visible before it is made.
 */
export function StartPlanDialog({
  program,
  initialVariantId = null,
  currentRun,
  onClose,
  onStarted,
}: {
  program: Program | null
  /** Preselect the routine the caller was already showing. */
  initialVariantId?: number | null
  currentRun: ProgramRun | null
  onClose: () => void
  onStarted: (run: ProgramRun) => void
}) {
  const { t } = useTranslation()
  const [variantId, setVariantId] = useState<number | null>(null)
  const [startedOn, setStartedOn] = useState(nextMonday)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!program) return
    setVariantId(initialVariantId ?? program.variants[0]?.id ?? null)
    setStartedOn(nextMonday())
    setError(null)
  }, [program, initialVariantId])

  const weeks =
    program?.variants.find((v) => v.id === variantId)?.total_weeks ?? 0
  const endsOn = useMemo(
    () => (weeks > 0 ? addDays(startedOn, weeks * 7 - 1) : null),
    [startedOn, weeks],
  )

  const start = () => {
    if (variantId === null) return
    setSaving(true)
    setError(null)
    api.training.runs.start({ variant: variantId, started_on: startedOn }).then(
      (run) => {
        setSaving(false)
        onStarted(run)
      },
      (e: Error) => {
        setSaving(false)
        setError(e.message)
      },
    )
  }

  return (
    <Dialog open={program !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('training.startPlanTitle', { name: program?.name })}</DialogTitle>
          <DialogDescription>{t('training.startPlanDescription')}</DialogDescription>
        </DialogHeader>

        {program && program.variants.length > 1 && (
          <div className="grid gap-2">
            <p className="text-sm font-medium">{t('training.startPlanRoutine')}</p>
            {program.variants.map((variant) => (
              <button
                key={variant.id}
                type="button"
                onClick={() => setVariantId(variant.id)}
                className={cn(
                  'rounded-lg border px-3 py-2 text-left text-sm transition-colors',
                  variant.id === variantId
                    ? 'border-primary bg-accent'
                    : 'hover:bg-accent/50',
                )}
              >
                {routineLabel(variant, t)}
              </button>
            ))}
          </div>
        )}

        <div className="grid gap-2">
          <label className="text-sm font-medium" htmlFor="plan-start">
            {t('training.startPlanDate')}
          </label>
          <Input
            id="plan-start"
            type="date"
            value={startedOn}
            // Any date is accepted and snapped to its Monday, here and on the
            // server, so the two can never disagree.
            onChange={(e) => e.target.value && setStartedOn(mondayOf(e.target.value))}
          />
          {endsOn && (
            <p className="text-sm text-muted-foreground">
              {t('training.startPlanSummary', {
                weeks,
                end: formatShortDate(endsOn),
              })}
            </p>
          )}
        </div>

        {currentRun && (
          <p className="text-sm text-muted-foreground">
            {t('training.startPlanReplace', { name: currentRun.program.name })}
          </p>
        )}

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div>
          <Button onClick={start} disabled={saving || variantId === null}>
            {saving ? t('training.starting') : t('training.startPlanConfirm')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
