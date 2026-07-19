// Per-user accent color. The actual token values live in index.css keyed by the
// `data-accent` attribute on <html>; here we only track which one is selected,
// mirror it to localStorage for an instant, flash-free apply, and expose the
// list for the settings swatches. The `color` string is the oklch of that
// accent's --primary, used to paint the swatch (single source of truth).

const STORAGE_KEY = 'ohara-accent'

export const DEFAULT_ACCENT = 'blue'

export const ACCENTS = [
  { code: 'blue', labelKey: 'settings.accents.blue', color: 'oklch(0.77 0.14 235)' },
  { code: 'green', labelKey: 'settings.accents.green', color: 'oklch(0.77 0.152 163)' },
  { code: 'teal', labelKey: 'settings.accents.teal', color: 'oklch(0.77 0.12 190)' },
  { code: 'violet', labelKey: 'settings.accents.violet', color: 'oklch(0.72 0.14 285)' },
  { code: 'rose', labelKey: 'settings.accents.rose', color: 'oklch(0.72 0.14 350)' },
  { code: 'amber', labelKey: 'settings.accents.amber', color: 'oklch(0.80 0.14 80)' },
  { code: 'coral', labelKey: 'settings.accents.coral', color: 'oklch(0.74 0.15 35)' },
] as const

const CODES = ACCENTS.map((a) => a.code) as readonly string[]

export function storedAccent(): string {
  const value = localStorage.getItem(STORAGE_KEY)
  return value && CODES.includes(value) ? value : DEFAULT_ACCENT
}

export function applyAccent(code: string) {
  document.documentElement.dataset.accent = code
}

export function setAccent(code: string) {
  localStorage.setItem(STORAGE_KEY, code)
  applyAccent(code)
}
