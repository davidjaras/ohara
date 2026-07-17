import { useEffect, useState, type FormEvent } from 'react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const METRIC = 'estudio'

export function SettingsPage() {
  const [minutes, setMinutes] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.goal.get(METRIC).then(
      (goal) => setMinutes(String(goal.minutes)),
      (e: Error) => setError(e.message),
    )
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)
    api.goal.set(METRIC, Number(minutes)).then(
      (goal) => {
        setSaving(false)
        setMinutes(String(goal.minutes))
        setMessage('Meta actualizada. Aplica desde esta semana; las pasadas no cambian.')
      },
      (err: Error) => {
        setSaving(false)
        setError(err.message)
      },
    )
  }

  return (
    <div className="mx-auto grid max-w-xl gap-4 sm:gap-5">
      <Card>
        <CardHeader>
          <CardTitle>Meta semanal</CardTitle>
          <CardDescription>
            Minutos de estudio por semana. El default es 270 (3 sesiones de 90).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="goal-minutes">Minutos por semana</Label>
              <Input
                id="goal-minutes"
                type="number"
                min={1}
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                required
              />
              <p className="text-sm text-muted-foreground">
                Los cambios aplican de esta semana en adelante; las semanas pasadas se
                evalúan con la meta que tenían.
              </p>
            </div>
            {message && <p className="text-sm text-primary">{message}</p>}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div>
              <Button type="submit" disabled={saving || !minutes}>
                {saving ? 'Guardando…' : 'Guardar meta'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
