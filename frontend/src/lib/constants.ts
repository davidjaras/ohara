/** Domain constants shared across pages. Mirrors backend/config/settings/base.py. */

export const METRIC_ESTUDIO = 'estudio'
export const METRIC_PESO = 'peso'

/** Minutes a day has: no day can hold more time than this. */
export const MAX_DAY_MINUTES = 24 * 60
/** Minutes a week has. */
export const MAX_WEEK_MINUTES = 7 * MAX_DAY_MINUTES

/**
 * Planned-session presets (minutes) offered in the start block. One preset
 * plus "other" and "no limit": a longer row of round numbers was three taps
 * pretending to be a choice, and any other duration is one field away.
 */
export const PLANNED_PRESET_MINUTES = [25]
/** First-run default until a last-used duration is remembered. */
export const DEFAULT_PLANNED_MINUTES = 25
/** Minutes each extension adds when a planned session runs out. */
export const EXTEND_MINUTES = 15

/** Reminder presets (minutes) for no-limit sessions. */
export const REMINDER_PRESET_MINUTES = [15, 30, 45, 60]
/** Ceiling for the reminder threshold. Mirrors MAX_REMINDER_MINUTES. */
export const MAX_REMINDER_MINUTES = 120
