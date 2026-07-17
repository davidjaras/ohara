import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailyPoint, WeekSummary } from '@/lib/api'
import { formatDayTick, formatMinutes, formatShortDate, formatWeekRange } from '@/lib/format'

// Colors come from the theme so charts follow the design tokens.
const ACCENT = 'var(--chart-1)'
const DIMMED = 'var(--chart-2)'
const GRID = 'oklch(1 0 0 / 7%)'
const TICK = { fill: 'var(--muted-foreground)', fontSize: 12 }
const HOVER_CURSOR = { fill: 'oklch(1 0 0 / 6%)' }

interface TooltipRow {
  title: string
  lines: string[]
}

function ChartTooltip({ title, lines }: TooltipRow) {
  return (
    <div className="rounded-md border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-foreground">{title}</p>
      {lines.map((line) => (
        <p key={line} className="text-muted-foreground">
          {line}
        </p>
      ))}
    </div>
  )
}

export function DailyChart({ data }: { data: DailyPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDayTick}
          tick={TICK}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis tick={TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip
          cursor={HOVER_CURSOR}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const point = payload[0].payload as DailyPoint
            return (
              <ChartTooltip
                title={formatDayTick(point.date)}
                lines={[formatMinutes(point.minutes)]}
              />
            )
          }}
        />
        <Bar dataKey="minutes" fill={ACCENT} radius={[4, 4, 0, 0]} maxBarSize={24} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function WeeklyChart({ data }: { data: WeekSummary[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          dataKey="week_start"
          tickFormatter={formatShortDate}
          tick={TICK}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={24}
        />
        <YAxis tick={TICK} tickLine={false} axisLine={false} allowDecimals={false} />
        <Tooltip
          cursor={HOVER_CURSOR}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const week = payload[0].payload as WeekSummary
            return (
              <ChartTooltip
                title={`Semana del ${formatWeekRange(week.week_start)}`}
                lines={[
                  formatMinutes(week.minutes),
                  `Meta: ${formatMinutes(week.goal_minutes)}`,
                  week.met ? 'Meta cumplida ✓' : 'Meta no cumplida',
                ]}
              />
            )
          }}
        />
        {/* Weeks that met their goal are emerald; the rest stay dimmed. */}
        <Bar dataKey="minutes" radius={[4, 4, 0, 0]} maxBarSize={24}>
          {data.map((week) => (
            <Cell key={week.week_start} fill={week.met ? ACCENT : DIMMED} />
          ))}
        </Bar>
        {/* Step line showing the goal in effect on each week. */}
        <Line
          type="stepAfter"
          dataKey="goal_minutes"
          stroke="oklch(1 0 0 / 35%)"
          strokeWidth={2}
          strokeDasharray="4 4"
          dot={false}
          activeDot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
