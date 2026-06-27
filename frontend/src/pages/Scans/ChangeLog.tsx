import { useEffect, useState, useMemo } from 'react'
import { History, AlertTriangle, RefreshCw, ArrowUp, ArrowDown, Pencil } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { schoolsApi, type SchoolRegistry, type ScanDiff } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

type LoadState = 'loading' | 'ok' | 'error'

export function ChangeLogPage() {
  const [schools, setSchools] = useState<SchoolRegistry[]>([])
  const [diffs, setDiffs] = useState<Map<number, ScanDiff>>(new Map())
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const fetchData = async () => {
    setLoadState('loading')
    try {
      const schoolsData = await schoolsApi.list()
      setSchools(schoolsData)

      const diffMap = new Map<number, ScanDiff>()
      await Promise.all(
        schoolsData.map(async (s) => {
          try {
            const d = await schoolsApi.diff(s.id)
            diffMap.set(s.id, d)
          } catch {
            // skip if diff fails
          }
        }),
      )
      setDiffs(diffMap)
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

  const timeline = useMemo(() => {
    const entries: { school: SchoolRegistry; diff: ScanDiff; total: number }[] = []
    for (const school of schools) {
      const diff = diffs.get(school.id)
      if (diff && diff.scan_run) {
        const total = diff.new_courses.length + diff.modified_courses.length + diff.removed_courses.length
        if (total > 0) {
          entries.push({ school, diff, total })
        }
      }
    }
    return entries.sort((a, b) => {
      const aDate = a.diff.scan_run?.started_at ?? ''
      const bDate = b.diff.scan_run?.started_at ?? ''
      return bDate.localeCompare(aDate)
    })
  }, [schools, diffs])

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Journal des modifications</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Journal des modifications</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les modifications</p>
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
          <h2 className="text-xl font-semibold">Journal des modifications</h2>
          <p className="text-sm text-muted-foreground">
            Évolution des catalogues écoles détectée par scan
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void fetchData()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualiser
        </Button>
      </div>

      {timeline.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <History className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="font-medium text-muted-foreground">Aucun changement détecté</p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              Les modifications apparaîtront ici après les premiers scans.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {timeline.map(({ school, diff, total }) => (
            <Card key={school.id}>
              <CardContent className="p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{school.name}</h3>
                    <p className="text-xs text-muted-foreground">
                      {diff.scan_run?.started_at
                        ? new Date(diff.scan_run.started_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                        : '—'}
                    </p>
                  </div>
                  <span className="text-sm text-muted-foreground">{total} changement{total > 1 ? 's' : ''}</span>
                </div>

                <div className="space-y-2">
                  {diff.new_courses.length > 0 && (
                    <div>
                          <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-green-400">
                            <ArrowUp className="h-3 w-3" /> {diff.new_courses.length} nouveau{diff.new_courses.length > 1 ? 'x' : ''}
                          </p>
                      <div className="space-y-0.5">
                        {diff.new_courses.slice(0, 5).map((c) => (
                          <p key={c.id} className="truncate rounded bg-green-500/5 px-2 py-1 text-xs">{c.title}</p>
                        ))}
                        {diff.new_courses.length > 5 && (
                          <p className="px-2 text-xs text-muted-foreground">+{diff.new_courses.length - 5} autres</p>
                        )}
                      </div>
                    </div>
                  )}

                  {diff.removed_courses.length > 0 && (
                    <div>
                          <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-red-400">
                            <ArrowDown className="h-3 w-3" /> {diff.removed_courses.length} supprimé{diff.removed_courses.length > 1 ? 's' : ''}
                          </p>
                      <div className="space-y-0.5">
                        {diff.removed_courses.slice(0, 5).map((c) => (
                          <p key={c.id} className="truncate rounded bg-red-500/5 px-2 py-1 text-xs line-through">{c.title}</p>
                        ))}
                        {diff.removed_courses.length > 5 && (
                          <p className="px-2 text-xs text-muted-foreground">+{diff.removed_courses.length - 5} autres</p>
                        )}
                      </div>
                    </div>
                  )}

                  {diff.modified_courses.length > 0 && (
                    <div>
                          <p className="mb-1 flex items-center gap-1 text-xs font-semibold text-blue-400">
                            <Pencil className="h-3 w-3" /> {diff.modified_courses.length} modifié{diff.modified_courses.length > 1 ? 's' : ''}
                          </p>
                      <div className="space-y-0.5">
                        {diff.modified_courses.slice(0, 5).map((c) => (
                          <p key={c.id} className="truncate rounded bg-blue-500/5 px-2 py-1 text-xs">{c.title}</p>
                        ))}
                        {diff.modified_courses.length > 5 && (
                          <p className="px-2 text-xs text-muted-foreground">+{diff.modified_courses.length - 5} autres</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
