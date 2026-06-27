import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { BookOpen, Users, UserMinus, AlertTriangle, GraduationCap, Sparkles, XCircle, PlusCircle, RefreshCw } from 'lucide-react'
import { api, ApiError, type AnalyticsPopularity, type DashboardCounts, type GapRecommendationList, dashboardApi, gapApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { MOCK_ANALYTICS } from './mock-data'
import { cn } from '@/lib/utils'

// ── StatCard ─────────────────────────────────────────────────────────────────

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

// ── PopularityChart ──────────────────────────────────────────────────────────

interface PopularityChartProps {
  title: string
  description: string
  data: Array<{ title: string; popularity_score: number }>
  barColor: string
}

function PopularityChart({ title, description, data, barColor }: PopularityChartProps) {
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
              contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '6px', fontSize: '12px', color: 'hsl(var(--foreground))' }}
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

// ── Widget recommandations ───────────────────────────────────────────────────

function RecommendationsWidget({ recommendations, onApprove }: {
  recommendations: GapRecommendationList[]
  onApprove: (id: number) => void
}) {
  if (recommendations.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recommandations</CardTitle>
          <CardDescription>Aucune recommandation en attente</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-muted-foreground">
            Lancez une analyse depuis la section Recommandations pour générer des suggestions.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Recommandations récentes</CardTitle>
          <span className="text-xs text-muted-foreground">{recommendations.length} en attente</span>
        </div>
        <CardDescription>Actions rapides sur les suggestions les plus pertinentes</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {recommendations.map((rec) => (
          <div key={rec.id} className="flex items-start gap-3 rounded-md border border-border p-3">
            <div className={cn(
              'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
              rec.recommendation_type === 'closure' ? 'bg-amber-500/15 text-amber-400' : 'bg-emerald-500/15 text-emerald-400',
            )}>
              {rec.recommendation_type === 'closure' ? <XCircle className="h-3.5 w-3.5" /> : <PlusCircle className="h-3.5 w-3.5" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-foreground truncate">
                {rec.rationale ?? `Recommandation #${rec.id}`}
              </p>
              <div className="mt-1 flex items-center gap-2">
                <span className={cn(
                  'inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider',
                  rec.recommendation_type === 'closure'
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-emerald-500/10 text-emerald-400',
                )}>
                  {rec.recommendation_type === 'closure' ? 'Fermeture' : 'Création'}
                </span>
                <span className="text-xs tabular-nums text-muted-foreground">Score {rec.score}</span>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="shrink-0 text-xs"
              onClick={() => onApprove(rec.id)}
              disabled={rec.status !== 'draft'}
            >
              Approuver
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ── Widget vue d'ensemble ────────────────────────────────────────────────────

function OverviewWidget({ counts }: { counts: DashboardCounts | null }) {
  if (!counts) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Vue d'ensemble</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-muted-foreground">Indisponible</p>
        </CardContent>
      </Card>
    )
  }

  const items = [
    { label: 'Écoles suivies', value: counts.total_schools, icon: GraduationCap, color: 'text-sky-400' },
    { label: 'Scans non examinés', value: counts.unreviewed_scans, icon: RefreshCw, color: counts.unreviewed_scans > 0 ? 'text-amber-400' : 'text-muted-foreground' },
    { label: 'Fermetures proposées', value: counts.closure_candidates, icon: XCircle, color: 'text-amber-400' },
    { label: 'Créations suggérées', value: counts.creation_suggestions, icon: Sparkles, color: 'text-emerald-400' },
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Vue d'ensemble</CardTitle>
        <CardDescription>État du système de veille</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => (
          <div key={item.label} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <item.icon className={cn('h-4 w-4', item.color)} aria-hidden="true" />
              <span className="text-sm text-muted-foreground">{item.label}</span>
            </div>
            <span className="text-sm font-semibold tabular-nums text-foreground">{item.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ── Page Dashboard ───────────────────────────────────────────────────────────

type LoadState = 'loading' | 'ok' | 'mock' | 'error'

export function DashboardPage() {
  const [data, setData] = useState<AnalyticsPopularity | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Hub data
  const [counts, setCounts] = useState<DashboardCounts | null>(null)
  const [recommendations, setRecommendations] = useState<GapRecommendationList[]>([])

  useEffect(() => {
    let cancelled = false

    const fetchAll = async () => {
      try {
        const [result, countsData, recs] = await Promise.all([
          api.get<AnalyticsPopularity>('/analytics/popularity'),
          dashboardApi.counts().catch(() => null),
          gapApi.list({ limit: 3 }).catch(() => [] as GapRecommendationList[]),
        ])
        if (!cancelled) {
          setData(result)
          setCounts(countsData)
          setRecommendations(recs)
          setLoadState('ok')
        }
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 0) {
          setData(MOCK_ANALYTICS)
          setLoadState('mock')
        } else {
          const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
          setErrorMsg(msg)
          setLoadState('error')
        }
      }
    }

    void fetchAll()
    return () => { cancelled = true }
  }, [])

  const handleApprove = async (id: number) => {
    try {
      await gapApi.approve(id)
      setRecommendations((prev) => prev.filter((r) => r.id !== id))
    } catch {
      // Silently fail — user will see error toast in future
    }
  }

  // Loading state
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

  // Error state
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

  const analytics = data as AnalyticsPopularity

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold">Tableau de bord</h2>
        {loadState === 'mock' && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-medium text-amber-400">
            <AlertTriangle className="h-3 w-3" aria-hidden="true" />
            Données de démonstration — backend non connecté
          </span>
        )}
      </div>

      {/* Row 1 — Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Cours actifs" value={analytics.total_courses} icon={BookOpen} />
        <StatCard label="Inscriptions totales" value={analytics.total_enrolled} icon={Users} />
        <StatCard label="Désistements" value={analytics.total_dropouts} icon={UserMinus} />
      </div>

      {/* Row 2 — Hub widgets */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecommendationsWidget recommendations={recommendations} onApprove={handleApprove} />
        </div>
        <div>
          <OverviewWidget counts={counts} />
        </div>
      </div>

      {/* Row 3 — Charts */}
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
