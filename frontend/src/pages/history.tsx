import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Timer, Trash2 } from 'lucide-react'
import { api, type Session } from '@/lib/api'
import { formatLongDate, formatMinutes, todayISO } from '@/lib/format'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

const METRIC = 'estudio'

function ManualEntryForm({ onSaved }: { onSaved: () => void }) {
  const { t } = useTranslation()
  const [date, setDate] = useState(todayISO())
  const [minutes, setMinutes] = useState('')
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    api.sessions
      .create({ metric: METRIC, date, minutes: Number(minutes), note: note.trim() })
      .then(
        () => {
          setSaving(false)
          setMinutes('')
          setNote('')
          onSaved()
        },
        (err: Error) => {
          setSaving(false)
          setError(err.message)
        },
      )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('history.manualTitle')}</CardTitle>
        <CardDescription>{t('history.manualDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="entry-date">{t('history.date')}</Label>
              <Input
                id="entry-date"
                type="date"
                value={date}
                max={todayISO()}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="entry-minutes">{t('history.minutes')}</Label>
              <Input
                id="entry-minutes"
                type="number"
                min={1}
                placeholder="90"
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="entry-note">{t('history.note')}</Label>
            <Textarea
              id="entry-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t('timer.noteLabel')}
              rows={3}
            />
            <p className="text-sm text-muted-foreground">{t('history.noteHint')}</p>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div>
            <Button type="submit" disabled={saving || !minutes}>
              {saving ? t('history.saving') : t('history.save')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function SessionList({ sessions, onDeleted }: { sessions: Session[]; onDeleted: () => void }) {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)

  const handleDelete = (session: Session) => {
    if (!window.confirm(t('history.deleteConfirm', { date: formatLongDate(session.date) }))) return
    api.sessions.remove(session.id).then(onDeleted, (e: Error) => setError(e.message))
  }

  if (sessions.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">{t('history.empty')}</p>
    )
  }

  return (
    <>
      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
      <ul className="divide-y">
        {sessions.map((session) => (
          <li key={session.id} className="flex items-start gap-3 py-3">
            <div className="mt-0.5 rounded-md bg-accent p-2">
              <Timer className="size-4 text-muted-foreground" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {formatLongDate(session.date)}
                <span className="ml-2 whitespace-nowrap text-primary">
                  {formatMinutes(session.minutes)}
                </span>
                {!session.started_at && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    {t('history.manualTag')}
                  </span>
                )}
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

export function HistoryPage() {
  const { t } = useTranslation()
  const [sessions, setSessions] = useState<Session[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api.sessions.list(METRIC).then(setSessions, (e: Error) => setError(e.message))
  }, [])

  useEffect(load, [load])

  return (
    <div className="grid gap-4 sm:gap-5">
      <ManualEntryForm onSaved={load} />
      <Card>
        <CardHeader>
          <CardTitle>{t('history.sessionsTitle')}</CardTitle>
          <CardDescription>{t('history.sessionsDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-destructive">{error}</p>
          ) : (
            <SessionList sessions={sessions} onDeleted={load} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
