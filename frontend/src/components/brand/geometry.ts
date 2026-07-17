export const OHARA_LOGO_GEOMETRY = {
  viewBox: '0 0 64 64',
  center: 32,
  radius: 20,
  strokeWidth: 7,
  gapDegrees: 50,
  gapCenterDegrees: -45,
  rotationDegrees: -20,
} as const

// Flat equivalent of the reference image's soft-gradient green (its hue with
// the perceived mid lightness). Standalone exports and the favicon use it;
// in-product renders use `currentColor` and take the app accent instead.
export const OHARA_EMERALD = '#4FC580'

export const OHARA_DARK = '#0B0F0D'
export const OHARA_LIGHT = '#F5F5F5'
