import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Pause, Play, Plus, Square, Trash2 } from 'lucide-react'
import { api, ApiError, type TimerState } from '@/lib/api'
import {
  DEFAULT_PLANNED_MINUTES,
  EXTEND_MINUTES,
  MAX_DAY_MINUTES,
  PLANNED_PRESET_MINUTES,
} from '@/lib/constants'
import { formatClock, formatMinutes } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { RangeSelect } from '@/components/range-select'
import { TimerRing } from '@/components/timer-ring'

interface TimerCardProps {
  metric: string
  onSessionSaved: () => void
}

// The habitual block: the last planned duration the user picked.
const LAST_PLANNED_KEY = 'ohara-last-planned-minutes'

type DurationChoice = number | 'custom' | 'none'

function storedPlannedMinutes(): number {
  const raw = Number(localStorage.getItem(LAST_PLANNED_KEY))
  return Number.isInteger(raw) && raw >= 1 && raw <= MAX_DAY_MINUTES
    ? raw
    : DEFAULT_PLANNED_MINUTES
}

export function TimerCard({ metric, onSessionSaved }: TimerCardProps) {
  const { t } = useTranslation()
  const [timer, setTimer] = useState<TimerState | null>(null)
  // Reference point to extrapolate the server-reported elapsed time locally.
  const fetchedAtRef = useRef(performance.now())
  const [, setTick] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [finishOpen, setFinishOpen] = useState(false)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  // Whether *we* paused the clock to open the finish dialog: only then does
  // cancelling resume it. A timer you had already paused stays paused.
  const [pausedForFinish, setPausedForFinish] = useState(false)
  const [pausing, setPausing] = useState(false)
  // In-flight guard for the refetch that lets the server auto-close.
  const finalizingRef = useRef(false)

  const [choice, setChoice] = useState<DurationChoice>(() => {
    const stored = storedPlannedMinutes()
    return PLANNED_PRESET_MINUTES.includes(stored) ? stored : 'custom'
  })
  const [customMinutes, setCustomMinutes] = useState(() => {
    const stored = storedPlannedMinutes()
    return PLANNED_PRESET_MINUTES.includes(stored) ? '' : String(stored)
  })

  const applyState = useCallback((state: TimerState) => {
    fetchedAtRef.current = performance.now()
    setTimer(state)
    setError(null)
  }, [])

  const refresh = useCallback(() => {
    api.timer.get(metric).then(applyState, (e: Error) => setError(e.message))
  }, [metric, applyState])

  useEffect(refresh, [refresh])

  const running = Boolean(timer?.active && !timer.is_paused)

  // Re-render every second while the clock is running.
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setTick((n) => n + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  const elapsedSeconds = timer?.active
    ? (timer.elapsed_seconds ?? 0) +
      (running ? (performance.now() - fetchedAtRef.current) / 1000 : 0)
    : 0

  const planned = timer?.active ? (timer.planned_duration_seconds ?? null) : null
  const graceSeconds = timer?.grace_seconds ?? 0
  const remaining = planned !== null ? planned - elapsedSeconds : 0
  const inGrace = planned !== null && remaining <= 0

  // No-limit sessions run on a reminder cycle instead of a countdown.
  const interval =
    timer?.active && planned === null ? (timer.reminder_interval_seconds ?? null) : null
  const sinceConfirmed = interval !== null ? elapsedSeconds - (timer?.confirmed_seconds ?? 0) : 0
  const inReminder = interval !== null && sinceConfirmed >= interval

  const dueAtSeconds =
    planned !== null
      ? planned + graceSeconds
      : interval !== null
        ? (timer?.confirmed_seconds ?? 0) + 2 * interval
        : null

  // When the local clock crosses the auto-close deadline, ask the server:
  // that query is what finalizes the session (there is no background job),
  // and the {active: false} response collapses this card to the start block.
  useEffect(() => {
    if (!running || dueAtSeconds === null) return
    if (elapsedSeconds < dueAtSeconds + 2 || finalizingRef.current) return
    finalizingRef.current = true
    api.timer.get(metric).then(
      (state) => {
        finalizingRef.current = false
        applyState(state)
        if (!state.active) onSessionSaved()
      },
      () => {
        finalizingRef.current = false
      },
    )
  })

  const act = (action: () => Promise<TimerState>) => {
    action().then(applyState, (e: Error) => {
      // A conflict usually means the timer expired server-side: refetch
      // instead of surfacing a dead error, and let the dashboard show the
      // review banner.
      if (e instanceof ApiError && e.status === 409) {
        refresh()
        onSessionSaved()
        return
      }
      setError(e.message)
    })
  }

  const customInvalid =
    choice === 'custom' &&
    (!Number.isInteger(Number(customMinutes)) ||
      Number(customMinutes) < 1 ||
      Number(customMinutes) > MAX_DAY_MINUTES)

  const handleStart = () => {
    const minutes =
      choice === 'none' ? null : choice === 'custom' ? Number(customMinutes) : choice
    if (minutes !== null) localStorage.setItem(LAST_PLANNED_KEY, String(minutes))
    act(() => api.timer.start(metric, minutes))
  }

  // The time spent writing the note is not study time, so the clock stops
  // while the dialog is open. The pause is real (not just visual): that is
  // what makes `finish` record the right duration, and closing the tab
  // mid-note leaves the timer paused, which is the honest state.
  const openFinish = () => {
    setFinishOpen(true)
    if (!running) return
    setPausing(true)
    api.timer.pause(metric).then(
      (state) => {
        setPausing(false)
        setPausedForFinish(true)
        applyState(state)
      },
      (e: Error) => {
        setPausing(false)
        setError(e.message)
      },
    )
  }

  const closeFinish = () => {
    setFinishOpen(false)
    if (!pausedForFinish) return
    setPausedForFinish(false)
    act(() => api.timer.resume(metric))
  }

  const handleFinish = () => {
    setSaving(true)
    api.timer.finish(metric, note.trim()).then(
      () => {
        setSaving(false)
        setFinishOpen(false)
        setPausedForFinish(false)
        setNote('')
        setTimer({ active: false })
        onSessionSaved()
      },
      (e: Error) => {
        setSaving(false)
        setError(e.message)
      },
    )
  }

  const handleDiscard = () => {
    if (!window.confirm(t('timer.discardConfirm'))) return
    api.timer.discard(metric).then(
      () => setTimer({ active: false }),
      (e: Error) => setError(e.message),
    )
  }

  const clock = (seconds: number) => (
    <p className="font-mono text-4xl font-semibold tabular-nums sm:text-5xl">
      {formatClock(seconds)}
    </p>
  )

  return (
    <Card>
      <CardContent className="p-5 sm:p-6">
        {timer === null ? (
          <p className="py-6 text-center text-sm text-muted-foreground">{t('timer.loading')}</p>
        ) : !timer.active ? (
          <div className="flex flex-col items-center gap-4 py-4">
            <RangeSelect<DurationChoice>
              options={[
                ...PLANNED_PRESET_MINUTES.map((minutes) => ({
                  value: minutes as DurationChoice,
                  label: t('timer.presetMinutes', { count: minutes }),
                })),
                { value: 'custom', label: t('timer.custom') },
                { value: 'none', label: t('timer.noLimit') },
              ]}
              value={choice}
              onChange={setChoice}
            />
            {choice === 'custom' && (
              <Input
                type="number"
                min={1}
                max={MAX_DAY_MINUTES}
                step={1}
                placeholder="40"
                aria-label={t('timer.customMinutes')}
                className="w-32 text-center"
                value={customMinutes}
                onChange={(e) => setCustomMinutes(e.target.value)}
              />
            )}
            <Button
              size="lg"
              className="h-12 px-8 text-base"
              onClick={handleStart}
              disabled={customInvalid}
            >
              <Play className="size-5" />
              {t('timer.start')}
            </Button>
            <p className="text-sm text-muted-foreground">{t('timer.keepsRunning')}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 py-2">
            <div className="flex items-center gap-2 text-sm">
              {timer.is_paused ? (
                <span className="text-muted-foreground">{t('timer.paused')}</span>
              ) : (
                <>
                  <span className="size-2 animate-pulse rounded-full bg-primary" />
                  <span className="text-primary">{t('timer.running')}</span>
                </>
              )}
            </div>
            {planned !== null ? (
              <TimerRing progress={elapsedSeconds / planned} mode="planned">
                {clock(Math.max(0, remaining))}
                {inGrace ? (
                  <p className="text-sm font-medium text-primary">{t('timer.timeUp')}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t('timer.plannedOf', { duration: formatMinutes(planned / 60) })}
                  </p>
                )}
              </TimerRing>
            ) : interval !== null ? (
              <TimerRing progress={sinceConfirmed / interval} mode="cycle">
                {clock(elapsedSeconds)}
                {inReminder ? (
                  <p className="text-sm font-medium text-primary">{t('timer.stillStudying')}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    {t('timer.nextReminder', {
                      duration: formatMinutes(
                        Math.max(1, Math.ceil((interval - sinceConfirmed) / 60)),
                      ),
                    })}
                  </p>
                )}
              </TimerRing>
            ) : (
              <p className="font-mono text-5xl font-semibold tabular-nums sm:text-6xl">
                {formatClock(elapsedSeconds)}
              </p>
            )}
            {inGrace && (
              <p className="max-w-sm text-center text-sm text-muted-foreground">
                {t('timer.timeUpHint')}
              </p>
            )}
            {inReminder && (
              <p className="max-w-sm text-center text-sm text-muted-foreground">
                {t('timer.reminderHint')}
              </p>
            )}
            <div className="flex flex-wrap items-center justify-center gap-2">
              {inReminder && (
                <Button size="lg" onClick={() => act(() => api.timer.checkin(metric))}>
                  <Check className="size-4" />
                  {t('timer.checkin')}
                </Button>
              )}
              {inGrace ? (
                // Extending must cost one action and carry the same visual
                // weight as finishing: a goal is not a ceiling.
                <Button size="lg" onClick={() => act(() => api.timer.extend(metric, EXTEND_MINUTES))}>
                  <Plus className="size-4" />
                  {t('timer.extend', { minutes: EXTEND_MINUTES })}
                </Button>
              ) : timer.is_paused ? (
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => act(() => api.timer.resume(metric))}
                >
                  <Play className="size-4" />
                  {t('timer.resume')}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => act(() => api.timer.pause(metric))}
                >
                  <Pause className="size-4" />
                  {t('timer.pause')}
                </Button>
              )}
              <Button size="lg" onClick={openFinish}>
                <Square className="size-4" />
                {t('timer.finish')}
              </Button>
              <Button
                variant="ghost"
                size="lg"
                className="text-muted-foreground"
                onClick={handleDiscard}
              >
                <Trash2 className="size-4" />
                {t('timer.discard')}
              </Button>
            </div>
          </div>
        )}
        {error && <p className="mt-3 text-center text-sm text-destructive">{error}</p>}
      </CardContent>

      <Dialog open={finishOpen} onOpenChange={(open) => !open && closeFinish()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('timer.finishTitle')}</DialogTitle>
            <DialogDescription>
              {t('timer.studied', { duration: formatMinutes(Math.floor(elapsedSeconds / 60)) })}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="session-note">{t('timer.noteLabel')}</Label>
            <Textarea
              id="session-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t('timer.notePlaceholder')}
              rows={4}
              autoFocus
            />
            <p className="text-sm text-muted-foreground">{t('timer.noteHint')}</p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={closeFinish} disabled={saving}>
              {t('timer.cancel')}
            </Button>
            <Button onClick={handleFinish} disabled={saving || pausing}>
              {saving ? t('timer.saving') : t('timer.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
