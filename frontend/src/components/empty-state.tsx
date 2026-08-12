import { cn } from '@/lib/utils'

interface EmptyStateProps {
  children: string
  /** `error` paints it destructive; used for the page-level failure message. */
  tone?: 'muted' | 'error'
  className?: string
}

/** The centered sentence shown when a list is empty, still loading, or failed. */
export function EmptyState({ children, tone = 'muted', className }: EmptyStateProps) {
  return (
    <p
      className={cn(
        'py-8 text-center text-sm',
        tone === 'error' ? 'text-destructive' : 'text-muted-foreground',
        className,
      )}
    >
      {children}
    </p>
  )
}
