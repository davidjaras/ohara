import type { TFunction } from 'i18next'
import type { ProgramVariant } from './api'

/**
 * "4 días/semana · gimnasio" — a routine described by what it asks of you,
 * not by its slug. Shared by the program screen and the start-plan dialog so
 * the same routine never reads two different ways.
 */
export function routineLabel(variant: ProgramVariant, t: TFunction): string {
  const parts: string[] = []
  if (variant.days_per_week) {
    parts.push(t('training.routineDays', { count: variant.days_per_week }))
  }
  if (variant.environment === 'gym') parts.push(t('training.envGym'))
  if (variant.environment === 'home') parts.push(t('training.envHome'))
  return parts.length > 0 ? parts.join(' · ') : variant.slug
}
