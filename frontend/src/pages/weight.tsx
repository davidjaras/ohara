import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Scale, Trash2 } from 'lucide-react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api, type Measurement } from '@/lib/api'
import { formatLongDate, formatShortDate, todayISO } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const METRIC = 'peso'

function WeightChart({ data }: { data: Measurement[] }) {
  // Oldest first, one point per date (the most recent entry wins).
  const points = useMemo(() => {
    const byDate = new Map<string, number>()
    for (const row of [...data].reverse()) byDate.set(row.date, Number(row.value))
    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, value]) => ({ date, value }))
  }, [data])

  if (points.length < 2) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        Registrá al menos dos mediciones para ver la evolución.
      </p>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="oklch(1 0 0 / 7%)" />
        <XAxis
          dataKey="date"
          tickFormatter={formatShortDate}
          tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis
          domain={['dataMin - 1', 'dataMax + 1']}
          tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => v.toFixed(1)}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const point = payload[0].payload as { date: string; value: number }
            return (
              <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
                <p className="mb-1 font-medium text-foreground">{formatShortDate(point.date)}</p>
                <p className="text-muted-foreground">{point.value.toFixed(1)} kg</p>
              </div>
            )
          }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="var(--chart-1)"
          strokeWidth={2}
          dot={{ r: 4, fill: 'var(--chart-1)', stroke: 'var(--card)', strokeWidth: 2 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function WeightForm({ onSaved }: { onSaved: () => void }) {
  const [date, setDate] = useState(todayISO())
  const [value, setValue] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    api.measurements.create({ metric: METRIC, date, value: Number(value), note: '' }).then(
      () => {
        setSaving(false)
        setValue('')
        onSaved()
      },
      (err: Error) => {
        setSaving(false)
        setError(err.message)
      },
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registrar peso</CardTitle>
        <CardDescription>Una medición puntual por fecha.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="weight-date">Fecha</Label>
              <Input
                id="weight-date"
                type="date"
                value={date}
                max={todayISO()}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="weight-value">Peso (kg)</Label>
              <Input
                id="weight-value"
                type="number"
                step="0.1"
                min={1}
                placeholder="78.4"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                required
              />
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div>
            <Button type="submit" disabled={saving || !value}>
              {saving ? 'Guardando…' : 'Guardar medición'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export function WeightPage() {
  const [rows, setRows] = useState<Measurement[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.measurements.list(METRIC).then(setRows, (e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

  const handleDelete = (row: Measurement) => {
    if (!window.confirm(`¿Borrar la medición del ${formatLongDate(row.date)}?`)) return
    api.measurements.remove(row.id).then(load, (e: Error) => setError(e.message))
  }

  return (
    <div className="grid gap-4 sm:gap-5">
      <WeightForm onSaved={load} />
      <Card>
        <CardHeader>
          <CardTitle>Evolución</CardTitle>
          <CardDescription>Peso en el tiempo</CardDescription>
        </CardHeader>
        <CardContent>
          <WeightChart data={rows} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Mediciones</CardTitle>
          <CardDescription>Las más recientes primero.</CardDescription>
        </CardHeader>
        <CardContent>
          {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
          {rows.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Todavía no hay mediciones.
            </p>
          ) : (
            <ul className="divide-y">
              {rows.map((row) => (
                <li key={row.id} className="flex items-center gap-3 py-3">
                  <div className="rounded-md bg-accent p-2">
                    <Scale className="size-4 text-muted-foreground" />
                  </div>
                  <p className="min-w-0 flex-1 text-sm font-medium">
                    {formatLongDate(row.date)}
                    <span className="ml-2 whitespace-nowrap text-primary">
                      {Number(row.value).toFixed(1)} kg
                    </span>
                  </p>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-destructive"
                    onClick={() => handleDelete(row)}
                    aria-label="Borrar medición"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
