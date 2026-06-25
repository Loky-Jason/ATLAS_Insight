import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  TrendingUp,
  Lightbulb,
  Archive,
  Upload,
  LogOut,
  Activity,
} from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { ErrorBoundary } from '@/components/ErrorBoundary'
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
  const location = useLocation()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className="flex w-60 flex-shrink-0 flex-col border-r border-border bg-card"
        aria-label="Navigation principale"
      >
        {/* Logo */}
        <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Activity className="h-4 w-4 text-primary-foreground" aria-hidden="true" />
          </div>
          <span className="text-base font-semibold tracking-tight text-foreground">
            ATLAS<em className="text-primary not-italic"> Insight</em>
          </span>
        </div>

        {/* Navigation */}
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/dashboard'}
              className={({ isActive }) =>
                cn(
                  'group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition duration-[var(--duration-normal)] ease-[var(--ease-out)]',
                  isActive
                    ? 'bg-primary/15 text-primary'
                    : 'text-muted-foreground hover:bg-accent/10 hover:text-foreground',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <div className={cn(
                    'flex h-5 w-5 items-center justify-center',
                    isActive && 'text-primary',
                  )}>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <span className="flex-1">{label}</span>
                  {isActive && (
                    <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-border p-3">
          <div className="mb-2 flex items-center gap-2.5 rounded-md px-2.5 py-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-xs font-semibold text-primary">
              {user?.email.charAt(0).toUpperCase() ?? '?'}
            </div>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-xs font-medium text-foreground">
                {user?.email ?? ''}
              </span>
              {user?.role && (
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {user.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            onClick={() => void handleLogout()}
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Déconnexion
          </Button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center border-b border-border bg-card px-6">
          <h1 className="text-sm font-medium text-muted-foreground">
            Tableau de bord décisionnel — <em className="text-foreground not-italic">SCAP.paris</em>
          </h1>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
