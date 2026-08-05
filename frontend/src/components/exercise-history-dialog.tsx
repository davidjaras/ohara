import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type ExerciseHistory, type TrainingExercise } from '@/lib/api'
import { formatShortDate } from '@/lib/format'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/** "40 × 10" — the same shape the day screen prints inline. */
function setLabel(weight: string | null, reps: number | null): string {
  const load = weight === null ? null : String(Number(weight))
  const count = reps === null ? '—' : String(reps)
  return load === null ? count : `${load}×${count}`
}

/**
 * Every session in which this exercise was actually performed, newest first.
 * Keyed server-side on the performed exercise, so a substituted set appears
 * under what was done — including the imported historical logs.
 */
export function ExerciseHistoryDialog({
  exercise,
  onClose,
}: {
  exercise: TrainingExercise | null
  onClose: () => void
}) {
  const { t } = useTranslation()
  const [history, setHistory] = useState<ExerciseHistory | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!exercise) return
    let cancelled = false
    setHistory(null)
    setError(null)
    api.training.exerciseHistory(exercise.id).then(
      (data) => !cancelled && setHistory(data),
      (e: Error) => !cancelled && setError(e.message),
    )
    return () => {
      cancelled = true
    }
  }, [exercise])

  return (
    <Dialog open={exercise !== null} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{exercise?.name}</DialogTitle>
          <DialogDescription>{t('training.historyDescription')}</DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {!history && !error && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t('training.loading')}
          </p>
        )}

        {history && history.sessions.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t('training.historyEmpty')}
          </p>
        )}

        {history && history.sessions.length > 0 && (
          <ul className="grid max-h-80 gap-3 overflow-y-auto">
            {history.sessions.map((session) => (
              <li key={session.id} className="grid gap-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-sm font-medium">
                    {/* Imported rows carry no date; the source had none. */}
                    {session.performed_on
                      ? formatShortDate(session.performed_on)
                      : t('training.historyUndated')}
                  </span>
                  <span className="truncate text-xs text-muted-foreground">
                    {session.day_name}
                  </span>
                </div>
                <p className="flex flex-wrap gap-x-2 gap-y-1 text-sm text-muted-foreground">
                  {session.sets.map((set) => (
                    <span key={set.set_number}>
                      {setLabel(set.weight, set.reps)}
                      {set.was_substituted && (
                        <sup className="ml-0.5 text-[9px] text-primary">
                          {t('training.historySubstituted')}
                        </sup>
                      )}
                    </span>
                  ))}
                </p>
              </li>
            ))}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  )
}
