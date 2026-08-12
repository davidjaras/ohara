import { cn } from '@/lib/utils'

export interface RangeOption<T extends string | number> {
  value: T
  label: string
}

interface RangeSelectProps<T extends string | number> {
  options: RangeOption<T>[]
  value: T
  onChange: (value: T) => void
  /**
   * `compact` is the segmented control that rides along a section label
   * (chart ranges). `chips` is the row of standalone pills used where the
   * choice is the point of the block, like the timer presets — it scrolls
   * instead of wrapping so the row height never changes.
   */
  size?: 'compact' | 'chips'
  className?: string
}

/** Single-choice control rendered as glass pills. */
export function RangeSelect<T extends string | number>({
  options,
  value,
  onChange,
  size = 'compact',
  className,
}: RangeSelectProps<T>) {
  const chips = size === 'chips'
  return (
    <div
      className={cn(
        chips
          ? 'flex gap-2 overflow-x-auto py-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden'
          : 'glass-subtle flex shrink-0 gap-0.5 rounded-full p-0.5',
        className,
      )}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              'shrink-0 rounded-full font-medium transition-colors',
              chips
                ? 'border px-4 py-2 text-sm'
                : 'px-2.5 py-1 text-xs',
              selected
                ? chips
                  ? 'border-primary/50 bg-primary/25 text-foreground'
                  : 'bg-primary/20 text-foreground'
                : chips
                  ? 'border-glass-border bg-glass text-muted-foreground hover:text-foreground'
                  : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
