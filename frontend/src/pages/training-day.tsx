import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, ArrowLeftRight, Check, Timer } from 'lucide-react'
import {
  api,
  type ExerciseSlot,
  type SetLog,
  type SetPrescription,
  type Substitution,
  type TrainingExercise,
  type WorkoutDayDetail,
  type WorkoutSession,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useLayoutContext } from '@/components/layout'
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

function memberLabel(slot: ExerciseSlot): string {
  return slot.series_position !== null
    ? `${slot.series_label}${slot.series_position}`
    : ''
}

function setKey(slot: ExerciseSlot, prescription: SetPrescription): string {
  return `${slot.id}:${prescription.set_number}`
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

/** Shared column template so the header and every row align. */
const TABLE_GRID =
  'grid grid-cols-[2rem_minmax(0,1fr)_minmax(0,1fr)_4.5rem_3.5rem_2rem] items-center gap-x-2'

function SetRow({
  prescription,
  log,
  saving,
  onLog,
  onUnlog,
}: {
  prescription: SetPrescription
  log: SetLog | undefined
  saving: boolean
  onLog: (weight: number | null, reps: number | null) => void
  onUnlog: () => void
}) {
  const { t } = useTranslation()
  const [weight, setWeight] = useState('')
  const [reps, setReps] = useState(() => initialReps(prescription))
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
            : 'text-transparent hover:border-primary',
          saving && 'opacity-50',
        )}
      >
        <Check className="size-3.5" />
      </button>
    </div>
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
  onLog: (prescription: SetPrescription, weight: number | null, reps: number | null) => void
  onUnlog: (prescription: SetPrescription, log: SetLog) => void
}) {
  const { t } = useTranslation()
  const label = memberLabel(slot)
  const perSide = slot.sets.some((p) => p.reps_per_side)

  return (
    <div className="grid gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold">
            {label && <span className="mr-2 text-primary">{label}</span>}
            {slot.exercise.name}
          </p>
          {substitution && (
            <p className="text-xs text-primary">
              {t('training.substitutedBy', { name: substitution.replacement.name })}
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
                <span
                  key={i}
                  className="rounded bg-accent px-1.5 py-0.5 text-xs text-muted-foreground"
                >
                  {modifier.type.replaceAll('_', ' ')}
                </span>
              ))}
            </p>
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

      <ExerciseMedia exercise={substitution ? substitution.replacement : slot.exercise} />

      <div>
        <div className={cn(TABLE_GRID, 'pb-1 text-xs text-muted-foreground')}>
          <span className="text-center">{t('training.colSet')}</span>
          <span className="text-center">{t('training.colTempo')}</span>
          <span className="text-center">{t('training.colRest')}</span>
          <span className="text-center">
            {t('training.weightLabel', { unit: weightUnit })}
          </span>
          <span className="text-center">{t('training.colReps')}</span>
          <span />
        </div>
        <div className="grid gap-1">
          {slot.sets.map((prescription) => {
            const log = logs.get(setKey(slot, prescription))
            return (
              <SetRow
                key={prescription.id}
                prescription={prescription}
                log={log}
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
  const weekNumber = Math.max(1, Number(searchParams.get('semana')) || 1)
  const { training } = useLayoutContext()
  const weightUnit = training?.weight_unit ?? 'kg'

  const [day, setDay] = useState<WorkoutDayDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [logs, setLogs] = useState<Map<string, SetLog>>(new Map())
  const [substitutions, setSubstitutions] = useState<Record<number, Substitution>>({})
  const [substituting, setSubstituting] = useState<ExerciseSlot | null>(null)
  const [rest, setRest] = useState<RestRequest | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [completedAt, setCompletedAt] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [completing, setCompleting] = useState(false)

  // One workout session per visit, created on the first logged set.
  const sessionPromise = useRef<Promise<WorkoutSession> | null>(null)

  useEffect(() => {
    api.training.day(Number(dayId)).then(setDay, (e: Error) => setError(e.message))
  }, [dayId])

  const ensureSession = useCallback((): Promise<WorkoutSession> => {
    if (!sessionPromise.current) {
      sessionPromise.current = api.training.sessions
        .create({ day: Number(dayId), week_number: weekNumber })
        .then((session) => {
          setSessionId(session.id)
          return session
        })
      sessionPromise.current.catch(() => {
        sessionPromise.current = null
      })
    }
    return sessionPromise.current
  }, [dayId, weekNumber])

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

  const handleSubstituted = useCallback((slotId: number, substitution: Substitution) => {
    setSubstitutions((prev) => ({ ...prev, [slotId]: substitution }))
  }, [])

  if (error && !day) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }
  if (!day) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        {t('training.loading')}
      </p>
    )
  }

  const groups = groupSlots(day.slots)

  return (
    <div className="mx-auto grid w-full max-w-lg gap-4 sm:gap-5">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/entrenamiento" aria-label={t('nav.training')}>
            <ArrowLeft className="size-5" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-semibold">{day.name}</h1>
          <p className="text-sm text-muted-foreground">
            {t('training.week', { number: weekNumber })}
          </p>
        </div>
        {completedAt && (
          <span className="rounded bg-primary/15 px-2 py-1 text-sm text-primary">
            {t('training.dayCompleted')}
          </span>
        )}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {groups.map((group) =>
        group.label !== null ? (
          // Superset: one joined card, members divided, accent on the edge.
          <Card key={`series-${group.slots[0].id}`} className="border-l-4 border-l-primary">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                {t('training.superset', { label: group.label })}
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                {t('training.supersetHint', {
                  sequence: group.slots.map(memberLabel).join(' → '),
                })}
              </p>
            </CardHeader>
            <CardContent className="grid gap-4 divide-y [&>*:not(:first-child)]:pt-4">
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
                  onLog={(prescription, weight, reps) =>
                    logSet(slot, prescription, weight, reps)
                  }
                  onUnlog={(prescription, log) => unlogSet(slot, prescription, log)}
                />
              ))}
            </CardContent>
          </Card>
        ) : (
          <Card key={`slot-${group.slots[0].id}`}>
            <CardContent>
              <SlotBlock
                slot={group.slots[0]}
                substitution={substitutions[group.slots[0].id] ?? null}
                logs={logs}
                saving={saving}
                weightUnit={weightUnit}
                onSubstitute={() => setSubstituting(group.slots[0])}
                onOpenRest={() => openRest(group, group.slots[0])}
                onLog={(prescription, weight, reps) =>
                  logSet(group.slots[0], prescription, weight, reps)
                }
                onUnlog={(prescription, log) =>
                  unlogSet(group.slots[0], prescription, log)
                }
              />
            </CardContent>
          </Card>
        ),
      )}

      {sessionId !== null && !completedAt && (
        <div>
          <Button onClick={completeDay} disabled={completing}>
            {completing ? t('training.completingDay') : t('training.completeDay')}
          </Button>
        </div>
      )}

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
