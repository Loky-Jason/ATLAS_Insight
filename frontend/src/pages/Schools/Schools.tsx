import { useEffect, useState } from 'react'
import { Plus, Pencil, Trash2, Play, Eye, Search, GraduationCap, AlertTriangle, CheckCircle2, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
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

interface ScraperConfig {
  mode: 'sitemap' | 'list'
  sitemap_url: string
  url_pattern: string
  list_url: string
  course_link_selector: string
  use_jsonld: boolean
  selectors: Record<string, string>
}

const emptyConfig: ScraperConfig = {
  mode: 'sitemap',
  sitemap_url: 'auto',
  url_pattern: '/formation/',
  list_url: '',
  course_link_selector: 'a',
  use_jsonld: true,
  selectors: {
    title: '',
    description: '',
    duration: '',
    price: '',
    category: '',
    format: '',
    certification: '',
  },
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
  strategies,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  school: SchoolRegistry | null
  strategies: string[]
  onSave: (data: SchoolRegistryCreate) => Promise<void>
}) {
  const [form, setForm] = useState<SchoolRegistryCreate>(emptyForm)
  const [cfg, setCfg] = useState<ScraperConfig>(emptyConfig)
  const [saving, setSaving] = useState(false)
  const [showSelectors, setShowSelectors] = useState(false)
  const [connError, setConnError] = useState<string | null>(null)

  const isGeneric = form.scraper_strategy === 'generic'

  useEffect(() => {
    if (open) {
      const base = school
        ? {
            name: school.name,
            url: school.url,
            scraper_strategy: school.scraper_strategy,
            active: school.active,
            scan_interval: school.scan_interval,
          }
        : emptyForm
      setForm(base)
      setCfg(
        school?.config
          ? { ...emptyConfig, ...school.config, selectors: { ...emptyConfig.selectors, ...((school.config as Record<string, unknown>).selectors as Record<string, string> || {}) } }
          : emptyConfig,
      )
      setConnError(null)
    }
  }, [open, school])

  const updateCfg = (patch: Partial<ScraperConfig>) => {
    const next = { ...cfg, ...patch }
    setCfg(next)
    setForm({ ...form, config: next as unknown as Record<string, unknown> })
  }

  const updateSelector = (key: string, val: string) => {
    const next = { ...cfg, selectors: { ...cfg.selectors, [key]: val } }
    setCfg(next)
    setForm({ ...form, config: next as unknown as Record<string, unknown> })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setConnError(null)
    setSaving(true)
    try {
      const payload: SchoolRegistryCreate = isGeneric
        ? { ...form, config: cfg as unknown as Record<string, unknown> }
        : { name: form.name, url: form.url, scraper_strategy: form.scraper_strategy ?? 'stub', active: form.active ?? true, scan_interval: form.scan_interval ?? 1440 }
      const testResult = await schoolsApi.testConnection(payload.url)
      if (!testResult.success) {
        setConnError(testResult.error_msg || 'Connexion échouée.')
        return
      }
      await onSave(payload)
      onOpenChange(false)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inattendue'
      setConnError(msg)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
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
                {strategies.map((s) => (
                  <option key={s} value={s}>
                    {s === 'stub' ? 'Démo' : s}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="school-interval">Intervalle (min)</Label>
              <Input id="school-interval" type="number" min={1} value={form.scan_interval} onChange={(e) => setForm({ ...form, scan_interval: Number(e.target.value) })} />
            </div>
          </div>

          {isGeneric && (
            <div className="space-y-4 rounded-lg border border-border/50 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Configuration scraper générique</p>

              <div className="space-y-2">
                <Label htmlFor="scraper-mode">Mode</Label>
                <select
                  id="scraper-mode"
                  value={cfg.mode}
                  onChange={(e) => updateCfg({ mode: e.target.value as 'sitemap' | 'list' })}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="sitemap">Sitemap (auto-détection)</option>
                  <option value="list">Page liste</option>
                </select>
              </div>

              {cfg.mode === 'sitemap' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="sitemap-url">URL du sitemap</Label>
                    <Input id="sitemap-url" value={cfg.sitemap_url} onChange={(e) => updateCfg({ sitemap_url: e.target.value })} placeholder="auto (détection automatique)" />
                    <p className="text-xs text-muted-foreground">Laissez « auto » pour détecter automatiquement /sitemap.xml</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="url-pattern">Filtre URL</Label>
                    <Input id="url-pattern" value={cfg.url_pattern} onChange={(e) => updateCfg({ url_pattern: e.target.value })} placeholder="/formation/" />
                    <p className="text-xs text-muted-foreground">Ne garder que les URLs contenant ce pattern</p>
                  </div>
                </>
              )}

              {cfg.mode === 'list' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="list-url">URL de la page liste</Label>
                    <Input id="list-url" value={cfg.list_url} onChange={(e) => updateCfg({ list_url: e.target.value })} placeholder="https://..." />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="link-selector">Sélecteur lien cours</Label>
                    <Input id="link-selector" value={cfg.course_link_selector} onChange={(e) => updateCfg({ course_link_selector: e.target.value })} placeholder="a.card" />
                    <p className="text-xs text-muted-foreground">Sélecteur CSS pour les liens vers chaque cours</p>
                  </div>
                </>
              )}

              <div className="flex items-center gap-2">
                <input
                  id="use-jsonld"
                  type="checkbox"
                  checked={cfg.use_jsonld}
                  onChange={(e) => updateCfg({ use_jsonld: e.target.checked })}
                  className="h-4 w-4 rounded border-border"
                />
                <Label htmlFor="use-jsonld">Extraire JSON-LD automatiquement</Label>
              </div>

              <div className="border-t border-border/50 pt-2">
                <button type="button" onClick={() => setShowSelectors(!showSelectors)} className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
                  {showSelectors ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                  Sélecteurs CSS (fallback si JSON-LD insuffisant)
                </button>
                {showSelectors && (
                  <div className="mt-3 grid grid-cols-2 gap-3">
                    {Object.keys(emptyConfig.selectors).map((key) => (
                      <div key={key} className="space-y-1">
                        <Label htmlFor={`sel-${key}`} className="text-xs capitalize">{key}</Label>
                        <Input id={`sel-${key}`} value={cfg.selectors[key] || ''} onChange={(e) => updateSelector(key, e.target.value)} placeholder={`selecteur ${key}`} className="h-8 text-xs" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

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
          {connError && (
            <div className="flex items-center gap-3 rounded-md border border-destructive/50 bg-destructive/5 p-3">
              <AlertTriangle className="h-5 w-5 shrink-0 text-destructive" />
              <p className="text-sm text-destructive">{connError}</p>
            </div>
          )}
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
  const [strategies, setStrategies] = useState<string[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [diffDialogOpen, setDiffDialogOpen] = useState(false)
  const [editingSchool, setEditingSchool] = useState<SchoolRegistry | null>(null)
  const [diffSchool, setDiffSchool] = useState<SchoolRegistry | null>(null)
  const [scanningIds, setScanningIds] = useState<Set<number>>(new Set())
  const [scanMsg, setScanMsg] = useState<{ text: string; variant: 'success' | 'error' } | null>(null)

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
    schoolsApi
      .listStrategies()
      .then(setStrategies)
      .catch(() => setStrategies([]))
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
      const result = await schoolsApi.scan(school.id)
      if (result.status === 'error') {
        setScanMsg({ text: result.error_msg || 'Échec du scan', variant: 'error' })
      } else {
        setScanMsg({ text: `Scan terminé : ${result.new} nouveau(x), ${result.modified} modifié(s)`, variant: 'success' })
        setErrorMsg(null)
      }
      await fetchSchools()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setScanMsg({ text: msg, variant: 'error' })
      await fetchSchools()
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

      {scanMsg && (
        <Card className={scanMsg.variant === 'error' ? 'border-destructive/50' : 'border-emerald-500/50'}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              {scanMsg.variant === 'error' ? (
                <AlertTriangle className="h-5 w-5 text-destructive" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              )}
              <p className={cn("text-sm", scanMsg.variant === 'error' ? "text-destructive" : "text-emerald-600")}>{scanMsg.text}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setScanMsg(null)}>Fermer</Button>
          </CardContent>
        </Card>
      )}

      {errorMsg && !scanMsg && (
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

      <SchoolFormDialog open={dialogOpen} onOpenChange={setDialogOpen} school={editingSchool} strategies={strategies} onSave={handleSave} />
      <DiffDialog open={diffDialogOpen} onOpenChange={setDiffDialogOpen} school={diffSchool} />
    </div>
  )
}
