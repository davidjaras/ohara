/**
 * The color layer the glass refracts.
 *
 * Without something colorful behind them, `backdrop-filter` panels have
 * nothing to blur and read as flat gray cards — the exact failure this
 * redesign exists to avoid. So the ambient field is not decoration: it is
 * half the material.
 *
 * Built from radial gradients rather than `filter: blur()` on a solid
 * circle. Visually identical at these radii, but a blur filter forces the
 * compositor to rasterize a large layer on every paint, which is the kind
 * of thing that shows up on a phone.
 *
 * The colors come from `--ambient-*`, which `index.css` derives from
 * `--primary` with `color-mix` — so the field follows the user's accent
 * without a single hardcoded hue.
 */
export function AmbientBackdrop() {
  return (
    // The field tracks the content column rather than the viewport: anchored
    // to the far corners of a wide screen it would light up empty margins and
    // leave the panels with nothing to refract.
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="relative mx-auto h-full w-full max-w-3xl">
        <div
          className="absolute -top-32 -right-24 size-[min(30rem,85vw)] rounded-full"
          style={{ background: 'radial-gradient(closest-side, var(--ambient-strong), transparent)' }}
        />
        <div
          className="absolute top-[38%] -left-32 size-[min(26rem,80vw)] rounded-full"
          style={{ background: 'radial-gradient(closest-side, var(--ambient-soft), transparent)' }}
        />
        <div
          className="absolute -bottom-24 -right-20 size-[min(24rem,75vw)] rounded-full"
          style={{ background: 'radial-gradient(closest-side, var(--ambient-neutral), transparent)' }}
        />
      </div>
    </div>
  )
}
