import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { TimerOff, Trash2 } from 'lucide-react'
import { api, type Session } from '@/lib/api'
import { formatLongDate, formatMinutes, formatTimeOfDay } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface SessionReviewBannerProps {
  metric: string
  /** Bumped by the parent whenever the pending list may have changed. */
  refreshKey: number
  onResolved: () => void
}

/** ISO timestamp -> the local value a datetime-local input expects. */
function toLocalInputValue(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Resolution of auto-closed sessions: confirm the estimate as it is, adjust
 * the end time (the real start is kept), or discard. Shown one at a time,
 * oldest first, in normal flow — never a blocking modal. */
export function SessionReviewBanner({ metric, refreshKey, onResolved }: SessionReviewBannerProps) {
  const { t } = useTranslation()
  const [pending, setPending] = useState<Session[]>([])
  const [adjusting, setAdjusting] = useState(false)
  const [endValue, setEndValue] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.sessions.pendingReview(metric).then(setPending, () => setPending([]))
  }, [metric, refreshKey])

  const session: Session | undefined = pending[0]

  // Fresh local state each time a different session comes up for review.
  useEffect(() => {
    setAdjusting(false)
    setNote('')
    setError(null)
    setEndValue(session?.ended_at ? toLocalInputValue(session.ended_at) : '')
  }, [session?.id, session?.ended_at])

  if (!session) return null

  const resolve = (action: () => Promise<unknown>) => {
    setSaving(true)
    setError(null)
    action().then(
      () => {
        setSaving(false)
        onResolved()
      },
      (e: Error) => {
        setSaving(false)
        setError(e.message)
      },
    )
  }

  const handleConfirm = () =>
    resolve(() =>
      api.sessions.review(session.id, { action: 'confirm', note: note.trim() || undefined }),
    )

  const handleAdjust = () =>
    resolve(() =>
      api.sessions.review(session.id, {
        action: 'adjust',
        ended_at: new Date(endValue).toISOString(),
        note: note.trim() || undefined,
      }),
    )

  const handleDiscard = () => {
    if (!window.confirm(t('review.discardConfirm'))) return
    resolve(() => api.sessions.remove(session.id))
  }

  return (
    <Card className="ring-primary/40">
      <CardContent className="p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-md bg-primary/10 p-2">
            <TimerOff className="size-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{t('review.title')}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {t(
                session.close_reason === 'idle_timeout'
                  ? 'review.idleTimeout'
                  : 'review.plannedEnd',
              )}
            </p>
            <p className="mt-2 text-sm">
              {formatLongDate(session.date)}
              {session.started_at && (
                <> · {t('review.startedAt', { time: formatTimeOfDay(session.started_at) })}</>
              )}
              {' · '}
              <span className="whitespace-nowrap text-primary">
                {formatMinutes(session.minutes)}
              </span>
            </p>

            {adjusting && (
              <div className="mt-3 grid gap-2">
                <Label htmlFor="review-end">{t('review.adjustLabel')}</Label>
                <Input
                  id="review-end"
                  type="datetime-local"
                  className="sm:w-64"
                  value={endValue}
                  onChange={(e) => setEndValue(e.target.value)}
                />
                <p className="text-sm text-muted-foreground">{t('review.adjustHint')}</p>
              </div>
            )}

            <div className="mt-3 grid gap-2">
              <Label htmlFor="review-note">{t('review.noteLabel')}</Label>
              <Textarea
                id="review-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder={t('timer.notePlaceholder')}
                rows={2}
              />
            </div>

            {error && <p className="mt-2 text-sm text-destructive">{error}</p>}

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {adjusting ? (
                <>
                  <Button onClick={handleAdjust} disabled={saving || !endValue}>
                    {t('review.save')}
                  </Button>
                  <Button variant="ghost" onClick={() => setAdjusting(false)} disabled={saving}>
                    {t('review.cancel')}
                  </Button>
                </>
              ) : (
                <>
                  <Button onClick={handleConfirm} disabled={saving}>
                    {t('review.confirm')}
                  </Button>
                  <Button variant="outline" onClick={() => setAdjusting(true)} disabled={saving}>
                    {t('review.adjust')}
                  </Button>
                  <Button
                    variant="ghost"
                    className="text-muted-foreground"
                    onClick={handleDiscard}
                    disabled={saving}
                  >
                    <Trash2 className="size-4" />
                    {t('review.discard')}
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
