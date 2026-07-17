// Date and duration formatting helpers, locale-aware via i18next.

import i18n from '@/lib/i18n'

/** "hh:mm:ss" clock for the running timer. */
export function formatClock(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  const hours = Math.floor(s / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const seconds = s % 60
  const mm = String(minutes).padStart(2, '0')
  const ss = String(seconds).padStart(2, '0')
  return hours > 0 ? `${hours}:${mm}:${ss}` : `${mm}:${ss}`
}

/** "4 h 30 min" (or "45 min") for durations shown in text. */
export function formatMinutes(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes} min`
  if (minutes === 0) return `${hours} h`
  return `${hours} h ${minutes} min`
}

/** Parse "YYYY-MM-DD" as a local date (avoids the UTC shift of new Date()). */
export function parseISODate(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}

/** Today as "YYYY-MM-DD" in local time. */
export function todayISO(): string {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

type Style = 'shortDay' | 'shortDate' | 'longDate'

const OPTIONS: Record<Style, Intl.DateTimeFormatOptions> = {
  shortDay: { weekday: 'short' },
  shortDate: { day: 'numeric', month: 'short' },
  longDate: { weekday: 'long', day: 'numeric', month: 'long' },
}

const cache = new Map<string, Intl.DateTimeFormat>()

function formatter(style: Style): Intl.DateTimeFormat {
  const key = `${i18n.language}:${style}`
  let fmt = cache.get(key)
  if (!fmt) {
    fmt = new Intl.DateTimeFormat(i18n.language, OPTIONS[style])
    cache.set(key, fmt)
  }
  return fmt
}

/** "lun 6" / "Mon 6" — tick label for daily charts. */
export function formatDayTick(iso: string): string {
  const d = parseISODate(iso)
  return `${formatter('shortDay').format(d)} ${d.getDate()}`
}

/** "6 jul" / "Jul 6" — start-of-week label. */
export function formatShortDate(iso: string): string {
  return formatter('shortDate').format(parseISODate(iso))
}

/** "6 – 12 jul" / "Jul 6 – 12" (full dates across months) — week range label. */
export function formatWeekRange(weekStartISO: string): string {
  const start = parseISODate(weekStartISO)
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  const fmt = formatter('shortDate')
  if (start.getMonth() !== end.getMonth()) {
    return `${fmt.format(start)} – ${fmt.format(end)}`
  }
  // Same month: collapse it on the side the locale writes it (day-first
  // locales drop it from the start, month-first locales from the end).
  const dayFirst = /^\d/.test(fmt.format(start))
  return dayFirst
    ? `${start.getDate()} – ${fmt.format(end)}`
    : `${fmt.format(start)} – ${end.getDate()}`
}

/** "lunes, 6 de julio" / "Monday, July 6" — headers and lists. */
export function formatLongDate(iso: string): string {
  return formatter('longDate').format(parseISODate(iso))
}
