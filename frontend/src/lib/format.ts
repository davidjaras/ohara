// Date and duration formatting helpers (Spanish UI).

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

const shortDay = new Intl.DateTimeFormat('es', { weekday: 'short' })
const shortDate = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short' })
const longDate = new Intl.DateTimeFormat('es', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
})

/** "lun 6" — tick label for daily charts. */
export function formatDayTick(iso: string): string {
  const d = parseISODate(iso)
  return `${shortDay.format(d)} ${d.getDate()}`
}

/** "6 jul" — start-of-week label. */
export function formatShortDate(iso: string): string {
  return shortDate.format(parseISODate(iso))
}

/** "6 – 12 jul" (or "29 jun – 5 jul" across months) — week range label. */
export function formatWeekRange(weekStartISO: string): string {
  const start = parseISODate(weekStartISO)
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  const startLabel =
    start.getMonth() === end.getMonth() ? String(start.getDate()) : shortDate.format(start)
  return `${startLabel} – ${shortDate.format(end)}`
}

/** "lunes, 6 de julio" — headers and lists. */
export function formatLongDate(iso: string): string {
  return longDate.format(parseISODate(iso))
}
