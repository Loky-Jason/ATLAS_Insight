import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  TrendingUp,
  Lightbulb,
  Archive,
  Upload,
  LogOut,
  ChevronRight,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

// ── Navigation items ──────────────────────────────────────────────────────────

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
  { to: '/courses', label: 'Cours SCAP', icon: BookOpen },
  { to: '/market-watch', label: 'Veille marché', icon: TrendingUp },
  { to: '/proposals', label: 'Propositions', icon: Lightbulb },
  { to: '/import', label: 'Import', icon: Upload },
  { to: '/archives', label: 'Archives', icon: Archive },
] as const

// ── AppShell ──────────────────────────────────────────────────────────────────

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar verticale */}
      <aside
        className="flex w-60 flex-shrink-0 flex-col border-r border-border bg-card"
        aria-label="Navigation principale"
      >
        {/* Logo / Titre */}
        <div className="flex h-16 items-center border-b border-border px-6">
          <span className="text-lg font-bold tracking-tight text-foreground">
            ATLAS<span className="text-primary"> Insight</span>
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                  <span className="flex-1">{label}</span>
                  {isActive && (
                    <ChevronRight className="h-3 w-3 opacity-60" aria-hidden="true" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer sidebar */}
        <div className="border-t border-border p-3">
          <div className="mb-2 flex items-center gap-2 px-2 py-1">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
              {user?.email.charAt(0).toUpperCase() ?? '?'}
            </div>
            <span className="flex-1 truncate text-xs text-muted-foreground">
              {user?.email ?? ''}
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
            onClick={() => void handleLogout()}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Déconnexion
          </Button>
        </div>
      </aside>

      {/* Zone principale */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center border-b border-border bg-card px-6">
          <h1 className="text-sm font-medium text-muted-foreground">
            Tableau de bord décisionnel — SCAP.paris
          </h1>
        </header>

        {/* Contenu de la page */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
