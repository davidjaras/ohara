import { useTranslation } from 'react-i18next'
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { CumulativePoint, WeekSummary } from '@/lib/api'
import { formatDayTick, formatMinutes, formatShortDate, formatWeekRange } from '@/lib/format'

// Colors come from the theme so charts follow the design tokens.
const MET = 'var(--chart-1)' // azure: goal reached
const BELOW = 'var(--chart-2)' // neutral gray: below the goal
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

interface CumulativeWeekChartProps {
  data: CumulativePoint[]
  goal: number
}

/** Cumulative minutes across the current week, stopping at today. */
export function CumulativeWeekChart({ data, goal }: CumulativeWeekChartProps) {
  const { t } = useTranslation()

  // Pad the week out to Sunday with empty points so the axis always shows
  // the full week; the line itself deliberately stops at today.
  const monday = data.length > 0 ? new Date(`${data[0].date}T00:00:00`) : new Date()
  const points: Array<{ date: string; minutes: number | null; cumulative: number | null }> = []
  for (let i = 0; i < 7; i++) {
    const day = new Date(monday)
    day.setDate(day.getDate() + i)
    const iso = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(
      day.getDate(),
    ).padStart(2, '0')}`
    const point = data[i]
    points.push(
      point && point.date === iso
        ? { date: iso, minutes: point.minutes, cumulative: point.cumulative_minutes }
        : { date: iso, minutes: null, cumulative: null },
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={points} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDayTick}
          tick={TICK}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis
          tick={TICK}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
          domain={[0, (dataMax: number) => Math.ceil(Math.max(dataMax, goal) * 1.08)]}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const point = payload[0].payload as (typeof points)[number]
            if (point.cumulative === null) return null
            return (
              <ChartTooltip
                title={formatDayTick(point.date)}
                lines={[
                  `${t('cumulativeChart.accumulated')}: ${formatMinutes(point.cumulative)}`,
                  `+${formatMinutes(point.minutes ?? 0)}`,
                ]}
              />
            )
          }}
        />
        <ReferenceLine
          y={goal}
          stroke="oklch(1 0 0 / 35%)"
          strokeWidth={2}
          strokeDasharray="4 4"
        />
        <Line
          type="linear"
          dataKey="cumulative"
          stroke={MET}
          strokeWidth={2}
          dot={{ r: 4, fill: MET, stroke: 'var(--card)', strokeWidth: 2 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

interface WeekBarShapeProps {
  x?: number
  y?: number
  width?: number
  height?: number
  fill?: string
  radius?: number | [number, number, number, number]
  payload?: WeekSummary
}

/** Bar with an azure check drawn above it when the week met its goal.

    Implemented as a custom shape (not LabelList) so the check renders
    reliably for every bar. */
function WeekBarShape(props: WeekBarShapeProps) {
  const { x = 0, y = 0, width = 0, height = 0, fill, payload } = props
  const [rtl] = Array.isArray(props.radius) ? props.radius : [4]
  const r = Math.min(rtl ?? 4, width / 2, height)
  return (
    <g>
      {height > 0 && (
        <path
          d={`M ${x},${y + height}
              L ${x},${y + r}
              Q ${x},${y} ${x + r},${y}
              L ${x + width - r},${y}
              Q ${x + width},${y} ${x + width},${y + r}
              L ${x + width},${y + height} Z`}
          fill={fill}
        />
      )}
      {payload?.met && (
        <path
          d={`M ${x + width / 2 - 4.5} ${y - 10} l 3 3 l 6 -6.5`}
          fill="none"
          stroke={MET}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
    </g>
  )
}

export function WeeklyChart({ data }: { data: WeekSummary[] }) {
  const { t } = useTranslation()
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart data={data} margin={{ top: 18, right: 4, left: -16, bottom: 0 }}>
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
                title={t('weeklyChart.weekOf', { range: formatWeekRange(week.week_start) })}
                lines={[
                  formatMinutes(week.minutes),
                  t('weeklyChart.goal', { goal: formatMinutes(week.goal_minutes) }),
                  week.met ? t('weeklyChart.met') : t('weeklyChart.notMet'),
                ]}
              />
            )
          }}
        />
        {/* Gray while below the weekly goal, azure once it is met; the
            check above the bar is a deliberate redundant signal. */}
        <Bar
          dataKey="minutes"
          radius={[4, 4, 0, 0]}
          maxBarSize={24}
          shape={(props: unknown) => <WeekBarShape {...(props as WeekBarShapeProps)} />}
        >
          {data.map((week) => (
            <Cell key={week.week_start} fill={week.met ? MET : BELOW} />
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
