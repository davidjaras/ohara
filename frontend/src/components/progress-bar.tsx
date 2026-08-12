import { cn } from '@/lib/utils'

interface ProgressBarProps {
  /** 0..100. Values outside the range are clamped. */
  value: number
  className?: string
}

/** Thin accent-filled track. Used for the weekly goal and for plan adherence. */
export function ProgressBar({ value, className }: ProgressBarProps) {
  return (
    <div className={cn('h-1.5 overflow-hidden rounded-full bg-glass-strong', className)}>
      <div
        className="h-full rounded-full bg-primary transition-all"
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  )
}
