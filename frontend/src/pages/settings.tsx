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
import { requestNotificationPermission } from '@/lib/notify'
import { ACCENTS, setAccent, storedAccent } from '@/lib/theme'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
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
import { Section } from '@/components/section'

function GoalSection() {
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
    <Section title={t('settings.goalTitle')} description={t('settings.goalDescription')}>
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
    </Section>
  )
}

type ReminderChoice = number | 'custom' | 'off'

function ReminderSection() {
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
    // The one moment of explicit intent: someone configuring reminders wants
    // to be reminded, so this is where the browser permission is requested.
    if (minutes !== null) requestNotificationPermission()
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
    <Section title={t('settings.reminderTitle')} description={t('settings.reminderDescription')}>
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
    </Section>
  )
}

function LanguageSection() {
  const { t, i18n } = useTranslation()

  return (
    <Section title={t('settings.languageTitle')} description={t('settings.languageDescription')}>
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
    </Section>
  )
}

function ThemeSection() {
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
    <Section title={t('settings.themeTitle')} description={t('settings.themeDescription')}>
      <form onSubmit={handleSubmit} className="grid gap-4">
        <div className="flex flex-wrap gap-2.5">
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
                  // The selection ring is neutral rather than --ring: --ring
                  // follows the accent, so on its own swatch it disappears.
                  'size-9 rounded-full ring-offset-2 ring-offset-background transition-transform focus-visible:ring-2 focus-visible:ring-foreground/70 focus-visible:outline-none',
                  isSelected ? 'scale-110 ring-2 ring-foreground/70' : 'hover:scale-105',
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
    </Section>
  )
}

function AccountSection() {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')

  useEffect(() => {
    api.me().then((me) => setUsername(me.username), () => {})
  }, [])

  return (
    <Section
      title={t('settings.accountTitle')}
      description={t('settings.accountDescription', { username })}
    >
      <div className="flex flex-wrap gap-2">
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
      </div>
    </Section>
  )
}

export function SettingsPage() {
  return (
    <div className="grid gap-8">
      <GoalSection />
      <ReminderSection />
      <LanguageSection />
      <ThemeSection />
      <AccountSection />
    </div>
  )
}
