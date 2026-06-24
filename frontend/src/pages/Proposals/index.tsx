import { useEffect, useState, useMemo } from 'react'
import {
  Search,
  Plus,
  Pencil,
  AlertTriangle,
  Lightbulb,
} from 'lucide-react'
import { api, ApiError, type CourseProposal } from '@/lib/api'
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

interface CourseProposalForm {
  title: string
  description: string
  hours_estimated: number | null
  certification_suggestions: string
  based_on: string
  status: CourseProposal['status']
}

const emptyForm: CourseProposalForm = {
  title: '',
  description: '',
  hours_estimated: null,
  certification_suggestions: '',
  based_on: '',
  status: 'draft',
}

const STATUS_LABELS: Record<CourseProposal['status'], string> = {
  draft: 'Brouillon',
  proposed: 'Proposé',
  exported: 'Exporté',
}

const STATUS_COLORS: Record<CourseProposal['status'], string> = {
  draft: 'bg-gray-500/15 text-gray-400',
  proposed: 'bg-blue-500/15 text-blue-400',
  exported: 'bg-green-500/15 text-green-400',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function ProposalModal({
  open,
  onOpenChange,
  proposal,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  proposal: CourseProposal | null
  onSave: (data: CourseProposalForm) => Promise<void>
}) {
  const [form, setForm] = useState<CourseProposalForm>(emptyForm)
  const [saving, setSaving] = useState(false)
  const isEdit = proposal !== null

  useEffect(() => {
    if (open) {
      setForm(
        proposal
          ? {
              title: proposal.title,
              description: proposal.description ?? '',
              hours_estimated: proposal.hours_estimated,
              certification_suggestions: proposal.certification_suggestions ?? '',
              based_on: proposal.based_on ?? '',
              status: proposal.status,
            }
          : emptyForm,
      )
    }
  }, [open, proposal])

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
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? "Modifier la proposition" : "Nouvelle proposition"}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? "Modifiez les informations de la proposition ci-dessous."
              : "Créez une nouvelle proposition de cours."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="prop-title">Titre</Label>
            <Input
              id="prop-title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="prop-description">Description</Label>
            <textarea
              id="prop-description"
              className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="prop-hours">Heures estimées</Label>
              <Input
                id="prop-hours"
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
            <div className="space-y-2">
              <Label htmlFor="prop-status">Statut</Label>
              <select
                id="prop-status"
                value={form.status}
                onChange={(e) =>
                  setForm({ ...form, status: e.target.value as CourseProposal['status'] })
                }
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="draft">Brouillon</option>
                <option value="proposed">Proposé</option>
                <option value="exported">Exporté</option>
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="prop-cert">Pistes certification</Label>
            <textarea
              id="prop-cert"
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={form.certification_suggestions}
              onChange={(e) =>
                setForm({ ...form, certification_suggestions: e.target.value })
              }
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="prop-based">Basé sur</Label>
            <Input
              id="prop-based"
              value={form.based_on}
              onChange={(e) => setForm({ ...form, based_on: e.target.value })}
              placeholder="Ex: veille marché, analyse tendances..."
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

export function ProposalsPage() {
  const [proposals, setProposals] = useState<CourseProposal[]>([])
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingProposal, setEditingProposal] = useState<CourseProposal | null>(null)

  const fetchProposals = async () => {
    setLoadState('loading')
    try {
      const data = await api.get<CourseProposal[]>('/proposals')
      setProposals(data)
      setLoadState('ok')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur inconnue'
      setErrorMsg(msg)
      setLoadState('error')
    }
  }

  useEffect(() => {
    void fetchProposals()
  }, [])

  const filtered = useMemo(() => {
    let result = proposals
    if (search) {
      const q = search.toLowerCase()
      result = result.filter((p) => p.title.toLowerCase().includes(q))
    }
    if (statusFilter) {
      result = result.filter((p) => p.status === statusFilter)
    }
    return result
  }, [proposals, search, statusFilter])

  const openCreate = () => {
    setEditingProposal(null)
    setDialogOpen(true)
  }

  const openEdit = (proposal: CourseProposal) => {
    setEditingProposal(proposal)
    setDialogOpen(true)
  }

  const handleSave = async (form: CourseProposalForm) => {
    if (editingProposal) {
      await api.patch(`/proposals/${editingProposal.id}`, form)
    } else {
      await api.post('/proposals', form)
    }
    await fetchProposals()
  }

  if (loadState === 'loading') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Propositions</h2>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm">Chargement des propositions...</span>
        </div>
      </div>
    )
  }

  if (loadState === 'error') {
    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Propositions</h2>
        <Card className="border-destructive/50">
          <CardContent className="flex items-center gap-3 p-6">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            <div>
              <p className="font-medium">Impossible de charger les propositions</p>
              <p className="text-sm text-muted-foreground">{errorMsg}</p>
            </div>
          </CardContent>
        </Card>
        <Button variant="outline" onClick={() => void fetchProposals()}>
          Réessayer
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Propositions</h2>
          <p className="text-sm text-muted-foreground">
            Nouveaux cours proposés automatiquement
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Nouvelle proposition
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
              <option value="draft">Brouillon</option>
              <option value="proposed">Proposé</option>
              <option value="exported">Exporté</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Lightbulb className="h-10 w-10 text-muted-foreground/40" />
            <p className="font-medium text-muted-foreground">
              {proposals.length === 0
                ? 'Aucune proposition'
                : 'Aucune proposition ne correspond aux filtres'}
            </p>
            <p className="max-w-xs text-sm text-muted-foreground/70">
              {proposals.length === 0
                ? 'Créez votre première proposition avec le bouton « Nouvelle proposition ».'
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
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Description</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Heures estimées</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Pistes certification</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Statut</th>
                  <th className="px-4 py-3 text-left font-medium text-muted-foreground">Créé le</th>
                  <th className="px-4 py-3 text-right font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((proposal) => (
                  <tr
                    key={proposal.id}
                    className="border-b border-border last:border-0 hover:bg-muted/50"
                  >
                    <td className="px-4 py-3 font-medium">{proposal.title}</td>
                    <td className="max-w-[200px] truncate px-4 py-3 text-muted-foreground">
                      {proposal.description ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-muted-foreground">
                      {proposal.hours_estimated ?? '—'}
                    </td>
                    <td className="max-w-[180px] truncate px-4 py-3 text-muted-foreground">
                      {proposal.certification_suggestions ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                          STATUS_COLORS[proposal.status],
                        )}
                      >
                        {STATUS_LABELS[proposal.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {formatDate(proposal.created_at)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Modifier"
                        onClick={() => openEdit(proposal)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <ProposalModal
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        proposal={editingProposal}
        onSave={handleSave}
      />
    </div>
  )
}
