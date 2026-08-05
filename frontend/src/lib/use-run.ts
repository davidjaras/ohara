import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type ProgramRun, type ScheduledDay } from './api'

/**
 * The active plan, or null when nothing is running.
 *
 * Deliberately uncached, unlike the program tree: the schedule carries which
 * days are done, and that changes the moment a workout is completed.
 */
export function useActiveRun() {
  const [run, setRun] = useState<ProgramRun | null>(null)
  const [loaded, setLoaded] = useState(false)

  const refresh = useCallback(() => {
    return api.training.runs.active().then(
      (found) => {
        setRun(found)
        setLoaded(true)
      },
      () => setLoaded(true),
    )
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { run, loaded, refresh }
}

/**
 * Day id → its place in the plan, but only while the run is of this program:
 * browsing another program must not date its days.
 */
export function useSchedule(run: ProgramRun | null, programSlug: string | undefined) {
  return useMemo(() => {
    const map = new Map<number, ScheduledDay>()
    if (!run || !programSlug || run.program.slug !== programSlug) return map
    for (const entry of run.schedule ?? []) map.set(entry.day.id, entry)
    return map
  }, [run, programSlug])
}
