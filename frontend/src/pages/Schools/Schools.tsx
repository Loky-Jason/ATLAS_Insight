import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Play, Eye, Search, GraduationCap, AlertTriangle, RefreshCw } from 'lucide-react'
import { ApiError } from '@/lib/api'
import { schoolsApi, type SchoolRegistry, type SchoolRegistryCreate, type ScanDiff } from '@/lib/api'
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

const emptyForm: SchoolRegistryCreate = {
  name: '',
  url: '',
  scraper_strategy: 'stub',
  active: true,
  scan_interval: 1440,
}

function StrategyBadge({ strategy }: { strategy: string }) {
  const isStub = strategy === 'stub'
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        isStub ? 'bg-yellow-500/15 text-yellow-400' : 'bg-blue-500/15 text-blue-400',
      )}
    >
      {isStub ? 'Démo' : strategy}
    </span>
  )
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        active ? 'bg-green-500/15 text-green-400' : 'bg-gray-500/15 text-gray-400',
      )}
    >
      {active ? 'Actif' : 'Inactif'}
    </span>
  )
}

function SchoolFormDialog({
  open,
  onOpenChange,
  school,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  school: SchoolRegistry | null
  onSave: (data: SchoolRegistryCreate) => Promise<void>
}) {
  const [form, setForm] = useState<SchoolRegistryCreate>(emptyForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(
        school
          ? {
              name: school.name,
              url: school.url,
              scraper_strategy: school.scraper_strategy,
              active: school.active,
              scan_interval: school.scan_interval,
            }
          : emptyForm,
      )
    }
  }, [open, school])

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
          <DialogTitle>{school ? 'Modifier l\'école' : 'Ajouter une école'}</DialogTitle>
          <DialogDescription>
            {school
              ? 'Modifiez les paramètres de l\'école suivie.'
              : 'Ajoutez une nouvelle école à surveiller.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="school-name">Nom</Label>
            <Input id="school-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="school-url">URL</Label>
            <Input id="school-url" type="url" value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} required />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="school-strategy">Stratégie</Label>
              <select
                id="school-strategy"
                value={form.scraper_strategy}
                onChange={(e) => setForm({ ...form, scraper_strategy: e.target.value })}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="stub">Démo</option>
                <option value="SCAP">SCAP</option>
                <option value="ORSYS">ORSYS</option>
                <option value="Cegos">Cegos</option>
                <option value="Demos">Demos</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="school-interval">Intervalle (min)</Label>
              <Input id="school-interval" type="number" min={1} value={form.scan_interval} onChange={(e) => setForm({ ...form, scan_interval: Number(e.target.value) })} />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="school-active"
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
              className="h-4 w-4 rounded border-border"
            />
            <Label htmlFor="school-active">Active</Label>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">Annuler</Button>
            </DialogClose>
            <Button type="submit" disabled={saving}>
              {saving ? 'Enregistrement...' : school ? 'Enregistrer' : 'Ajouter'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DiffDialog({
  open,
  onOpenChange,
  school,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  school: SchoolRegistry | null
}) {
  const [diff, setDiff] = useState<ScanDiff | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && school) {
      setLoading(true)
      setError(null)
      schoolsApi.diff(school.id)
        .then(setDiff)
        .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur inconnue'))
        .finally(() => setLoading(false))
    }
  }, [open, school])

  const total = diff ? diff.new_courses.length + diff.modified_courses.length + diff.removed_courses.length : 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Diff — {school?.name}</DialogTitle>
          <DialogDescription>
            Modifications détectées lors du dernier scan
          </DialogDescription>
        </DialogHeader>
        {loading && (
          <div className="flex items-center gap-2 py-8 text-muted-foreground">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span className="text-sm">Chargement du diff...</span>
          </div>
        )}
        {error && (
          <div className="flex items-center gap-3 rounded-md border border-destructive/50 p-4 text-sm">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <span>{error}</span>
          </div>
        )}
        {!loading && !error && diff && (
          <div className="space-y-6">
            {diff.scan_run && (
              <div className="grid grid-cols-4 gap-4">
                <div className="rounded-lg bg-muted/30 p-3 text-center">
                  <div className="text-2xl font-bold">{diff.scan_run.courses_found}</div>
                  <div className="text-xs text-muted-foreground">Cours trouvés</div>
                </div>
                <div className="rounded-lg bg-green-500/10 p-3 text-center">
                  <div className="text-2xl font-bold text-green-400">{diff.new_courses.length}</div>
                  <div className="text-xs text-muted-foreground">Nouveaux</div>
                </div>
                <div className="rounded-lg bg-blue-500/10 p-3 text-center">
                  <div className="text-2xl font-bold text-blue-400">{diff.modified_courses.length}</div>
                  <div className="text-xs text-muted-foreground">Modifiés</div>
                </div>
                <div className="rounded-lg bg-red-500/10 p-3 text-center">
                  <div className="text-2xl font-bold text-red-400">{diff.removed_courses.length}</div>
                  <div className="text-xs text-muted-foreground">Supprimés</div>
                </div>
              </div>
            )}
            {total === 0 && <p className="text-sm text-muted-foreground py-4">Aucun changement détecté lors du dernier scan.</p>}
            {diff.new_courses.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-green-400">Nouveaux cours ({diff.new_courses.length})</h4>
                <div className="space-y-1">
                  {diff.new_courses.map((c) => (
                    <div key={c.id} className="rounded-md border border-border/50 px-3 py-2 text-sm">{c.title}</div>
                  ))}
                </div>
              </div>
            )}
            {diff.modified_courses.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-blue-400">Cours modifiés ({diff.modified_courses.length})</h4>
                <div className="space-y-1">
                  {diff.modified_courses.map((c) => (
                    <div key={c.id} className="rounded-md border border-border/50 px-3 py-2 text-sm">{c.title}</div>
                  ))}
                </div>
              </div>
            )}
            {diff.removed_courses.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-red-400">Cours supprimés ({diff.removed_courses.length})</h4>
                <div className="space-y-1">
                  {diff.removed_courses.map((c) => (
                    <div key={c.id} className="rounded-md border border-border/50 px-3 py-2 text-sm line-through text-muted-foreground">{c.title}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function SchoolsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [schools, setSchools] = useState<SchoolRegistry[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [diffDialogOpen, setDiffDialogOpen] = useState(false)
  const [editingSchool, setEditingSchool] = useState<SchoolRegistry | null>(null)
  const [diffSchool, setDiffSchool] = useState<SchoolRegistry | null>(null)
  const [scanningIds, setScanningIds] = useState<Set<number>>(new Set())

  const fetchSchools = async () => {
    setLoadState('loading')
    try {
      const data = await schoolsApi.list()
      setSchools(data)
      setLoadState('ok')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setLoadState('error')
    }
  }

  useEffect(() => {
    void fetchSchools()
  }, [])

  const filtered = search
    ? schools.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()))
    : schools

  const openCreate = () => {
    setEditingSchool(null)
    setDialogOpen(true)
  }

  const openEdit = (school: SchoolRegistry) => {
    setEditingSchool(school)
    setDialogOpen(true)
  }

  const openDiff = (school: SchoolRegistry) => {
    setDiffSchool(school)
    setDiffDialogOpen(true)
  }

  const handleSave = async (form: SchoolRegistryCreate) => {
    if (editingSchool) {
      await schoolsApi.update(editingSchool.id, form)
    } else {
      await schoolsApi.create(form)
    }
    await fetchSchools()
  }

  const handleDelete = async (school: SchoolRegistry) => {
    if (!confirm(`Supprimer l'école « ${school.name} » ? Cette action est irréversible.`)) return
    try {
      await schoolsApi.delete(school.id)
      await fetchSchools()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
    }
  }

  const handleScan = async (school: SchoolRegistry) => {
    setScanningIds((prev) => new Set(prev).add(school.id))
    try {
      await schoolsApi.scan(school.id)
      await fetchSchools()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
    } finally {
      setScanningIds((prev) => { const next = new Set(prev); next.delete(school.id); return next })
    }
  }

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Écoles suivies</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des écoles...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Écoles suivies</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les écoles</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void fetchSchools()}>Réessayer</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Écoles suivies</h2>
          <p className="text-sm text-muted-foreground">
            Gérez les établissements surveillés par le système de veille
          </p>
        </div>
        {isAdmin && (
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Ajouter une école
          </Button>
        )}
      </div>

      {errorMsg && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <p className="text-sm text-destructive">{errorMsg}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setErrorMsg(null)}>Fermer</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Rechercher par nom..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <GraduationCap className="h-10 w-10 text-muted-foreground/40" aria-hidden="true" />
            <p className="font-medium text-muted-foreground">
              {schools.length === 0 ? 'Aucune école configurée' : 'Aucune école ne correspond'}
            </p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              {schools.length === 0
                ? 'Ajoutez une première école avec le bouton « Ajouter une école ».'
                : 'Essayez de modifier votre recherche.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Nom</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Stratégie</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Statut</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Dernier scan</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Intervalle</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((school) => (
                  <tr key={school.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="px-4 py-3 font-medium">{school.name}</td>
                    <td className="px-4 py-3"><StrategyBadge strategy={school.scraper_strategy} /></td>
                    <td className="px-4 py-3"><StatusBadge active={school.active} /></td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {school.last_scanned_at
                        ? new Date(school.last_scanned_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
                        : 'Jamais'}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                      {school.scan_interval} min
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="icon" title="Voir le diff" onClick={() => openDiff(school)}>
                          <Eye className="h-4 w-4" />
                        </Button>
                        {isAdmin && (
                          <>
                            <Button variant="ghost" size="icon" title="Lancer un scan" disabled={scanningIds.has(school.id)} onClick={() => void handleScan(school)}>
                              {scanningIds.has(school.id) ? (
                                <RefreshCw className="h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button variant="ghost" size="icon" title="Modifier" onClick={() => openEdit(school)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" title="Supprimer" className="hover:text-destructive" onClick={() => void handleDelete(school)}>
                              <Trash2 className="h-4 w-4" />
                            </Button>
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

      <SchoolFormDialog open={dialogOpen} onOpenChange={setDialogOpen} school={editingSchool} onSave={handleSave} />
      <DiffDialog open={diffDialogOpen} onOpenChange={setDiffDialogOpen} school={diffSchool} />
    </div>
  )
}
