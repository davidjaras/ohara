import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface SectionProps {
  /** Small uppercase label. Omit for an unlabelled block. */
  title?: ReactNode
  /** One line under the title, same register as the old card description. */
  description?: ReactNode
  /** Right side of the label row: a range selector, a total, a link. */
  action?: ReactNode
  className?: string
  children?: ReactNode
}

/**
 * The default shape of a block: a label, a hairline, and content sitting on
 * the page — no box around it.
 *
 * This is what replaced most of the cards. A card gives every block the same
 * weight; a hairline separates without competing, which is what lets the one
 * panel on the screen actually read as raised.
 */
export function Section({ title, description, action, className, children }: SectionProps) {
  return (
    <section className={cn('grid gap-3', className)}>
      {(title || action) && (
        <div className="border-b border-hairline pb-2">
          {/* The action rides the label line and the description gets the
              full width under it — a description squeezed into the space a
              range selector leaves over turns into a column of two words. */}
          <div className="flex items-center justify-between gap-3">
            {title && (
              <h2 className="min-w-0 truncate text-xs font-medium tracking-[0.08em] text-muted-foreground uppercase">
                {title}
              </h2>
            )}
            {action && <div className="shrink-0">{action}</div>}
          </div>
          {description && (
            <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      {children}
    </section>
  )
}
