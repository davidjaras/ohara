import { Navigate, Route, Routes, useParams, useSearchParams } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { DashboardPage } from '@/pages/dashboard'
import { HistoryPage } from '@/pages/history'
import { SettingsPage } from '@/pages/settings'
import { TrainingPage } from '@/pages/training'
import { TrainingProgramPage } from '@/pages/training-program'
import { TrainingPhasePage } from '@/pages/training-phase'
import { TrainingDayPage } from '@/pages/training-day'
import { WeightPage } from '@/pages/weight'
import { BrandPreview } from '@/pages/BrandPreview'

/**
 * The day is the one legacy path that carried a query param, and the week it
 * names ends up on the WorkoutSession — so the redirect translates it instead
 * of dropping it.
 */
function LegacyDayRedirect() {
  const { dayId } = useParams()
  const [searchParams] = useSearchParams()
  const week = searchParams.get('semana')
  const query = week ? `?week=${week}` : ''
  return <Navigate to={`/training/day/${dayId}${query}`} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="brand-preview" element={<BrandPreview />} />
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="history" element={<HistoryPage />} />
        {/* The training gate lives in the nav render, not here: without the
            module these routes just hit 404s from the API and render nothing. */}
        <Route path="training" element={<TrainingPage />} />
        <Route path="training/day/:dayId" element={<TrainingDayPage />} />
        <Route path="training/:slug" element={<TrainingProgramPage />} />
        <Route path="training/:slug/phase/:phaseId" element={<TrainingPhasePage />} />
        <Route path="weight" element={<WeightPage />} />
        <Route path="settings" element={<SettingsPage />} />

        {/* Spanish paths the deployed app used to serve; kept so old bookmarks
            and browser history still land somewhere. The UI language never
            depended on them — routes are the same in es and en. */}
        <Route path="historial" element={<Navigate to="/history" replace />} />
        <Route path="peso" element={<Navigate to="/weight" replace />} />
        <Route path="ajustes" element={<Navigate to="/settings" replace />} />
        <Route path="entrenamiento" element={<Navigate to="/training" replace />} />
        <Route path="entrenamiento/dia/:dayId" element={<LegacyDayRedirect />} />
      </Route>
    </Routes>
  )
}
