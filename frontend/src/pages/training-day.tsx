import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeftRight, Check, History, Info, Timer } from 'lucide-react'
import {
  api,
  type ExerciseSlot,
  type Performance,
  type SetLog,
  type SetPrescription,
  type Substitution,
  type TrainingExercise,
  type WorkoutDayDetail,
  type WorkoutSession,
} from '@/lib/api'
import { formatShortDate, formatWeekdayDate, todayISO } from '@/lib/format'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/empty-state'
import { PageHeader } from '@/components/page-header'
import { Panel } from '@/components/panel'
import { Pill } from '@/components/pill'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useLayoutContext } from '@/components/layout'
import { ExerciseHistoryDialog } from '@/components/exercise-history-dialog'
import { RestTimer, type RestRequest } from '@/components/rest-timer'
import { SubstitutionDialog } from '@/components/substitution-dialog'

/** A1/A2/A3 render joined in one card; standalone slots get their own. */
interface SlotGroup {
  label: string | null
  slots: ExerciseSlot[]
}

function groupSlots(slots: ExerciseSlot[]): SlotGroup[] {
  const groups: SlotGroup[] = []
  for (const slot of slots) {
    const label = slot.is_superset ? slot.series_label : null
    const last = groups[groups.length - 1]
    if (label !== null && last && last.label === label) last.slots.push(slot)
    else groups.push({ label, slots: [slot] })
  }
  return groups
}

/** "A" for a standalone slot, "B1"/"B2" for superset members. Every slot
 *  carries the letter the coach wrote, superset or not. */
function memberLabel(slot: ExerciseSlot): string {
  return `${slot.series_label}${slot.series_position ?? ''}`
}

function setKey(slot: ExerciseSlot, prescription: SetPrescription): string {
  return `${slot.id}:${prescription.set_number}`
}

/**
 * Rebuilds the checked-set map from the session the API sends with the day.
 * Logs carry their slot, so this needs no walk of the prescription tree; a log
 * whose prescription was deleted has none and is skipped.
 */
function hydrateLogs(detail: WorkoutDayDetail): Map<string, SetLog> {
  const map = new Map<string, SetLog>()
  for (const log of detail.session?.logs ?? []) {
    if (log.slot !== null) map.set(`${log.slot}:${log.set_number}`, log)
  }
  return map
}

/**
 * The swaps in force, resolved server-side against this session's scope. They
 * arrive with the day so a reload keeps showing the exercise you are actually
 * doing instead of reverting to the prescription.
 */
function hydrateSubstitutions(detail: WorkoutDayDetail): Record<number, Substitution> {
  const map: Record<number, Substitution> = {}
  for (const slot of detail.slots) {
    if (slot.substitution) map[slot.id] = slot.substitution
  }
  return map
}

/** "40 × 10 · 40 × 10 · 35 × 8" — a past session at a glance. */
function formatSets(performance: Performance): string {
  return performance.sets
    .map((set) => {
      const weight = set.weight === null ? null : trimWeight(set.weight)
      const reps = set.reps === null ? '—' : String(set.reps)
      return weight === null ? reps : `${weight}×${reps}`
    })
    .join(' · ')
}

/** "40.00" reads as 40, "17.50" as 17.5 — trailing zeros are noise on a phone. */
function trimWeight(weight: string): string {
  const value = Number(weight)
  return Number.isFinite(value) ? String(value) : weight
}

type DayStatus = 'today' | 'late' | 'ahead' | 'offPlan'

/**
 * Where this workout sits relative to the plan. A day outside the active plan
 * is still trainable — it just says so, and never counts for adherence.
 */
function dayStatus(day: WorkoutDayDetail): DayStatus | null {
  if (!day.in_active_plan) return 'offPlan'
  if (!day.scheduled_on) return null
  const today = todayISO()
  if (day.scheduled_on === today) return 'today'
  return day.scheduled_on < today ? 'late' : 'ahead'
}

/**
 * Reserved media slot between the exercise header and the set table.
 * Renders nothing in this MVP — the ExerciseDB follow-up session
 * (exercisedb_next_session/) plugs the preview GIF in here without
 * touching the card layout.
 */
function ExerciseMedia(_props: { exercise: TrainingExercise }) {
  return null
}

/** Prefill: the target the coach expects if you just check the set. */
function initialReps(p: SetPrescription): string {
  if (p.to_failure || p.cluster_reps?.length || p.hold_seconds) return ''
  const target = p.target_reps_max ?? p.target_reps_min
  return target !== null ? String(target) : ''
}

/** Placeholder for sets whose target is not a plain number. */
function repsPlaceholder(p: SetPrescription): string {
  if (p.to_failure) return 'MAX'
  if (p.cluster_reps?.length) return p.cluster_reps.join('+')
  if (p.hold_seconds) return `${p.hold_seconds}s`
  if (p.target_reps_min !== null && p.target_reps_max !== null)
    return `${p.target_reps_min}–${p.target_reps_max}`
  return p.reps_raw
}

/**
 * The tempo digits are never emphasised: which phase the coach highlighted is
 * not in the source data (the programs ship the code as a plain number), so
 * the column explains itself instead of guessing.
 */
function TempoLegend({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('training.tempoLegendTitle')}</DialogTitle>
          <DialogDescription>{t('training.tempoLegendIntro')}</DialogDescription>
        </DialogHeader>
        <ul className="grid gap-2 text-sm">
          <li>{t('training.tempoEccentric')}</li>
          <li>{t('training.tempoBottom')}</li>
          <li>{t('training.tempoConcentric')}</li>
          <li>{t('training.tempoTop')}</li>
        </ul>
        <p className="text-xs text-muted-foreground">{t('training.tempoCompound')}</p>
      </DialogContent>
    </Dialog>
  )
}

/** Shared column template so the header and every row align. */
const TABLE_GRID =
  'grid grid-cols-[2rem_minmax(0,1fr)_minmax(0,1fr)_4.5rem_3.5rem_2rem] items-center gap-x-2'

function SetRow({
  prescription,
  log,
  lastWeight,
  saving,
  onLog,
  onUnlog,
}: {
  prescription: SetPrescription
  log: SetLog | undefined
  lastWeight: string | null
  saving: boolean
  onLog: (weight: number | null, reps: number | null) => void
  onUnlog: () => void
}) {
  const { t } = useTranslation()
  // Reopened sets show what was logged; the inputs are the row's own state
  // only while it is unchecked.
  const [weight, setWeight] = useState(() =>
    log?.weight != null ? trimWeight(log.weight) : '',
  )
  const [reps, setReps] = useState(() =>
    log?.reps != null ? String(log.reps) : initialReps(prescription),
  )
  const logged = log !== undefined

  const toggle = () => {
    if (logged) onUnlog()
    else onLog(weight === '' ? null : Number(weight), reps === '' ? null : Number(reps))
  }

  return (
    <div className={cn(TABLE_GRID, 'py-1')}>
      <span className="text-center text-sm">
        {prescription.set_number}
        {prescription.is_backoff_set && (
          <sup className="ml-0.5 text-[9px] text-muted-foreground" title={t('training.backoff')}>
            BO
          </sup>
        )}
      </span>
      <span className="truncate text-center text-sm text-muted-foreground">
        {prescription.tempo || '—'}
      </span>
      <span className="text-center text-sm text-muted-foreground">
        {prescription.rest_seconds !== null ? `${prescription.rest_seconds}s` : '—'}
      </span>
      <Input
        type="number"
        inputMode="decimal"
        step="0.5"
        min={0}
        // Last time's load is a hint, never a prefill: checking a set must not
        // record a weight that was never chosen.
        placeholder={lastWeight ?? ''}
        value={weight}
        onChange={(e) => setWeight(e.target.value)}
        disabled={logged}
        className="h-8 px-1 text-center text-sm"
        aria-label={t('training.colWeight')}
      />
      <Input
        type="number"
        inputMode="numeric"
        min={0}
        placeholder={repsPlaceholder(prescription)}
        value={reps}
        onChange={(e) => setReps(e.target.value)}
        disabled={logged}
        className="h-8 px-1 text-center text-sm"
        aria-label={t('training.colReps')}
      />
      <button
        type="button"
        disabled={saving}
        onClick={toggle}
        aria-label={t(logged ? 'training.unlogAria' : 'training.logAria', {
          number: prescription.set_number,
        })}
        className={cn(
          'mx-auto flex size-6 items-center justify-center rounded-full border transition-colors',
          logged
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-glass-border text-transparent hover:border-primary',
          saving && 'opacity-50',
        )}
      >
        <Check className="size-3.5" />
      </button>
    </div>
  )
}

/** "Última vez · 12 jul: 40×10 · 40×10 · 35×8", tappable into the full history. */
function LastPerformance({
  performance,
  onOpen,
}: {
  performance: Performance
  onOpen: () => void
}) {
  const { t } = useTranslation()
  const when = performance.performed_on
    ? formatShortDate(performance.performed_on)
    : t('training.historyUndated')

  return (
    <button
      type="button"
      onClick={onOpen}
      className="mt-1 flex w-full items-center gap-1 text-left text-xs text-muted-foreground transition-colors hover:text-foreground"
    >
      <History className="size-3 shrink-0" />
      <span className="truncate">
        {t('training.lastTime', { when, sets: formatSets(performance) })}
      </span>
    </button>
  )
}

function SlotBlock({
  slot,
  substitution,
  logs,
  saving,
  weightUnit,
  onSubstitute,
  onOpenRest,
  onOpenTempoLegend,
  onOpenHistory,
  onLog,
  onUnlog,
}: {
  slot: ExerciseSlot
  substitution: Substitution | null
  logs: Map<string, SetLog>
  saving: boolean
  weightUnit: string
  onSubstitute: () => void
  onOpenRest: () => void
  onOpenTempoLegend: () => void
  onOpenHistory: (exercise: TrainingExercise) => void
  onLog: (prescription: SetPrescription, weight: number | null, reps: number | null) => void
  onUnlog: (prescription: SetPrescription, log: SetLog) => void
}) {
  const { t } = useTranslation()
  const label = memberLabel(slot)
  const perSide = slot.sets.some((p) => p.reps_per_side)
  // The card is titled by what you are doing, not by what was prescribed:
  // after a swap the substitute IS the exercise, and its own history is the
  // one worth seeing.
  const performed = substitution ? substitution.replacement : slot.exercise
  const last = slot.last_performance

  return (
    <div className="grid gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold">
            {label && <span className="mr-2 text-primary">{label}</span>}
            {performed.name}
          </p>
          {substitution && (
            <p className="text-xs text-muted-foreground">
              {t('training.insteadOf', { name: slot.exercise.name })}
            </p>
          )}
          {(slot.coach_annotation || perSide) && (
            <p className="mt-1 text-xs text-muted-foreground">
              {[slot.coach_annotation, perSide ? t('training.perSideNote') : '']
                .filter(Boolean)
                .join(' · ')}
            </p>
          )}
          {slot.modifiers.length > 0 && (
            <p className="mt-1 flex flex-wrap gap-1">
              {slot.modifiers.map((modifier, i) => (
                <Pill key={i}>{modifier.type.replaceAll('_', ' ')}</Pill>
              ))}
            </p>
          )}
          {last ? (
            <LastPerformance
              performance={last}
              onOpen={() => onOpenHistory(performed)}
            />
          ) : (
            <button
              type="button"
              onClick={() => onOpenHistory(performed)}
              className="mt-1 flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              <History className="size-3 shrink-0" />
              {t('training.lastTimeNever')}
            </button>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {slot.sets[0]?.rest_seconds != null && slot.sets[0].rest_seconds > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="px-2 text-muted-foreground"
              onClick={onOpenRest}
              aria-label={t('training.restOpen')}
            >
              <Timer className="size-4" />
              {slot.sets[0].rest_seconds}
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground"
            onClick={onSubstitute}
            aria-label={t('training.substitute')}
          >
            <ArrowLeftRight className="size-4" />
          </Button>
        </div>
      </div>

      <ExerciseMedia exercise={performed} />

      <div>
        <div
          className={cn(
            TABLE_GRID,
            'border-b border-hairline pb-1.5 text-xs text-muted-foreground',
          )}
        >
          <span className="text-center">{t('training.colSet')}</span>
          <button
            type="button"
            onClick={onOpenTempoLegend}
            aria-label={t('training.tempoLegendOpen')}
            className="flex items-center justify-center gap-1 transition-colors hover:text-foreground"
          >
            {t('training.colTempo')}
            <Info className="size-3" />
          </button>
          <span className="text-center">{t('training.colRest')}</span>
          <span className="text-center">
            {t('training.weightLabel', { unit: weightUnit })}
          </span>
          <span className="text-center">{t('training.colReps')}</span>
          <span />
        </div>
        <div className="grid gap-1 pt-1.5">
          {slot.sets.map((prescription) => {
            const log = logs.get(setKey(slot, prescription))
            // Same set number last time when it exists, else the last set of
            // that session — a 4-set day after a 3-set one still gets a hint.
            const previous =
              last?.sets.find((s) => s.set_number === prescription.set_number) ??
              last?.sets[last.sets.length - 1]
            return (
              // Keyed on the prescription alone: unchecking a set must keep
              // the values in the inputs so they can be corrected.
              <SetRow
                key={prescription.id}
                prescription={prescription}
                log={log}
                lastWeight={previous?.weight ? trimWeight(previous.weight) : null}
                saving={saving}
                onLog={(weight, reps) => onLog(prescription, weight, reps)}
                onUnlog={() => log && onUnlog(prescription, log)}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function TrainingDayPage() {
  const { t } = useTranslation()
  const { dayId } = useParams()
  const [searchParams] = useSearchParams()
  // Where the day was opened from, so "back" lands on the phase and not at
  // the root. Absent (a shared or bookmarked link) falls back to the list.
  const fromProgram = searchParams.get('program')
  const fromPhase = searchParams.get('phase')
  const { training } = useLayoutContext()
  const weightUnit = training?.weight_unit ?? 'kg'

  const [day, setDay] = useState<WorkoutDayDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<Map<string, SetLog>>(new Map())
  const [substitutions, setSubstitutions] = useState<Record<number, Substitution>>({})
  const [substituting, setSubstituting] = useState<ExerciseSlot | null>(null)
  const [historyFor, setHistoryFor] = useState<TrainingExercise | null>(null)
  const [rest, setRest] = useState<RestRequest | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [completedAt, setCompletedAt] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [completing, setCompleting] = useState(false)
  const [tempoLegend, setTempoLegend] = useState(false)

  // Guards against two fast clicks creating two sessions; the endpoint itself
  // is idempotent per day, so a reload can never fork one either.
  const sessionPromise = useRef<Promise<WorkoutSession> | null>(null)

  // The day arrives with whatever was already logged on it and whichever
  // swaps are in force. Rebuilding that state is what makes reopening a
  // finished workout show the workout, and the substitute stay the title.
  const applyDay = useCallback((detail: WorkoutDayDetail) => {
    setDay(detail)
    setSessionId(detail.session?.id ?? null)
    setCompletedAt(detail.session?.completed_at ?? null)
    setLogs(hydrateLogs(detail))
    setSubstitutions(hydrateSubstitutions(detail))
    sessionPromise.current = detail.session ? Promise.resolve(detail.session) : null
  }, [])

  useEffect(() => {
    let cancelled = false
    api.training.day(Number(dayId)).then(
      (detail) => !cancelled && applyDay(detail),
      (e: Error) => !cancelled && setError(e.message),
    )
    return () => {
      cancelled = true
    }
  }, [dayId, applyDay])

  const backTo =
    fromProgram && fromPhase
      ? `/training/${fromProgram}/phase/${fromPhase}`
      : day
        ? `/training/${day.program_slug}/phase/${day.phase}`
        : '/training'

  const ensureSession = useCallback((): Promise<WorkoutSession> => {
    if (!sessionPromise.current) {
      sessionPromise.current = api.training.sessions
        .create({ day: Number(dayId) })
        .then((session) => {
          setSessionId(session.id)
          return session
        })
      sessionPromise.current.catch(() => {
        sessionPromise.current = null
      })
    }
    return sessionPromise.current
  }, [dayId])

  // The rest timer is opened deliberately from the exercise's clock icon and
  // waits for play — logging a set never starts it.
  const openRest = useCallback(
    (group: SlotGroup, slot: ExerciseSlot) => {
      const prescription = slot.sets[0]
      if (!prescription || prescription.rest_seconds === null) return
      let nextLabel: string | undefined
      if (prescription.rest_role === 'superset_transition') {
        const index = group.slots.indexOf(slot)
        const next = group.slots[(index + 1) % group.slots.length]
        if (next && next !== slot) {
          const substituted = substitutions[next.id]
          const name = substituted ? substituted.replacement.name : next.exercise.name
          nextLabel = `${memberLabel(next)} · ${name}`
        }
      }
      setRest({
        nonce: Date.now(),
        seconds: prescription.rest_seconds,
        role: prescription.rest_role,
        nextLabel,
      })
    },
    [substitutions],
  )

  const logSet = useCallback(
    (
      slot: ExerciseSlot,
      prescription: SetPrescription,
      weight: number | null,
      reps: number | null,
    ) => {
      setSaving(true)
      setError(null)
      ensureSession()
        .then((session) =>
          api.training.sessions.log(session.id, {
            slot: slot.id,
            set_number: prescription.set_number,
            weight,
            reps,
          }),
        )
        .then(
          (log) => {
            setSaving(false)
            setLogs((prev) => new Map(prev).set(setKey(slot, prescription), log))
          },
          (e: Error) => {
            setSaving(false)
            setError(e.message)
          },
        )
    },
    [ensureSession],
  )

  const unlogSet = useCallback(
    (slot: ExerciseSlot, prescription: SetPrescription, log: SetLog) => {
      if (sessionId === null) return
      setSaving(true)
      setError(null)
      api.training.sessions.unlog(sessionId, log.id).then(
        () => {
          setSaving(false)
          setLogs((prev) => {
            const next = new Map(prev)
            next.delete(setKey(slot, prescription))
            return next
          })
        },
        (e: Error) => {
          setSaving(false)
          setError(e.message)
        },
      )
    },
    [sessionId],
  )

  const completeDay = useCallback(() => {
    if (sessionId === null) return
    setCompleting(true)
    setError(null)
    api.training.sessions.update(sessionId, { completed: true }).then(
      (session) => {
        setCompleting(false)
        setCompletedAt(session.completed_at)
      },
      (e: Error) => {
        setCompleting(false)
        setError(e.message)
      },
    )
  }, [sessionId])

  const handleSubstituted = useCallback(
    (slotId: number, substitution: Substitution) => {
      // Retitle the card immediately, then refetch: "última vez" belongs to
      // the new exercise and only the server can resolve it.
      setSubstitutions((prev) => ({ ...prev, [slotId]: substitution }))
      api.training.day(Number(dayId)).then(applyDay, () => {})
    },
    [dayId, applyDay],
  )

  if (error && !day) {
    return <EmptyState tone="error">{error}</EmptyState>
  }
  if (!day) {
    return <EmptyState>{t('training.loading')}</EmptyState>
  }

  const groups = groupSlots(day.slots)
  const status = dayStatus(day)

  return (
    // Tighter than the other screens on purpose: this stack is a list of
    // exercises you scroll through mid-workout, not a handful of sections.
    <div className="page-stack gap-6 sm:gap-8">
      <PageHeader
        title={day.name}
        subtitle={[
          t('training.week', { number: day.plan_week ?? day.week_number }),
          day.scheduled_on ? formatWeekdayDate(day.scheduled_on) : null,
        ]
          .filter(Boolean)
          .join(' · ')}
        backTo={backTo}
        backLabel={t('training.backToPhase')}
        action={
          completedAt ? (
            <Pill tone="accent">{t('training.dayCompleted')}</Pill>
          ) : (
            status && (
              <Pill tone={status === 'today' ? 'accent' : 'muted'}>
                {t(`training.status_${status}`)}
              </Pill>
            )
          )
        }
      />

      {error && <p className="text-sm text-destructive">{error}</p>}

      {groups.map((group) =>
        group.label !== null ? (
          // Supersets are the one grouping on this screen that must read as a
          // unit, so they keep a panel and an accent edge while standalone
          // exercises are plain hairline-separated blocks.
          <Panel
            variant="subtle"
            key={`series-${group.slots[0].id}`}
            className="border-l-2 border-l-primary p-4"
          >
            <p className="text-sm font-semibold">
              {t('training.superset', { label: group.label })}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {t('training.supersetHint', {
                sequence: group.slots.map(memberLabel).join(' → '),
              })}
            </p>
            <div className="mt-4 grid gap-4 divide-y divide-hairline [&>*:not(:first-child)]:pt-4">
              {group.slots.map((slot) => (
                <SlotBlock
                  key={slot.id}
                  slot={slot}
                  substitution={substitutions[slot.id] ?? null}
                  logs={logs}
                  saving={saving}
                  weightUnit={weightUnit}
                  onSubstitute={() => setSubstituting(slot)}
                  onOpenRest={() => openRest(group, slot)}
                  onOpenTempoLegend={() => setTempoLegend(true)}
                  onOpenHistory={setHistoryFor}
                  onLog={(prescription, weight, reps) =>
                    logSet(slot, prescription, weight, reps)
                  }
                  onUnlog={(prescription, log) => unlogSet(slot, prescription, log)}
                />
              ))}
            </div>
          </Panel>
        ) : (
          <div key={`slot-${group.slots[0].id}`} className="border-t border-hairline pt-4">
              <SlotBlock
                slot={group.slots[0]}
                substitution={substitutions[group.slots[0].id] ?? null}
                logs={logs}
                saving={saving}
                weightUnit={weightUnit}
                onSubstitute={() => setSubstituting(group.slots[0])}
                onOpenRest={() => openRest(group, group.slots[0])}
                onOpenTempoLegend={() => setTempoLegend(true)}
                onOpenHistory={setHistoryFor}
                onLog={(prescription, weight, reps) =>
                  logSet(group.slots[0], prescription, weight, reps)
                }
                onUnlog={(prescription, log) =>
                  unlogSet(group.slots[0], prescription, log)
                }
              />
          </div>
        ),
      )}

      {sessionId !== null && !completedAt && (
        <div>
          <Button onClick={completeDay} disabled={completing}>
            {completing ? t('training.completingDay') : t('training.completeDay')}
          </Button>
        </div>
      )}

      <TempoLegend open={tempoLegend} onClose={() => setTempoLegend(false)} />

      <ExerciseHistoryDialog
        exercise={historyFor}
        onClose={() => setHistoryFor(null)}
      />

      <SubstitutionDialog
        slot={substituting}
        sessionId={sessionId}
        onClose={() => setSubstituting(null)}
        onSubstituted={handleSubstituted}
      />

      {rest && <RestTimer request={rest} onDismiss={() => setRest(null)} />}
    </div>
  )
}
