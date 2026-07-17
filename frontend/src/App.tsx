import { Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/layout'
import { DashboardPage } from '@/pages/dashboard'
import { HistoryPage } from '@/pages/history'
import { SettingsPage } from '@/pages/settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="historial" element={<HistoryPage />} />
        <Route path="ajustes" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
