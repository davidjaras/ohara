import { useCallback, useEffect, useRef, useState } from 'react'
import { Pause, Play, Square, Trash2 } from 'lucide-react'
import { api, type TimerState } from '@/lib/api'
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
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

interface TimerCardProps {
  metric: string
  onSessionSaved: () => void
}

export function TimerCard({ metric, onSessionSaved }: TimerCardProps) {
  const [timer, setTimer] = useState<TimerState | null>(null)
  // Reference point to extrapolate the server-reported elapsed time locally.
  const fetchedAtRef = useRef(performance.now())
  const [, setTick] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [finishOpen, setFinishOpen] = useState(false)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)

  const applyState = useCallback((state: TimerState) => {
    fetchedAtRef.current = performance.now()
    setTimer(state)
    setError(null)
  }, [])

  useEffect(() => {
    api.timer.get(metric).then(applyState, (e: Error) => setError(e.message))
  }, [metric, applyState])

  const running = Boolean(timer?.active && !timer.is_paused)

  // Re-render every second while the clock is running.
  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  const elapsedSeconds = timer?.active
    ? (timer.elapsed_seconds ?? 0) +
      (running ? (performance.now() - fetchedAtRef.current) / 1000 : 0)
    : 0

  const act = (action: () => Promise<TimerState>) => {
    action().then(applyState, (e: Error) => setError(e.message))
  }

  const handleFinish = () => {
    setSaving(true)
    api.timer.finish(metric, note.trim()).then(
      () => {
        setSaving(false)
        setFinishOpen(false)
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
    if (!window.confirm('¿Descartar la sesión en curso? El tiempo no se guardará.')) return
    api.timer.discard(metric).then(
      () => setTimer({ active: false }),
      (e: Error) => setError(e.message),
    )
  }

  return (
    <Card>
      <CardContent className="p-5 sm:p-6">
        {timer === null ? (
          <p className="py-6 text-center text-sm text-muted-foreground">Cargando…</p>
        ) : !timer.active ? (
          <div className="flex flex-col items-center gap-3 py-4">
            <Button size="lg" className="h-12 px-8 text-base" onClick={() => act(() => api.timer.start(metric))}>
              <Play className="size-5" />
              Iniciar sesión de estudio
            </Button>
            <p className="text-sm text-muted-foreground">
              El cronómetro sigue corriendo aunque cierres esta pestaña.
            </p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-5 py-2">
            <div className="flex items-center gap-2 text-sm">
              {timer.is_paused ? (
                <span className="text-muted-foreground">En pausa</span>
              ) : (
                <>
                  <span className="size-2 animate-pulse rounded-full bg-primary" />
                  <span className="text-primary">En curso</span>
                </>
              )}
            </div>
            <p className="font-mono text-5xl font-semibold tabular-nums sm:text-6xl">
              {formatClock(elapsedSeconds)}
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {timer.is_paused ? (
                <Button variant="outline" size="lg" onClick={() => act(() => api.timer.resume(metric))}>
                  <Play className="size-4" />
                  Reanudar
                </Button>
              ) : (
                <Button variant="outline" size="lg" onClick={() => act(() => api.timer.pause(metric))}>
                  <Pause className="size-4" />
                  Pausar
                </Button>
              )}
              <Button size="lg" onClick={() => setFinishOpen(true)}>
                <Square className="size-4" />
                Finalizar sesión
              </Button>
              <Button variant="ghost" size="lg" className="text-muted-foreground" onClick={handleDiscard}>
                <Trash2 className="size-4" />
                Descartar
              </Button>
            </div>
          </div>
        )}
        {error && <p className="mt-3 text-center text-sm text-destructive">{error}</p>}
      </CardContent>

      <Dialog open={finishOpen} onOpenChange={setFinishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Finalizar sesión</DialogTitle>
            <DialogDescription>
              Tiempo estudiado: {formatMinutes(Math.floor(elapsedSeconds / 60))}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label htmlFor="session-note">¿Qué estudiaste y qué aprendiste?</Label>
            <Textarea
              id="session-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ej. Repasé índices en Postgres; aprendí cuándo conviene un índice parcial."
              rows={4}
              autoFocus
            />
            <p className="text-sm text-muted-foreground">
              La nota queda guardada junto con la sesión.
            </p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setFinishOpen(false)} disabled={saving}>
              Cancelar
            </Button>
            <Button onClick={handleFinish} disabled={saving}>
              {saving ? 'Guardando…' : 'Guardar sesión'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
