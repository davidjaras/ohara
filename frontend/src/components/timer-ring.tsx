import type { ReactNode } from 'react'

interface TimerRingProps {
  /** Fraction of the ring that is filled, 0..1. */
  progress: number
  /** `planned` fills toward the agreed duration; `cycle` (thinner, dotted
   * track) loops toward the next check-in and must never read as progress
   * toward a total that does not exist. */
  mode: 'planned' | 'cycle'
  children: ReactNode
}

export function TimerRing({ progress, mode, children }: TimerRingProps) {
  const filled = Math.min(1, Math.max(0, progress)) * 360
  const strokeWidth = mode === 'planned' ? 7 : 3.5

  return (
    <div className="relative size-56 sm:size-64">
      <svg viewBox="0 0 120 120" className="size-full -rotate-90">
        <circle
          cx={60}
          cy={60}
          r={54}
          className="stroke-glass-strong"
          strokeWidth={strokeWidth}
          fill="none"
          pathLength={360}
          strokeDasharray={mode === 'cycle' ? '1 7' : undefined}
          strokeLinecap="round"
        />
        {filled > 0 && (
          <circle
            cx={60}
            cy={60}
            r={54}
            // The glow is what keeps the arc from disappearing into the
            // glass it sits on; it follows the accent like the stroke does.
            className="stroke-primary transition-[stroke-dasharray] duration-1000 ease-linear [filter:drop-shadow(0_0_6px_var(--ambient-strong))]"
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            pathLength={360}
            strokeDasharray={`${filled} ${360 - filled}`}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
        {children}
      </div>
    </div>
  )
}
