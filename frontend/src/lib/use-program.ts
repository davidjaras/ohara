import { useEffect, useState } from 'react'
import { api, type ProgramDetail } from './api'

/**
 * The program endpoint answers the whole tree (routines → phases → weeks →
 * days) in one payload, and the three training screens all read from it. A
 * module-level cache keeps navigating between them from refetching it; the
 * tree is static content, so a stale entry is not a concern within a visit.
 */
const cache = new Map<string, ProgramDetail>()

export function useProgramDetail(slug: string | undefined) {
  const [detail, setDetail] = useState<ProgramDetail | null>(
    slug ? (cache.get(slug) ?? null) : null,
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    const cached = cache.get(slug)
    if (cached) {
      setDetail(cached)
      return
    }
    let active = true
    setDetail(null)
    setError(null)
    api.training.program(slug).then(
      (loaded) => {
        cache.set(slug, loaded)
        if (active) setDetail(loaded)
      },
      (e: Error) => {
        if (active) setError(e.message)
      },
    )
    return () => {
      active = false
    }
  }, [slug])

  return { detail, error }
}
