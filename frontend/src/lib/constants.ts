/** Domain constants shared across pages. Mirrors backend/config/settings/base.py. */

export const METRIC_ESTUDIO = 'estudio'
export const METRIC_PESO = 'peso'

/** Minutes a day has: no day can hold more time than this. */
export const MAX_DAY_MINUTES = 24 * 60
/** Minutes a week has. */
export const MAX_WEEK_MINUTES = 7 * MAX_DAY_MINUTES

/** Planned-session presets (minutes) offered in the start block. */
export const PLANNED_PRESET_MINUTES = [25, 50, 90]
/** First-run default until a last-used duration is remembered. */
export const DEFAULT_PLANNED_MINUTES = 50
/** Minutes each extension adds when a planned session runs out. */
export const EXTEND_MINUTES = 15
