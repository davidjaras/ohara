import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown } from 'lucide-react'
import {
  api,
  type ExerciseSlot,
  type Substitution,
  type SubstitutionOptions,
  type TrainingExercise,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

function OptionButton({
  exercise,
  selected,
  onSelect,
}: {
  exercise: TrainingExercise
  selected: boolean
  onSelect: () => void
}) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        'w-full rounded-xl border px-3 py-2.5 text-left transition-colors',
        selected
          ? 'border-primary/50 bg-primary/15'
          : 'border-glass-border bg-glass hover:bg-glass-strong',
      )}
    >
      <span className="block text-sm font-medium">{exercise.name}</span>
      <span className="mt-1 flex flex-wrap gap-1">
        {exercise.equipment_required.length === 0 ? (
          <span className="glass-subtle rounded-full px-2 py-0.5 text-xs text-muted-foreground">
            {t('training.noEquipment')}
          </span>
        ) : (
          exercise.equipment_required.map((name) => (
            <span
              key={name}
              className="glass-subtle rounded-full px-2 py-0.5 text-xs text-muted-foreground"
            >
              {name}
            </span>
          ))
        )}
      </span>
    </button>
  )
}

/**
 * Picker for replacing a slot's exercise: same-muscle options grouped by
 * setting, "At home" first and expanded, "At the gym" collapsed below.
 */
export function SubstitutionDialog({
  slot,
  sessionId,
  preselect,
  onClose,
  onSubstituted,
  onReverted,
}: {
  slot: ExerciseSlot | null
  sessionId: number | null
  /** Exercise id to open with already picked — the "la última vez hiciste X"
   *  hint hands the choice over rather than making it silently. */
  preselect?: number | null
  onClose: () => void
  onSubstituted: (slotId: number, substitution: Substitution) => void
  onReverted: (slotId: number) => void
}) {
  const { t } = useTranslation()
  const [options, setOptions] = useState<SubstitutionOptions | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [scope, setScope] = useState<'session' | 'program'>('session')
  const [gymOpen, setGymOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slot) return
    setOptions(null)
    setSelectedId(preselect ?? null)
    // Coming from the hint, the point is to stop repeating the swap by hand:
    // "todo el programa" is the answer that makes it stick.
    setScope(preselect ? 'program' : 'session')
    setGymOpen(false)
    setError(null)
    // The session decides whether a session-scoped swap counts as active.
    // Nothing is reported back on open any more: the day payload already
    // carries the substitution in force, so the card is never out of date.
    api.training.substitutions(slot.id, sessionId).then(setOptions, (e: Error) =>
      setError(e.message),
    )
  }, [slot, sessionId, preselect])

  const confirm = () => {
    if (!slot || selectedId === null) return
    setSaving(true)
    setError(null)
    api.training
      .substitute(slot.id, {
        replacement: selectedId,
        scope,
        session: scope === 'session' ? sessionId : null,
      })
      .then(
        (substitution) => {
          setSaving(false)
          onSubstituted(slot.id, substitution)
          onClose()
        },
        (e: Error) => {
          setSaving(false)
          setError(e.message)
        },
      )
  }

  const revert = () => {
    if (!slot) return
    setSaving(true)
    setError(null)
    api.training.unsubstitute(slot.id, sessionId).then(
      () => {
        setSaving(false)
        onReverted(slot.id)
        onClose()
      },
      (e: Error) => {
        setSaving(false)
        setError(e.message)
      },
    )
  }

  return (
    <Dialog open={slot !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[85svh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {/* What you are replacing is what you are currently doing, which
                after an earlier swap is the substitute, not the prescription. */}
            {t('training.substituteTitle', {
              name: slot
                ? (slot.substitution?.replacement.name ?? slot.exercise.name)
                : '',
            })}
          </DialogTitle>
          <DialogDescription>{t('training.substituteDescription')}</DialogDescription>
        </DialogHeader>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {!options && !error && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t('training.loading')}
          </p>
        )}

        {options && options.home.length === 0 && options.gym.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t('training.substituteEmpty')}
          </p>
        )}

        {options && (options.home.length > 0 || options.gym.length > 0) && (
          <div className="grid gap-4">
            {options.home.length > 0 && (
              <div className="grid gap-2">
                <p className="text-sm font-medium">{t('training.substituteHome')}</p>
                {options.home.map((exercise) => (
                  <OptionButton
                    key={exercise.id}
                    exercise={exercise}
                    selected={exercise.id === selectedId}
                    onSelect={() => setSelectedId(exercise.id)}
                  />
                ))}
              </div>
            )}
            {options.gym.length > 0 && (
              <div className="grid gap-2">
                <button
                  type="button"
                  onClick={() => setGymOpen((o) => !o)}
                  className="flex items-center justify-between text-left text-sm font-medium"
                >
                  {t('training.substituteGym')}
                  <ChevronDown
                    className={cn(
                      'size-4 text-muted-foreground transition-transform',
                      gymOpen && 'rotate-180',
                    )}
                  />
                </button>
                {gymOpen &&
                  options.gym.map((exercise) => (
                    <OptionButton
                      key={exercise.id}
                      exercise={exercise}
                      selected={exercise.id === selectedId}
                      onSelect={() => setSelectedId(exercise.id)}
                    />
                  ))}
              </div>
            )}

            <div className="grid gap-2">
              <Label>{t('training.scopeLabel')}</Label>
              <Select
                value={scope}
                onValueChange={(v) => setScope(v as 'session' | 'program')}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="session">{t('training.scopeSession')}</SelectItem>
                  <SelectItem value="program">{t('training.scopeProgram')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        <DialogFooter className="sm:justify-between">
          {/* Only offered when there is something to undo. Which swap it undoes
              is decided by the server, so it always matches the card. */}
          {slot?.substitution ? (
            <Button variant="ghost" onClick={revert} disabled={saving}>
              {t('training.revertSubstitution')}
            </Button>
          ) : (
            <span />
          )}
          <Button onClick={confirm} disabled={selectedId === null || saving}>
            {t('training.substitute')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
