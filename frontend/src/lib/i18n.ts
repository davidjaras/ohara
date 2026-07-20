import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const STORAGE_KEY = 'ohara-language'

export const LANGUAGES = [
  { code: 'es', label: 'Español' },
  { code: 'en', label: 'English' },
] as const

const es = {
  nav: {
    dashboard: 'Panel',
    history: 'Historial',
    weight: 'Peso',
    settings: 'Ajustes',
  },
  stats: {
    streak: 'Racha',
    week: 'Semana',
    weeks: 'Semanas',
  },
  timer: {
    start: 'Iniciar sesión de estudio',
    keepsRunning: 'El cronómetro sigue corriendo aunque cierres esta pestaña.',
    running: 'En curso',
    paused: 'En pausa',
    pause: 'Pausar',
    resume: 'Reanudar',
    finish: 'Finalizar sesión',
    discard: 'Descartar',
    discardConfirm: '¿Descartar la sesión en curso? El tiempo no se guardará.',
    finishTitle: 'Finalizar sesión',
    studied: 'Tiempo estudiado: {{duration}}',
    noteLabel: '¿Qué estudiaste y qué aprendiste?',
    notePlaceholder:
      'Ej. Repasé índices en Postgres; aprendí cuándo conviene un índice parcial.',
    noteHint: 'La nota queda guardada junto con la sesión.',
    cancel: 'Cancelar',
    save: 'Guardar sesión',
    saving: 'Guardando…',
    loading: 'Cargando…',
  },
  weekProgress: {
    title: 'Esta semana',
    ofGoal: '{{minutes}} de {{goal}}',
    met: 'meta cumplida ✓',
  },
  cumulativeChart: {
    title: 'Acumulado de la semana',
    description: 'Minutos acumulados de lunes a domingo · la línea punteada es la meta',
    goal: 'Meta',
    accumulated: 'Acumulado',
  },
  weeklyChart: {
    title: 'Minutos por semana',
    description: 'Barra a color: meta cumplida · gris: por debajo · la línea punteada es la meta vigente',
    weekOf: 'Semana del {{range}}',
    goal: 'Meta: {{goal}}',
    met: 'Meta cumplida ✓',
    notMet: 'Meta no cumplida',
  },
  weekList: {
    title: 'Semanas cumplidas',
    goal: 'Meta semanal: {{goal}}',
    current: 'en curso',
  },
  ranges: {
    weeks: '{{count}} sem',
    month: '1 mes',
    quarter: '3 meses',
    year: '1 año',
    all: 'Todo',
  },
  history: {
    manualTitle: 'Registro manual',
    manualDescription: 'Rellená sesiones pasadas que no cronometraste.',
    date: 'Fecha',
    minutes: 'Minutos',
    note: 'Nota',
    noteHint: 'Opcional, pero tu yo futuro la agradece.',
    save: 'Guardar registro',
    saving: 'Guardando…',
    sessionsTitle: 'Sesiones',
    sessionsDescription: 'Las más recientes primero.',
    empty: 'Todavía no hay sesiones registradas.',
    manualTag: 'manual',
    deleteConfirm: '¿Borrar la sesión del {{date}}?',
    deleteLabel: 'Borrar sesión',
  },
  weight: {
    formTitle: 'Registrar peso',
    formDescription: 'Una medición puntual por fecha.',
    date: 'Fecha',
    value: 'Peso (kg)',
    save: 'Guardar medición',
    saving: 'Guardando…',
    chartTitle: 'Evolución',
    chartDescription: 'Peso en el tiempo',
    needTwo: 'Registrá al menos dos mediciones para ver la evolución.',
    listTitle: 'Mediciones',
    listDescription: 'Las más recientes primero.',
    empty: 'Todavía no hay mediciones.',
    deleteConfirm: '¿Borrar la medición del {{date}}?',
    deleteLabel: 'Borrar medición',
  },
  settings: {
    goalTitle: 'Meta semanal',
    goalDescription: 'Minutos de estudio por semana. El default es 270 (3 sesiones de 90).',
    goalLabel: 'Minutos por semana',
    goalHint:
      'Los cambios aplican de esta semana en adelante; las semanas pasadas se evalúan con la meta que tenían.',
    goalSaved: 'Meta actualizada. Aplica desde esta semana; las pasadas no cambian.',
    save: 'Guardar meta',
    saving: 'Guardando…',
    languageTitle: 'Idioma',
    languageDescription: 'Idioma de la interfaz.',
    languageLabel: 'Idioma de la app',
    themeTitle: 'Color de acento',
    themeDescription: 'Elegí el color del tema. Aplica a botones, gráficas y el logo.',
    apply: 'Aplicar',
    themeSaved: 'Color actualizado.',
    accents: {
      blue: 'Azul',
      green: 'Verde',
      teal: 'Turquesa',
      violet: 'Violeta',
      rose: 'Rosa',
      amber: 'Ámbar',
      coral: 'Coral',
    },
    accountTitle: 'Cuenta',
    accountDescription: 'Sesión iniciada como {{username}}.',
    changePassword: 'Cambiar contraseña',
    logout: 'Cerrar sesión',
  },
  common: {
    hours: '{{hours}} h',
    hoursMinutes: '{{hours}} h {{minutes}} min',
    minutesOnly: '{{minutes}} min',
  },
}

// English mirrors the Spanish structure key by key.
const en: typeof es = {
  nav: {
    dashboard: 'Dashboard',
    history: 'History',
    weight: 'Weight',
    settings: 'Settings',
  },
  stats: {
    streak: 'Streak',
    week: 'Week',
    weeks: 'Weeks',
  },
  timer: {
    start: 'Start study session',
    keepsRunning: 'The timer keeps running even if you close this tab.',
    running: 'Running',
    paused: 'Paused',
    pause: 'Pause',
    resume: 'Resume',
    finish: 'Finish session',
    discard: 'Discard',
    discardConfirm: 'Discard the session in progress? The time will not be saved.',
    finishTitle: 'Finish session',
    studied: 'Time studied: {{duration}}',
    noteLabel: 'What did you study and what did you learn?',
    notePlaceholder:
      'E.g. Reviewed Postgres indexes; learned when a partial index pays off.',
    noteHint: 'The note is stored with the session.',
    cancel: 'Cancel',
    save: 'Save session',
    saving: 'Saving…',
    loading: 'Loading…',
  },
  weekProgress: {
    title: 'This week',
    ofGoal: '{{minutes}} of {{goal}}',
    met: 'goal met ✓',
  },
  cumulativeChart: {
    title: 'Week running total',
    description: 'Cumulative minutes from Monday to Sunday · the dashed line is the goal',
    goal: 'Goal',
    accumulated: 'Accumulated',
  },
  weeklyChart: {
    title: 'Minutes per week',
    description: 'Colored bar: goal met · gray: below goal · the dashed line is the goal in effect',
    weekOf: 'Week of {{range}}',
    goal: 'Goal: {{goal}}',
    met: 'Goal met ✓',
    notMet: 'Goal not met',
  },
  weekList: {
    title: 'Weeks completed',
    goal: 'Weekly goal: {{goal}}',
    current: 'in progress',
  },
  ranges: {
    weeks: '{{count}} wk',
    month: '1 month',
    quarter: '3 months',
    year: '1 year',
    all: 'All',
  },
  history: {
    manualTitle: 'Manual entry',
    manualDescription: 'Backfill past sessions you did not time.',
    date: 'Date',
    minutes: 'Minutes',
    note: 'Note',
    noteHint: 'Optional, but your future self will thank you.',
    save: 'Save entry',
    saving: 'Saving…',
    sessionsTitle: 'Sessions',
    sessionsDescription: 'Most recent first.',
    empty: 'No sessions logged yet.',
    manualTag: 'manual',
    deleteConfirm: 'Delete the session from {{date}}?',
    deleteLabel: 'Delete session',
  },
  weight: {
    formTitle: 'Log weight',
    formDescription: 'One point-in-time measurement per date.',
    date: 'Date',
    value: 'Weight (kg)',
    save: 'Save measurement',
    saving: 'Saving…',
    chartTitle: 'Trend',
    chartDescription: 'Weight over time',
    needTwo: 'Log at least two measurements to see the trend.',
    listTitle: 'Measurements',
    listDescription: 'Most recent first.',
    empty: 'No measurements yet.',
    deleteConfirm: 'Delete the measurement from {{date}}?',
    deleteLabel: 'Delete measurement',
  },
  settings: {
    goalTitle: 'Weekly goal',
    goalDescription: 'Study minutes per week. The default is 270 (3 sessions of 90).',
    goalLabel: 'Minutes per week',
    goalHint:
      'Changes apply from this week onward; past weeks are evaluated with the goal they had.',
    goalSaved: 'Goal updated. It applies from this week on; past weeks do not change.',
    save: 'Save goal',
    saving: 'Saving…',
    languageTitle: 'Language',
    languageDescription: 'Interface language.',
    languageLabel: 'App language',
    themeTitle: 'Accent color',
    themeDescription: 'Pick the theme color. It applies to buttons, charts and the logo.',
    apply: 'Apply',
    themeSaved: 'Color updated.',
    accents: {
      blue: 'Blue',
      green: 'Green',
      teal: 'Teal',
      violet: 'Violet',
      rose: 'Rose',
      amber: 'Amber',
      coral: 'Coral',
    },
    accountTitle: 'Account',
    accountDescription: 'Signed in as {{username}}.',
    changePassword: 'Change password',
    logout: 'Log out',
  },
  common: {
    hours: '{{hours}} h',
    hoursMinutes: '{{hours}} h {{minutes}} min',
    minutesOnly: '{{minutes}} min',
  },
}

export function storedLanguage(): string {
  return localStorage.getItem(STORAGE_KEY) ?? 'es'
}

export function setLanguage(code: string) {
  localStorage.setItem(STORAGE_KEY, code)
  i18n.changeLanguage(code)
  document.documentElement.lang = code
}

i18n.use(initReactI18next).init({
  resources: { es: { translation: es }, en: { translation: en } },
  lng: storedLanguage(),
  fallbackLng: 'es',
  interpolation: { escapeValue: false },
})

export default i18n
