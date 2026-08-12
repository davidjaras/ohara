import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface PageHeaderProps {
  title: ReactNode
  subtitle?: ReactNode
  /** Route the back arrow goes to. Without it no arrow renders. */
  backTo?: string
  backLabel?: string
  /** Right side of the row: a status pill, an action. */
  action?: ReactNode
  className?: string
}

/** Title row of a screen, with the optional back arrow the deeper training
 *  screens need. Three copies of this markup used to live in the training
 *  pages, drifting slightly apart. */
export function PageHeader({
  title,
  subtitle,
  backTo,
  backLabel,
  action,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      {backTo && (
        <Button variant="ghost" size="icon" className="-ml-2 shrink-0" asChild>
          <Link to={backTo} aria-label={backLabel}>
            <ArrowLeft className="size-5" />
          </Link>
        </Button>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold">{title}</h1>
        {subtitle && (
          <p className="truncate text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  )
}
