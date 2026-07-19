# Ohara brand

## Concept

The Ohara symbol is an open circular **O**. It represents the first letter of
the product name, continuous progress, a recurring weekly cycle, and a goal
that advances. Its meaning is intentionally broader than studying so the mark
can remain relevant as Ohara tracks other kinds of personal progress.

The canonical geometry uses a mathematical circle with a constant 7-unit
stroke on a 64 × 64 viewBox. The 50-degree opening is centered at 1:30
(-45 degrees in SVG coordinates), with fully rounded endpoints. The outer
visible bounds are 47 × 47 units and are centered in the viewBox, leaving 8.5
units of optical padding on every side.

## Colors and variants

| Token | Value | Use |
| --- | --- | --- |
| Ohara azure | `#57A9E5` | Primary symbol color (standalone exports, favicon) |
| Dark background | `#0B0F0D` | Canonical dark surface |
| Light foreground | `#F5F5F5` | White mark on dark surfaces |

Ohara azure is the flat equivalent of the reference image's soft sky-blue:
same hue, mid perceived lightness.

Approved variants are azure or white on the dark background, and azure or
near-black (`#0B0F0D`) on a light background. **In-product**, the symbol is
rendered with `currentColor` taking the app's accent token (`--primary`), so
the mark always matches the surrounding UI. Maintain sufficient contrast in
every use. The canonical SVG and React component use `currentColor`; set the
CSS `color` property to select an approved color without changing the geometry.

## Spacing and size

Keep clear space of at least one stroke width around the outer visible bounds
of the symbol. In the canonical 64-unit coordinate system, that means at least
seven units of unobstructed space beyond each visible edge.

The minimum recommended digital size is **16 × 16 pixels**. Use the supplied
favicon at browser-icon sizes and do not reduce the stroke weight.

## Restrictions

- Do not close, widen, narrow, redraw, or distort the ring.
- Do not rotate or reposition the opening. It must remain in the upper-right
  area around 1:30 and must not be rotated to the top.
- Do not change the stroke width or replace the rounded endpoints.
- Do not add gradients, shadows, glow, textures, internal marks, or enclosing
  shapes.
- Do not place a checkmark, letter, or illustrative object inside the symbol.
- Do not use unapproved colors or place the mark on a low-contrast background.

The visual reference for the mark is `docs/brand-reference.png` (soft
gradient, app-tile framing); the canonical assets are its flat, geometric
formalization.

## Files

- `frontend/public/brand/ohara-symbol.svg`: canonical `currentColor` symbol.
- `frontend/public/brand/ohara-symbol-azure.svg`: azure standalone export.
- `frontend/public/brand/ohara-symbol-white.svg`: light standalone export.
- `frontend/public/favicon.svg`: small-size azure browser icon on the flat
  dark application tile.
- `frontend/src/components/brand/geometry.ts`: shared canonical geometry and color values.
- `frontend/src/components/brand/OharaLogo.tsx`: reusable React component.
- `frontend/src/pages/BrandPreview.tsx`: internal geometry, scale, and color
  review page.

Raster, ICO, PWA, social, and Open Graph exports are deliberately deferred.

## React usage

Import the component and control its color with CSS. `size` sets equal width
and height, while standard SVG properties such as `className`, `aria-label`,
and event handlers are accepted. Supply `title` or another accessible label
when the symbol conveys meaning; unlabeled instances are hidden from assistive
technology.

```tsx
import { OharaLogo } from '@/components/brand/OharaLogo'

<OharaLogo size={32} className="text-[#57A9E5]" title="Ohara" />
```
