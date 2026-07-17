import { cn } from '@/lib/utils'

export interface RangeOption<T extends string | number> {
  value: T
  label: string
}

interface RangeSelectProps<T extends string | number> {
  options: RangeOption<T>[]
  value: T
  onChange: (value: T) => void
}

/** Small segmented control used to pick a chart's time range. */
export function RangeSelect<T extends string | number>({
  options,
  value,
  onChange,
}: RangeSelectProps<T>) {
  return (
    <div className="flex shrink-0 gap-0.5 rounded-lg border p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cn(
            'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
            option.value === value
              ? 'bg-accent text-foreground'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
