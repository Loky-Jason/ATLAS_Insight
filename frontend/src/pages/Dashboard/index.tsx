import { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { BookOpen, Users, UserMinus, AlertTriangle } from 'lucide-react'
import { api, ApiError, type AnalyticsPopularity } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { MOCK_ANALYTICS } from './mock-data'
import { cn } from '@/lib/utils'

// ── Composant carte de stat ───────────────────────────────────────────────────

interface StatCardProps {
  label: string
  value: number
  icon: React.ElementType
  className?: string
}

function StatCard({ label, value, icon: Icon, className }: StatCardProps) {
  return (
    <Card className={cn('group relative overflow-hidden transition duration-[var(--duration-normal)] ease-[var(--ease-out)] hover:-translate-y-0.5', className)}>
      <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.03] to-transparent" aria-hidden="true" />
      <CardContent className="relative flex items-center gap-4 p-6">
        <div className="rounded-lg bg-primary/10 p-3 transition-colors group-hover:bg-primary/15">
          <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
        </div>
        <div>
          <p className="text-2xl font-bold tracking-tight tabular-nums">{value.toLocaleString('fr-FR')}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Composant graphe popularité ───────────────────────────────────────────────

interface PopularityChartProps {
  title: string
  description: string
  data: Array<{ title: string; popularity_score: number }>
  barColor: string
}

function PopularityChart({ title, description, data, barColor }: PopularityChartProps) {
  // Troncature du titre pour l'axe X (espace limité)
  const formatted = data.map((d) => ({
    ...d,
    shortTitle: d.title.length > 20 ? d.title.slice(0, 18) + '…' : d.title,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={formatted} margin={{ top: 4, right: 16, left: 0, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis
              dataKey="shortTitle"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              angle={-35}
              textAnchor="end"
              interval={0}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickFormatter={(v: number) => `${v}`}
              label={{
                value: 'Score',
                angle: -90,
                position: 'insideLeft',
                offset: 10,
                style: { fontSize: 11, fill: 'hsl(var(--muted-foreground))' },
              }}
            />
            <Tooltip
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '6px',
                fontSize: '12px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(value: number) => [`${value} / 100`, 'Score popularité']}
              labelFormatter={(label: string) => label}
            />
            <Bar dataKey="popularity_score" radius={[4, 4, 0, 0]} maxBarSize={48}>
              {formatted.map((_, index) => (
                <Cell key={index} fill={barColor} fillOpacity={0.85 - index * 0.1} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

// ── Page Dashboard ────────────────────────────────────────────────────────────

type LoadState = 'loading' | 'ok' | 'mock' | 'error'

export function DashboardPage() {
  const [data, setData] = useState<AnalyticsPopularity | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const fetchAnalytics = async () => {
      try {
        const result = await api.get<AnalyticsPopularity>('/analytics/popularity')
        if (!cancelled) {
          setData(result)
          setLoadState('ok')
        }
      } catch (err) {
        if (cancelled) return

        if (err instanceof ApiError && err.status === 0) {
          // Backend inaccessible → données mock
          setData(MOCK_ANALYTICS)
          setLoadState('mock')
        } else {
          const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
          setErrorMsg(msg)
          setLoadState('error')
        }
      }
    }

    void fetchAnalytics()
    return () => { cancelled = true }
  }, [])

  // ── États de chargement / erreur ──
  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Tableau de bord</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des données...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Tableau de bord</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les données</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // data est garanti non-null ici (loadState = 'ok' | 'mock')
  const analytics = data as AnalyticsPopularity

  return (
    <div className="space-y-6">
      {/* Titre + badge mock */}
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold">Tableau de bord</h2>
        {loadState === 'mock' && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-medium text-amber-400">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            Données de démonstration — backend non connecté
          </span>
        )}
      </div>

      {/* Cartes de stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Cours actifs"
          value={analytics.total_courses}
          icon={BookOpen}
        />
        <StatCard
          label="Inscriptions totales"
          value={analytics.total_enrolled}
          icon={Users}
        />
        <StatCard
          label="Désistements"
          value={analytics.total_dropouts}
          icon={UserMinus}
        />
      </div>

      {/* Graphiques popularité */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <PopularityChart
          title="Cours les plus populaires"
          description="Top 5 par score de popularité (inscrits − désistements, normalisé)"
          data={analytics.most_popular}
          barColor="hsl(217.2, 91.2%, 59.8%)"
        />
        <PopularityChart
          title="Cours les moins populaires"
          description="Les 5 cours avec le score le plus faible — à revoir ou fermer"
          data={analytics.least_popular}
          barColor="hsl(0, 62.8%, 50%)"
        />
      </div>
    </div>
  )
}
