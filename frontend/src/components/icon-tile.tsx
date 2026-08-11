import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface IconTileProps {
  children: ReactNode
  /** `accent` for the icon of something live, `muted` for list decoration. */
  tone?: 'accent' | 'muted'
  className?: string
}

/** The small rounded square behind a lucide icon. */
export function IconTile({ children, tone = 'accent', className }: IconTileProps) {
  return (
    <div
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-xl border',
        tone === 'accent'
          ? 'border-primary/25 bg-primary/15 text-primary'
          : 'glass-subtle text-muted-foreground',
        className,
      )}
    >
      {children}
    </div>
  )
}
