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
        <div className="flex items-end justify-between gap-3 border-b border-hairline pb-2">
          <div className="grid min-w-0 gap-1">
            {title && (
              <h2 className="text-xs font-medium tracking-[0.08em] text-muted-foreground uppercase">
                {title}
              </h2>
            )}
            {description && (
              <p className="text-sm text-muted-foreground">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </section>
  )
}
