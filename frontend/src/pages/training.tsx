import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight } from 'lucide-react'
import { api, type Program } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useLayoutContext } from '@/components/layout'

/**
 * Entry screen of the training module: one card per program, nothing else.
 * Routines, phases, weeks and days each live on their own screen below.
 */
export function TrainingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { training, refreshTraining } = useLayoutContext()
  const [programs, setPrograms] = useState<Program[] | null>(null)
  const [activating, setActivating] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.training.programs().then(setPrograms, (e: Error) => setError(e.message))
  }, [])

  // Activating means picking a routine: with a single one there is nothing to
  // choose, with several the program screen asks for it (?pick=1).
  const activate = (program: Program) => {
    if (program.variants.length !== 1) {
      navigate(`/training/${program.slug}?pick=1`)
      return
    }
    setActivating(program.id)
    setError(null)
    api.training.updateProfile({ active_variant: program.variants[0].id }).then(
      () => {
        setActivating(null)
        refreshTraining()
      },
      (e: Error) => {
        setActivating(null)
        setError(e.message)
      },
    )
  }

  if (error && !programs) {
    return <p className="py-10 text-center text-sm text-destructive">{error}</p>
  }

  return (
    <div className="mx-auto grid w-full max-w-lg gap-4">
      <div className="grid gap-1">
        <h1 className="text-lg font-semibold">{t('training.programsTitle')}</h1>
        <p className="text-sm text-muted-foreground">{t('training.programsDescription')}</p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {programs === null ? (
        <p className="py-6 text-center text-sm text-muted-foreground">{t('training.loading')}</p>
      ) : programs.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">
          {t('training.programsEmpty')}
        </p>
      ) : (
        <div className="grid gap-3">
          {programs.map((program) => {
            const isActive = program.slug === training?.active_program
            const subtitle = [
              program.coach ? t('training.coach', { coach: program.coach }) : '',
              program.variants.length > 1
                ? t('training.routineCount', { count: program.variants.length })
                : '',
            ]
              .filter(Boolean)
              .join(' · ')

            return (
              <Card key={program.id}>
                <Link
                  to={`/training/${program.slug}`}
                  className="block transition-colors hover:bg-accent/40"
                >
                  <CardHeader className="flex items-center gap-3">
                    <div className="grid min-w-0 flex-1 gap-1">
                      <CardTitle>{program.name}</CardTitle>
                      {subtitle && <CardDescription>{subtitle}</CardDescription>}
                    </div>
                    {isActive && (
                      <span className="shrink-0 rounded bg-primary/15 px-2 py-0.5 text-xs text-primary">
                        {t('training.activeProgramTag')}
                      </span>
                    )}
                    <ChevronRight className="size-5 shrink-0 text-muted-foreground" />
                  </CardHeader>
                </Link>
                {!isActive && (
                  <CardContent>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={activating === program.id}
                      onClick={() => activate(program)}
                    >
                      {t('training.activate')}
                    </Button>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
