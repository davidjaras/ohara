import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRound, LogOut } from 'lucide-react'
import { api, logout } from '@/lib/api'
import {
  MAX_REMINDER_MINUTES,
  MAX_WEEK_MINUTES,
  METRIC_ESTUDIO,
  REMINDER_PRESET_MINUTES,
} from '@/lib/constants'
import { LANGUAGES, setLanguage } from '@/lib/i18n'
import { ACCENTS, setAccent, storedAccent } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { RangeSelect } from '@/components/range-select'

function GoalCard() {
  const { t } = useTranslation()
  const [minutes, setMinutes] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.goal.get(METRIC_ESTUDIO).then(
      (goal) => setMinutes(String(goal.minutes)),
      (e: Error) => setError(e.message),
    )
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)
    api.goal.set(METRIC_ESTUDIO, Number(minutes)).then(
      (goal) => {
        setSaving(false)
        setMinutes(String(goal.minutes))
        setMessage(t('settings.goalSaved'))
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
        <CardTitle>{t('settings.goalTitle')}</CardTitle>
        <CardDescription>{t('settings.goalDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="goal-minutes">{t('settings.goalLabel')}</Label>
            <Input
              id="goal-minutes"
              type="number"
              min={1}
              max={MAX_WEEK_MINUTES}
              step={1}
              value={minutes}
              onChange={(e) => setMinutes(e.target.value)}
              required
            />
            <p className="text-sm text-muted-foreground">{t('settings.goalHint')}</p>
          </div>
          {message && <p className="text-sm text-primary">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div>
            <Button type="submit" disabled={saving || !minutes}>
              {saving ? t('settings.saving') : t('settings.save')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

type ReminderChoice = number | 'custom' | 'off'

function ReminderCard() {
  const { t } = useTranslation()
  const [choice, setChoice] = useState<ReminderChoice>(30)
  const [customMinutes, setCustomMinutes] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.preferences.get().then(
      (pref) => {
        setLoaded(true)
        if (pref.reminder_minutes === null) {
          setChoice('off')
        } else if (REMINDER_PRESET_MINUTES.includes(pref.reminder_minutes)) {
          setChoice(pref.reminder_minutes)
        } else {
          setChoice('custom')
          setCustomMinutes(String(pref.reminder_minutes))
        }
      },
      (e: Error) => setError(e.message),
    )
  }, [])

  const customInvalid =
    choice === 'custom' &&
    (!Number.isInteger(Number(customMinutes)) ||
      Number(customMinutes) < 1 ||
      Number(customMinutes) > MAX_REMINDER_MINUTES)

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const minutes =
      choice === 'off' ? null : choice === 'custom' ? Number(customMinutes) : choice
    setSaving(true)
    setMessage(null)
    setError(null)
    api.preferences.set({ reminder_minutes: minutes }).then(
      () => {
        setSaving(false)
        setMessage(t('settings.reminderSaved'))
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
        <CardTitle>{t('settings.reminderTitle')}</CardTitle>
        <CardDescription>{t('settings.reminderDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <RangeSelect<ReminderChoice>
              options={[
                ...REMINDER_PRESET_MINUTES.map((minutes) => ({
                  value: minutes as ReminderChoice,
                  label: t('timer.presetMinutes', { count: minutes }),
                })),
                { value: 'custom', label: t('settings.reminderCustom') },
                { value: 'off', label: t('settings.reminderOff') },
              ]}
              value={choice}
              onChange={setChoice}
            />
            {choice === 'custom' && (
              <Input
                type="number"
                min={1}
                max={MAX_REMINDER_MINUTES}
                step={1}
                aria-label={t('settings.reminderCustomLabel')}
                className="w-24"
                value={customMinutes}
                onChange={(e) => setCustomMinutes(e.target.value)}
              />
            )}
          </div>
          <p className="text-sm text-muted-foreground">{t('settings.reminderHint')}</p>
          {message && <p className="text-sm text-primary">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div>
            <Button type="submit" disabled={saving || !loaded || customInvalid}>
              {saving ? t('settings.saving') : t('settings.reminderSave')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function LanguageCard() {
  const { t, i18n } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.languageTitle')}</CardTitle>
        <CardDescription>{t('settings.languageDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-2">
          <Label>{t('settings.languageLabel')}</Label>
          <Select value={i18n.language} onValueChange={setLanguage}>
            <SelectTrigger className="w-full sm:w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map((lang) => (
                <SelectItem key={lang.code} value={lang.code}>
                  {lang.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}

function ThemeCard() {
  const { t } = useTranslation()
  const [selected, setSelected] = useState(storedAccent())
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.preferences.get().then(
      (pref) => setSelected(pref.accent_color),
      () => {},
    )
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)
    api.preferences.set({ accent_color: selected }).then(
      (pref) => {
        setSaving(false)
        setAccent(pref.accent_color)
        setMessage(t('settings.themeSaved'))
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
        <CardTitle>{t('settings.themeTitle')}</CardTitle>
        <CardDescription>{t('settings.themeDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="flex flex-wrap gap-3">
            {ACCENTS.map((accent) => {
              const isSelected = selected === accent.code
              return (
                <button
                  key={accent.code}
                  type="button"
                  onClick={() => setSelected(accent.code)}
                  aria-label={t(accent.labelKey)}
                  aria-pressed={isSelected}
                  title={t(accent.labelKey)}
                  className={cn(
                    'size-10 rounded-full ring-offset-2 ring-offset-background transition-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isSelected ? 'ring-2 ring-ring scale-110' : 'hover:scale-105',
                  )}
                  style={{ background: accent.color }}
                />
              )
            })}
          </div>
          {message && <p className="text-sm text-primary">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div>
            <Button type="submit" disabled={saving}>
              {saving ? t('settings.saving') : t('settings.apply')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function AccountCard() {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')

  useEffect(() => {
    api.me().then((me) => setUsername(me.username), () => {})
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.accountTitle')}</CardTitle>
        <CardDescription>{t('settings.accountDescription', { username })}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button variant="outline" asChild>
          <a href="/accounts/password_change/">
            <KeyRound className="size-4" />
            {t('settings.changePassword')}
          </a>
        </Button>
        <Button
          variant="ghost"
          className="text-muted-foreground"
          onClick={() => void logout()}
        >
          <LogOut className="size-4" />
          {t('settings.logout')}
        </Button>
      </CardContent>
    </Card>
  )
}

export function SettingsPage() {
  return (
    <div className="mx-auto grid max-w-xl gap-4 sm:gap-5">
      <GoalCard />
      <ReminderCard />
      <LanguageCard />
      <ThemeCard />
      <AccountCard />
    </div>
  )
}
