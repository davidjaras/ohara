import type { LucideIcon } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  unit?: string
  highlight?: boolean
}

export function StatCard({ icon: Icon, label, value, unit, highlight }: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 p-4 sm:p-5">
        <div className="rounded-md bg-accent p-2">
          <Icon className={highlight ? 'size-5 text-primary' : 'size-5 text-muted-foreground'} />
        </div>
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-0.5 truncate text-2xl font-semibold sm:text-3xl">
            {value}
            {unit && <span className="ml-1.5 text-sm font-normal text-muted-foreground">{unit}</span>}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
