import { useEffect, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { KeyRound, LogOut } from 'lucide-react'
import { api, logout } from '@/lib/api'
import { LANGUAGES, setLanguage } from '@/lib/i18n'
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

const METRIC = 'estudio'

function GoalCard() {
  const { t } = useTranslation()
  const [minutes, setMinutes] = useState('')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.goal.get(METRIC).then(
      (goal) => setMinutes(String(goal.minutes)),
      (e: Error) => setError(e.message),
    )
  }, [])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    setError(null)
    api.goal.set(METRIC, Number(minutes)).then(
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
      <LanguageCard />
      <AccountCard />
    </div>
  )
}
