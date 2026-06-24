import { useEffect, useState, useMemo } from 'react'
import {
  Search,
  Plus,
  Pencil,
  Trash2,
  ExternalLink,
  AlertTriangle,
  TrendingUp,
} from 'lucide-react'
import { api, ApiError, type MarketCourse } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

type LoadState = 'loading' | 'ok' | 'error'

interface MarketCourseForm {
  title: string
  school: string
  source_url: string
  summary: string
  relevance_score: number | null
  why_it_works: string
  status: MarketCourse['status']
}

const emptyForm: MarketCourseForm = {
  title: '',
  school: '',
  source_url: '',
  summary: '',
  relevance_score: null,
  why_it_works: '',
  status: 'candidate',
}

const STATUS_LABELS: Record<MarketCourse['status'], string> = {
  candidate: 'Candidat',
  reviewed: 'Examiné',
  adopted: 'Adopté',
  rejected: 'Rejeté',
}

const STATUS_COLORS: Record<MarketCourse['status'], string> = {
  candidate: 'bg-blue-500/15 text-blue-400',
  reviewed: 'bg-amber-500/15 text-amber-400',
  adopted: 'bg-green-500/15 text-green-400',
  rejected: 'bg-red-500/15 text-red-400',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function RelevanceBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-muted-foreground">—</span>
  const color =
    score > 0.7
      ? 'bg-green-500/15 text-green-400'
      : score > 0.4
        ? 'bg-amber-500/15 text-amber-400'
        : 'bg-red-500/15 text-red-400'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        color,
      )}
    >
      {score.toFixed(2)}
    </span>
  )
}

function MarketCourseModal({
  open,
  onOpenChange,
  course,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  course: MarketCourse | null
  onSave: (data: MarketCourseForm) => Promise<void>
}) {
  const [form, setForm] = useState<MarketCourseForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const isEdit = course !== null

  useEffect(() => {
    if (open) {
      setForm(
        course
          ? {
              title: course.title,
              school: course.school ?? '',
              source_url: course.source_url ?? '',
              summary: course.summary ?? '',
              relevance_score: course.relevance_score,
              why_it_works: course.why_it_works ?? '',
              status: course.status,
            }
          : emptyForm,
      )
    }
  }, [open, course])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setErrorMsg(null)
    try {
      await onSave(form)
      onOpenChange(false)
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erreur d'enregistrement"
      setErrorMsg(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Modifier l'observation" : 'Ajouter une observation'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Modifiez les informations de l'observation ci-dessous."
              : 'Ajoutez un cours repéré sur le marché parisien.'}
          </DialogDescription>
        </DialogHeader>
        {errorMsg && (
          <div className="flex items-center gap-2 rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="mw-title">Titre</Label>
            <Input
              id="mw-title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mw-school">École</Label>
              <Input
                id="mw-school"
                value={form.school}
                onChange={(e) => setForm({ ...form, school: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mw-score">Score pertinence (0–1)</Label>
              <Input
                id="mw-score"
                type="number"
                min={0}
                max={1}
                step={0.01}
                placeholder="0.00"
              value={form.relevance_score !== null ? form.relevance_score : ''}
              onChange={(e) =>
                setForm({
                  ...form,
                  relevance_score: e.target.value ? Number(e.target.value) : null,
                })
              }
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="mw-url">URL source</Label>
            <Input
              id="mw-url"
              type="url"
              value={form.source_url}
              onChange={(e) => setForm({ ...form, source_url: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mw-summary">Résumé</Label>
            <textarea
              id="mw-summary"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={form.summary}
              onChange={(e) => setForm({ ...form, summary: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mw-why">Pourquoi ça marche</Label>
            <textarea
              id="mw-why"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={form.why_it_works}
              onChange={(e) => setForm({ ...form, why_it_works: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mw-status">Statut</Label>
            <select
              id="mw-status"
              value={form.status}
              onChange={(e) =>
                setForm({ ...form, status: e.target.value as MarketCourse['status'] })
              }
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="candidate">Candidat</option>
              <option value="reviewed">Examiné</option>
              <option value="adopted">Adopté</option>
              <option value="rejected">Rejeté</option>
            </select>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Annuler
              </Button>
            </DialogClose>
            <Button type="submit" disabled={saving}>
              {saving ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Ajouter'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function MarketWatchPage() {
  const { user } = useAuth()
  const [courses, setCourses] = useState<MarketCourse[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [schoolFilter, setSchoolFilter] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCourse, setEditingCourse] = useState<MarketCourse | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const isAdmin = user?.role === 'admin'

  const fetchCourses = async () => {
    setLoadState('loading')
    try {
      const data = await api.get<MarketCourse[]>('/market-courses')
      setCourses(data)
      setLoadState('ok')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setLoadState('error')
    }
  }

  useEffect(() => {
    void fetchCourses()
  }, [])

  const schools = useMemo(() => {
    const set = new Set(courses.map((c) => c.school).filter((s): s is string => s !== null))
    return Array.from(set).sort()
  }, [courses])

  const filtered = useMemo(() => {
    let result = courses
    if (search) {
      const q = search.toLowerCase()
      result = result.filter((c) => c.title.toLowerCase().includes(q))
    }
    if (statusFilter) {
      result = result.filter((c) => c.status === statusFilter)
    }
    if (schoolFilter) {
      result = result.filter((c) => c.school === schoolFilter)
    }
    return result
  }, [courses, search, statusFilter, schoolFilter])

  const openCreate = () => {
    setEditingCourse(null)
    setDialogOpen(true)
  }

  const openEdit = (course: MarketCourse) => {
    setEditingCourse(course)
    setDialogOpen(true)
  }

  const handleSave = async (form: MarketCourseForm) => {
    try {
      if (editingCourse) {
        await api.patch(`/market-courses/${editingCourse.id}`, form)
      } else {
        await api.post('/market-courses', form)
      }
      await fetchCourses()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      throw err
    }
  }

  const handleDelete = async (id: number) => {
    await api.delete(`/market-courses/${id}`)
    setDeleteConfirm(null)
    await fetchCourses()
  }

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Veille marché</h2>
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
        <h2 className="text-xl font-semibold">Veille marché</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les données</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void fetchCourses()}>
          Réessayer
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Veille marché</h2>
          <p className="text-sm text-muted-foreground">
            Cours proposés par d'autres écoles parisiennes
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Ajouter
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Rechercher par titre..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Tous les statuts</option>
              <option value="candidate">Candidat</option>
              <option value="reviewed">Examiné</option>
              <option value="adopted">Adopté</option>
              <option value="rejected">Rejeté</option>
            </select>
            <select
              value={schoolFilter}
              onChange={(e) => setSchoolFilter(e.target.value)}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Toutes les écoles</option>
              {schools.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <TrendingUp className="h-10 w-10 text-muted-foreground/40" />
            <p className="font-medium text-muted-foreground">
              {courses.length === 0
                ? 'Aucune observation'
                : 'Aucune observation ne correspond aux filtres'}
            </p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              {courses.length === 0
                ? 'Ajoutez votre première observation avec le bouton « Ajouter ».'
                : 'Essayez de modifier vos critères de recherche.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Titre</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">École</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Score pertinence</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Statut</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Source</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Découvert le</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((course) => (
                  <tr
                    key={course.id}
                    className="border-b border-border last:border-0 hover:bg-muted/50"
                  >
                    <td className="px-4 py-3 font-medium">{course.title}</td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {course.school ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <RelevanceBadge score={course.relevance_score} />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                          STATUS_COLORS[course.status],
                        )}
                      >
                        {STATUS_LABELS[course.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {course.source_url ? (
                        <a
                          href={course.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          <span className="max-w-[140px] truncate">
                            {course.source_url.replace(/^https?:\/\//, '').replace(/\/.*$/, '')}
                          </span>
                          <ExternalLink className="h-3 w-3 shrink-0" />
                        </a>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDate(course.discovered_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Modifier"
                          onClick={() => openEdit(course)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        {isAdmin && (
                          <>
                            {deleteConfirm === course.id ? (
                              <div className="flex items-center gap-1">
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() => void handleDelete(course.id)}
                                >
                                  Confirmer
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setDeleteConfirm(null)}
                                >
                                  Annuler
                                </Button>
                              </div>
                            ) : (
                              <Button
                                variant="ghost"
                                size="icon"
                                title="Supprimer"
                                onClick={() => setDeleteConfirm(course.id)}
                              >
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <MarketCourseModal
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        course={editingCourse}
        onSave={handleSave}
      />
    </div>
  )
}
