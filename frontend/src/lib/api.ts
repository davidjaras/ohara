// Typed client for the Django REST API. In development Vite proxies /api to
// the backend (see vite.config.ts); in production both share the origin.

export interface Metric {
  key: string
  name: string
  kind: 'session' | 'measurement'
  unit: string
  default_weekly_goal_minutes: number | null
}

export interface TimerState {
  active: boolean
  metric?: string
  started_at?: string
  is_paused?: boolean
  elapsed_seconds?: number
  server_time?: string
}

export interface Session {
  id: number
  metric: string
  date: string
  duration_seconds: number
  minutes: number
  note: string
  started_at: string | null
  ended_at: string | null
  created_at: string
}

export interface Measurement {
  id: number
  metric: string
  date: string
  value: string
  note: string
  created_at: string
}

export interface DailyPoint {
  date: string
  minutes: number
}

export interface WeekSummary {
  week_start: string
  minutes: number
  goal_minutes: number
  met: boolean
}

export interface Stats {
  metric: string
  today: string
  today_minutes: number
  week_minutes: number
  week_goal_minutes: number
  week_met: boolean
  streak_weeks: number
  total_minutes: number
  daily: DailyPoint[]
  weekly: WeekSummary[]
}

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `Error ${res.status}`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  metrics: () => request<Metric[]>('/api/metrics/'),

  timer: {
    get: (metric: string) => request<TimerState>(`/api/timer/?metric=${metric}`),
    start: (metric: string) =>
      request<TimerState>('/api/timer/start/', {
        method: 'POST',
        body: JSON.stringify({ metric }),
      }),
    pause: (metric: string) =>
      request<TimerState>('/api/timer/pause/', {
        method: 'POST',
        body: JSON.stringify({ metric }),
      }),
    resume: (metric: string) =>
      request<TimerState>('/api/timer/resume/', {
        method: 'POST',
        body: JSON.stringify({ metric }),
      }),
    finish: (metric: string, note: string) =>
      request<Session>('/api/timer/finish/', {
        method: 'POST',
        body: JSON.stringify({ metric, note }),
      }),
    discard: (metric: string) =>
      request<void>(`/api/timer/?metric=${metric}`, { method: 'DELETE' }),
  },

  sessions: {
    list: (metric: string, limit = 50) =>
      request<Session[]>(`/api/sessions/?metric=${metric}&limit=${limit}`),
    create: (data: { metric: string; date: string; minutes: number; note: string }) =>
      request<Session>('/api/sessions/', { method: 'POST', body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/api/sessions/${id}/`, { method: 'DELETE' }),
  },

  measurements: {
    list: (metric: string, limit = 100) =>
      request<Measurement[]>(`/api/measurements/?metric=${metric}&limit=${limit}`),
    create: (data: { metric: string; date: string; value: number; note: string }) =>
      request<Measurement>('/api/measurements/', { method: 'POST', body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/api/measurements/${id}/`, { method: 'DELETE' }),
  },

  goal: {
    get: (metric: string) =>
      request<{ metric: string; minutes: number }>(`/api/goal/?metric=${metric}`),
    set: (metric: string, minutes: number) =>
      request<{ metric: string; minutes: number }>('/api/goal/', {
        method: 'PUT',
        body: JSON.stringify({ metric, minutes }),
      }),
  },

  stats: (metric: string, days = 14, weeks = 12) =>
    request<Stats>(`/api/stats/?metric=${metric}&days=${days}&weeks=${weeks}`),
}
