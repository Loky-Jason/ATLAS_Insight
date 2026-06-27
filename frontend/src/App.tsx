import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './lib/auth'
import { AppShell } from './components/AppShell'
import { LoginPage } from './pages/Login'
import { DashboardPage } from './pages/Dashboard'
import { CoursesPage } from './pages/Courses'
import { ProposalsPage } from './pages/Proposals'
import { ImportPage } from './pages/Import'
import { ArchivesPage } from './pages/Archives'
import { ScanResultsPage } from './pages/Scans/ScanResults'
import { ChangeLogPage } from './pages/Scans/ChangeLog'
import { SchoolsPage } from './pages/Schools/Schools'
import { GapClosurePage } from './pages/Gap/GapClosure'
import { GapCreationPage } from './pages/Gap/GapCreation'

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
        {/* Veille */}
        <Route path="scan-results" element={<ScanResultsPage />} />
        <Route path="changelog" element={<ChangeLogPage />} />
        <Route path="schools" element={<SchoolsPage />} />
        {/* Recommandations */}
        <Route path="gap-closure" element={<GapClosurePage />} />
        <Route path="gap-creation" element={<GapCreationPage />} />
        <Route path="proposals" element={<ProposalsPage />} />
        {/* Catalogue */}
        <Route path="courses" element={<CoursesPage />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="archives" element={<ArchivesPage />} />
        {/* Redirections anciens chemins */}
        <Route path="market-watch" element={<Navigate to="/scan-results" replace />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
