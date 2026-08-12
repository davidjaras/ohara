import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'
import { cn } from '@/lib/utils'

/**
 * The small rounded label used for tags, states and counters.
 *
 * `accent` marks the thing that is true right now — today's workout, the
 * active routine, a met week. `muted` is everything else, so an accent pill
 * only ever means one thing on a screen.
 */
const pillVariants = cva(
  'inline-flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap',
  {
    variants: {
      tone: {
        accent: 'border-primary/30 bg-primary/15 text-primary',
        muted: 'glass-subtle text-muted-foreground',
      },
    },
    defaultVariants: { tone: 'muted' },
  },
)

export function Pill({
  className,
  tone,
  ...props
}: ComponentProps<'span'> & VariantProps<typeof pillVariants>) {
  return <span className={cn(pillVariants({ tone }), className)} {...props} />
}
