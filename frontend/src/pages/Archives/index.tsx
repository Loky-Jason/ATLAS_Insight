import { useCallback, useEffect, useMemo, useState } from 'react'
import { Archive, AlertTriangle, RotateCcw, Search, ClipboardCheck } from 'lucide-react'
import {
  ApiError,
  coursesApi,
  gapApi,
  type Course,
  type GapRecommendationList,
} from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

type LoadState = 'loading' | 'ok' | 'error'

/** Plafond serveur de `GET /gap-recommendations` (`limit` max 200). */
const RECOMMENDATIONS_LIMIT = 200

/**
 * Lignes de cours rendues d'emblée. `GET /courses` n'est pas borné côté serveur
 * et les postes de la Mairie sont peu puissants : au-delà, l'affichage est
 * déplié à la demande plutôt que d'un bloc.
 */
const COURSES_PAGE_SIZE = 100

function formatDate(value: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString('fr-FR')
}

function TypeBadge({ type }: { type: GapRecommendationList['recommendation_type'] }) {
  const isClosure = type === 'closure'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        isClosure ? 'bg-red-500/15 text-red-400' : 'bg-emerald-500/15 text-emerald-400',
      )}
    >
      {isClosure ? 'Fermeture' : 'Création'}
    </span>
  )
}

export function ArchivesPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [courses, setCourses] = useState<Course[]>([])
  const [recommendations, setRecommendations] = useState<GapRecommendationList[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [restoringId, setRestoringId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [showAllCourses, setShowAllCourses] = useState(false)

  const fetchAll = useCallback(async () => {
    setLoadState('loading')
    try {
      // En parallèle : deux sources indépendantes, pas de cascade de latence.
      const [archivedCourses, approvedRecommendations] = await Promise.all([
        coursesApi.list({ status: 'archived' }),
        gapApi.list({ status: 'approved', limit: RECOMMENDATIONS_LIMIT }),
      ])
      setCourses(archivedCourses)
      setRecommendations(approvedRecommendations)
      setLoadState('ok')
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Erreur inconnue')
      setLoadState('error')
    }
  }, [])

  useEffect(() => {
    void fetchAll()
  }, [fetchAll])

  const filteredCourses = useMemo(() => {
    if (!search) return courses
    const query = search.toLowerCase()
    return courses.filter(
      (course) =>
        course.title.toLowerCase().includes(query) ||
        (course.category ?? '').toLowerCase().includes(query),
    )
  }, [courses, search])

  const visibleCourses = showAllCourses
    ? filteredCourses
    : filteredCourses.slice(0, COURSES_PAGE_SIZE)
  const hiddenCoursesCount = filteredCourses.length - visibleCourses.length
  // Le serveur tronque silencieusement : à ras du plafond, le total peut être plus grand.
  const recommendationsTruncated = recommendations.length === RECOMMENDATIONS_LIMIT

  const handleRestore = async (course: Course) => {
    setActionError(null)
    setRestoringId(course.id)
    try {
      await coursesApi.restore(course.id)
      // Seuls les cours changent : inutile de recharger les recommandations.
      setCourses(await coursesApi.list({ status: 'archived' }))
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? `Restauration impossible : ${err.message}`
          : 'Restauration impossible : erreur inconnue.',
      )
    } finally {
      setRestoringId(null)
    }
  }

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Archives</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des archives...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Archives</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les archives</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void fetchAll()}>
          Réessayer
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Archives</h2>
        <p className="text-sm text-muted-foreground">
          Cours fermés et décisions déjà validées
        </p>
      </div>

      {actionError && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
              <p className="text-sm">{actionError}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setActionError(null)}>
              Fermer
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ── Cours archivés ─────────────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-medium">
            Cours archivés{' '}
            <span className="text-sm font-normal text-muted-foreground">
              ({courses.length})
            </span>
          </h3>
          {courses.length > 0 && (
            <div className="relative min-w-[220px]">
              <Search
                className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <Input
                placeholder="Rechercher un cours archivé..."
                aria-label="Rechercher un cours archivé"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
          )}
        </div>

        {filteredCourses.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <Archive className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
              <p className="font-medium text-muted-foreground">
                {courses.length === 0
                  ? 'Aucun cours archivé'
                  : 'Aucun cours ne correspond à la recherche'}
              </p>
              <p className="max-w-xs text-sm text-muted-foreground/70">
                {courses.length === 0
                  ? 'Les cours fermés depuis le catalogue apparaîtront ici.'
                  : 'Essayez un autre terme de recherche.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      Titre
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      Catégorie
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      Inscrits
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                      Année
                    </th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">
                      Dernière modification
                    </th>
                    {isAdmin && (
                      <th className="px-4 py-3 text-right font-medium text-muted-foreground">
                        Actions
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {visibleCourses.map((course) => (
                    <tr
                      key={course.id}
                      className="border-b border-border last:border-0 hover:bg-muted/50"
                    >
                      <td className="px-4 py-3 font-medium">{course.title}</td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {course.category ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {course.enrolled_count}
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                        {course.year ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {formatDate(course.updated_at)}
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            disabled={restoringId === course.id}
                            onClick={() => void handleRestore(course)}
                          >
                            <RotateCcw className="mr-2 h-4 w-4" aria-hidden="true" />
                            {restoringId === course.id ? 'Restauration...' : 'Restaurer'}
                          </Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {hiddenCoursesCount > 0 && (
              <div className="border-t border-border p-3 text-center">
                <Button variant="outline" size="sm" onClick={() => setShowAllCourses(true)}>
                  Afficher les {hiddenCoursesCount} cours restants
                </Button>
              </div>
            )}
          </Card>
        )}
      </section>

      {/* ── Recommandations traitées ───────────────────────────────────── */}
      <section className="space-y-3">
        <h3 className="font-medium">
          Recommandations validées{' '}
          <span className="text-sm font-normal text-muted-foreground">
            ({recommendations.length}
            {recommendationsTruncated ? ' affichées' : ''})
          </span>
        </h3>
        {recommendationsTruncated && (
          <p className="text-sm text-muted-foreground">
            Affichage limité aux {RECOMMENDATIONS_LIMIT} recommandations les mieux
            notées.
          </p>
        )}

        {recommendations.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
              <ClipboardCheck
                className="h-10 w-10 text-muted-foreground/40"
                aria-hidden="true"
              />
              <p className="font-medium text-muted-foreground">
                Aucune recommandation validée
              </p>
              <p className="max-w-xs text-sm text-muted-foreground/70">
                Les recommandations approuvées depuis « À fermer » ou « À créer »
                seront listées ici.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <ul className="divide-y divide-border">
              {recommendations.map((rec) => (
                <li key={rec.id} className="flex flex-wrap items-start gap-3 p-4">
                  <TypeBadge type={rec.recommendation_type} />
                  <p className="min-w-[200px] flex-1 text-sm">
                    {rec.rationale ?? 'Aucun motif enregistré.'}
                  </p>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    Score {rec.score}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {formatDate(rec.created_at)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </section>
    </div>
  )
}
