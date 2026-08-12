import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

/**
 * A pane of glass.
 *
 * Deliberately not the default container: most blocks on a screen are a
 * `Section` sitting directly on the page. A panel means "this is raised above
 * the rest", so it is reserved for the focal element of a screen (`hero`), an
 * item that stands apart from a list (`elevated`), and groupings that need an
 * outline to read as one unit (`subtle`).
 */
// `min-w-0` for the same reason as Section: a panel is usually a grid item of
// the page stack, and without it any nowrap text inside widens the page.
const panelVariants = cva('relative min-w-0', {
  variants: {
    variant: {
      subtle: 'glass-subtle rounded-2xl',
      elevated: 'glass-elevated glass-lit rounded-2xl',
      hero: 'glass-hero glass-lit rounded-[28px]',
    },
  },
  defaultVariants: { variant: 'elevated' },
})

export function Panel({
  className,
  variant,
  ...props
}: ComponentProps<'div'> & VariantProps<typeof panelVariants>) {
  return <div className={cn(panelVariants({ variant }), className)} {...props} />
}
