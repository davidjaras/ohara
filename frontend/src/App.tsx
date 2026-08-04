import { Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { DashboardPage } from '@/pages/dashboard'
import { HistoryPage } from '@/pages/history'
import { SettingsPage } from '@/pages/settings'
import { TrainingPage } from '@/pages/training'
import { TrainingDayPage } from '@/pages/training-day'
import { WeightPage } from '@/pages/weight'
import { BrandPreview } from '@/pages/BrandPreview'

export default function App() {
  return (
    <Routes>
      <Route path="brand-preview" element={<BrandPreview />} />
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="historial" element={<HistoryPage />} />
        {/* The training gate lives in the nav render, not here: without the
            module these routes just hit 404s from the API and render nothing. */}
        <Route path="entrenamiento" element={<TrainingPage />} />
        <Route path="entrenamiento/dia/:dayId" element={<TrainingDayPage />} />
        <Route path="peso" element={<WeightPage />} />
        <Route path="ajustes" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
