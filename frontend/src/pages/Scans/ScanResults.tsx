import { useEffect, useState, useMemo } from 'react'
import { FileSearch, AlertTriangle, RefreshCw } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { scanRunsApi, schoolsApi, type ScanRun, type SchoolRegistry } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type LoadState = 'loading' | 'ok' | 'error'

function ScanStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: 'bg-green-500/15 text-green-400',
    running: 'bg-blue-500/15 text-blue-400',
    error: 'bg-red-500/15 text-red-400',
  }
  const labels: Record<string, string> = {
    completed: 'Terminé',
    running: 'En cours',
    error: 'Erreur',
  }
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', colors[status] ?? 'bg-gray-500/15 text-gray-400')}>
      {labels[status] ?? status}
    </span>
  )
}

export function ScanResultsPage() {
  const [runs, setRuns] = useState<ScanRun[]>([])
  const [schools, setSchools] = useState<SchoolRegistry[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [schoolFilter, setSchoolFilter] = useState<string>('')

  const fetchData = async () => {
    setLoadState('loading')
    try {
      const [runsData, schoolsData] = await Promise.all([
        scanRunsApi.list({ limit: 200 }),
        schoolsApi.list(),
      ])
      setRuns(runsData)
      setSchools(schoolsData)
      setLoadState('ok')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setLoadState('error')
    }
  }

  useEffect(() => {
    void fetchData()
  }, [])

  const schoolMap = useMemo(() => {
    const m = new Map<number, string>()
    for (const s of schools) m.set(s.id, s.name)
    return m
  }, [schools])

  const filtered = schoolFilter ? runs.filter((r) => r.school_registry_id === Number(schoolFilter)) : runs

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Résultats de scan</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des résultats...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Résultats de scan</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les résultats</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void fetchData()}>Réessayer</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Résultats de scan</h2>
          <p className="text-sm text-muted-foreground">
            Historique des scans par école
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void fetchData()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualiser
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <select
            value={schoolFilter}
            onChange={(e) => setSchoolFilter(e.target.value)}
            className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="">Toutes les écoles</option>
            {schools.map((s) => (
              <option key={s.id} value={String(s.id)}>{s.name}</option>
            ))}
          </select>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <FileSearch className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="font-medium text-muted-foreground">Aucun scan trouvé</p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              Lancez un scan depuis la page « Écoles suivies ».
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">École</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Date</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Statut</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Trouvés</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Nouveaux</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Modifiés</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Supprimés</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((run) => (
                  <tr key={run.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium">{schoolMap.get(run.school_registry_id) ?? `École #${run.school_registry_id}`}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {new Date(run.started_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3"><ScanStatusBadge status={run.status} /></td>
                    <td className="px-4 py-3 text-right tabular-nums">{run.courses_found}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-green-400">{run.courses_new}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-blue-400">{run.courses_modified}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-red-400">{run.courses_removed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
