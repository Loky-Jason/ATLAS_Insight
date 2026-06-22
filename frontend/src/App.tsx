import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './lib/auth'
import { AppShell } from './components/AppShell'
import { LoginPage } from './pages/Login'
import { DashboardPage } from './pages/Dashboard'
import { CoursesPage } from './pages/Courses'
import { MarketWatchPage } from './pages/MarketWatch'
import { ProposalsPage } from './pages/Proposals'
import { ArchivesPage } from './pages/Archives'

// Garde de route : redirige vers /login si non authentifié
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-muted-foreground text-sm">Chargement...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="market-watch" element={<MarketWatchPage />} />
        <Route path="proposals" element={<ProposalsPage />} />
        <Route path="archives" element={<ArchivesPage />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
