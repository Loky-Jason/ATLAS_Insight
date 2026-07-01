import { useEffect, useState } from 'react'
import { AlertTriangle, PlusCircle, XCircle, Clock, Award, CheckCircle2, ThumbsDown, Loader2 } from 'lucide-react'
import { ApiError, gapApi, type GapRecommendationRead } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Variant = 'closure' | 'creation'
type LoadState = 'loading' | 'ok' | 'error'

type CertSuggestion = { label?: string; type?: string }

const FACTOR_LABELS: Record<string, string> = {
  schools_offering_count: 'écoles concurrentes',
  low_popularity: 'popularité faible',
  title_similarity: 'similarité de titre',
  market_age: 'ancienneté marché',
  price_pressure: 'pression prix',
  high_demand: 'demande élevée',
  competitive_gap: 'absence concurrentielle',
}

function parseJsonArray(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === 'string') : []
  } catch { return [] }
}

function parseCertifications(raw: string | null): CertSuggestion[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .map((c) => (c && typeof c === 'object' ? (c as CertSuggestion) : null))
      .filter((c): c is CertSuggestion => c !== null && Boolean(c.label || c.type))
  } catch { return [] }
}

export function GapRecommendationsList({ variant }: { variant: Variant }) {
  const isClosure = variant === 'closure'
  const [items, setItems] = useState<GapRecommendationRead[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [actionId, setActionId] = useState<number | null>(null)

  const fetchItems = async () => {
    setLoadState('loading')
    setErrorMsg(null)
    try {
      const data = isClosure ? await gapApi.listClosure() : await gapApi.listCreation()
      setItems(data)
      setLoadState('ok')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setLoadState('error')
      console.error('Failed to load recommendations:', err)
    }
  }

  useEffect(() => { void fetchItems() }, [variant])

  const handleAction = async (id: number, action: 'approve' | 'reject') => {
    setErrorMsg(null)
    setActionId(id)
    try {
      if (action === 'approve') {
        await gapApi.approve(id)
      } else {
        await gapApi.reject(id)
      }
      setItems((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      const reason = action === 'approve' ? "de l'approbation" : 'du rejet'
      setErrorMsg(err instanceof ApiError ? err.message : `Erreur lors ${reason}`)
      console.error(`Recommendation ${action} failed:`, err)
    } finally { setActionId(null) }
  }

  const Icon = isClosure ? XCircle : PlusCircle
  const iconBg = isClosure ? 'bg-amber-500/15 text-amber-400' : 'bg-emerald-500/15 text-emerald-400'
  const scoreHigh = isClosure ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-400'
  const label = isClosure ? 'Fermeture' : 'Création'
  const emptyTitle = isClosure ? 'Aucune recommandation de fermeture' : 'Aucune suggestion de création'
  const emptyDesc = isClosure
    ? 'Lancez une analyse depuis le tableau de bord pour détecter les cours menacés.'
    : 'Lancez une analyse depuis le tableau de bord pour identifier les formations à créer.'
  const pageTitle = isClosure ? 'Recommandations — À fermer' : 'Recommandations — À créer'

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">{pageTitle}</h2>
        <Card><CardContent className="py-12 text-center text-muted-foreground">Chargement...</CardContent></Card>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">{pageTitle}</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-4">
            <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
            <p className="text-sm text-destructive">{errorMsg}</p>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void fetchItems()}>Réessayer</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{pageTitle}</h2>
        <span className="text-sm text-muted-foreground">
          {items.length} {isClosure ? 'candidat' : 'suggestion'}{items.length !== 1 ? 's' : ''}
        </span>
      </div>

      {errorMsg && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-4">
            <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
            <p className="text-sm text-destructive">{errorMsg}</p>
            <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setErrorMsg(null)}>Fermer</Button>
          </CardContent>
        </Card>
      )}

      {items.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Icon className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="font-medium text-muted-foreground">{emptyTitle}</p>
            <p className="max-w-xs text-sm text-muted-foreground/70">{emptyDesc}</p>
          </CardContent>
        </Card>
      )}

      {items.map((rec) => {
        const schools = parseJsonArray(rec.schools_offering)
        const certs = parseCertifications(rec.certification_suggestions)
        const isBusy = actionId === rec.id

        let factors: { key: string; display: string }[] = []
        if (rec.score_breakdown) {
          try {
            const raw = JSON.parse(rec.score_breakdown)
            if (raw && typeof raw === 'object') {
              factors = Object.entries(raw)
                .filter(([k]) => k !== 'representative_title' && k !== 'weighted_score')
                .map(([k, v]) => ({
                  key: k,
                  display: typeof v === 'number' ? `${(v * 100).toFixed(0)}` : String(v),
                }))
            }
          } catch { /* ignore malformed JSON */ }
        }

        const certLabel = (cert: CertSuggestion) => cert.label ?? cert.type ?? ''

        return (
          <Card key={rec.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className={cn('mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full', iconBg)}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <CardTitle className="text-base">
                      {rec.course_title ?? rec.rationale ?? `Recommandation #${rec.id}`}
                    </CardTitle>
                    {rec.course_description && (
                      <p
                        className="mt-1 line-clamp-2 text-sm text-muted-foreground"
                        title={rec.course_description}
                      >
                        {rec.course_description}
                      </p>
                    )}
                    {schools.length > 0 && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Proposé par {schools.join(', ')}
                      </p>
                    )}
                  </div>
                </div>
                <span className={cn(
                  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0',
                  rec.score >= 70 ? scoreHigh :
                  rec.score >= 50 ? 'bg-amber-500/15 text-amber-400' :
                  'bg-yellow-500/15 text-yellow-400',
                )}>
                  Score {rec.score}
                </span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {!isClosure && (rec.suggested_hours != null || certs.length > 0) && (
                <div className="flex flex-wrap gap-2">
                  {rec.suggested_hours != null && (
                    <span className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {rec.suggested_hours}h estimées
                    </span>
                  )}
                  {certs.slice(0, 3).map((cert) => (
                    <span key={certLabel(cert)} className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      <Award className="h-3 w-3" />
                      {certLabel(cert)}
                    </span>
                  ))}
                  {certs.length > 3 && (
                    <span className="text-[11px] text-muted-foreground">+{certs.length - 3} autres</span>
                  )}
                </div>
              )}
              {factors.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {factors.map((f) => (
                    <span key={f.key} className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">
                      {FACTOR_LABELS[f.key] ?? f.key.replace(/_/g, ' ')}
                      <span className="font-medium tabular-nums">{f.display}</span>
                    </span>
                  ))}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="default"
                  disabled={isBusy || rec.status !== 'draft'}
                  onClick={() => void handleAction(rec.id, 'approve')}
                >
                  {isBusy ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <><CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Approuver</>
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={isBusy || rec.status !== 'draft'}
                  onClick={() => void handleAction(rec.id, 'reject')}
                >
                  {isBusy ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <><ThumbsDown className="mr-1 h-3.5 w-3.5" /> Rejeter</>
                  )}
                </Button>
                {rec.status !== 'draft' && (
                  <span className="text-xs text-muted-foreground">
                    {rec.status === 'approved'
                      ? `Approuvée (${label})`
                      : rec.status === 'implemented'
                        ? 'Traitée'
                        : 'Rejetée'}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
