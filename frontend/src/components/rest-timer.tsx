import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowRight, Check, Play, Timer } from 'lucide-react'
import type { RestRole } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

/** One rest countdown, opened from an exercise's clock icon. */
export interface RestRequest {
  /** Distinct per tap so reopening the same exercise resets the timer. */
  nonce: number
  seconds: number
  /**
   * Decides what the countdown MEANS, not just how long it is. Inside a
   * superset 15 s is the A1→A2 transition and 150 s closes the round; reading
   * rest_seconds without the role would make the user wait 2:30 between the
   * two exercises of the pair.
   */
  role: RestRole
  /** "A2 · Flat DB Flyes" — shown only for superset transitions. */
  nextLabel?: string
}

const DONE_DISMISS_MS = 4000

export function RestTimer({
  request,
  onDismiss,
}: {
  request: RestRequest
  onDismiss: () => void
}) {
  const { t } = useTranslation()
  // null = ready, waiting for play; set to the end timestamp once running.
  const [endAt, setEndAt] = useState<number | null>(null)
  const [remaining, setRemaining] = useState(request.seconds)

  useEffect(() => {
    // A new request reopens in the ready state.
    setEndAt(null)
    setRemaining(request.seconds)
  }, [request])

  useEffect(() => {
    if (endAt === null) return
    // Timestamp-based so a backgrounded tab still counts down correctly.
    const tick = window.setInterval(() => {
      setRemaining(Math.max(0, Math.round((endAt - Date.now()) / 1000)))
    }, 250)
    return () => window.clearInterval(tick)
  }, [endAt])

  const running = endAt !== null
  const done = running && remaining <= 0

  useEffect(() => {
    if (!done) return
    const timeout = window.setTimeout(onDismiss, DONE_DISMISS_MS)
    return () => window.clearTimeout(timeout)
  }, [done, onDismiss])

  const isTransition = request.role === 'superset_transition'
  const title = isTransition
    ? t('training.restTimerTransition', { label: request.nextLabel ?? '' })
    : request.role === 'superset_round_end'
      ? t('training.restTimerRoundEnd')
      : t('training.restTimerBetween')

  return (
    <div className="fixed inset-x-4 bottom-20 z-30 mx-auto max-w-md sm:bottom-6">
      <div
        className={cn(
          'flex items-center gap-3 rounded-lg border bg-card px-4 py-3 shadow-lg',
          isTransition && 'border-primary',
        )}
      >
        <div className={cn('rounded-md bg-accent p-2', done && 'bg-primary/15')}>
          {done ? (
            <Check className="size-4 text-primary" />
          ) : isTransition ? (
            <ArrowRight className="size-4 text-primary" />
          ) : (
            <Timer className="size-4 text-muted-foreground" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">
            {done ? t('training.restDone') : title}
          </p>
          <p className="font-mono text-lg tabular-nums text-primary">{remaining}</p>
        </div>
        {!running && (
          <Button size="sm" onClick={() => setEndAt(Date.now() + request.seconds * 1000)}>
            <Play className="size-4" />
            {t('training.restStart')}
          </Button>
        )}
        <Button variant="ghost" size="sm" onClick={onDismiss}>
          {t('training.restSkip')}
        </Button>
      </div>
    </div>
  )
}
