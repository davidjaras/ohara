import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
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
import { RangeSelect } from '@/components/range-select'

const METRIC = 'peso'

type WeightRange = '1m' | '3m' | '1y' | 'all'

const RANGE_DAYS: Record<Exclude<WeightRange, 'all'>, number> = {
  '1m': 30,
  '3m': 91,
  '1y': 365,
}

function WeightChart({ data, range }: { data: Measurement[]; range: WeightRange }) {
  const { t } = useTranslation()

  // Oldest first, one point per date (the most recent entry wins), limited
  // to the selected range.
  const points = useMemo(() => {
    let rows = data
    if (range !== 'all') {
      const cutoff = new Date()
      cutoff.setDate(cutoff.getDate() - RANGE_DAYS[range])
      const cutoffISO = cutoff.toISOString().slice(0, 10)
      rows = data.filter((row) => row.date >= cutoffISO)
    }
    const byDate = new Map<string, number>()
    for (const row of [...rows].reverse()) byDate.set(row.date, Number(row.value))
    return [...byDate.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, value]) => ({ date, value }))
  }, [data, range])

  if (points.length < 2) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">{t('weight.needTwo')}</p>
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
  const { t } = useTranslation()
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
        <CardTitle>{t('weight.formTitle')}</CardTitle>
        <CardDescription>{t('weight.formDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="weight-date">{t('weight.date')}</Label>
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
              <Label htmlFor="weight-value">{t('weight.value')}</Label>
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
              {saving ? t('weight.saving') : t('weight.save')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

export function WeightPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Measurement[]>([])
  const [range, setRange] = useState<WeightRange>('3m')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.measurements.list(METRIC).then(setRows, (e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

  const handleDelete = (row: Measurement) => {
    if (!window.confirm(t('weight.deleteConfirm', { date: formatLongDate(row.date) }))) return
    api.measurements.remove(row.id).then(load, (e: Error) => setError(e.message))
  }

  return (
    <div className="grid gap-4 sm:gap-5">
      <WeightForm onSaved={load} />
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
          <div className="grid gap-1.5">
            <CardTitle>{t('weight.chartTitle')}</CardTitle>
            <CardDescription>{t('weight.chartDescription')}</CardDescription>
          </div>
          <RangeSelect
            options={[
              { value: '1m' as const, label: t('ranges.month') },
              { value: '3m' as const, label: t('ranges.quarter') },
              { value: '1y' as const, label: t('ranges.year') },
              { value: 'all' as const, label: t('ranges.all') },
            ]}
            value={range}
            onChange={setRange}
          />
        </CardHeader>
        <CardContent>
          <WeightChart data={rows} range={range} />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>{t('weight.listTitle')}</CardTitle>
          <CardDescription>{t('weight.listDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
          {rows.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t('weight.empty')}</p>
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
                    aria-label={t('weight.deleteLabel')}
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
