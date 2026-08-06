// Typed client for the Django REST API. In development Vite proxies /api to
// the backend (see vite.config.ts); in production both share the origin.
// Auth is Django's session auth: unauthenticated responses redirect the
// browser to the native login page.

import i18n from '@/lib/i18n'

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
  planned_duration_seconds?: number | null
  grace_seconds?: number
  reminder_interval_seconds?: number | null
  confirmed_seconds?: number
  server_time?: string
}

export interface Preferences {
  accent_color: string
  reminder_minutes: number | null
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
  close_reason: string
  estimated_duration_seconds: number | null
  needs_review: boolean
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

export interface CumulativePoint {
  date: string
  minutes: number
  cumulative_minutes: number
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
  week_minutes: number
  week_goal_minutes: number
  week_met: boolean
  streak_weeks: number
  total_minutes: number
  week_cumulative: CumulativePoint[]
  weekly: WeekSummary[]
}

// --- Training module ---------------------------------------------------------
// Every /api/training/ endpoint answers 404 when the module is disabled for
// the user (deliberately not 403, so the module's existence is not revealed).
// Callers treat that 404 as "training does not exist" and render nothing.

export type RestRole = 'between_sets' | 'superset_transition' | 'superset_round_end'

export interface TrainingExercise {
  id: number
  slug: string
  name: string
  primary_muscle: string
  secondary_muscles: string[]
  movement_pattern: string
  equipment_required: string[]
  is_unilateral: boolean
  setting: 'home' | 'gym'
}

export interface SetPrescription {
  id: number
  set_number: number
  target_reps_min: number | null
  target_reps_max: number | null
  to_failure: boolean
  hold_seconds: number | null
  reps_per_side: boolean
  rest_seconds: number | null
  rest_role: RestRole
  tempo: string
  is_backoff_set: boolean
  cluster_reps: number[] | null
  reps_raw: string
}

/** One set of a past session, as shown in "última vez" and the history dialog. */
export interface PerformedSet {
  set_number: number
  weight: string | null
  weight_basis: 'total' | 'per_dumbbell' | 'bodyweight' | 'added'
  reps: number | null
  was_substituted: boolean
}

export interface Performance {
  id: number
  performed_on: string | null
  day_name: string
  program: string
  sets: PerformedSet[]
}

export interface ExerciseSlot {
  id: number
  order: number
  series_label: string
  series_position: number | null
  is_superset: boolean
  coach_annotation: string
  modifiers: { type: string }[]
  /** What the coach prescribed. What you are doing is `substitution` when
   *  there is one — that is what titles the card and what a set records. */
  exercise: TrainingExercise
  sets: SetPrescription[]
  substitution: Substitution | null
  /** The previous time the *performed* exercise was logged; excludes today's
   *  session, so the line never mirrors what was just typed. */
  last_performance: Performance | null
}

export interface WorkoutDay {
  id: number
  order: number
  name: string
  day_of_week: string
}

export interface WorkoutDayDetail extends WorkoutDay {
  week_number: number
  phase_number: number
  /** Phase id — what `/training/:slug/phase/:phaseId` routes on. */
  phase: number
  program_slug: string
  /** Set only while the day belongs to the active plan. */
  scheduled_on: string | null
  plan_week: number | null
  in_active_plan: boolean
  /** What was already logged on this day — null until the first set. */
  session: WorkoutSessionDetail | null
  slots: ExerciseSlot[]
}

export interface TrainingWeek {
  id: number
  number: number
  is_deload: boolean
  is_synthesised: boolean
  days: WorkoutDay[]
}

export interface TrainingPhase {
  id: number
  number: number
  label: string
  weeks_count: number
  weeks_declared_in_source: number | null
  number_inferred: boolean
  weeks: TrainingWeek[]
}

export interface ProgramVariant {
  id: number
  slug: string
  days_per_week: number
  environment: string
  /** Weeks across every phase — how long committing to this routine is. */
  total_weeks: number
}

export interface ProgramVariantDetail extends ProgramVariant {
  phases: TrainingPhase[]
}

export interface Program {
  id: number
  slug: string
  name: string
  coach: string
  variants: ProgramVariant[]
}

export interface ProgramDetail extends Omit<Program, 'variants'> {
  variants: ProgramVariantDetail[]
}

export interface TrainingProfile {
  /** All three derive from the active run: the profile stores preferences. */
  active_variant: ProgramVariant | null
  active_program: string | null
  active_run: number | null
  weight_unit: string
}

export type RunStatus = 'active' | 'completed' | 'abandoned'

/** One day of the plan on a real date. */
export interface ScheduledDay {
  day: WorkoutDay
  plan_week: number
  scheduled_on: string
  done: boolean
  started: boolean
  session_id: number | null
}

export interface Adherence {
  done: number
  planned: number
  weeks: Record<string, { done: number; planned: number }>
}

/**
 * A plan: a variant committed to from a start date. `schedule`, `adherence`,
 * `plan_week` and `active_day` only come back for the active run.
 */
export interface ProgramRun {
  id: number
  program: Program
  variant: ProgramVariant
  started_on: string
  ends_on: string
  total_weeks: number
  status: RunStatus
  ended_on: string | null
  plan_week?: number
  adherence?: Adherence
  schedule?: ScheduledDay[]
  active_day?: ScheduledDay | null
}

export interface ExerciseHistory {
  exercise: TrainingExercise
  sessions: Performance[]
}

export interface Substitution {
  id: number
  slot: number
  replacement: TrainingExercise
  scope: 'session' | 'program'
  session: number | null
  reason: string
  created_at: string
}

export interface SubstitutionOptions {
  home: TrainingExercise[]
  gym: TrainingExercise[]
  active: Substitution | null
}

export interface SetLog {
  id: number
  /** Resolved server-side from the prescription; the UI keys its rows by it. */
  slot: number | null
  prescription: number | null
  performed_exercise: string
  was_substituted: boolean
  set_number: number
  weight: string | null
  weight_basis: 'total' | 'per_dumbbell' | 'bodyweight' | 'added'
  reps: number | null
  rpe: string | null
  rir: number | null
  import_note: string
}

export interface WorkoutSession {
  id: number
  day: WorkoutDay
  run: number | null
  /** Trained outside the active plan (or imported): never counts for adherence. */
  off_plan: boolean
  week_number: number
  performed_on: string
  completed_at: string | null
  notes: string
}

export interface WorkoutSessionDetail extends WorkoutSession {
  logs: SetLog[]
}

export class ApiError extends Error {
  status: number

  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

export function loginUrl(): string {
  const next = encodeURIComponent(window.location.pathname)
  return `/accounts/login/?next=${next}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? 'GET'
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept-Language': i18n.language,
  }
  if (method !== 'GET') {
    headers['X-CSRFToken'] = getCookie('csrftoken') ?? ''
  }
  const res = await fetch(path, { credentials: 'same-origin', ...init, headers })
  if (res.status === 401 || res.status === 403) {
    // Session expired or not signed in: send the browser to the login page.
    window.location.assign(loginUrl())
    return new Promise<T>(() => {}) // never resolves; navigation is underway
  }
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

/** POST to Django's native logout view, then land on the login page. */
export async function logout(): Promise<void> {
  await fetch('/accounts/logout/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': getCookie('csrftoken') ?? '' },
  })
  window.location.assign('/accounts/login/')
}

export const api = {
  me: () => request<{ username: string }>('/api/me/'),

  metrics: () => request<Metric[]>('/api/metrics/'),

  timer: {
    get: (metric: string) => request<TimerState>(`/api/timer/?metric=${metric}`),
    start: (metric: string, plannedMinutes: number | null) =>
      request<TimerState>('/api/timer/start/', {
        method: 'POST',
        body: JSON.stringify({ metric, planned_minutes: plannedMinutes }),
      }),
    extend: (metric: string, minutes: number) =>
      request<TimerState>('/api/timer/extend/', {
        method: 'POST',
        body: JSON.stringify({ metric, minutes }),
      }),
    checkin: (metric: string) =>
      request<TimerState>('/api/timer/checkin/', {
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
    pendingReview: (metric: string) =>
      request<Session[]>(`/api/sessions/?metric=${metric}&needs_review=1`),
    review: (id: number, data: { action: 'confirm' | 'adjust'; ended_at?: string; note?: string }) =>
      request<Session>(`/api/sessions/${id}/review/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    create: (data: { metric: string; date: string; minutes: number; note: string }) =>
      request<Session>('/api/sessions/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: { date?: string; minutes?: number; note?: string }) =>
      request<Session>(`/api/sessions/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }),
    remove: (id: number) => request<void>(`/api/sessions/${id}/`, { method: 'DELETE' }),
  },

  measurements: {
    list: (metric: string, limit = 1000) =>
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

  preferences: {
    get: () => request<Preferences>('/api/preferences/'),
    set: (data: Partial<Preferences>) =>
      request<Preferences>('/api/preferences/', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },

  stats: (metric: string, weeks = 12) =>
    request<Stats>(`/api/stats/?metric=${metric}&weeks=${weeks}`),

  training: {
    profile: () => request<TrainingProfile>('/api/training/profile/'),
    updateProfile: (data: { weight_unit?: string }) =>
      request<TrainingProfile>('/api/training/profile/', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    programs: () => request<Program[]>('/api/training/programs/'),
    program: (slug: string) => request<ProgramDetail>(`/api/training/programs/${slug}/`),
    day: (id: number) => request<WorkoutDayDetail>(`/api/training/days/${id}/`),
    runs: {
      list: () => request<ProgramRun[]>('/api/training/runs/'),
      // 204 when nothing is running; `request` turns that into undefined.
      active: () =>
        request<ProgramRun | undefined>('/api/training/runs/active/').then(
          (run) => run ?? null,
        ),
      start: (data: { variant: number; started_on?: string }) =>
        request<ProgramRun>('/api/training/runs/', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      update: (id: number, data: { status?: RunStatus; started_on?: string }) =>
        request<ProgramRun>(`/api/training/runs/${id}/`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),
    },
    exerciseHistory: (exerciseId: number) =>
      request<ExerciseHistory>(`/api/training/exercises/${exerciseId}/history/`),
    // The session decides whether a session-scoped swap is in force; without
    // one only program-scoped substitutions apply.
    substitutions: (slotId: number, sessionId?: number | null) =>
      request<SubstitutionOptions>(
        `/api/training/slots/${slotId}/substitutions/` +
          (sessionId ? `?session=${sessionId}` : ''),
      ),
    substitute: (
      slotId: number,
      data: { replacement: number; scope: 'session' | 'program'; session?: number | null; reason?: string },
    ) =>
      request<Substitution>(`/api/training/slots/${slotId}/substitutions/`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    sessions: {
      list: () => request<WorkoutSession[]>('/api/training/sessions/'),
      get: (id: number) => request<WorkoutSessionDetail>(`/api/training/sessions/${id}/`),
      // Idempotent per day: reopening a workout returns the session it
      // already has instead of forking a second one.
      create: (data: { day: number }) =>
        request<WorkoutSession>('/api/training/sessions/', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      update: (id: number, data: { notes?: string; completed?: boolean }) =>
        request<WorkoutSessionDetail>(`/api/training/sessions/${id}/`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),
      log: (
        sessionId: number,
        data: {
          slot: number
          set_number: number
          weight?: number | null
          weight_basis?: 'total' | 'per_dumbbell' | 'bodyweight' | 'added'
          reps?: number | null
          rpe?: number | null
          rir?: number | null
        },
      ) =>
        request<SetLog>(`/api/training/sessions/${sessionId}/logs/`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      unlog: (sessionId: number, logId: number) =>
        request<void>(`/api/training/sessions/${sessionId}/logs/${logId}/`, {
          method: 'DELETE',
        }),
    },
  },
}
