import { useEffect, useState, useMemo } from 'react'
import {
  Search,
  Plus,
  Pencil,
  Archive,
  RotateCcw,
  AlertTriangle,
  Files,
} from 'lucide-react'
import { api, ApiError, type Course } from '@/lib/api'
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

interface CourseForm {
  title: string
  category: string
  year: number
  hours_estimated: number | null
  notes: string
}

const emptyForm: CourseForm = {
  title: '',
  category: '',
  year: new Date().getFullYear(),
  hours_estimated: null,
  notes: '',
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === 'active'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        isActive
          ? 'bg-green-500/15 text-green-400'
          : 'bg-gray-500/15 text-gray-400',
      )}
    >
      {isActive ? 'Actif' : 'Archivé'}
    </span>
  )
}

function PopularityBar({ score }: { score: number }) {
  const hue = Math.round((score / 100) * 120)
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-20 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${score}%`,
            backgroundColor: `hsl(${hue}, 70%, 45%)`,
          }}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">{score}</span>
    </div>
  )
}

function CourseModal({
  open,
  onOpenChange,
  course,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  course: Course | null
  onSave: (data: CourseForm) => Promise<void>
}) {
  const [form, setForm] = useState<CourseForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const isEdit = course !== null

  useEffect(() => {
    if (open) {
      setForm(
        course
          ? {
              title: course.title,
              category: course.category,
              year: course.year,
              hours_estimated: course.hours_estimated,
              notes: course.notes ?? '',
            }
          : emptyForm,
      )
    }
  }, [open, course])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSave(form)
      onOpenChange(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Modifier le cours' : 'Nouveau cours'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Modifiez les informations du cours ci-dessous.'
              : 'Remplissez les informations pour ajouter un nouveau cours au catalogue.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="course-title">Titre</Label>
            <Input
              id="course-title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="course-category">Catégorie</Label>
            <Input
              id="course-category"
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="course-year">Année</Label>
              <Input
                id="course-year"
                type="number"
                min={2000}
                max={2099}
                value={form.year}
                onChange={(e) => setForm({ ...form, year: Number(e.target.value) })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="course-hours">Heures estimées</Label>
              <Input
                id="course-hours"
                type="number"
                min={0}
                placeholder="—"
                value={form.hours_estimated ?? ''}
                onChange={(e) =>
                  setForm({
                    ...form,
                    hours_estimated: e.target.value ? Number(e.target.value) : null,
                  })
                }
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="course-notes">Notes</Label>
            <textarea
              id="course-notes"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Annuler
              </Button>
            </DialogClose>
            <Button type="submit" disabled={saving}>
              {saving ? 'Enregistrement...' : isEdit ? 'Enregistrer' : 'Créer'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export function CoursesPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [courses, setCourses] = useState<Course[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [yearFilter, setYearFilter] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingCourse, setEditingCourse] = useState<Course | null>(null)

  const fetchCourses = async () => {
    setLoadState('loading')
    try {
      const data = await api.get<Course[]>('/courses')
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

  const categories = useMemo(() => {
    const set = new Set(courses.map((c) => c.category))
    return Array.from(set).sort()
  }, [courses])

  const years = useMemo(() => {
    const set = new Set(courses.map((c) => c.year))
    return Array.from(set).sort((a, b) => b - a)
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
    if (categoryFilter) {
      result = result.filter((c) => c.category === categoryFilter)
    }
    if (yearFilter) {
      result = result.filter((c) => c.year === Number(yearFilter))
    }
    return result
  }, [courses, search, statusFilter, categoryFilter, yearFilter])

  const openCreate = () => {
    setEditingCourse(null)
    setDialogOpen(true)
  }

  const openEdit = (course: Course) => {
    setEditingCourse(course)
    setDialogOpen(true)
  }

  const handleSave = async (form: CourseForm) => {
    if (editingCourse) {
      await api.patch(`/courses/${editingCourse.id}`, form)
    } else {
      await api.post('/courses', form)
    }
    await fetchCourses()
  }

  const handleArchive = async (course: Course) => {
    if (course.status === 'active') {
      await api.post(`/courses/${course.id}/archive`)
    } else {
      await api.post(`/courses/${course.id}/restore`)
    }
    await fetchCourses()
  }

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Cours SCAP</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des cours...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Cours SCAP</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les cours</p>
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
          <h2 className="text-xl font-semibold">Cours SCAP</h2>
          <p className="text-sm text-muted-foreground">
            Gérez les cours du catalogue SCAP
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nouveau cours
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
              <option value="active">Actif</option>
              <option value="archived">Archivé</option>
            </select>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Toutes les catégories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
            <select
              value={yearFilter}
              onChange={(e) => setYearFilter(e.target.value)}
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="">Toutes les années</option>
              {years.map((y) => (
                <option key={y} value={String(y)}>
                  {y}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Files className="h-10 w-10 text-muted-foreground/40" />
            <p className="font-medium text-muted-foreground">
              {courses.length === 0
                ? 'Aucun cours dans le catalogue'
                : 'Aucun cours ne correspond aux filtres'}
            </p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              {courses.length === 0
                ? 'Créez votre premier cours avec le bouton « Nouveau cours ».'
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
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Catégorie</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Statut</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Inscrits</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Abandons</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Score popularité</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Année</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((course) => (
                  <tr key={course.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium">{course.title}</td>
                    <td className="px-4 py-3 text-muted-foreground">{course.category}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={course.status} />
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{course.enrolled_count}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-destructive">
                      {course.dropout_count}
                    </td>
                    <td className="px-4 py-3">
                      <PopularityBar score={course.popularity_score} />
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                      {course.year}
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
                          <Button
                            variant="ghost"
                            size="icon"
                            title={course.status === 'active' ? 'Archiver' : 'Restaurer'}
                            onClick={() => void handleArchive(course)}
                          >
                            {course.status === 'active' ? (
                              <Archive className="h-4 w-4" />
                            ) : (
                              <RotateCcw className="h-4 w-4" />
                            )}
                          </Button>
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

      <CourseModal
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        course={editingCourse}
        onSave={handleSave}
      />
    </div>
  )
}
