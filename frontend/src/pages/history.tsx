import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Pencil, Timer, Trash2 } from 'lucide-react'
import { api, type Session, type Stats } from '@/lib/api'
import { MAX_DAY_MINUTES, METRIC_ESTUDIO } from '@/lib/constants'
import { formatLongDate, formatMinutes, todayISO } from '@/lib/format'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { WeeklyChart } from '@/components/charts'
import { EmptyState } from '@/components/empty-state'
import { IconTile } from '@/components/icon-tile'
import { Pill } from '@/components/pill'
import { RangeSelect } from '@/components/range-select'
import { Section } from '@/components/section'
import { WeekList } from '@/components/week-list'
import { useLayoutContext } from '@/components/layout'

// 12 weeks (a quarter) reads at a glance; 4 zooms into the current month and
// 26/52 give the half-year and full-year picture.
const WEEK_RANGES = [4, 12, 26, 52]

// Enough to cover a normal month of study without a tap, short enough that the
// list stops being a wall you scroll past to reach the rest of the page.
const SESSION_PAGE_SIZE = 20

type EntryDraft = { date: string; minutes: string; note: string }

/** Local check mirroring the backend guards, so typos never need a round trip. */
function minutesError(minutes: string): 'notWhole' | 'tooLong' | null {
  const value = Number(minutes)
  if (!Number.isInteger(value)) return 'notWhole'
  if (value < 1 || value > MAX_DAY_MINUTES) return 'tooLong'
  return null
}

/** The date/minutes/note fields, shared by the entry form and the edit dialog. */
function EntryFields({
  idPrefix,
  draft,
  onChange,
}: {
  idPrefix: string
  draft: EntryDraft
  onChange: (draft: EntryDraft) => void
}) {
  const { t } = useTranslation()

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="grid gap-2">
          <Label htmlFor={`${idPrefix}-date`}>{t('history.date')}</Label>
          <Input
            id={`${idPrefix}-date`}
            type="date"
            value={draft.date}
            max={todayISO()}
            onChange={(e) => onChange({ ...draft, date: e.target.value })}
            required
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor={`${idPrefix}-minutes`}>{t('history.minutes')}</Label>
          <Input
            id={`${idPrefix}-minutes`}
            type="number"
            min={1}
            max={MAX_DAY_MINUTES}
            step={1}
            placeholder="90"
            value={draft.minutes}
            onChange={(e) => onChange({ ...draft, minutes: e.target.value })}
            required
          />
        </div>
      </div>
      <div className="grid gap-2">
        <Label htmlFor={`${idPrefix}-note`}>{t('history.note')}</Label>
        <Textarea
          id={`${idPrefix}-note`}
          value={draft.note}
          onChange={(e) => onChange({ ...draft, note: e.target.value })}
          placeholder={t('timer.noteLabel')}
          rows={3}
        />
      </div>
    </>
  )
}

function ManualEntryForm({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<EntryDraft>({ date: todayISO(), minutes: '', note: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const invalid = minutesError(draft.minutes)
    if (invalid) {
      setError(t(`history.${invalid}`, { max: MAX_DAY_MINUTES }))
      return
    }
    setSaving(true)
    setError(null)
    api.sessions
      .create({
        metric: METRIC_ESTUDIO,
        date: draft.date,
        minutes: Number(draft.minutes),
        note: draft.note.trim(),
      })
      .then(
        () => {
          setSaving(false)
          setDraft({ ...draft, minutes: '', note: '' })
          onSaved()
        },
        (err: Error) => {
          setSaving(false)
          setError(err.message)
        },
      )
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <EntryFields idPrefix="entry" draft={draft} onChange={setDraft} />
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div>
        <Button type="submit" disabled={saving || !draft.minutes}>
          {saving ? t('history.saving') : t('history.save')}
        </Button>
      </div>
    </form>
  )
}

function EditEntryDialog({
  session,
  onClose,
  onSaved,
}: {
  session: Session | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<EntryDraft>({ date: '', minutes: '', note: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!session) return
    setDraft({
      date: session.date,
      minutes: String(session.minutes),
      note: session.note,
    })
    setError(null)
  }, [session])

  const handleSave = () => {
    if (!session) return
    const invalid = minutesError(draft.minutes)
    if (invalid) {
      setError(t(`history.${invalid}`, { max: MAX_DAY_MINUTES }))
      return
    }
    setSaving(true)
    setError(null)
    api.sessions
      .update(session.id, {
        date: draft.date,
        minutes: Number(draft.minutes),
        note: draft.note.trim(),
      })
      .then(
        () => {
          setSaving(false)
          onSaved()
          onClose()
        },
        (err: Error) => {
          setSaving(false)
          setError(err.message)
        },
      )
  }

  return (
    <Dialog open={session !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg" aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{t('history.editTitle')}</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4">
          <EntryFields idPrefix="edit" draft={draft} onChange={setDraft} />
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={saving}>
            {t('history.cancel')}
          </Button>
          <Button onClick={handleSave} disabled={saving || !draft.minutes}>
            {t('history.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SessionList({
  sessions,
  onEdit,
  onDeleted,
}: {
  sessions: Session[]
  onEdit: (session: Session) => void
  onDeleted: () => void
}) {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)

  const handleDelete = (session: Session) => {
    if (!window.confirm(t('history.deleteConfirm', { date: formatLongDate(session.date) }))) return
    api.sessions.remove(session.id).then(onDeleted, (e: Error) => setError(e.message))
  }

  if (sessions.length === 0) {
    return <EmptyState>{t('history.empty')}</EmptyState>
  }

  return (
    <>
      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
      <ul className="divide-y divide-hairline">
        {sessions.map((session) => (
          <li key={session.id} className="flex items-start gap-3 py-3">
            <IconTile tone="muted" className="mt-0.5">
              <Timer className="size-4" />
            </IconTile>
            <div className="min-w-0 flex-1">
              <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium">
                {formatLongDate(session.date)}
                <span className="whitespace-nowrap text-primary">
                  {formatMinutes(session.minutes)}
                </span>
                {!session.started_at && <Pill>{t('history.manualTag')}</Pill>}
                {session.close_reason && <Pill>{t('history.estimatedTag')}</Pill>}
              </p>
              {session.note && (
                <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                  {session.note}
                </p>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-foreground"
              onClick={() => onEdit(session)}
              aria-label={t('history.editLabel')}
            >
              <Pencil className="size-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-destructive"
              onClick={() => handleDelete(session)}
              aria-label={t('history.deleteLabel')}
            >
              <Trash2 className="size-4" />
            </Button>
          </li>
        ))}
      </ul>
    </>
  )
}

/**
 * The screen that holds the record: the shape of the last weeks, which of them
 * met their goal, and every session behind those numbers. The dashboard used
 * to carry the first two, which made it a report instead of a starting point.
 */
export function HistoryPage() {
  const { t } = useTranslation()
  const { refreshStreak } = useLayoutContext()
  const [sessions, setSessions] = useState<Session[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [weeks, setWeeks] = useState(12)
  const [editing, setEditing] = useState<Session | null>(null)
  const [error, setError] = useState<string | null>(null)
  // A short page means the server has nothing left, so there is no total to
  // keep in sync with a list that gains and loses rows while you read it.
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const load = useCallback(() => {
    api.sessions.list(METRIC_ESTUDIO, SESSION_PAGE_SIZE).then((rows) => {
      setSessions(rows)
      setHasMore(rows.length === SESSION_PAGE_SIZE)
    }, (e: Error) => setError(e.message))
  }, [])

  // Paging is by offset, so anything added or removed above the window shifts
  // it. Every mutation on this page reloads from the first page instead.
  const loadMore = useCallback(() => {
    setLoadingMore(true)
    api.sessions.list(METRIC_ESTUDIO, SESSION_PAGE_SIZE, sessions.length).then(
      (rows) => {
        setLoadingMore(false)
        setSessions((current) => [...current, ...rows])
        setHasMore(rows.length === SESSION_PAGE_SIZE)
      },
      (e: Error) => {
        setLoadingMore(false)
        setError(e.message)
      },
    )
  }, [sessions.length])

  const loadStats = useCallback(() => {
    api.stats(METRIC_ESTUDIO, weeks).then(setStats, (e: Error) => setError(e.message))
  }, [weeks])

  useEffect(load, [load])
  useEffect(loadStats, [loadStats])

  // Adding, editing or removing a session can change which weeks met their
  // goal, so reload the list, the weekly aggregates and the streak together.
  const reload = useCallback(() => {
    load()
    loadStats()
    refreshStreak()
  }, [load, loadStats, refreshStreak])

  return (
    <div className="page-stack gap-10 sm:gap-12">
      <Section
        title={t('weeklyChart.title')}
        description={t('weeklyChart.description')}
        action={
          <RangeSelect
            options={WEEK_RANGES.map((n) => ({
              value: n,
              label: t('ranges.weeks', { count: n }),
            }))}
            value={weeks}
            onChange={setWeeks}
          />
        }
      >
        {stats ? (
          <WeeklyChart data={stats.weekly} />
        ) : (
          <EmptyState>{t('timer.loading')}</EmptyState>
        )}
      </Section>

      {/* No goal in the section header: every row prints its own week's goal,
          and the header showed the CURRENT one — on a week where the goal
          changed it contradicted the rows under it. */}
      {stats && stats.weekly.length > 0 && (
        <Section title={t('weekList.title')}>
          <WeekList
            weeks={stats.weekly.slice(-8)}
            currentWeekStart={stats.weekly[stats.weekly.length - 1].week_start}
          />
        </Section>
      )}

      <Section title={t('history.manualTitle')}>
        <ManualEntryForm onSaved={reload} />
      </Section>

      <Section title={t('history.sessionsTitle')}>
        {error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <>
            <SessionList sessions={sessions} onEdit={setEditing} onDeleted={reload} />
            {hasMore && (
              <Button
                variant="outline"
                className="mt-3 w-full"
                onClick={loadMore}
                disabled={loadingMore}
              >
                {loadingMore ? t('common.loading') : t('common.loadMore')}
              </Button>
            )}
          </>
        )}
      </Section>

      <EditEntryDialog session={editing} onClose={() => setEditing(null)} onSaved={reload} />
    </div>
  )
}
